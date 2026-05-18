import html
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.db import database
from app.db.settings_database import get_setting, set_setting

# Keep stock/watchlist/cache data in tech_screener.db, but route personal app
# settings such as API keys, SEC User-Agent, and UI preferences to personal_settings.db.
database.get_setting = get_setting
database.set_setting = set_setting

from app.db.database import (
    add_ticker,
    delete_ticker,
    init_db,
    insert_api_cache_rows,
    list_tickers,
)
from app.services.finnhub_service import refresh_finnhub_rows
from app.services.historical_data_service import rebuild_historical_fundamentals_for_ticker
from app.services.market_data_service import normalize_market_data_for_ticker
from app.services.peer_service import list_peer_comparison
from app.services.readiness_service import calculate_model_readiness_for_ticker
from app.services.sec_service import refresh_sec_rows
from app.services.watchlist_service import list_master_watchlist
from app.ui.main_window import (
    DARK_STYLE,
    DEFAULT_PEER_GROUPS,
    DEFAULT_SEC_USER_AGENT,
    MainWindow,
    apply_windows_dark_title_bar,
    make_metric_card,
    polish_table,
)

SEC_USER_AGENT_HELP = (
    "Format: Your Name your-email@example.com. "
    "Example: Jane Doe jane@example.com. "
    "Required by the SEC request policy; saved locally only."
)

def merged_peer_groups() -> list[str]:
    groups: list[str] = []
    for group in DEFAULT_PEER_GROUPS:
        if group not in groups:
            groups.append(group)
    return groups


def esc(value) -> str:
    return html.escape(str(value or ""))


def flag_class(value: str) -> str:
    value = (value or "").upper()
    if "GREEN" in value or "CONTINUE" in value or value.startswith("A"):
        return "good"
    if "YELLOW" in value or "NEEDS" in value or "WATCH" in value or "MIXED" in value or value.startswith("B"):
        return "watch"
    if "RED" in value or "PASS" in value or "WEAK" in value or value.startswith("D"):
        return "bad"
    if "PURPLE" in value or "SPEC" in value:
        return "spec"
    return "neutral"


