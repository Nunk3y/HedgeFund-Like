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
QMainWindow {
    background-color: #05070b;
}

QWidget#AppRoot {
    background-color: qradialgradient(cx:0.18, cy:0.08, radius:1.25, stop:0 #132033, stop:0.42 #070b12, stop:1 #040507);
    color: #e5e7eb;
    font-family: Segoe UI, Inter, Arial;
    font-size: 10pt;
}

QWidget#TopBar {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #111827, stop:0.45 #0b1120, stop:1 #11151f);
    border: 1px solid #243044;
    border-radius: 24px;
}

QWidget#Sidebar, QWidget#InsightPanel, QWidget#CachePanel, QWidget#DashboardHero {
    background-color: rgba(10, 15, 24, 235);
    border: 1px solid #233044;
    border-radius: 24px;
}

QWidget#MetricCard {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #101827, stop:1 #0b1019);
    border: 1px solid #28364d;
    border-radius: 20px;
}

QWidget#ActionGroup {
    background-color: #090d14;
    border: 1px solid #1f2937;
    border-radius: 18px;
}

QSplitter::handle {
    background-color: transparent;
    width: 12px;
}

QLabel {
    color: #e5e7eb;
}

QLabel#AppTitle {
    color: #f8fafc;
    font-size: 31px;
    font-weight: 850;
    letter-spacing: 0.5px;
}

QLabel#AppSubtitle {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2px;
}

QLabel#Eyebrow {
    color: #7dd3fc;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1.8px;
}

QLabel#HeroTitle {
    color: #f8fafc;
    font-size: 28px;
    font-weight: 850;
}

QLabel#HeroSubtitle {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 500;
}

QLabel#SectionTitle {
    color: #f8fafc;
    font-size: 15px;
    font-weight: 800;
}

QLabel#SectionHint {
    color: #667085;
    font-size: 9px;
    font-weight: 600;
}

QLabel#MetricLabel {
    color: #8fa0b8;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1.1px;
}

QLabel#MetricValue {
    color: #f8fafc;
    font-size: 28px;
    font-weight: 850;
}

QLabel#MetricSubtext {
    color: #64748b;
    font-size: 9px;
    font-weight: 600;
}

QLabel#PremiumBadge {
    color: #fde68a;
    background-color: #2a2110;
    border: 1px solid #8a6f2a;
    border-radius: 15px;
    padding: 8px 13px;
    font-weight: 850;
    letter-spacing: 0.6px;
}

QLineEdit, QComboBox {
    background-color: #0d1320;
    border: 1px solid #263349;
    padding: 10px 12px;
    border-radius: 13px;
    color: #f8fafc;
    selection-background-color: #2563eb;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #60a5fa;
    background-color: #111827;
}

QComboBox::drop-down {
    border: 0px;
    width: 28px;
}

QPushButton {
    background-color: #121a28;
    color: #e5e7eb;
    border: 1px solid #2a3952;
    padding: 10px 13px;
    border-radius: 13px;
    font-weight: 750;
}

QPushButton:hover {
    background-color: #1b2638;
    border: 1px solid #40536f;
}

QPushButton:pressed {
    background-color: #0b1019;
}

QPushButton#PrimaryButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
    border: 1px solid #60a5fa;
    color: #ffffff;
}

QPushButton#PrimaryButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #6d28d9);
}

QPushButton#DangerButton {
    background-color: #261016;
    border: 1px solid #7f1d1d;
    color: #fecaca;
}

QPushButton#DangerButton:hover {
    background-color: #3a141c;
    border: 1px solid #991b1b;
}

QPushButton#QuietButton {
    background-color: #0d1320;
    border: 1px solid #263349;
    color: #cbd5e1;
}

QTableWidget {
    background-color: #080c13;
    alternate-background-color: #0d1320;
    color: #dbe4ef;
    gridline-color: #111827;
    border: 1px solid #223047;
    border-radius: 18px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #111827;
}

