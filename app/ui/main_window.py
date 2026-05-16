import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QSplitter, QTextEdit,
    QTabWidget, QFormLayout, QComboBox, QGridLayout
)

from app.db.database import (
    init_db, add_ticker, delete_ticker, list_tickers, insert_api_cache_rows, list_api_cache,
    list_market_data, list_model_readiness, get_setting, set_setting
)
from app.services.sec_service import refresh_sec_rows
from app.services.finnhub_service import refresh_finnhub_rows
from app.services.market_data_service import normalize_market_data_for_ticker
from app.services.readiness_service import calculate_model_readiness_for_ticker
from app.services.watchlist_service import list_master_watchlist
from app.services.peer_service import list_peer_comparison


DARK_STYLE = """
QMainWindow { background-color: #000000; }
QWidget#AppRoot {
    background-color: qradialgradient(cx:0.50, cy:0.00, radius:1.00, stop:0 #071426, stop:0.42 #02040a, stop:1 #000000);
    color: #f8fafc;
    font-family: Segoe UI, Inter, Arial;
    font-size: 10pt;
}
QWidget#TopNav {
    background-color: rgba(0, 0, 0, 210);
    border-bottom: 1px solid #111827;
}
QWidget#ControlPanel, QWidget#DecisionPanel, QWidget#PreviewShell, QWidget#DashboardCard, QWidget#DataPanel {
    background-color: rgba(5, 9, 16, 238);
    border: 1px solid #1f2937;
    border-radius: 26px;
}
QWidget#MiniCard {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #050914);
    border: 1px solid #263349;
    border-radius: 20px;
}
QWidget#ActionGroup {
    background-color: #030712;
    border: 1px solid #111827;
    border-radius: 20px;
}
QLabel { color: #e5e7eb; }
QLabel#Brand {
    color: #f8fafc;
    font-size: 16px;
    font-weight: 900;
    letter-spacing: 0.2px;
}
QLabel#NavItem {
    color: #94a3b8;
    font-size: 10px;
    font-weight: 750;
    padding: 2px 8px;
}
QLabel#HeroEyebrow {
    color: #60a5fa;
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 2.4px;
}
QLabel#HeroTitle {
    color: #ffffff;
    font-size: 40px;
    font-weight: 900;
    letter-spacing: -0.8px;
}
QLabel#HeroSubtitle {
    color: #cbd5e1;
    font-size: 14px;
    font-weight: 500;
}
QLabel#PanelTitle {
    color: #f8fafc;
    font-size: 15px;
    font-weight: 850;
}
QLabel#PanelHint {
    color: #64748b;
    font-size: 9px;
    font-weight: 650;
}
QLabel#MetricLabel {
    color: #8fa0b8;
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 1.2px;
}
QLabel#MetricValue {
    color: #f8fafc;
    font-size: 30px;
    font-weight: 900;
}
QLabel#MetricSubtext {
    color: #64748b;
    font-size: 9px;
    font-weight: 650;
}
QLabel#Pill {
    color: #bfdbfe;
    background-color: #0b1b33;
    border: 1px solid #1d4ed8;
    border-radius: 14px;
    padding: 7px 12px;
    font-weight: 850;
}
QLineEdit, QComboBox {
    background-color: #050914;
    border: 1px solid #263349;
    padding: 10px 12px;
    border-radius: 13px;
    color: #f8fafc;
    selection-background-color: #2563eb;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #60a5fa;
    background-color: #0b1220;
}
QComboBox::drop-down { border: 0px; width: 28px; }
QPushButton {
    background-color: #0b1220;
    color: #e5e7eb;
    border: 1px solid #263349;
    padding: 10px 14px;
    border-radius: 14px;
    font-weight: 800;
}
QPushButton:hover { background-color: #111827; border: 1px solid #40536f; }
QPushButton:pressed { background-color: #050914; }
QPushButton#HeroButton, QPushButton#PrimaryButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1d4ed8);
    border: 1px solid #60a5fa;
    color: #ffffff;
    padding: 12px 22px;
    border-radius: 18px;
    font-weight: 900;
}
QPushButton#HeroButton:hover, QPushButton#PrimaryButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #2563eb);
}
QPushButton#DangerButton { background-color: #220d14; border: 1px solid #7f1d1d; color: #fecaca; }
QPushButton#DangerButton:hover { background-color: #3a141c; border: 1px solid #991b1b; }
QPushButton#QuietButton { background-color: #050914; border: 1px solid #1f2937; color: #cbd5e1; }
QTableWidget {
    background-color: #02050b;
    alternate-background-color: #060b14;
    color: #dbe4ef;
    gridline-color: #0f172a;
    border: 1px solid #1f2937;
    border-radius: 18px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
}
QTableWidget::item { padding: 8px; border-bottom: 1px solid #0f172a; }
QTableWidget::item:hover { background-color: #101827; }
QHeaderView::section {
    background-color: #050914;
    color: #94a3b8;
    padding: 10px 9px;
    border: 0px;
    border-bottom: 1px solid #263349;
    font-weight: 850;
}
QHeaderView::section:hover { background-color: #101827; color: #ffffff; }
QTabWidget::pane {
    border: 1px solid #111827;
    border-radius: 24px;
    background-color: rgba(2, 5, 11, 225);
    top: -1px;
}
QTabBar::tab {
    background-color: #02050b;
    color: #94a3b8;
    padding: 12px 18px;
    margin-right: 7px;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    border: 1px solid #111827;
    font-weight: 850;
}
QTabBar::tab:selected { background-color: #0b1220; color: #ffffff; border-bottom: 1px solid #0b1220; }
QTabBar::tab:hover:!selected { background-color: #050914; color: #cbd5e1; }
QTextEdit {
    background-color: #02050b;
    border: 1px solid #1f2937;
    border-radius: 18px;
    color: #dbe4ef;
    padding: 14px;
    line-height: 150%;
    selection-background-color: #2563eb;
}
QScrollBar:vertical {
    background-color: #0b111c;
    width: 22px;
    margin: 4px 2px 4px 2px;
    border-radius: 10px;
}
QScrollBar::handle:vertical {
    background-color: #64748b;
    border: 2px solid #0b111c;
    border-radius: 10px;
    min-height: 58px;
}
QScrollBar::handle:vertical:hover { background-color: #94a3b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal {
    background-color: #0b111c;
    height: 22px;
    margin: 2px 4px 2px 4px;
    border-radius: 10px;
}
QScrollBar::handle:horizontal {
    background-color: #64748b;
    border: 2px solid #0b111c;
    border-radius: 10px;
    min-width: 58px;
}
QScrollBar::handle:horizontal:hover { background-color: #94a3b8; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: none; border: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
"""