class StreamlinedMainWindow(MainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.hide_top_nav_buttons()
        self.build_research_workflow_tabs()
        self.auto_fit_tab_labels()
        self.update_active_tab_header()
        self.refresh_auto_review_panels(self.current_ticker() or None)

    def hide_top_nav_buttons(self) -> None:
        for button in self.findChildren(QPushButton):
            if button.objectName() == "NavButton":
                button.hide()

    def auto_fit_tab_labels(self) -> None:
        for tabs in self.findChildren(QTabWidget):
            tabs.setUsesScrollButtons(False)
            tabs.setElideMode(Qt.ElideNone)
            tab_bar = tabs.tabBar()
            tab_bar.setExpanding(True)
            for index in range(tabs.count()):
                tab_bar.setTabToolTip(index, tabs.tabText(index))
            tab_bar.setStyleSheet(
                "QTabBar::tab { min-width: 0px; padding-left: 8px; padding-right: 8px; }"
            )

    def build_research_workflow_tabs(self) -> None:
        if not hasattr(self, "center_tabs"):
            return

        existing_tabs: dict[str, QWidget] = {}
        while self.center_tabs.count() > 0:
            name = self.center_tabs.tabText(0)
            widget = self.center_tabs.widget(0)
            existing_tabs[name] = widget
            self.center_tabs.removeTab(0)

        self.center_tabs.addTab(
            self.make_nested_tab_panel(
                "0. Idea Entry",
                "Pick the ticker to review. This is the screener and flag-review doorway, not a buy signal.",
                [
                    ("Overview", existing_tabs.get("Overview")),
                    ("Master Watchlist", existing_tabs.get("Master Watchlist")),
                    ("Data Quality", existing_tabs.get("Data Quality")),
                    ("Flag Review", self.make_auto_flag_review_panel()),
                ],
            ),
            "0. Idea Entry",
        )
        self.center_tabs.addTab(
            self.make_nested_tab_panel(
                "1. Data Check",
                "Make sure the local data is clean enough to compare this ticker against peers.",
                [
                    ("Data Check", self.make_auto_data_check_panel()),
                    ("Model Readiness", existing_tabs.get("Model Readiness")),
                    ("Historical Fundamentals", existing_tabs.get("Historical Fundamentals")),
                    ("Market Data", existing_tabs.get("Market Data")),
                    ("API Cache", existing_tabs.get("API Cache")),
                ],
            ),
            "1. Data Check",
        )
        self.center_tabs.addTab(self.make_auto_red_flag_panel(), "2. Red Flag Check")
        self.center_tabs.addTab(
            self.make_nested_tab_panel(
                "3. Peer Gate",
                "Check whether this flagged company is actually better than the other available choices.",
                [
                    ("Peer Check", self.make_auto_peer_check_panel()),
                    ("Peer Comparison", existing_tabs.get("Peer Comparison")),
                ],
            ),
            "3. Peer Gate",
        )
        self.center_tabs.addTab(
            self.make_notes_panel(
                "4. Risk / Reward vs ETF",
                "Placeholder for the next build: bear/base/bull values from history, peers, four valuation methods, and ETF comparison.",
                "Planned output:\n"
                "Bear downside:\n"
                "Base upside:\n"
                "Bull upside:\n"
                "ETF comparison:\n"
                "Risk/reward label:\n"
                "Key assumption:\n",
            ),
            "4. Risk / Reward vs ETF",
        )
        self.center_tabs.addTab(
            self.make_notes_panel(
                "5. Decision / Action",
                "Final screener handoff. This decides whether to pass, watch, or leave the app for real company research.",
                "Data Check:\n"
                "Red Flag Check:\n"
                "Peer Gate:\n"
                "Risk / Reward vs ETF:\n"
                "Decision: Pass / Watchlist / Deep Dive / Candidate Position\n"
                "Reason:\n"
                "Next action:\n",
            ),
            "5. Decision / Action",
        )

        if self.center_tabs.count() > 0:
            self.center_tabs.setCurrentIndex(0)

    def make_auto_flag_review_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("DataPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Flag Review")
        title.setObjectName("PanelTitle")
        hint = QLabel("Enter the ticker you are reviewing. The app builds a quick doorway view from local screener and data-quality outputs.")
        hint.setObjectName("PanelHint")
        hint.setWordWrap(True)

        input_row = QHBoxLayout()
        self.flag_review_ticker_input = QLineEdit()
        self.flag_review_ticker_input.setPlaceholderText("Ticker to deep dive, e.g. QCOM")
        self.flag_review_ticker_input.returnPressed.connect(self.autofill_flag_review)
        button = QPushButton("Answer Flag Review")
        button.setObjectName("PrimaryButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(self.autofill_flag_review)
        input_row.addWidget(self.flag_review_ticker_input, 1)
        input_row.addWidget(button)

        self.flag_review_editor = QTextEdit()
        self.flag_review_editor.setObjectName("Hud")
        self.flag_review_editor.setReadOnly(True)
        self.flag_review_editor.setHtml(
            self.flag_review_empty_html("Enter a ticker above, then click Answer Flag Review. Run the full pipeline first if the ticker has no output yet.")
        )

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(input_row)
        layout.addWidget(self.flag_review_editor, 1)
        return panel

    def autofill_flag_review(self) -> None:
        ticker = self.flag_review_ticker_input.text().strip().upper()
        if not ticker:
            ticker = self.current_ticker() or ""
        if not ticker:
            QMessageBox.warning(self, "Missing ticker", "Enter a ticker or select one from the watchlist.")
            return
        self.selected_ticker = ticker
        self.refresh_auto_review_panels(ticker)

    def flag_review_css(self) -> str:
        return """
        body { background: #020814; color: #dfeeff; font-family: Arial, sans-serif; }
        .wrap { padding: 10px; }
        .top { border: 1px solid #2f5f96; border-radius: 14px; padding: 16px; background: #07172a; }
        .ticker { font-size: 34px; font-weight: 800; color: white; }
        .subtitle { color: #9fb7d8; font-size: 13px; margin-top: 4px; }
        .grid { margin-top: 14px; }
        .card { display: inline-block; min-width: 148px; margin: 6px; padding: 12px; border: 1px solid #274c78; border-radius: 12px; background: #0a1627; vertical-align: top; }
        .label { color: #9fb7d8; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
        .value { color: white; font-size: 20px; font-weight: 800; margin-top: 5px; }
        .badge { display: inline-block; padding: 6px 10px; border-radius: 999px; font-weight: 800; font-size: 12px; }
        .good { background: #123f2b; color: #7ff0ad; border: 1px solid #2c8f58; }
        .watch { background: #3d3214; color: #ffd36a; border: 1px solid #9b771f; }
        .bad { background: #411a1e; color: #ff8c9a; border: 1px solid #a43d4a; }
        .spec { background: #30214d; color: #c9a7ff; border: 1px solid #7254b6; }
        .neutral { background: #182438; color: #b8c9e6; border: 1px solid #3b557a; }
        .section { margin-top: 14px; padding: 14px; border: 1px solid #233d60; border-radius: 12px; background: #050d1a; }
        .section h3 { margin: 0 0 8px 0; color: white; }
        .text { color: #d9e8ff; line-height: 1.45; }
        .muted { color: #9fb7d8; }
        .row { margin: 5px 0; }
        b { color: white; }
        """

    def flag_review_empty_html(self, message: str) -> str:
        return f"""
        <html><head><style>{self.flag_review_css()}</style></head>
        <body><div class='wrap'>
          <div class='top'>
            <div class='ticker'>Flag Review HUD</div>
            <div class='subtitle'>{esc(message)}</div>
          </div>
        </div></body></html>
        """

    def build_flag_review_html(self, ticker: str) -> str:
        ticker = ticker.strip().upper()
        watch_rows = getattr(self, "_master_rows", None)
        if watch_rows is None:
            watch_rows = list_master_watchlist()
            self._master_rows = watch_rows
        watch_row = self.find_local_row(watch_rows, ticker)

        if not watch_row:
            return self.flag_review_empty_html(
                f"{ticker} was not found in local screener output. Add it, assign a peer group, and run the full pipeline."
            )

        data_flag = watch_row.get("Data Confidence Flag", "")
        data_score = int(float(str(watch_row.get("Data Score", "0") or "0")))
        status = watch_row.get("Review Status", "")
        red_flags = watch_row.get("Red Flags", "") or "None flagged"
        watch_items = watch_row.get("Watch Items", "") or "None flagged"
        action = watch_row.get("Action", "")
        weak_areas = watch_row.get("Missing / Weak Areas", "") or "None listed."
        peer_group = watch_row.get("Peer Group", "") or "Not assigned"

        if str(status).startswith("GREEN"):
            gate_result = "Continue"
            verify_next = "Data Check, then Red Flag Check, then Peer Gate."
            proof_line = "This is only a screener doorway. Peer Gate decides whether the company is actually better than alternatives."
        elif str(status).startswith("GRAY"):
            gate_result = "Fix Data"
            verify_next = "Data Check."
            proof_line = "Fix missing data or the peer group before trusting the review."
        elif str(status).startswith("RED"):
            gate_result = "Pass For Now"
            verify_next = "Red Flag Check."
            proof_line = "Continue only if you already have a specific reason the red flag is acceptable."
        else:
            gate_result = "Needs Proof"
            verify_next = "Data Check and Red Flag Check."
            proof_line = "The app sees watch items. Those need context before peer comparison."

        return f"""
        <html><head><style>{self.flag_review_css()}</style></head>
        <body><div class='wrap'>
          <div class='top'>
            <div class='ticker'>{esc(ticker)}</div>
            <div class='subtitle'>Flag Review - local screener doorway only</div>
            <div class='grid'>
              <div class='card'><div class='label'>Review Status</div><div class='value'><span class='badge {flag_class(status)}'>{esc(status)}</span></div></div>
              <div class='card'><div class='label'>Data Score</div><div class='value'>{esc(data_score)}</div></div>
              <div class='card'><div class='label'>Peer Group</div><div class='value'>{esc(peer_group)}</div></div>
              <div class='card'><div class='label'>Gate Result</div><div class='value'><span class='badge {flag_class(gate_result)}'>{esc(gate_result)}</span></div></div>
            </div>
          </div>

          <div class='section'>
            <h3>Why It Was Flagged</h3>
            <div class='text row'><b>Red flags:</b> {esc(red_flags)}</div>
            <div class='text row'><b>Watch items:</b> {esc(watch_items)}</div>
            <div class='text row'><b>Missing / weak areas:</b> {esc(weak_areas)}</div>
          </div>

          <div class='section'>
            <h3>Standalone Checks</h3>
            <div class='grid'>
              <div class='card'><div class='label'>Data</div><div class='value'><span class='badge {flag_class(data_flag)}'>{esc(data_flag)}</span></div></div>
              <div class='card'><div class='label'>Business</div><div class='value'><span class='badge {flag_class(watch_row.get('Standalone Business Flag', ''))}'>{esc(watch_row.get('Standalone Business Flag', ''))}</span></div></div>
              <div class='card'><div class='label'>Valuation</div><div class='value'><span class='badge {flag_class(watch_row.get('Standalone Valuation Flag', ''))}'>{esc(watch_row.get('Standalone Valuation Flag', ''))}</span></div></div>
              <div class='card'><div class='label'>Balance</div><div class='value'><span class='badge {flag_class(watch_row.get('Standalone Balance Flag', ''))}'>{esc(watch_row.get('Standalone Balance Flag', ''))}</span></div></div>
              <div class='card'><div class='label'>Dilution</div><div class='value'><span class='badge {flag_class(watch_row.get('Standalone Dilution Flag', ''))}'>{esc(watch_row.get('Standalone Dilution Flag', ''))}</span></div></div>
            </div>
            <div class='text row'><b>Plain English:</b> These checks only catch obvious danger. They do not prove the company is good. Peer Gate compares valuation, quality, balance sheet, and dilution against similar companies.</div>
          </div>

          <div class='section'>
            <h3>Next Action</h3>
            <div class='text row'><b>App action:</b> {esc(action)}</div>
            <div class='text row'><b>Verify next:</b> {esc(verify_next)}</div>
            <div class='text row'><b>Missing / weak areas:</b> {esc(weak_areas)}</div>
            <div class='text row'><b>Gate note:</b> {esc(proof_line)}</div>
          </div>
        </div></body></html>
        """

    def make_auto_data_check_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("DataPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Data Check")
        title.setObjectName("PanelTitle")
        hint = QLabel("Auto-filled from the stock you are reviewing. This checks whether the local data is clean enough for peer comparison.")
        hint.setObjectName("PanelHint")
        hint.setWordWrap(True)

        self.data_check_editor = QTextEdit()
        self.data_check_editor.setObjectName("Hud")
        self.data_check_editor.setReadOnly(True)
        self.data_check_editor.setHtml(
            self.data_check_empty_html("Select a ticker from the watchlist or answer Flag Review to auto-fill this check.")
        )

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.data_check_editor, 1)
        return panel

    def data_check_empty_html(self, message: str) -> str:
        return f"""
        <html><head><style>{self.flag_review_css()}</style></head>
        <body><div class='wrap'>
          <div class='top'>
            <div class='ticker'>Data Check HUD</div>
            <div class='subtitle'>{esc(message)}</div>
          </div>
        </div></body></html>
        """

    def build_data_check_html(self, ticker: str) -> str:
        ticker = ticker.strip().upper()
        watch_rows = getattr(self, "_master_rows", None)
        if watch_rows is None:
            watch_rows = list_master_watchlist()
            self._master_rows = watch_rows
        watch_row = self.find_local_row(watch_rows, ticker)

        if not watch_row:
            return self.data_check_empty_html(
                f"{ticker} does not have enough local output yet. Run the full pipeline first."
            )

        data_score = int(float(str(watch_row.get("Data Score", "0") or "0")))
        data_flag = watch_row.get("Data Confidence Flag", "")
        readiness = watch_row.get("Readiness", "")
        weak_areas = watch_row.get("Missing / Weak Areas", "") or "None flagged."
        source_status = watch_row.get("Source Status", "") or "No source status listed."

        if str(data_flag).startswith("GRAY") or "NOT SCREEN READY" in str(readiness).upper() or data_score < 60:
            gate_result = "Needs Proof"
            gate_note = "Fix or understand the missing data before comparing this ticker to peers."
        elif weak_areas and weak_areas != "None flagged." and weak_areas != "None flagged":
            gate_result = "Needs Proof"
            gate_note = "The data is usable, but the listed weak areas need a quick look before Peer Gate."
        else:
            gate_result = "Continue"
            gate_note = "The local data is clean enough. Peer Gate should decide whether the financials are actually good versus alternatives."

        return f"""
        <html><head><style>{self.flag_review_css()}</style></head>
        <body><div class='wrap'>
          <div class='top'>
            <div class='ticker'>{esc(ticker)}</div>
            <div class='subtitle'>Data Check • clean enough to compare?</div>
            <div class='grid'>
              <div class='card'><div class='label'>Data Score</div><div class='value'>{esc(data_score)}</div></div>
              <div class='card'><div class='label'>Data Flag</div><div class='value'><span class='badge {flag_class(data_flag)}'>{esc(data_flag)}</span></div></div>
              <div class='card'><div class='label'>Gate Result</div><div class='value'><span class='badge {flag_class(gate_result)}'>{esc(gate_result)}</span></div></div>
            </div>
          </div>

          <div class='section'>
            <h3>Bottom Line</h3>
            <div class='text row'><b>What this gate says:</b> {esc(gate_note)}</div>
            <div class='text row'><b>What this gate does not decide:</b> Whether valuation, margins, balance sheet, or dilution are good. Peer Gate compares those against similar companies.</div>
          </div>

          <div class='section'>
            <h3>Data Evidence</h3>
            <div class='text row'><b>Readiness:</b> {esc(readiness)}</div>
            <div class='text row'><b>Missing / weak areas:</b> {esc(weak_areas)}</div>
            <div class='text row'><b>Source status:</b> {esc(source_status)}</div>
          </div>
        </div></body></html>
        """

    def make_auto_red_flag_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("DataPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("2. Red Flag Check")
        title.setObjectName("PanelTitle")
        hint = QLabel("Auto-filled from the stock you are reviewing. This catches obvious danger before peer comparison.")
        hint.setObjectName("PanelHint")
        hint.setWordWrap(True)

        self.red_flag_editor = QTextEdit()
        self.red_flag_editor.setObjectName("Hud")
        self.red_flag_editor.setReadOnly(True)
        self.red_flag_editor.setHtml(
            self.red_flag_empty_html("Select a ticker from the watchlist or answer Flag Review to auto-fill this check.")
        )

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.red_flag_editor, 1)
        return panel

    def red_flag_empty_html(self, message: str) -> str:
        return f"""
        <html><head><style>{self.flag_review_css()}</style></head>
        <body><div class='wrap'>
          <div class='top'>
            <div class='ticker'>Red Flag Check HUD</div>
            <div class='subtitle'>{esc(message)}</div>
          </div>
        </div></body></html>
        """

    def build_red_flag_html(self, ticker: str) -> str:
        ticker = ticker.strip().upper()
        watch_rows = getattr(self, "_master_rows", None)
        if watch_rows is None:
            watch_rows = list_master_watchlist()
            self._master_rows = watch_rows
        watch_row = self.find_local_row(watch_rows, ticker)

        if not watch_row:
            return self.red_flag_empty_html(
                f"{ticker} does not have enough local output yet. Run the full pipeline first."
            )

        status = watch_row.get("Red Flag Result", "")
        red_flags = watch_row.get("Red Flags", "") or "None flagged"
        watch_items = watch_row.get("Watch Items", "") or "None flagged"
        action = watch_row.get("Action", "")

        if str(status).startswith("GREEN"):
            gate_result = "Continue"
            gate_note = "Nothing obvious blocks peer comparison. The next step is proving it against alternatives."
        elif str(status).startswith("GRAY"):
            gate_result = "Fix Data"
            gate_note = "The app cannot trust the red-flag check until the data problem or peer group is fixed."
        elif str(status).startswith("RED"):
            gate_result = "Pass For Now"
            gate_note = "There is an obvious standalone danger. Continue only if your outside thesis directly explains it."
        else:
            gate_result = "Needs Proof"
            gate_note = "No automatic pass/fail yet. The watch items need context before the Peer Gate."

        return f"""
        <html><head><style>{self.flag_review_css()}</style></head>
        <body><div class='wrap'>
          <div class='top'>
            <div class='ticker'>{esc(ticker)}</div>
            <div class='subtitle'>Red Flag Check - danger before peers?</div>
            <div class='grid'>
              <div class='card'><div class='label'>Result</div><div class='value'><span class='badge {flag_class(status)}'>{esc(status)}</span></div></div>
              <div class='card'><div class='label'>Gate Result</div><div class='value'><span class='badge {flag_class(gate_result)}'>{esc(gate_result)}</span></div></div>
              <div class='card'><div class='label'>Data</div><div class='value'><span class='badge {flag_class(watch_row.get('Data Confidence Flag', ''))}'>{esc(watch_row.get('Data Confidence Flag', ''))}</span></div></div>
            </div>
          </div>

          <div class='section'>
            <h3>Red Flags</h3>
            <div class='text row'><b>Danger items:</b> {esc(red_flags)}</div>
            <div class='text row'><b>Watch items:</b> {esc(watch_items)}</div>
          </div>

          <div class='section'>
            <h3>Evidence</h3>
            <div class='grid'>
              <div class='card'><div class='label'>Business</div><div class='value'><span class='badge {flag_class(watch_row.get('Standalone Business Flag', ''))}'>{esc(watch_row.get('Standalone Business Flag', ''))}</span></div></div>
              <div class='card'><div class='label'>Valuation</div><div class='value'><span class='badge {flag_class(watch_row.get('Standalone Valuation Flag', ''))}'>{esc(watch_row.get('Standalone Valuation Flag', ''))}</span></div></div>
              <div class='card'><div class='label'>Balance</div><div class='value'><span class='badge {flag_class(watch_row.get('Standalone Balance Flag', ''))}'>{esc(watch_row.get('Standalone Balance Flag', ''))}</span></div></div>
              <div class='card'><div class='label'>Dilution</div><div class='value'><span class='badge {flag_class(watch_row.get('Standalone Dilution Flag', ''))}'>{esc(watch_row.get('Standalone Dilution Flag', ''))}</span></div></div>
            </div>
            <div class='text row'><b>Plain English:</b> This step is not trying to reward a company for good-looking numbers. It only asks whether anything is dangerous enough to stop before peer comparison.</div>
          </div>

          <div class='section'>
            <h3>Next Action</h3>
            <div class='text row'><b>App action:</b> {esc(action)}</div>
            <div class='text row'><b>Gate note:</b> {esc(gate_note)}</div>
            <div class='text row'><b>Missing / weak areas:</b> {esc(watch_row.get('Missing / Weak Areas', '') or 'None listed.')}</div>
          </div>
        </div></body></html>
        """

    def make_auto_peer_check_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("DataPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Peer Check")
        title.setObjectName("PanelTitle")
        hint = QLabel("Enter the ticker you are comparing. The app builds a quick peer HUD from local peer-comparison output.")
        hint.setObjectName("PanelHint")
        hint.setWordWrap(True)

        input_row = QHBoxLayout()
        self.peer_check_ticker_input = QLineEdit()
        self.peer_check_ticker_input.setPlaceholderText("Ticker to compare, e.g. QCOM")
        self.peer_check_ticker_input.returnPressed.connect(self.autofill_peer_check)
        button = QPushButton("Answer Peer Check")
        button.setObjectName("PrimaryButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(self.autofill_peer_check)
        input_row.addWidget(self.peer_check_ticker_input, 1)
        input_row.addWidget(button)

        self.peer_check_editor = QTextEdit()
        self.peer_check_editor.setObjectName("Hud")
        self.peer_check_editor.setReadOnly(True)
        self.peer_check_editor.setHtml(
            self.peer_check_empty_html("Enter a ticker above, then click Answer Peer Check. Run the full pipeline first if the ticker has no peer output yet.")
        )

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(input_row)
        layout.addWidget(self.peer_check_editor, 1)
        return panel

    def autofill_peer_check(self) -> None:
        ticker = self.peer_check_ticker_input.text().strip().upper()
        if not ticker:
            ticker = self.current_ticker() or ""
        if not ticker:
            QMessageBox.warning(self, "Missing ticker", "Enter a ticker or select one from the watchlist.")
            return
        self.selected_ticker = ticker
        self.refresh_auto_review_panels(ticker)

    def peer_check_empty_html(self, message: str) -> str:
        return f"""
        <html><head><style>{self.flag_review_css()}</style></head>
        <body><div class='wrap'>
          <div class='top'>
            <div class='ticker'>Peer Check HUD</div>
            <div class='subtitle'>{esc(message)}</div>
          </div>
        </div></body></html>
        """

    def peer_metric_row(self, label: str, value, median_label: str, median_value) -> str:
        return (
            "<div class='text row'>"
            f"<b>{esc(label)}:</b> {esc(value)} "
            f"<span class='muted'>({esc(median_label)}: {esc(median_value)})</span>"
            "</div>"
        )

    def peer_takeaway(self, component: str, flag: str) -> str:
        flag_upper = str(flag or "").upper()
        if "NO PEER BENCHMARK" in flag_upper:
            return "The app does not have enough peer data to judge this part."
        if component == "Valuation":
            if flag_upper.startswith("GREEN"):
                return "This ticker is cheaper than its peer group on the available price metrics."
            if flag_upper.startswith("RED"):
                return "This ticker is more expensive than its peer group on the available price metrics."
            return "This ticker is priced near the peer group, so it needs another reason to stand out."
        if component == "Quality":
            if flag_upper.startswith("GREEN"):
                return "This ticker converts sales into margins/cash better than the peer median."
            if flag_upper.startswith("RED"):
                return "This ticker converts sales into margins/cash worse than the peer median."
            return "This ticker looks roughly similar to peers on margins/cash."
        if component == "Balance":
            if flag_upper.startswith("GREEN"):
                return "This ticker has a stronger short-term financial cushion than peers."
            if flag_upper.startswith("RED"):
                return "This ticker has a weaker short-term financial cushion than peers."
            return "This ticker looks roughly similar to peers on short-term financial cushion."
        if component == "Dilution":
            if flag_upper.startswith("GREEN"):
                return "This ticker is creating fewer new shares than peers."
            if flag_upper.startswith("RED"):
                return "This ticker is creating more new shares than peers."
            return "This ticker is near the peer group on share dilution."
        return "Review this against the peer table."

    def peer_read_row(self, component: str, flag: str) -> str:
        return (
            "<div class='text row'>"
            f"<b>{esc(component)}:</b> "
            f"<span class='badge {flag_class(flag)}'>{esc(flag)}</span> "
            f"{esc(self.peer_takeaway(component, flag))}"
            "</div>"
        )

    def build_peer_check_html(self, ticker: str) -> str:
        ticker = ticker.strip().upper()
        peer_rows = getattr(self, "_peer_rows", None)
        if peer_rows is None:
            peer_rows = list_peer_comparison()
            self._peer_rows = peer_rows
        peer_row = self.find_local_row(peer_rows, ticker)

        if not peer_row:
            return self.peer_check_empty_html(
                f"{ticker} was not found in local peer comparison output. Run the full pipeline after assigning a peer group."
            )

        peer_flag = peer_row.get("Overall Peer Flag", "")
        if str(peer_flag).startswith("GREEN"):
            gate_result = "Continue"
            proof_line = "Peer signals support comparing this ticker against the manual Peer Result questions."
        elif str(peer_flag).startswith("RED"):
            gate_result = "Pass For Now"
            proof_line = "Peer signals are weak. Continue only with a specific thesis the peer table is missing."
        else:
            gate_result = "Needs Proof"
            proof_line = "Use the Peer Comparison table to prove why this is still the right sector vehicle."

        peer_read_rows = "".join([
            self.peer_read_row("Valuation", peer_row.get("Relative Valuation Flag", "")),
            self.peer_read_row("Quality", peer_row.get("Relative Quality Flag", "")),
            self.peer_read_row("Balance", peer_row.get("Relative Balance Flag", "")),
            self.peer_read_row("Dilution", peer_row.get("Relative Dilution Flag", "")),
        ])

        metric_rows = "".join([
            self.peer_metric_row("EV/Revenue", peer_row.get("EV/Revenue", ""), "peer median", peer_row.get("Peer Median EV/Revenue", "")),
            self.peer_metric_row("EV/FCF", peer_row.get("EV/FCF", ""), "peer median", peer_row.get("Peer Median EV/FCF", "")),
            self.peer_metric_row("P/S", peer_row.get("P/S", ""), "peer median", peer_row.get("Peer Median P/S", "")),
            self.peer_metric_row("FCF Margin", peer_row.get("FCF Margin", ""), "peer median", peer_row.get("Peer Median FCF Margin", "")),
            self.peer_metric_row("Operating Margin", peer_row.get("Operating Margin", ""), "peer median", peer_row.get("Peer Median Operating Margin", "")),
            self.peer_metric_row("Gross Margin", peer_row.get("Gross Margin", ""), "peer median", peer_row.get("Peer Median Gross Margin", "")),
            self.peer_metric_row("Current Ratio", peer_row.get("Current Ratio", ""), "peer median", peer_row.get("Peer Median Current Ratio", "")),
            self.peer_metric_row("Dilution 1Y", peer_row.get("Dilution 1Y", ""), "peer median", peer_row.get("Peer Median Dilution 1Y", "")),
            self.peer_metric_row("Dilution 3Y", peer_row.get("Dilution 3Y", ""), "peer median", peer_row.get("Peer Median Dilution 3Y", "")),
        ])

        return f"""
        <html><head><style>{self.flag_review_css()}</style></head>
        <body><div class='wrap'>
          <div class='top'>
            <div class='ticker'>{esc(ticker)}</div>
            <div class='subtitle'>Peer Gate • local peer comparison only</div>
            <div class='grid'>
              <div class='card'><div class='label'>Peer Group</div><div class='value'>{esc(peer_row.get('Peer Group', ''))}</div></div>
              <div class='card'><div class='label'>Peer Count</div><div class='value'>{esc(peer_row.get('Peer Count', ''))}</div></div>
              <div class='card'><div class='label'>Gate Result</div><div class='value'><span class='badge {flag_class(gate_result)}'>{esc(gate_result)}</span></div></div>
            </div>
          </div>

          <div class='section'>
            <h3>Peer Flags</h3>
            <div class='grid'>
              <div class='card'><div class='label'>Overall</div><div class='value'><span class='badge {flag_class(peer_flag)}'>{esc(peer_flag)}</span></div></div>
              <div class='card'><div class='label'>Valuation</div><div class='value'><span class='badge {flag_class(peer_row.get('Relative Valuation Flag', ''))}'>{esc(peer_row.get('Relative Valuation Flag', ''))}</span></div></div>
              <div class='card'><div class='label'>Quality</div><div class='value'><span class='badge {flag_class(peer_row.get('Relative Quality Flag', ''))}'>{esc(peer_row.get('Relative Quality Flag', ''))}</span></div></div>
              <div class='card'><div class='label'>Balance</div><div class='value'><span class='badge {flag_class(peer_row.get('Relative Balance Flag', ''))}'>{esc(peer_row.get('Relative Balance Flag', ''))}</span></div></div>
              <div class='card'><div class='label'>Dilution</div><div class='value'><span class='badge {flag_class(peer_row.get('Relative Dilution Flag', ''))}'>{esc(peer_row.get('Relative Dilution Flag', ''))}</span></div></div>
            </div>
          </div>

          <div class='section'>
            <h3>Peer Read</h3>
            {peer_read_rows}
          </div>

          <div class='section'>
            <h3>Relative Metrics</h3>
            {metric_rows}
          </div>

          <div class='section'>
            <h3>Next Action</h3>
            <div class='text row'><b>Readiness:</b> {esc(peer_row.get('Readiness', ''))}</div>
            <div class='text row'><b>Missing / weak areas:</b> {esc(peer_row.get('Missing / Weak Areas', ''))}</div>
            <div class='text row'><b>Gate note:</b> {esc(proof_line)}</div>
          </div>
        </div></body></html>
        """

    def find_local_row(self, rows: list[dict], ticker: str) -> dict | None:
        for row in rows:
            if str(row.get("Ticker", "")).strip().upper() == ticker:
                return row
        return None

    def refresh_auto_review_panels(self, ticker: str | None = None) -> None:
        ticker = (ticker or self.current_ticker() or "").strip().upper()

        if hasattr(self, "flag_review_editor"):
            if ticker:
                self.flag_review_ticker_input.setText(ticker)
                self.flag_review_editor.setHtml(self.build_flag_review_html(ticker))
            else:
                self.flag_review_editor.setHtml(
                    self.flag_review_empty_html("Select a ticker from the watchlist or enter one here to start the review.")
                )

        if hasattr(self, "data_check_editor"):
            if ticker:
                self.data_check_editor.setHtml(self.build_data_check_html(ticker))
            else:
                self.data_check_editor.setHtml(
                    self.data_check_empty_html("Select a ticker from the watchlist or answer Flag Review to auto-fill this check.")
                )

        if hasattr(self, "red_flag_editor"):
            if ticker:
                self.red_flag_editor.setHtml(self.build_red_flag_html(ticker))
            else:
                self.red_flag_editor.setHtml(
                    self.red_flag_empty_html("Select a ticker from the watchlist or answer Flag Review to auto-fill this check.")
                )

        if hasattr(self, "peer_check_editor"):
            if ticker:
                self.peer_check_ticker_input.setText(ticker)
                self.peer_check_editor.setHtml(self.build_peer_check_html(ticker))
            else:
                self.peer_check_editor.setHtml(
                    self.peer_check_empty_html("Select a ticker from the watchlist or answer Flag Review to auto-fill this gate.")
                )

    def table_selection_changed(self, table: QTableWidget, row: int) -> None:
        super().table_selection_changed(table, row)
        self.refresh_auto_review_panels(self.selected_ticker)

    def refresh_all_tables(self, ticker=None) -> None:
        super().refresh_all_tables(ticker)
        self.refresh_auto_review_panels(ticker)

    def make_nested_tab_panel(self, title_text: str, hint_text: str, tabs: list[tuple[str, QWidget | None]]) -> QWidget:
        panel = QWidget()
        panel.setObjectName("DataPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("PanelTitle")
        hint = QLabel(hint_text)
        hint.setObjectName("PanelHint")
        hint.setWordWrap(True)

        nested_tabs = QTabWidget()
        nested_tabs.setObjectName("WorkspaceTabs")
        nested_tabs.setDocumentMode(True)

        for name, widget in tabs:
            nested_tabs.addTab(widget or self.make_missing_panel(name), name)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(nested_tabs, 1)
        return panel

    def make_notes_panel(self, title_text: str, hint_text: str, template_text: str) -> QWidget:
        panel = QWidget()
        panel.setObjectName("DataPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("PanelTitle")
        hint = QLabel(hint_text)
        hint.setObjectName("PanelHint")
        hint.setWordWrap(True)

        editor = QTextEdit()
        editor.setObjectName("Hud")
        editor.setPlainText(template_text)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(editor, 1)
        return panel

    def make_missing_panel(self, name: str) -> QWidget:
        return self.make_notes_panel(
            name,
            "This supporting view was not available during UI construction.",
            "Run the app and verify this supporting tab is being created correctly.",
        )

    def build_overview_tab(self, tabs) -> None:
        overview = QWidget()
        layout = QVBoxLayout(overview)
        layout.setContentsMargins(22, 24, 22, 22)
        layout.setSpacing(20)

        summary = QWidget()
        summary.setObjectName("PreviewShell")
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(38, 34, 38, 34)
        summary_layout.setSpacing(18)

        eyebrow = QLabel("LOCAL STOCK SCREENER")
        eyebrow.setObjectName("HeroEyebrow")
        eyebrow.setAlignment(Qt.AlignCenter)

        title = QLabel("Overview")
        title.setObjectName("HeroTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)

        subtitle = QLabel("Local watchlist, SEC data, Finnhub data, price history, peer groups, and workflow status.")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        summary_layout.addWidget(eyebrow)
        summary_layout.addWidget(title)
        summary_layout.addWidget(subtitle)

        metric_grid = QGridLayout()
        metric_grid.setSpacing(14)
        card, self.metric_total, self.metric_total_sub = make_metric_card("Universe", "0", "tracked tickers")
        metric_grid.addWidget(card, 0, 0)
        card, self.metric_deep_dive, self.metric_deep_dive_sub = make_metric_card("Peer Ready", "0", "green rows")
        metric_grid.addWidget(card, 0, 1)
        card, self.metric_watch, self.metric_watch_sub = make_metric_card("Watch", "0", "needs context")
        metric_grid.addWidget(card, 0, 2)
        card, self.metric_data, self.metric_data_sub = make_metric_card("Needs Data", "0", "gray names")
        metric_grid.addWidget(card, 0, 3)
        summary_layout.addLayout(metric_grid)
        layout.addWidget(summary)

        dashboard = QWidget()
        dashboard.setObjectName("DashboardCard")
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(20, 20, 20, 20)
        dashboard_layout.setSpacing(12)

        dash_title = QLabel("Status Board")
        dash_title.setObjectName("PanelTitle")
        dash_hint = QLabel("Summary of the current local database and screening results.")
        dash_hint.setObjectName("PanelHint")

        self.hud = QTextEdit()
        self.hud.setObjectName("Hud")
        self.hud.setReadOnly(True)

        dashboard_layout.addWidget(dash_title)
        dashboard_layout.addWidget(dash_hint)
        dashboard_layout.addWidget(self.hud, 1)
        layout.addWidget(dashboard, 1)
        tabs.addTab(overview, "Overview")

    def build_left_panel(self) -> QWidget:
        left = QWidget()
        left.setObjectName("ControlPanel")
        left.setMinimumWidth(500)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(14)

        left_title = QLabel("Watchlist Control")
        left_title.setObjectName("PanelTitle")
        left_hint = QLabel("Add tickers, assign peer groups, then run the local research pipeline.")
        left_hint.setObjectName("PanelHint")
        left_layout.addWidget(left_title)
        left_layout.addWidget(left_hint)

        self.watchlist_filter_input = QLineEdit()
        self.watchlist_filter_input.setPlaceholderText("Search watchlist: ticker, company, or peer group")
        self.watchlist_filter_input.textChanged.connect(lambda _: self.refresh_watchlist())
        left_layout.addWidget(self.watchlist_filter_input)

        self.watchlist_table = QTableWidget()
        self.watchlist_table.setColumnCount(3)
        self.watchlist_table.setHorizontalHeaderLabels(["Ticker", "Company", "Peer Group"])
        self.watchlist_table.cellClicked.connect(self.watchlist_clicked)
        polish_table(self.watchlist_table, sticky_ticker=False)
        self.watchlist_table.setColumnWidth(0, 90)
        self.watchlist_table.setColumnWidth(1, 190)
        self.watchlist_table.setColumnWidth(2, 250)
        left_layout.addWidget(self.watchlist_table, 5)

        form_group = QWidget()
        form_group.setObjectName("ActionGroup")
        form_group_layout = QVBoxLayout(form_group)
        form_group_layout.setContentsMargins(15, 15, 15, 15)
        form_group_layout.setSpacing(11)

        setup_title = QLabel("Ticker Setup")
        setup_title.setObjectName("PanelTitle")
        form_group_layout.addWidget(setup_title)

        form = QFormLayout()
        form.setVerticalSpacing(10)
        self.ticker_input = QLineEdit()
        self.company_input = QLineEdit()
        self.peer_group_input = QComboBox()
        self.peer_group_input.setEditable(True)
        self.peer_group_input.addItems(merged_peer_groups())

        self.sec_user_agent = QLineEdit(get_setting("sec_user_agent", DEFAULT_SEC_USER_AGENT))
        self.sec_user_agent.setPlaceholderText("Format: Your Name your-email@example.com")
        self.sec_user_agent.setToolTip(SEC_USER_AGENT_HELP)

        self.finnhub_api_key = QLineEdit(get_setting("finnhub_api_key", ""))
        self.finnhub_api_key.setPlaceholderText("Finnhub API key; saved locally only")
        self.finnhub_api_key.setEchoMode(QLineEdit.Password)

        self.price_lookback_years_input = QLineEdit(get_setting("price_lookback_years", "3"))
        self.price_lookback_years_input.setPlaceholderText("3")

        self.sec_user_agent.editingFinished.connect(self.save_api_settings_silent)
        self.finnhub_api_key.editingFinished.connect(self.save_api_settings_silent)
        self.price_lookback_years_input.editingFinished.connect(self.save_api_settings_silent)

        self.ticker_input.setPlaceholderText("NVDA")
        self.company_input.setPlaceholderText("Optional company name")
        form.addRow("Ticker", self.ticker_input)
        form.addRow("Company", self.company_input)
        form.addRow("Peer Group", self.peer_group_input)
        form.addRow("SEC User-Agent", self.sec_user_agent)
        form.addRow("Finnhub API Key", self.finnhub_api_key)
        form.addRow("Price Lookback Years", self.price_lookback_years_input)
        form_group_layout.addLayout(form)
        left_layout.addWidget(form_group, 2)

        action_group = QWidget()
        action_group.setObjectName("ActionGroup")
        action_layout = QVBoxLayout(action_group)
        action_layout.setContentsMargins(15, 15, 15, 15)
        action_layout.setSpacing(10)

        action_title = QLabel("Actions")
        action_title.setObjectName("PanelTitle")
        action_layout.addWidget(action_title)

        for text, fn, style_name in [
            ("Add / Update Ticker", self.add_ticker_clicked, "PrimaryButton"),
            ("Run Full Pipeline", self.run_pipeline_clicked, "PrimaryButton"),
            ("Run Full Pipeline For All Active", self.run_all_active_pipeline_clicked, "PrimaryButton"),
            ("Save API Settings", self.save_api_settings, "QuietButton"),
            ("Delete Selected Ticker", self.delete_selected_ticker_clicked, "DangerButton"),
        ]:
            button = QPushButton(text)
            button.setObjectName(style_name)
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(42)
            button.setMinimumWidth(230)
            button.clicked.connect(fn)
            action_layout.addWidget(button)

        left_layout.addWidget(action_group, 0)
        return left

    def refresh_watchlist(self) -> None:
        rows = list_tickers()
        query = ""
        if hasattr(self, "watchlist_filter_input"):
            query = self.watchlist_filter_input.text().strip().lower()
        if query:
            rows = [
                row for row in rows
                if query in " ".join(
                    str(value or "")
                    for value in [row["ticker"], row["company"], row["peer_group"], row["category"]]
                ).lower()
            ]

        self.watchlist_table.setSortingEnabled(False)
        self.watchlist_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [row["ticker"], row["company"] or "", row["peer_group"] or row["category"] or ""]
            for c, val in enumerate(values):
                self.watchlist_table.setItem(r, c, QTableWidgetItem(str(val)))
        self.watchlist_table.setSortingEnabled(True)
        self.watchlist_table.resizeColumnsToContents()
        self.watchlist_table.setColumnWidth(0, max(self.watchlist_table.columnWidth(0), 90))
        self.watchlist_table.setColumnWidth(1, max(self.watchlist_table.columnWidth(1), 190))
        self.watchlist_table.setColumnWidth(2, max(self.watchlist_table.columnWidth(2), 250))

    def add_ticker_clicked(self) -> None:
        ticker = self.ticker_input.text().strip().upper()
        if not ticker:
            QMessageBox.warning(self, "Missing ticker", "Enter a ticker.")
            return
        peer_group = self.peer_group_input.currentText().strip()
        add_ticker(ticker, self.company_input.text().strip(), peer_group, peer_group, "")
        self.selected_ticker = ticker
        self.ticker_input.clear()
        self.company_input.clear()
        self.peer_group_input.setCurrentText("")
        if hasattr(self, "watchlist_filter_input"):
            self.watchlist_filter_input.clear()
        self.refresh_all_tables(ticker)

    def delete_selected_ticker_clicked(self) -> None:
        ticker = self.current_ticker()
        if not ticker:
            QMessageBox.warning(self, "No ticker selected", "Select a ticker from the watchlist first.")
            return
        result = QMessageBox.question(
            self,
            "Delete ticker",
            f"Delete {ticker} from the watchlist and remove its cached local data?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return
        delete_ticker(ticker, delete_cached_data=True)
        self.selected_ticker = None
        self.details.setText(f"Deleted {ticker} from the local watchlist and local cached data.")
        self.refresh_all_tables()

    def active_ticker_rows(self):
        return [
            row for row in list_tickers()
            if str(row["status"] or "active").strip().lower() == "active"
        ]

    def run_all_active_pipeline_clicked(self) -> None:
        ua = self.sec_user_agent.text().strip()
        key = self.finnhub_api_key.text().strip()

        if not ua or "@" not in ua:
            QMessageBox.warning(self, "SEC User-Agent required", "Enter it as: Your Name your-email@example.com")
            return
        if not key:
            QMessageBox.warning(self, "Finnhub API key required", "Paste your Finnhub API key before running the full pipeline.")
            return

        rows = self.active_ticker_rows()
        if not rows:
            QMessageBox.warning(self, "No active tickers", "No active tickers were found in the watchlist.")
            return

        result = QMessageBox.question(
            self,
            "Run all active tickers",
            f"Run the full SEC + Finnhub + price-history pipeline for {len(rows)} active tickers?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return

        self.save_api_settings()
        successes: list[str] = []
        failures: list[str] = []
        total = len(rows)

        for index, row in enumerate(rows, start=1):
            ticker = str(row["ticker"] or "").strip().upper()
            if not ticker:
                continue
            try:
                self.selected_ticker = ticker
                self.details.setText(f"Running full pipeline for all active tickers...\n\n{index}/{total}: {ticker}")
                QApplication.processEvents()

                sec_rows = refresh_sec_rows(ticker, ua, years=5)
                insert_api_cache_rows(sec_rows, replace_source_for_ticker=True)
                history_rows = rebuild_historical_fundamentals_for_ticker(ticker)
                fh_rows = refresh_finnhub_rows(ticker, key)
                insert_api_cache_rows(fh_rows, replace_source_for_ticker=True)
                price_rows, price_warning = self.refresh_price_history_for_ticker(ticker, key)
                normalize_market_data_for_ticker(ticker)
                calculate_model_readiness_for_ticker(ticker)
                successes.append(
                    f"{ticker}: SEC {len(sec_rows)}, Finnhub {len(fh_rows)}, history years {history_rows}, price candles {price_rows}{price_warning}"
                )
            except Exception as exc:
                failures.append(f"{ticker}: {exc}")

        self.refresh_all_tables(self.selected_ticker)
        lines = [
            "Full pipeline for all active tickers complete.",
            "",
            f"Succeeded: {len(successes)}",
            f"Failed: {len(failures)}",
        ]
        if successes:
            lines.extend(["", "Succeeded tickers"])
            lines.extend(successes)
        if failures:
            lines.extend(["", "Failed tickers"])
            lines.extend(failures)
        self.details.setText("\n".join(lines))


def run_app() -> None:
    init_db()
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = StreamlinedMainWindow()
    window.show()
    apply_windows_dark_title_bar(window)
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