QTableWidget::item:hover {
    background-color: #111827;
}

QHeaderView::section {
    background-color: #101827;
    color: #9aa8bd;
    padding: 10px 9px;
    border: 0px;
    border-bottom: 1px solid #2b3a52;
    font-weight: 800;
}

QHeaderView::section:hover {
    background-color: #152033;
    color: #f8fafc;
}

QTabWidget::pane {
    border: 1px solid #223047;
    border-radius: 22px;
    background-color: #070b12;
    top: -1px;
}

QTabBar::tab {
    background-color: #0a0f18;
    color: #8fa0b8;
    padding: 12px 18px;
    margin-right: 7px;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    border: 1px solid #1f2937;
    font-weight: 800;
}

QTabBar::tab:selected {
    background-color: #111827;
    color: #f8fafc;
    border-bottom: 1px solid #111827;
}

QTabBar::tab:hover:!selected {
    background-color: #0f172a;
    color: #cbd5e1;
}

QTextEdit {
    background-color: #080c13;
    border: 1px solid #223047;
    border-radius: 18px;
    color: #dbe4ef;
    padding: 13px;
    line-height: 150%;
    selection-background-color: #2563eb;
}

QScrollBar:vertical {
    background-color: transparent;
    width: 14px;
    margin: 6px 3px 6px 3px;
}

QScrollBar::handle:vertical {
    background-color: #293548;
    border: 3px solid #080c13;
    border-radius: 7px;
    min-height: 44px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4b5f7a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
    border: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 14px;
    margin: 3px 6px 3px 6px;
}

QScrollBar::handle:horizontal {
    background-color: #293548;
    border: 3px solid #080c13;
    border-radius: 7px;
    min-width: 44px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4b5f7a;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background: none;
    border: none;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}
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
    card.setObjectName("MetricCard")
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
    "Overall Flag",
    "Deep Dive Action",
    "Valuation Flag",
    "Quality Flag",
    "Balance Sheet Flag",
    "Dilution Flag",
    "Data Confidence Flag",
    "Overall Peer Flag",
    "Relative Valuation Flag",
    "Relative Quality Flag",
    "Relative Balance Flag",
    "Readiness",
}


DEFAULT_SEC_USER_AGENT = ""