def fmt(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def flag_colors(text: str):
    text = text or ""
    if text.startswith("GREEN"):
        return QColor("#0d3a24"), QColor("#8ff0b2")
    if text.startswith("YELLOW"):
        return QColor("#40320b"), QColor("#fde68a")
    if text.startswith("RED"):
        return QColor("#40161b"), QColor("#fca5a5")
    if text.startswith("GRAY"):
        return QColor("#1f2937"), QColor("#cbd5e1")
    if text.startswith("PURPLE"):
        return QColor("#311b52"), QColor("#d8b4fe")
    return None, None


def polish_table(table: QTableWidget) -> None:
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.setSortingEnabled(True)
    table.setMouseTracking(True)
    table.setColumnWidth(0, 92)


def make_metric_card(label: str, value: str, subtext: str) -> tuple[QWidget, QLabel, QLabel]:
    card = QWidget()
    card.setObjectName("MiniCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(4)
    label_widget = QLabel(label.upper())
    label_widget.setObjectName("MetricLabel")
    value_widget = QLabel(value)
    value_widget.setObjectName("MetricValue")
    subtext_widget = QLabel(subtext)
    subtext_widget.setObjectName("MetricSubtext")
    layout.addWidget(label_widget)
    layout.addWidget(value_widget)
    layout.addWidget(subtext_widget)
    return card, value_widget, subtext_widget


FLAG_COLUMNS = {
    "Overall Flag", "Deep Dive Action", "Valuation Flag", "Quality Flag", "Balance Sheet Flag",
    "Dilution Flag", "Data Confidence Flag", "Overall Peer Flag", "Relative Valuation Flag",
    "Relative Quality Flag", "Relative Balance Flag", "Readiness",
}

DEFAULT_SEC_USER_AGENT = ""

DEFAULT_PEER_GROUPS = [
    "", "AI Hardware / Semiconductors", "Semiconductor Manufacturing", "Semiconductor Equipment",
    "Semiconductor IP", "AI Infrastructure / Servers", "SMR / Nuclear", "Uranium / Nuclear Fuel",
    "Grid / Electrification", "Robotics / Automation", "Defense Tech", "Space / Satellites",
    "Quantum Computing", "Cybersecurity", "Cloud / AI Software", "Battery / Energy Storage",
    "Advanced Manufacturing", "Other / Custom",
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HedgeFund-Like")
        self.resize(1760, 1020)
        self.setStyleSheet(DARK_STYLE)

        root = QWidget()
        root.setObjectName("AppRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        nav = QWidget()
        nav.setObjectName("TopNav")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(18, 8, 18, 8)
        nav_layout.setSpacing(18)
        brand = QLabel("HedgeFund-Like")
        brand.setObjectName("Brand")
        nav_layout.addWidget(brand)
        for label in ["Overview", "Watchlist", "Peers", "Data", "Settings"]:
            item = QLabel(label)
            item.setObjectName("NavItem")
            nav_layout.addWidget(item)
        nav_layout.addStretch()
        pill = QLabel("LOCAL-FIRST · PRIVATE DATA")
        pill.setObjectName("Pill")
        nav_layout.addWidget(pill)
        root_layout.addWidget(nav)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        left.setObjectName("ControlPanel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)
        left_title = QLabel("Watchlist Control")
        left_title.setObjectName("PanelTitle")
        left_hint = QLabel("Add tickers, assign peer groups, then run the full local pipeline.")
        left_hint.setObjectName("PanelHint")
        left_layout.addWidget(left_title)
        left_layout.addWidget(left_hint)

        self.watchlist_table = QTableWidget()
        self.watchlist_table.setColumnCount(3)
        self.watchlist_table.setHorizontalHeaderLabels(["Ticker", "Company", "Peer Group"])
        self.watchlist_table.cellClicked.connect(self.watchlist_clicked)
        polish_table(self.watchlist_table)
        left_layout.addWidget(self.watchlist_table, 3)

        form_group = QWidget()
        form_group.setObjectName("ActionGroup")
        form_group_layout = QVBoxLayout(form_group)
        form_group_layout.setContentsMargins(14, 14, 14, 14)
        form_group_layout.setSpacing(10)
        setup_title = QLabel("Ticker Setup")
        setup_title.setObjectName("PanelTitle")
        form_group_layout.addWidget(setup_title)
        form = QFormLayout()
        form.setVerticalSpacing(9)
        self.ticker_input = QLineEdit()
        self.company_input = QLineEdit()
        self.peer_group_input = QComboBox()
        self.peer_group_input.setEditable(True)
        self.peer_group_input.addItems(DEFAULT_PEER_GROUPS)
        self.sec_user_agent = QLineEdit(get_setting("sec_user_agent", DEFAULT_SEC_USER_AGENT))
        self.finnhub_api_key = QLineEdit(get_setting("finnhub_api_key", ""))
        self.sec_user_agent.setPlaceholderText("SEC User-Agent; local only")
        self.finnhub_api_key.setPlaceholderText("Finnhub API key; local only")
        self.sec_user_agent.editingFinished.connect(self.save_api_settings_silent)
        self.finnhub_api_key.editingFinished.connect(self.save_api_settings_silent)
        self.ticker_input.setPlaceholderText("NVDA")
        self.company_input.setPlaceholderText("Optional company name")
        form.addRow("Ticker", self.ticker_input)
        form.addRow("Company", self.company_input)
        form.addRow("Peer Group", self.peer_group_input)
        form.addRow("SEC User-Agent", self.sec_user_agent)
        form.addRow("Finnhub API Key", self.finnhub_api_key)
        form_group_layout.addLayout(form)
        left_layout.addWidget(form_group, 2)

        action_group = QWidget()
        action_group.setObjectName("ActionGroup")
        action_layout = QVBoxLayout(action_group)
        action_layout.setContentsMargins(14, 14, 14, 14)
        action_layout.setSpacing(9)
        action_title = QLabel("Actions")
        action_title.setObjectName("PanelTitle")
        action_layout.addWidget(action_title)
        for text, fn, style_name in [
            ("Add / Update Ticker", self.add_ticker_clicked, "PrimaryButton"),
            ("Run Full Pipeline", self.run_pipeline_clicked, "PrimaryButton"),
            ("Save API Settings", self.save_api_settings, "QuietButton"),
            ("Delete Selected Ticker", self.delete_selected_ticker_clicked, "DangerButton"),
        ]:
            button = QPushButton(text)
            button.setObjectName(style_name)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(fn)
            action_layout.addWidget(button)
        left_layout.addWidget(action_group, 2)

        center_tabs = QTabWidget()
        center_tabs.setObjectName("WorkspaceTabs")
        self.build_overview_tab(center_tabs)
        self.build_data_tabs(center_tabs)

        right = QWidget()
        right.setObjectName("DecisionPanel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)
        right_title = QLabel("Decision Brief")
        right_title.setObjectName("PanelTitle")
        right_hint = QLabel("Selected ticker context and pipeline result.")
        right_hint.setObjectName("PanelHint")
        right_layout.addWidget(right_title)
        right_layout.addWidget(right_hint)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setText(
            "Select a ticker to begin.\n\n"
            "Workflow\n"
            "1. Add or select a ticker.\n"
            "2. Assign the correct peer group.\n"
            "3. Enter API settings once. They are stored only in your local tech_screener.db file.\n"
            "4. Run the full pipeline.\n\n"
            "The Overview tab ranks names by score and highlights candidates for deeper research."
        )
        right_layout.addWidget(self.details)

        splitter.addWidget(left)
        splitter.addWidget(center_tabs)
        splitter.addWidget(right)
        splitter.setSizes([390, 1040, 330])
        main_layout.addWidget(splitter)
        root_layout.addWidget(main)
        self.setCentralWidget(root)

        self.selected_ticker = None
        self.refresh_all_tables()

    def build_overview_tab(self, tabs: QTabWidget) -> None:
        overview = QWidget()
        layout = QVBoxLayout(overview)
        layout.setContentsMargins(20, 22, 20, 20)
        layout.setSpacing(18)

        hero = QWidget()
        hero.setObjectName("PreviewShell")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(34, 30, 34, 30)
        hero_layout.setSpacing(16)

        eyebrow = QLabel("SCREEN. RANK. RESEARCH. REPEAT.")
        eyebrow.setObjectName("HeroEyebrow")
        eyebrow.setAlignment(Qt.AlignCenter)
        title = QLabel("Find asymmetric stock setups before the market prices them in.")
        title.setObjectName("HeroTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        subtitle = QLabel(
            "Run SEC + Finnhub data through a local scoring model to rank quality, valuation, balance sheet strength, dilution risk, and data confidence."
        )
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        hero_button_row = QHBoxLayout()
        hero_button_row.addStretch()
        hero_button = QPushButton("Run Full Pipeline")
        hero_button.setObjectName("HeroButton")
        hero_button.setCursor(Qt.PointingHandCursor)
        hero_button.clicked.connect(self.run_pipeline_clicked)
        hero_button_row.addWidget(hero_button)
        hero_button_row.addStretch()
        hero_layout.addWidget(eyebrow)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        hero_layout.addLayout(hero_button_row)

        metric_grid = QGridLayout()
        metric_grid.setSpacing(12)
        card, self.metric_total, self.metric_total_sub = make_metric_card("Universe", "0", "tracked tickers")
        metric_grid.addWidget(card, 0, 0)
        card, self.metric_deep_dive, self.metric_deep_dive_sub = make_metric_card("Deep Dive", "0", "green candidates")
        metric_grid.addWidget(card, 0, 1)
        card, self.metric_watch, self.metric_watch_sub = make_metric_card("Watch", "0", "yellow names")
        metric_grid.addWidget(card, 0, 2)
        card, self.metric_data, self.metric_data_sub = make_metric_card("Needs Data", "0", "gray names")
        metric_grid.addWidget(card, 0, 3)
        hero_layout.addLayout(metric_grid)
        layout.addWidget(hero)

        dashboard = QWidget()
        dashboard.setObjectName("DashboardCard")
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(18, 18, 18, 18)
        dashboard_layout.setSpacing(10)
        dash_title = QLabel("Research Dashboard Preview")
        dash_title.setObjectName("PanelTitle")
        dash_hint = QLabel("Readable screening views stay separate from raw SEC, Finnhub, cache, and normalized data tabs.")
        dash_hint.setObjectName("PanelHint")
        self.hud = QTextEdit()
        self.hud.setReadOnly(True)
        dashboard_layout.addWidget(dash_title)
        dashboard_layout.addWidget(dash_hint)
        dashboard_layout.addWidget(self.hud, 1)
        layout.addWidget(dashboard, 1)
        tabs.addTab(overview, "Overview")

    def build_data_tabs(self, tabs: QTabWidget) -> None:
        self.master_columns = [
            "Ticker", "Final Rank", "Score", "Quality Score", "Valuation Score", "Balance Score", "Dilution Score",
            "FCF Score", "Data Score", "Overall Flag", "Deep Dive Action", "Valuation Flag", "Quality Flag",
            "Balance Sheet Flag", "Dilution Flag", "Data Confidence Flag", "Company", "Peer Group", "Price",
            "Market Cap", "EV", "Revenue", "FCF", "Cash", "Debt", "Current Ratio", "Shares Out",
            "Diluted Shares", "Dilution 1Y", "Dilution 3Y", "EV/Revenue", "EV/FCF", "P/S", "P/E",
            "Beta", "52W High", "52W Low", "Cash Runway", "Readiness", "Next Action", "Missing / Weak Areas", "Source Status"
        ]
        self.master_table = QTableWidget()
        self.master_table.setColumnCount(len(self.master_columns))
        self.master_table.setHorizontalHeaderLabels(self.master_columns)
        polish_table(self.master_table)
        tabs.addTab(self.master_table, "Master Watchlist")

        self.peer_columns = [
            "Ticker", "Peer Group", "Peer Count", "Overall Peer Flag", "Relative Valuation Flag", "Relative Quality Flag",
            "Relative Balance Flag", "EV/Revenue", "Peer Median EV/Revenue", "EV/FCF", "Peer Median EV/FCF",
            "P/S", "Peer Median P/S", "FCF Margin", "Peer Median FCF Margin", "Operating Margin",
            "Peer Median Operating Margin", "Gross Margin", "Peer Median Gross Margin", "Current Ratio",
            "Peer Median Current Ratio", "Readiness", "Missing / Weak Areas"
        ]
        self.peer_table = QTableWidget()
        self.peer_table.setColumnCount(len(self.peer_columns))
        self.peer_table.setHorizontalHeaderLabels(self.peer_columns)
        polish_table(self.peer_table)
        tabs.addTab(self.peer_table, "Peer Comparison")

        cache_panel = QWidget()
        cache_panel.setObjectName("DataPanel")
        cache_layout = QVBoxLayout(cache_panel)
        cache_layout.setContentsMargins(14, 14, 14, 14)
        cache_tools = QHBoxLayout()
        cache_label = QLabel("API Cache")
        cache_label.setObjectName("PanelTitle")
        cache_tools.addWidget(cache_label)
        self.cache_filter_input = QLineEdit()
        self.cache_filter_input.setPlaceholderText("Filter cache rows: cash, capex, operating, expenditures")
        self.cache_filter_input.textChanged.connect(lambda _: self.refresh_cache_table(self.current_ticker() or None))
        cache_tools.addWidget(self.cache_filter_input)
        cache_layout.addLayout(cache_tools)
        self.cache_table = QTableWidget()
        self.cache_table.setColumnCount(10)
        self.cache_table.setHorizontalHeaderLabels(["Ticker", "Source", "Endpoint", "Field", "Value", "FY", "Status", "Concept", "Unit", "Filed"])
        polish_table(self.cache_table)
        cache_layout.addWidget(self.cache_table)
        tabs.addTab(cache_panel, "API Cache")

        self.market_columns = [
            "ticker", "company", "peer_group", "price_per_share", "market_cap_raw", "enterprise_value_raw",
            "shares_out_raw", "diluted_shares_raw", "high_52w", "low_52w", "beta", "avg_volume_shares",
            "pe_ratio", "eps_market", "revenue_raw", "gross_profit_raw", "operating_income_raw", "ebitda_raw",
            "net_income_raw", "eps_diluted", "operating_cash_flow_raw", "capex_raw", "fcf_raw", "cash_raw",
            "debt_raw", "net_debt_raw", "current_ratio", "equity_raw", "sbc_raw", "rd_raw", "sga_raw",
            "dilution_1y", "dilution_3y", "source_status"
        ]
        self.market_table = QTableWidget()
        self.market_table.setColumnCount(len(self.market_columns))
        self.market_table.setHorizontalHeaderLabels(self.market_columns)
        polish_table(self.market_table)
        tabs.addTab(self.market_table, "Market Data")

        self.readiness_columns = [
            "ticker", "company", "peer_group", "price_ok", "market_cap_ok", "shares_ok", "revenue_ok",
            "gross_profit_ok", "ebitda_ok", "fcf_ok", "cash_ok", "debt_ok", "liquidity_ok", "dilution_ok",
            "sbc_rd_sga_ok", "core_data_score", "readiness", "next_action", "missing_weak_areas"
        ]
        self.readiness_table = QTableWidget()
        self.readiness_table.setColumnCount(len(self.readiness_columns))
        self.readiness_table.setHorizontalHeaderLabels(self.readiness_columns)
        polish_table(self.readiness_table)
        tabs.addTab(self.readiness_table, "Model Readiness")

    def closeEvent(self, event) -> None:
        self.save_api_settings_silent()
        super().closeEvent(event)

    def save_api_settings_silent(self) -> None:
        set_setting("sec_user_agent", self.sec_user_agent.text().strip())
        set_setting("finnhub_api_key", self.finnhub_api_key.text().strip())

    def save_api_settings(self) -> None:
        self.save_api_settings_silent()
        self.details.setText("API settings saved locally in tech_screener.db. They are not saved to GitHub.")

    def current_ticker(self) -> str:
        return (self.selected_ticker or self.ticker_input.text().strip().upper()).upper().strip()

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
        self.refresh_all_tables(ticker)

    def delete_selected_ticker_clicked(self) -> None:
        ticker = self.current_ticker()
        if not ticker:
            QMessageBox.warning(self, "No ticker selected", "Select a ticker from the watchlist first.")
            return
        result = QMessageBox.question(
            self, "Delete ticker", f"Delete {ticker} from the watchlist and remove its cached local data?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return
        delete_ticker(ticker, delete_cached_data=True)
        self.selected_ticker = None
        self.details.setText(f"Deleted {ticker} from the local watchlist and local cached data.")
        self.refresh_all_tables()

    def refresh_watchlist(self) -> None:
        rows = list_tickers()
        self.watchlist_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [row["ticker"], row["company"] or "", row["peer_group"] or row["category"] or ""]
            for c, val in enumerate(values):
                self.watchlist_table.setItem(r, c, QTableWidgetItem(str(val)))
        self.watchlist_table.resizeColumnsToContents()

    def watchlist_clicked(self, row: int, col: int) -> None:
        item = self.watchlist_table.item(row, 0)
        if not item:
            return
        self.selected_ticker = item.text()
        self.details.setText(f"{self.selected_ticker}\n\nSelected. Run the full pipeline or inspect the screening and raw-data tabs.")
        self.refresh_all_tables(self.selected_ticker)

    def refresh_sec_clicked(self) -> None:
        ticker = self.current_ticker()
        if not ticker:
            QMessageBox.warning(self, "No ticker selected", "Select a ticker or enter one.")
            return
        ua = self.sec_user_agent.text().strip()
        if not ua or "@" not in ua:
            QMessageBox.warning(self, "SEC User-Agent required", "Enter your name and email.")
            return
        try:
            self.save_api_settings()
            self.details.setText(f"Refreshing SEC data for {ticker}...")
            QApplication.processEvents()
            rows = refresh_sec_rows(ticker, ua, years=5)
            insert_api_cache_rows(rows, replace_source_for_ticker=True)
            normalize_market_data_for_ticker(ticker)
            calculate_model_readiness_for_ticker(ticker)
            self.selected_ticker = ticker
            self.details.setText(f"{ticker}\n\nSEC refresh complete.\nRows: {len(rows)}\nOK rows: {sum(1 for r in rows if r.get('Status') == 'OK')}\nMarket Data normalized\nReadiness calculated")
            self.refresh_all_tables(ticker)
        except Exception as exc:
            QMessageBox.critical(self, "SEC refresh failed", str(exc))

    def refresh_finnhub_clicked(self) -> None:
        ticker = self.current_ticker()
        if not ticker:
            QMessageBox.warning(self, "No ticker selected", "Select a ticker or enter one.")
            return
        key = self.finnhub_api_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Finnhub API key required", "Paste your Finnhub API key.")
            return
        try:
            self.save_api_settings()
            self.details.setText(f"Refreshing Finnhub data for {ticker}...")
            QApplication.processEvents()
            rows = refresh_finnhub_rows(ticker, key)
            insert_api_cache_rows(rows, replace_source_for_ticker=True)
            normalize_market_data_for_ticker(ticker)
            calculate_model_readiness_for_ticker(ticker)
            self.selected_ticker = ticker
            self.details.setText(f"{ticker}\n\nFinnhub refresh complete.\nRows: {len(rows)}\nOK rows: {sum(1 for r in rows if r.get('Status') == 'OK')}\nMarket Data normalized\nReadiness calculated")
            self.refresh_all_tables(ticker)
        except Exception as exc:
            QMessageBox.critical(self, "Finnhub refresh failed", str(exc))

    def run_pipeline_clicked(self) -> None:
        ticker = self.current_ticker()
        if not ticker:
            QMessageBox.warning(self, "No ticker selected", "Select a ticker or enter one.")
            return
        ua = self.sec_user_agent.text().strip()
        key = self.finnhub_api_key.text().strip()
        if not ua or "@" not in ua:
            QMessageBox.warning(self, "SEC User-Agent required", "Enter your name and email in the SEC User-Agent field. It is saved only in your local database.")
            return
        if not key:
            QMessageBox.warning(self, "Finnhub API key required", "Paste your Finnhub API key before running the full pipeline.")
            return
        try:
            self.save_api_settings()
            self.details.setText(f"Running full pipeline for {ticker}...")
            QApplication.processEvents()
            sec_rows = refresh_sec_rows(ticker, ua, years=5)
            insert_api_cache_rows(sec_rows, replace_source_for_ticker=True)
            fh_rows = refresh_finnhub_rows(ticker, key)
            insert_api_cache_rows(fh_rows, replace_source_for_ticker=True)
            normalize_market_data_for_ticker(ticker)
            calculate_model_readiness_for_ticker(ticker)
            self.selected_ticker = ticker
            self.details.setText(f"{ticker}\n\nPipeline complete:\nSEC rows: {len(sec_rows)}\nFinnhub rows: {len(fh_rows)}\nMarket Data normalized\nReadiness calculated")
            self.refresh_all_tables(ticker)
        except Exception as exc:
            QMessageBox.critical(self, "Pipeline failed", str(exc))
            self.details.setText(f"{ticker}\n\nPipeline failed:\n{exc}")

    def refresh_cache_table(self, ticker=None) -> None:
        rows = list_api_cache(ticker=ticker, limit=500)
        query = self.cache_filter_input.text().strip().lower() if hasattr(self, "cache_filter_input") else ""
        if query:
            rows = [row for row in rows if query in " ".join(str(row[col] or "") for col in ["ticker", "source", "endpoint", "raw_field", "raw_value", "fiscal_year", "status", "sec_concept", "unit", "filed"]).lower()]
        self.cache_table.setSortingEnabled(False)
        self.cache_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [row["ticker"], row["source"], row["endpoint"], row["raw_field"], row["raw_value"], row["fiscal_year"], row["status"], row["sec_concept"], row["unit"], row["filed"]]
            for c, val in enumerate(values):
                self.cache_table.setItem(r, c, QTableWidgetItem("" if val is None else str(val)))
        self.cache_table.setSortingEnabled(True)
        self.cache_table.resizeColumnsToContents()

    def refresh_market_table(self, ticker=None) -> None:
        rows = list_market_data(ticker=ticker)
        self.market_table.setSortingEnabled(False)
        self.market_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, col in enumerate(self.market_columns):
                self.market_table.setItem(r, c, QTableWidgetItem(fmt(row[col])))
        self.market_table.setSortingEnabled(True)
        self.market_table.resizeColumnsToContents()

    def refresh_readiness_table(self, ticker=None) -> None:
        rows = list_model_readiness(ticker=ticker)
        self.readiness_table.setSortingEnabled(False)
        self.readiness_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, col in enumerate(self.readiness_columns):
                self.readiness_table.setItem(r, c, QTableWidgetItem(fmt(row[col])))
        self.readiness_table.setSortingEnabled(True)
        self.readiness_table.resizeColumnsToContents()

    def refresh_master_table(self) -> None:
        rows = list_master_watchlist()
        self.master_table.setSortingEnabled(False)
        self.master_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, col in enumerate(self.master_columns):
                text = str(row.get(col, ""))
                item = QTableWidgetItem(text)
                if col in FLAG_COLUMNS:
                    bg, fg = flag_colors(text)
                    if bg is not None:
                        item.setBackground(bg)
                        item.setForeground(fg)
                if col == "Deep Dive Action":
                    bg, fg = flag_colors(str(row.get("Overall Flag", "")))
                    if bg is not None:
                        item.setBackground(bg)
                        item.setForeground(fg)
                self.master_table.setItem(r, c, item)
        self.master_table.setSortingEnabled(True)
        self.master_table.resizeColumnsToContents()

    def refresh_peer_table(self) -> None:
        rows = list_peer_comparison()
        self.peer_table.setSortingEnabled(False)
        self.peer_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, col in enumerate(self.peer_columns):
                text = str(row.get(col, ""))
                item = QTableWidgetItem(text)
                if col in FLAG_COLUMNS:
                    bg, fg = flag_colors(text)
                    if bg is not None:
                        item.setBackground(bg)
                        item.setForeground(fg)
                self.peer_table.setItem(r, c, item)
        self.peer_table.setSortingEnabled(True)
        self.peer_table.resizeColumnsToContents()

    def refresh_hud_panel(self) -> None:
        rows = list_master_watchlist()
        peers = list_peer_comparison()

        def tickers_matching(prefix: str, limit: int = 20) -> str:
            vals = [r["Ticker"] for r in rows if str(r.get("Overall Flag", "")).startswith(prefix)]
            return ", ".join(vals[:limit]) if vals else "None"

        def count_matching(prefix: str) -> int:
            return sum(1 for r in rows if str(r.get("Overall Flag", "")).startswith(prefix))

        def score_value(row) -> int:
            try:
                return int(row.get("Score") or 0)
            except Exception:
                return 0

        ranked_rows = sorted(rows, key=score_value, reverse=True)
        top_rows = [r for r in ranked_rows if score_value(r) > 0][:10]
        need_data = [r for r in rows if str(r.get("Final Rank", "")) == "NEEDS DATA" or str(r.get("Overall Flag", "")).startswith("GRAY")]
        high_quality_expensive = [r for r in ranked_rows if str(r.get("Quality Flag", "")).startswith("GREEN") and str(r.get("Valuation Flag", "")).startswith("RED")]
        cheap_but_low_quality = [r for r in ranked_rows if str(r.get("Valuation Flag", "")).startswith("GREEN") and str(r.get("Quality Flag", "")).startswith("RED")]
        cheapest = [p for p in peers if str(p.get("Relative Valuation Flag", "")).startswith("GREEN")]
        strongest = [p for p in peers if str(p.get("Relative Quality Flag", "")).startswith("GREEN") or str(p.get("Relative Balance Flag", "")).startswith("GREEN")]
        warnings = [r for r in rows if str(r.get("Data Confidence Flag", "")).startswith("GRAY") or str(r.get("Overall Flag", "")).startswith("GRAY")]

        best = top_rows[0] if top_rows else None
        self.metric_total.setText(str(len(rows)))
        self.metric_deep_dive.setText(str(count_matching("GREEN")))
        self.metric_deep_dive_sub.setText(f"best: {best['Ticker']}" if best else "green candidates")
        self.metric_watch.setText(str(count_matching("YELLOW")))
        self.metric_data.setText(str(count_matching("GRAY")))

        lines = ["EXECUTIVE SUMMARY", "", "Top Opportunities by Score"]
        if top_rows:
            for idx, r in enumerate(top_rows, start=1):
                lines.append(f"{idx}. {r['Ticker']}  ·  {r.get('Final Rank', '')}  ·  Score {r.get('Score', '')}  ·  {r.get('Deep Dive Action', '')}")
                lines.append(f"   {r.get('Overall Flag', '')}")
        else:
            lines.append("- None yet. Add/select a ticker and run the pipeline.")

        lines.extend([
            "", "Decision Buckets",
            f"Deep-dive candidates: {tickers_matching('GREEN')}",
            f"Speculative catalyst names: {tickers_matching('PURPLE')}",
            f"Watchlist names: {tickers_matching('YELLOW')}",
            f"Skip/problem names: {tickers_matching('RED')}",
            f"Insufficient-data names: {tickers_matching('GRAY')}",
            "", "Needs Better Data",
        ])
        lines.extend([f"- {r['Ticker']}  ·  Score {r.get('Score', '')}  ·  {r.get('Missing / Weak Areas', '')}" for r in need_data[:15]] or ["- None"])
        lines.extend(["", "High Quality but Expensive"])
        lines.extend([f"- {r['Ticker']}  ·  Score {r.get('Score', '')}  ·  Quality: {r.get('Quality Flag', '')}  ·  Valuation: {r.get('Valuation Flag', '')}" for r in high_quality_expensive[:10]] or ["- None"])
        lines.extend(["", "Cheap but Low Quality"])
        lines.extend([f"- {r['Ticker']}  ·  Score {r.get('Score', '')}  ·  Valuation: {r.get('Valuation Flag', '')}  ·  Quality: {r.get('Quality Flag', '')}" for r in cheap_but_low_quality[:10]] or ["- None"])
        lines.extend(["", "Cheapest vs Peer Group"])
        lines.extend([f"- {p['Ticker']}  ·  {p['Peer Group']}  ·  {p['Relative Valuation Flag']}  ·  EV/Revenue {p['EV/Revenue']} vs median {p['Peer Median EV/Revenue']}" for p in cheapest[:15]] or ["- None"])
        lines.extend(["", "Strong Quality / Balance Peer Signals"])
        lines.extend([f"- {p['Ticker']}  ·  {p['Peer Group']}  ·  Quality: {p['Relative Quality Flag']}  ·  Balance: {p['Relative Balance Flag']}" for p in strongest[:15]] or ["- None"])
        lines.extend(["", "Missing Data / Warning List"])
        lines.extend([f"- {r['Ticker']}  ·  {r.get('Data Confidence Flag', '')}  ·  {r.get('Missing / Weak Areas', '')}" for r in warnings[:20]] or ["- None"])
        self.hud.setText("\n".join(lines))

    def refresh_all_tables(self, ticker=None) -> None:
        self.refresh_watchlist()
        self.refresh_master_table()
        self.refresh_peer_table()
        self.refresh_cache_table(ticker)
        self.refresh_market_table(ticker)
        self.refresh_readiness_table(ticker)
        self.refresh_hud_panel()


def run_app() -> None:
    init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())