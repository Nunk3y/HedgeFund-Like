import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGridLayout,
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
from app.services.readiness_service import calculate_model_readiness_for_ticker
from app.services.sec_service import refresh_sec_rows
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
    "Example: Sebastiaan Vriese savriese@gmail.com. "
    "Required by the SEC request policy; saved locally only."
)

EXTRA_PEER_GROUPS: list[str] = []

GATE_FOOTER = (
    "\n\n--- Gate Result ---\n"
    "Gate result: Continue / Needs Proof / Pass For Now\n"
    "Continue: move to the next gate.\n"
    "Needs Proof: write the proof needed before moving on.\n"
    "Pass For Now: place this ticker aside and review another idea.\n"
    "Proof needed or reason to pass for now:\n"
)


def merged_peer_groups() -> list[str]:
    groups: list[str] = []
    for group in [*DEFAULT_PEER_GROUPS, *EXTRA_PEER_GROUPS]:
        if group not in groups:
            groups.append(group)
    return groups


class StreamlinedMainWindow(MainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.hide_top_nav_buttons()
        self.build_research_workflow_tabs()
        self.auto_fit_tab_labels()
        self.update_active_tab_header()

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
                "0. Sector Funnel",
                "All-ticker screen. Start with the sector/theme you already believe in, then use the screen to find which companies earn a deeper look.",
                [
                    ("Overview", existing_tabs.get("Overview")),
                    ("Master Watchlist", existing_tabs.get("Master Watchlist")),
                    ("Data Quality", existing_tabs.get("Data Quality")),
                    ("Funnel Result", self.make_gate_panel("0. Sector Funnel Result", "Decide whether this ticker deserves more time inside this sector.", "Sector/theme I am testing:\nWhy I believe this sector should improve:\nTicker being tested:\nScreen note:\n")),
                ],
            ),
            "0. Sector Funnel",
        )

        self.center_tabs.addTab(
            self.make_gate_panel(
                "1. Exposure Gate",
                "Does this company actually give the sector exposure I want?",
                "Sector/theme I want exposure to:\n"
                "What part of the company is tied to that theme:\n"
                "How direct is the exposure: Direct / Mixed / Weak\n"
                "Reason this is not just a buzzword connection:\n"
                "If the sector improves, how does this company benefit:\n"
                "Main concern about exposure quality:\n",
            ),
            "1. Exposure Gate",
        )

        self.center_tabs.addTab(
            self.make_gate_panel(
                "2. Leader Gate",
                "Is this company likely to be one of the better public-company vehicles for this sector?",
                "Closest public companies in this sector:\n"
                "Why this company might be a leader:\n"
                "Why a different company might be better:\n"
                "Does this company have a real advantage: Product / scale / customers / manufacturing / ecosystem / cost / brand\n"
                "Leader status: Leader / Strong challenger / Average participant / Weak participant\n"
                "What would make me choose a peer instead:\n",
            ),
            "2. Leader Gate",
        )

        self.center_tabs.addTab(
            self.make_gate_panel(
                "3. Proof Gate",
                "Is the sector belief already showing up in this company, or is it still mostly a future story?",
                "Real product tied to the theme:\n"
                "Real revenue tied to the theme:\n"
                "Customers or contracts tied to the theme:\n"
                "Management guidance tied to the theme:\n"
                "Margins or cash flow improving from the theme:\n"
                "Proof level: Strong / Some proof / Early proof / Mostly story\n"
                "Proof still needed:\n",
            ),
            "3. Proof Gate",
        )

        self.center_tabs.addTab(
            self.make_nested_tab_panel(
                "4. Numbers Gate",
                "Are the numbers improving enough to keep going?",
                [
                    ("Historical Fundamentals", existing_tabs.get("Historical Fundamentals")),
                    ("Market Data", existing_tabs.get("Market Data")),
                    ("Score Details", existing_tabs.get("Score Details")),
                    ("Model Readiness", existing_tabs.get("Model Readiness")),
                    ("Numbers Result", self.make_gate_panel("4. Numbers Result", "Decide whether the financials support the sector idea.", "Revenue trend:\nMargin trend:\nFree cash flow trend:\nCash/debt situation:\nDilution/share count issue:\nData quality concern:\n")),
                ],
            ),
            "4. Numbers Gate",
        )

        self.center_tabs.addTab(
            self.make_nested_tab_panel(
                "5. Peer Gate",
                "Is this better than similar companies or the ETF?",
                [
                    ("Peer Comparison", existing_tabs.get("Peer Comparison")),
                    ("Peer Result", self.make_gate_panel("5. Peer Result", "Decide whether this ticker is a better sector vehicle than the available alternatives.", "Closest stronger peer:\nClosest cheaper peer:\nETF alternative:\nWhy this stock is a better sector vehicle:\nWhy this stock may be worse:\n")),
                ],
            ),
            "5. Peer Gate",
        )

        self.center_tabs.addTab(
            self.make_gate_panel(
                "6. Valuation Gate",
                "Is the sector future already priced in?",
                "Current price:\n"
                "Simple valuation method:\n"
                "Bear case:\n"
                "Base case:\n"
                "Bull case:\n"
                "Base-case upside:\n"
                "Bear-case downside:\n"
                "Assumptions required:\n"
                "Is the upside worth the risk:\n",
            ),
            "6. Valuation Gate",
        )

        self.center_tabs.addTab(
            self.make_nested_tab_panel(
                "7. Risk Gate",
                "What could make this the wrong vehicle for the sector?",
                [
                    ("Risk Result", self.make_gate_panel("7. Risk Result", "List the major reasons this may not be the right company to own for the sector.", "Main concern:\nCustomer/concentration concern:\nTechnology concern:\nDebt/liquidity concern:\nDilution concern:\nRegulatory/geopolitical concern:\nWhat would disprove the sector-vehicle case:\n")),
                    ("Filing Checklist", self.make_gate_panel("Filing Review Support", "Use filings only if earlier gates justify more work.", "Latest 10-K reviewed:\nLatest 10-Q reviewed:\nRecent 8-Ks reviewed:\nProxy reviewed:\nRisk factors notes:\nMD&A notes:\nDebt/liquidity notes:\nCustomer concentration notes:\nSBC/share-count notes:\n")),
                    ("API Cache", existing_tabs.get("API Cache")),
                    ("Price Trends", existing_tabs.get("Price Trends")),
                    ("Price History", existing_tabs.get("Price History")),
                ],
            ),
            "7. Risk Gate",
        )

        self.center_tabs.addTab(
            self.make_gate_panel(
                "8. Decision",
                "Final research decision. This decides the bucket, not necessarily a buy.",
                "Decision: Pass / Watch / Deep Dive More / Candidate Position\n"
                "Reason:\n"
                "Best gate result:\n"
                "Weakest gate result:\n"
                "Next proof needed:\n"
                "Next review trigger/date:\n",
                include_gate_footer=False,
            ),
            "8. Decision",
        )

        self.center_tabs.addTab(
            self.make_gate_panel(
                "9. Portfolio Fit",
                "Only use this after Decision says Candidate Position. This answers position size and concentration.",
                "Time horizon:\n"
                "Portfolio role:\n"
                "Ticker position %:\n"
                "Max allowed %:\n"
                "Theme exposure after purchase:\n"
                "Theme limit:\n"
                "ETF alternative:\n"
                "Would I buy this again today:\n"
                "Portfolio action:\n",
                include_gate_footer=False,
            ),
            "9. Portfolio Fit",
        )

        if self.center_tabs.count() > 0:
            self.center_tabs.setCurrentIndex(0)

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

    def make_gate_panel(self, title_text: str, hint_text: str, template_text: str, include_gate_footer: bool = True) -> QWidget:
        body = template_text + (GATE_FOOTER if include_gate_footer else "")
        return self.make_notes_panel(title_text, hint_text, body)

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
            "Run the app from the current branch and verify this tab is being created by the base UI.",
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

        subtitle = QLabel(
            "Local watchlist, SEC data, Finnhub data, price history, peer groups, and scoring status."
        )
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
        card, self.metric_deep_dive, self.metric_deep_dive_sub = make_metric_card("Deep Dive", "0", "green candidates")
        metric_grid.addWidget(card, 0, 1)
        card, self.metric_watch, self.metric_watch_sub = make_metric_card("Watch", "0", "yellow names")
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
            QMessageBox.warning(
                self,
                "SEC User-Agent required",
                "Enter it as: Your Name your-email@example.com",
            )
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