DEFAULT_PEER_GROUPS = [
    "",
    "AI Hardware / Semiconductors",
    "Semiconductor Manufacturing",
    "Semiconductor Equipment",
    "Semiconductor IP",
    "AI Infrastructure / Servers",
    "SMR / Nuclear",
    "Uranium / Nuclear Fuel",
    "Grid / Electrification",
    "Robotics / Automation",
    "Defense Tech",
    "Space / Satellites",
    "Quantum Computing",
    "Cybersecurity",
    "Cloud / AI Software",
    "Battery / Energy Storage",
    "Advanced Manufacturing",
    "Other / Custom",
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
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        top_bar = QWidget()
        top_bar.setObjectName("TopBar")
        top = QHBoxLayout(top_bar)
        top.setContentsMargins(22, 16, 22, 16)
        title_block = QVBoxLayout()
        title_block.setSpacing(3)
        eyebrow = QLabel("PRIVATE RESEARCH TERMINAL")
        eyebrow.setObjectName("Eyebrow")
        title = QLabel("HedgeFund-Like")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Decision-grade watchlist scoring, peer comparison, and data-quality review for high-conviction technology names")
        subtitle.setObjectName("AppSubtitle")
        title_block.addWidget(eyebrow)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        status_badge = QLabel("PRO WORKSPACE  ·  LOCAL-FIRST  ·  SEC + FINNHUB")
        status_badge.setObjectName("PremiumBadge")
        top.addLayout(title_block)
        top.addStretch()
        top.addWidget(status_badge)
        root_layout.addWidget(top_bar)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left.setObjectName("Sidebar")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)
        left_label = QLabel("Watchlist Control")
        left_label.setObjectName("SectionTitle")
        left_hint = QLabel("Build the universe. Run the pipeline. Let the dashboard force a decision.")
        left_hint.setObjectName("SectionHint")
        left_layout.addWidget(left_label)
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
        form_group_layout.setContentsMargins(13, 13, 13, 13)
        form_group_layout.setSpacing(10)
        form_title = QLabel("Ticker Setup")
        form_title.setObjectName("SectionTitle")
        form_group_layout.addWidget(form_title)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setVerticalSpacing(9)
        self.ticker_input = QLineEdit()
        self.company_input = QLineEdit()
        self.peer_group_input = QComboBox()
        self.peer_group_input.setEditable(True)
        self.peer_group_input.addItems(DEFAULT_PEER_GROUPS)
        self.sec_user_agent = QLineEdit(get_setting("sec_user_agent", DEFAULT_SEC_USER_AGENT))
        self.finnhub_api_key = QLineEdit(get_setting("finnhub_api_key", ""))
        self.sec_user_agent.setPlaceholderText("Name and email for SEC requests; saved locally only")
        self.finnhub_api_key.setPlaceholderText("Paste Finnhub API key; saved locally only")
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
        action_layout.setContentsMargins(13, 13, 13, 13)
        action_layout.setSpacing(9)
        action_title = QLabel("Actions")
        action_title.setObjectName("SectionTitle")
        action_layout.addWidget(action_title)
        buttons = [
            ("Add / Update Ticker", self.add_ticker_clicked, "PrimaryButton"),
            ("Run Full Pipeline", self.run_pipeline_clicked, "PrimaryButton"),
            ("Save API Settings", self.save_api_settings, "QuietButton"),
            ("Delete Selected Ticker", self.delete_selected_ticker_clicked, "DangerButton"),
        ]
        for text, fn, style_name in buttons:
            b = QPushButton(text)
            b.setObjectName(style_name)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            action_layout.addWidget(b)
        left_layout.addWidget(action_group, 2)

        center_tabs = QTabWidget()
        center_tabs.setObjectName("WorkspaceTabs")

        dashboard = QWidget()
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(14, 14, 14, 14)
        dashboard_layout.setSpacing(14)

        hero = QWidget()
        hero.setObjectName("DashboardHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 18, 18, 18)
        hero_layout.setSpacing(12)
        hero_eyebrow = QLabel("SCREENING COMMAND CENTER")
        hero_eyebrow.setObjectName("Eyebrow")
        hero_title = QLabel("Rank the watchlist. Isolate the best setups. Reject weak data.")
        hero_title.setObjectName("HeroTitle")
        hero_subtitle = QLabel("The dashboard summarizes model readiness, scoring, peer signals, and data gaps so each ticker has a clear next action.")
        hero_subtitle.setObjectName("HeroSubtitle")
        hero_layout.addWidget(hero_eyebrow)
        hero_layout.addWidget(hero_title)
        hero_layout.addWidget(hero_subtitle)

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
        dashboard_layout.addWidget(hero)

        self.hud = QTextEdit()
        self.hud.setReadOnly(True)
        dashboard_layout.addWidget(self.hud, 1)
        center_tabs.addTab(dashboard, "Overview")

        self.master_columns = [
            "Ticker", "Final Rank", "Score", "Quality Score", "Valuation Score", "Balance Score",
            "Dilution Score", "FCF Score", "Data Score", "Overall Flag", "Deep Dive Action",
            "Valuation Flag", "Quality Flag", "Balance Sheet Flag", "Dilution Flag", "Data Confidence Flag",
            "Company", "Peer Group", "Price", "Market Cap", "EV", "Revenue", "FCF", "Cash", "Debt",
            "Current Ratio", "Shares Out", "Diluted Shares", "Dilution 1Y", "Dilution 3Y",
            "EV/Revenue", "EV/FCF", "P/S", "P/E", "Beta", "52W High", "52W Low", "Cash Runway",
            "Readiness", "Next Action", "Missing / Weak Areas", "Source Status"
        ]
        self.master_table = QTableWidget()
        self.master_table.setColumnCount(len(self.master_columns))
        self.master_table.setHorizontalHeaderLabels(self.master_columns)
        polish_table(self.master_table)
        center_tabs.addTab(self.master_table, "Master Watchlist")

        self.peer_columns = [
            "Ticker", "Peer Group", "Peer Count", "Overall Peer Flag",
            "Relative Valuation Flag", "Relative Quality Flag", "Relative Balance Flag",
            "EV/Revenue", "Peer Median EV/Revenue",
            "EV/FCF", "Peer Median EV/FCF",
            "P/S", "Peer Median P/S",
            "FCF Margin", "Peer Median FCF Margin",
            "Operating Margin", "Peer Median Operating Margin",
            "Gross Margin", "Peer Median Gross Margin",
            "Current Ratio", "Peer Median Current Ratio",
            "Readiness", "Missing / Weak Areas"
        ]
        self.peer_table = QTableWidget()
        self.peer_table.setColumnCount(len(self.peer_columns))
        self.peer_table.setHorizontalHeaderLabels(self.peer_columns)
        polish_table(self.peer_table)
        center_tabs.addTab(self.peer_table, "Peer Comparison")

        cache_panel = QWidget()
        cache_panel.setObjectName("CachePanel")
        cache_layout = QVBoxLayout(cache_panel)
        cache_layout.setContentsMargins(14, 14, 14, 14)
        cache_tools = QHBoxLayout()
        cache_label = QLabel("API Cache")
        cache_label.setObjectName("SectionTitle")
        cache_tools.addWidget(cache_label)
        self.cache_filter_input = QLineEdit()
        self.cache_filter_input.setPlaceholderText("Filter visible cache rows, e.g. cash, capex, operating, expenditures")
        self.cache_filter_input.textChanged.connect(lambda _: self.refresh_cache_table(self.current_ticker() or None))
        cache_tools.addWidget(self.cache_filter_input)
        cache_layout.addLayout(cache_tools)
        self.cache_table = QTableWidget()
        self.cache_table.setColumnCount(10)
        self.cache_table.setHorizontalHeaderLabels(["Ticker", "Source", "Endpoint", "Field", "Value", "FY", "Status", "Concept", "Unit", "Filed"])
        polish_table(self.cache_table)
        cache_layout.addWidget(self.cache_table)
        center_tabs.addTab(cache_panel, "API Cache")

        self.market_columns = [
            "ticker","company","peer_group","price_per_share","market_cap_raw","enterprise_value_raw","shares_out_raw","diluted_shares_raw",
            "high_52w","low_52w","beta","avg_volume_shares","pe_ratio","eps_market",
            "revenue_raw","gross_profit_raw","operating_income_raw","ebitda_raw","net_income_raw","eps_diluted",
            "operating_cash_flow_raw","capex_raw","fcf_raw","cash_raw","debt_raw","net_debt_raw",
            "current_ratio","equity_raw","sbc_raw","rd_raw","sga_raw","dilution_1y","dilution_3y","source_status"
        ]
        self.market_table = QTableWidget()
        self.market_table.setColumnCount(len(self.market_columns))
        self.market_table.setHorizontalHeaderLabels(self.market_columns)
        polish_table(self.market_table)
        center_tabs.addTab(self.market_table, "Market Data")

        self.readiness_columns = [
            "ticker","company","peer_group","price_ok","market_cap_ok","shares_ok","revenue_ok","gross_profit_ok","ebitda_ok","fcf_ok",
            "cash_ok","debt_ok","liquidity_ok","dilution_ok","sbc_rd_sga_ok","core_data_score","readiness","next_action","missing_weak_areas"
        ]
        self.readiness_table = QTableWidget()
        self.readiness_table.setColumnCount(len(self.readiness_columns))
        self.readiness_table.setHorizontalHeaderLabels(self.readiness_columns)
        polish_table(self.readiness_table)
        center_tabs.addTab(self.readiness_table, "Model Readiness")

        right = QWidget()
        right.setObjectName("InsightPanel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)
        right_label = QLabel("Decision Brief")
        right_label.setObjectName("SectionTitle")
        right_hint = QLabel("Current ticker context, pipeline results, and next-action guidance.")
        right_hint.setObjectName("SectionHint")
        right_layout.addWidget(right_label)
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
            "The Overview tab ranks names by score and highlights candidates that deserve deeper research."
        )
        right_layout.addWidget(self.details)

        splitter.addWidget(left)
        splitter.addWidget(center_tabs)
        splitter.addWidget(right)
        splitter.setSizes([420, 980, 360])
        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

        self.selected_ticker = None
        self.refresh_all_tables()

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
        self.ticker_input.clear(); self.company_input.clear(); self.peer_group_input.setCurrentText("")
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
        self.details.setText(f"{self.selected_ticker}\n\nSelected. Run the full pipeline or inspect existing data in the workspace tabs.")
        self.refresh_all_tables(self.selected_ticker)

    def refresh_sec_clicked(self) -> None:
        ticker = self.current_ticker()
        if not ticker:
            QMessageBox.warning(self, "No ticker selected", "Select a ticker or enter one."); return
        ua = self.sec_user_agent.text().strip()
        if not ua or "@" not in ua:
            QMessageBox.warning(self, "SEC User-Agent required", "Enter your name and email."); return
        try:
            self.save_api_settings()
            self.details.setText(f"Refreshing SEC data for {ticker}..."); QApplication.processEvents()
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
            QMessageBox.warning(self, "No ticker selected", "Select a ticker or enter one."); return
        key = self.finnhub_api_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Finnhub API key required", "Paste your Finnhub API key."); return
        try:
            self.save_api_settings()
            self.details.setText(f"Refreshing Finnhub data for {ticker}..."); QApplication.processEvents()
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
            QMessageBox.warning(self, "No ticker selected", "Select a ticker or enter one."); return
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
            self.details.setText(f"Running full pipeline for {ticker}..."); QApplication.processEvents()
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
            filtered = []
            for row in rows:
                haystack = " ".join(str(row[col] or "") for col in ["ticker", "source", "endpoint", "raw_field", "raw_value", "fiscal_year", "status", "sec_concept", "unit", "filed"]).lower()
                if query in haystack:
                    filtered.append(row)
            rows = filtered

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
                        item.setBackground(bg); item.setForeground(fg)
                if col == "Deep Dive Action":
                    bg, fg = flag_colors(str(row.get("Overall Flag", "")))
                    if bg is not None:
                        item.setBackground(bg); item.setForeground(fg)
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
                        item.setBackground(bg); item.setForeground(fg)
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
        high_quality_expensive = [
            r for r in ranked_rows
            if str(r.get("Quality Flag", "")).startswith("GREEN") and str(r.get("Valuation Flag", "")).startswith("RED")
        ]
        cheap_but_low_quality = [
            r for r in ranked_rows
            if str(r.get("Valuation Flag", "")).startswith("GREEN") and str(r.get("Quality Flag", "")).startswith("RED")
        ]

        cheapest = [p for p in peers if str(p.get("Relative Valuation Flag", "")).startswith("GREEN")]
        strongest = [p for p in peers if str(p.get("Relative Quality Flag", "")).startswith("GREEN") or str(p.get("Relative Balance Flag", "")).startswith("GREEN")]
        warnings = [r for r in rows if str(r.get("Data Confidence Flag", "")).startswith("GRAY") or str(r.get("Overall Flag", "")).startswith("GRAY")]

        total = len(rows)
        green = count_matching("GREEN")
        yellow = count_matching("YELLOW")
        gray = count_matching("GRAY")
        best = top_rows[0] if top_rows else None
        self.metric_total.setText(str(total))
        self.metric_total_sub.setText("tracked tickers")
        self.metric_deep_dive.setText(str(green))
        self.metric_deep_dive_sub.setText(f"best: {best['Ticker']}" if best else "green candidates")
        self.metric_watch.setText(str(yellow))
        self.metric_watch_sub.setText("yellow watchlist names")
        self.metric_data.setText(str(gray))
        self.metric_data_sub.setText("needs better source data")

        lines = [
            "EXECUTIVE SUMMARY",
            "",
            "Top Opportunities by Score",
        ]
        if top_rows:
            for idx, r in enumerate(top_rows, start=1):
                lines.append(
                    f"{idx}. {r['Ticker']}  ·  {r.get('Final Rank', '')}  ·  Score {r.get('Score', '')}  ·  "
                    f"{r.get('Deep Dive Action', '')}"
                )
                lines.append(f"   {r.get('Overall Flag', '')}")
        else:
            lines.append("- None yet. Run the pipeline for at least one ticker.")

        lines.extend([
            "",
            "Decision Buckets",
            f"Deep-dive candidates: {tickers_matching('GREEN')}",
            f"Speculative catalyst names: {tickers_matching('PURPLE')}",
            f"Watchlist names: {tickers_matching('YELLOW')}",
            f"Skip/problem names: {tickers_matching('RED')}",
            f"Insufficient-data names: {tickers_matching('GRAY')}",
            "",
            "Needs Better Data",
        ])
        if need_data:
            for r in need_data[:15]:
                lines.append(f"- {r['Ticker']}  ·  Score {r.get('Score', '')}  ·  {r.get('Missing / Weak Areas', '')}")
        else:
            lines.append("- None")

        lines.extend(["", "High Quality but Expensive"])
        if high_quality_expensive:
            for r in high_quality_expensive[:10]:
                lines.append(
                    f"- {r['Ticker']}  ·  Score {r.get('Score', '')}  ·  Quality: {r.get('Quality Flag', '')}  ·  "
                    f"Valuation: {r.get('Valuation Flag', '')}"
                )
        else:
            lines.append("- None")

        lines.extend(["", "Cheap but Low Quality"])
        if cheap_but_low_quality:
            for r in cheap_but_low_quality[:10]:
                lines.append(
                    f"- {r['Ticker']}  ·  Score {r.get('Score', '')}  ·  Valuation: {r.get('Valuation Flag', '')}  ·  "
                    f"Quality: {r.get('Quality Flag', '')}"
                )
        else:
            lines.append("- None")

        lines.extend(["", "Cheapest vs Peer Group"])
        if cheapest:
            for p in cheapest[:15]:
                lines.append(f"- {p['Ticker']}  ·  {p['Peer Group']}  ·  {p['Relative Valuation Flag']}  ·  EV/Revenue {p['EV/Revenue']} vs median {p['Peer Median EV/Revenue']}")
        else:
            lines.append("- None")

        lines.extend(["", "Strong Quality / Balance Peer Signals"])
        if strongest:
            for p in strongest[:15]:
                lines.append(f"- {p['Ticker']}  ·  {p['Peer Group']}  ·  Quality: {p['Relative Quality Flag']}  ·  Balance: {p['Relative Balance Flag']}")
        else:
            lines.append("- None")

        lines.extend(["", "Missing Data / Warning List"])
        if warnings:
            for r in warnings[:20]:
                lines.append(f"- {r['Ticker']}  ·  {r.get('Data Confidence Flag', '')}  ·  {r.get('Missing / Weak Areas', '')}")
        else:
            lines.append("- None")

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