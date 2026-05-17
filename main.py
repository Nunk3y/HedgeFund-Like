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

EXTRA_PEER_GROUPS = [
    "AI Servers / Data Center Hardware",
    "Data Center Networking",
    "Data Center Power / Cooling",
    "Electrical Grid Equipment",
    "Electrical Grid Construction",
    "Industrial Automation / Robotics",
    "Medical Robotics",
    "Warehouse Robotics",
    "EVs / Batteries / Robotics",
    "Defense Drones",
    "Defense / Space Hardware",
    "Defense / Aerospace Hardware",
    "Space Hardware",
    "Satellite Communications",
    "Battery / Energy Storage",
    "Solar / Energy Hardware",
    "Battery Materials",
    "Solid-State Batteries",
    "Water Infrastructure Tech",
    "Water / Lab Equipment",
    "3D Printing / Additive Manufacturing",
    "Nuclear Hardware / Services",
    "SMR / Advanced Nuclear",
    "Advanced Nuclear / Microreactors",
    "Nuclear Fuel / Enrichment",
    "Uranium / Rare Earths",
    "Nuclear Power Operator",
    "Utility / Nuclear Power",
    "Fusion-Adjacent / Big Tech",
    "Fusion-Adjacent / Energy",
    "Fusion-Adjacent / Industrial Investor",
]

WORKFLOW_TABS = [
    "0. Idea Funnel",
    "1. Thesis",
    "2. Business",
    "3. Filing Review",
    "4. Historical Picture",
    "5. Business Quality",
    "6. Commercial Reality",
    "7. Peer Comparison",
    "8. Valuation",
    "9. Market Behavior",
    "10. Variant View",
    "11. Decision",
    "12. Portfolio Management",
]


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
                "0. Idea Funnel",
                "This is the all-ticker screening area. Use it to find which company deserves a deep dive. The single-company workflow starts after this tab.",
                [
                    ("Overview", existing_tabs.get("Overview")),
                    ("Master Watchlist", existing_tabs.get("Master Watchlist")),
                    ("Data Quality", existing_tabs.get("Data Quality")),
                ],
            ),
            "0. Idea Funnel",
        )

        self.center_tabs.addTab(
            self.make_notes_panel(
                "1. Thesis",
                "Start here after selecting one company from the Idea Funnel. State why you think the stock can go up before doing the deeper work.",
                "One-sentence thesis:\n"
                "Why I think this stock will go up:\n"
                "What has to happen for the thesis to work:\n"
                "What the market may be missing:\n"
                "Why now:\n"
                "What would make me stop researching it:\n"
                "What would prove the thesis wrong:\n",
            ),
            "1. Thesis",
        )

        self.center_tabs.addTab(
            self.make_notes_panel(
                "2. Business",
                "Start with the business, not the stock price.",
                "What does the company sell?\n"
                "Who are the customers?\n"
                "Why do customers choose it?\n"
                "Recurring, cyclical, regulated, or one-time demand?\n"
                "Does the company have pricing power?\n"
                "Key cost drivers:\n"
                "Main competitors:\n"
                "Obsolescence risk:\n"
                "What must go right for the company to keep growing?\n"
                "Five-sentence business explanation:\n",
            ),
            "2. Business",
        )

        self.center_tabs.addTab(
            self.make_nested_tab_panel(
                "3. Filing Review",
                "Use filings as the source of truth. Read what changed, not only the numbers.",
                [
                    (
                        "Checklist",
                        self.make_notes_panel(
                            "Filing checklist",
                            "Track the filing work required before a serious thesis.",
                            "Latest 10-K reviewed?\n"
                            "Latest 10-Q reviewed?\n"
                            "Recent 8-Ks reviewed?\n"
                            "Proxy reviewed?\n"
                            "Earnings call reviewed?\n"
                            "Investor presentation reviewed as management marketing?\n"
                            "Risk factors notes:\n"
                            "MD&A notes:\n"
                            "Financial statements / notes:\n"
                            "Liquidity / debt maturities:\n"
                            "Segment reporting:\n"
                            "Customer concentration:\n"
                            "Legal proceedings:\n"
                            "Related-party transactions:\n"
                            "SBC / share-count changes:\n"
                            "Executive compensation / insider ownership:\n"
                        ),
                    ),
                    ("API Cache", existing_tabs.get("API Cache")),
                ],
            ),
            "3. Filing Review",
        )

        self.center_tabs.addTab(
            self.make_nested_tab_panel(
                "4. Historical Picture",
                "Build the 3-5 year operating picture and look for trend changes.",
                [
                    ("Historical Fundamentals", existing_tabs.get("Historical Fundamentals")),
                    ("Market Data", existing_tabs.get("Market Data")),
                    (
                        "Trend Notes",
                        self.make_notes_panel(
                            "Historical trend notes",
                            "Summarize the operating history in plain English.",
                            "Revenue trend:\n"
                            "Gross margin trend:\n"
                            "Operating margin trend:\n"
                            "Net income trend:\n"
                            "Operating cash flow trend:\n"
                            "Capex / FCF trend:\n"
                            "Cash / debt / current ratio trend:\n"
                            "Share count / dilution trend:\n"
                            "SBC as % of revenue:\n"
                            "ROIC, if meaningful:\n"
                            "Main concern from history:\n",
                        ),
                    ),
                ],
            ),
            "4. Historical Picture",
        )

        self.center_tabs.addTab(
            self.make_nested_tab_panel(
                "5. Business Quality",
                "Judge whether the business is durable, improving, fragile, or deteriorating.",
                [
                    ("Score Details", existing_tabs.get("Score Details")),
                    ("Model Readiness", existing_tabs.get("Model Readiness")),
                    (
                        "Quality Notes",
                        self.make_notes_panel(
                            "Business quality notes",
                            "Add qualitative judgment that the score alone cannot capture.",
                            "Durable revenue growth?\n"
                            "High or improving gross margins?\n"
                            "Positive operating leverage?\n"
                            "Positive free cash flow?\n"
                            "Strong balance sheet?\n"
                            "Low dilution?\n"
                            "Pricing power?\n"
                            "Recurring/repeat demand?\n"
                            "Competitive advantage:\n"
                            "Management/capital allocation notes:\n"
                            "Main quality weakness:\n",
                        ),
                    ),
                ],
            ),
            "5. Business Quality",
        )

        self.center_tabs.addTab(
            self.make_notes_panel(
                "6. Commercial Reality",
                "Use this especially for future-tech and physical-product companies.",
                "Commercial reality stage: Real business / Early commercial / Pre-commercial / Concept-speculation\n"
                "Is there a real product today?\n"
                "Is revenue material or mostly future promises?\n"
                "Are customers paying now?\n"
                "Repeat buyers or one-time pilots?\n"
                "Are gross margins positive and improving?\n"
                "Does the company need constant capital raises?\n"
                "Is the technology proven outside demos?\n"
                "Regulatory approval risk:\n"
                "Infrastructure dependency:\n"
                "Commercialization timeline:\n"
                "Can larger competitors copy/outspend it?\n"
                "Owns manufacturing capacity or depends on partners?\n"
                "Unit economics proven at scale?\n"
                "Do partnerships produce meaningful revenue or just headlines?\n"
                "Position-size implication:\n",
            ),
            "6. Commercial Reality",
        )

        self.center_tabs.addTab(
            existing_tabs.get("Peer Comparison") or self.make_missing_panel("Peer Comparison"),
            "7. Peer Comparison",
        )

        self.center_tabs.addTab(
            self.make_notes_panel(
                "8. Valuation",
                "Build bear/base/bull valuation and decide what assumptions must be true.",
                "Primary method: EV/Revenue / EV/FCF / P/E / DCF / Sum-of-the-parts\n"
                "ETF alternative:\n"
                "EV/Revenue:\n"
                "EV/FCF:\n"
                "P/S:\n"
                "P/E:\n"
                "Peer median:\n"
                "Bear scenario: probability / value / reason\n"
                "Base scenario: probability / value / reason\n"
                "Bull scenario: probability / value / reason\n"
                "Expected value:\n"
                "Current price:\n"
                "Base-case upside:\n"
                "Bear-case downside:\n"
                "Is downside survivable?\n"
                "Current share count:\n"
                "Expected future share count:\n"
                "Upside before dilution:\n"
                "Upside after dilution:\n"
                "What assumptions must be true for the stock to be attractive?\n",
            ),
            "8. Valuation",
        )

        self.center_tabs.addTab(
            self.make_nested_tab_panel(
                "9. Market Behavior",
                "Use price behavior for timing and risk awareness. It is evidence, not the thesis.",
                [
                    ("Price Trends", existing_tabs.get("Price Trends")),
                    ("Price History", existing_tabs.get("Price History")),
                    (
                        "Market Notes",
                        self.make_notes_panel(
                            "Market behavior notes",
                            "Separate entry timing from the actual company thesis.",
                            "1M / 3M / 6M / 1Y return interpretation:\n"
                            "Momentum flag interpretation:\n"
                            "Drawdown interpretation:\n"
                            "Volatility / position-size implication:\n"
                            "What would price action confirm or invalidate?\n",
                        ),
                    ),
                ],
            ),
            "9. Market Behavior",
        )

        self.center_tabs.addTab(
            self.make_notes_panel(
                "10. Variant View",
                "Write why the market may be wrong and what would force a reprice.",
                "Consensus view:\n"
                "My variant view:\n"
                "Evidence:\n"
                "Catalyst:\n"
                "Timeline:\n"
                "Kill criteria / what proves me wrong:\n"
                "Bad-thesis check: Am I relying on hype, TAM, partnerships, price targets, or 'it could 10x'?\n"
            ),
            "10. Variant View",
        )

        self.center_tabs.addTab(
            self.make_notes_panel(
                "11. Decision",
                "Convert the research into a decision bucket. The score points to where to look; the memo decides what to do.",
                "Decision: Pass / Watchlist / Deep Dive / Candidate Position\n"
                "Reason:\n"
                "Required next work:\n"
                "Next review trigger/date:\n"
                "Pre-mortem: This investment failed because...\n"
                "Max position size if it becomes actionable:\n"
                "Max loss / review trigger:\n"
                "Correlated exposures:\n"
                "Why this stock instead of the ETF alternative?\n"
            ),
            "11. Decision",
        )

        self.center_tabs.addTab(
            self.make_notes_panel(
                "12. Portfolio Management",
                "Check whether this stock improves the portfolio after time horizon, role, risk, concentration, sizing, taxes, and ETF alternatives.",
                "Portfolio date:\n"
                "Total portfolio value:\n"
                "Time horizon for this position: 3 months / 1-2 years / 3-5 years\n"
                "Portfolio role: Core / researched individual / speculative future-tech\n"
                "Core ETF / diversified funds target %:\n"
                "Core ETF / diversified funds actual %:\n"
                "Researched individual stocks target %:\n"
                "Researched individual stocks actual %:\n"
                "Speculative future-tech target %:\n"
                "Speculative future-tech actual %:\n"
                "Cash reserve separate? Months covered:\n"
                "Ticker position %:\n"
                "Max allowed %:\n"
                "Theme:\n"
                "Theme exposure after purchase:\n"
                "Theme limit:\n"
                "Largest position:\n"
                "Largest theme:\n"
                "Total speculative exposure:\n"
                "Does this stock still beat the ETF alternative?\n"
                "Would I buy this position again today?\n"
                "Tax issue before buying/selling?\n"
                "Portfolio action: Add / Hold / Reduce / Sell / Rebalance / Do nothing\n",
            ),
            "12. Portfolio Management",
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
