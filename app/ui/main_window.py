import sys
import ctypes
import html
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.db.database import (
    add_ticker,
    delete_ticker,
    get_setting,
    init_db,
    insert_api_cache_rows,
    insert_price_history_rows,
    list_api_cache,
    list_historical_fundamentals,
    list_market_data,
    list_model_readiness,
    list_price_history,
    list_price_metrics,
    list_tickers,
    set_setting,
)
from app.services.data_quality_service import list_data_quality, list_data_quality_summary
from app.services.finnhub_service import refresh_finnhub_rows
from app.services.historical_data_service import rebuild_historical_fundamentals_for_ticker
from app.services.market_data_service import normalize_market_data_for_ticker
from app.services.peer_service import list_peer_comparison
from app.services.price_data_service import refresh_price_history_rows
from app.services.price_history_service import recalculate_price_metrics_for_ticker
from app.services.readiness_service import calculate_model_readiness_for_ticker
from app.services.repair_service import repair_all_missing_data
from app.services.sec_service import refresh_sec_rows
from app.services.watchlist_service import list_master_watchlist


DARK_STYLE = """
QMainWindow { background-color: #040812; }
QWidget#AppRoot {
    background-color: qradialgradient(cx:0.50, cy:0.00, radius:1.05, stop:0 #123052, stop:0.28 #081426, stop:0.62 #040812, stop:1 #070d18);
    color: #f8fafc;
    font-family: Segoe UI, Inter, Arial;
    font-size: 10pt;
}
QWidget#TopNav {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #081426, stop:0.50 #050a14, stop:1 #0b1728);
    border-bottom: 1px solid #233b5f;
}
QWidget#Workspace {
    background-color: qradialgradient(cx:0.46, cy:0.02, radius:1.15, stop:0 #102a49, stop:0.35 #071426, stop:0.72 #040812, stop:1 #08111f);
}
QWidget#ControlPanel, QWidget#DecisionPanel {
    background-color: #081424;
    border: 1px solid #38506d;
    border-radius: 18px;
}
QWidget#PreviewShell {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #12335c, stop:0.45 #08182c, stop:1 #050914);
    border: 1px solid #5aa6ff;
    border-radius: 20px;
}
QWidget#DashboardCard, QWidget#DataPanel, QWidget#ActionGroup {
    background-color: #07111f;
    border: 1px solid #2f4158;
    border-radius: 16px;
}
QWidget#TabTitleBar {
    background-color: #06101d;
    border: 1px solid #2f4158;
    border-radius: 14px;
}
QWidget#MiniCard {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #13223a, stop:1 #08111f);
    border: 1px solid #4a5f7c;
    border-radius: 14px;
}
QSplitter::handle { background-color: transparent; width: 16px; }
QLabel { color: #e5e7eb; }
QLabel#Brand { color: #ffffff; font-size: 18px; font-weight: 950; }
QLabel#PanelTitle { color: #ffffff; font-size: 16px; font-weight: 900; }
QLabel#PanelHint { color: #a8bad1; font-size: 9px; font-weight: 700; }
QLabel#ActiveTabTitle { color: #ffffff; font-size: 20px; font-weight: 950; }
QLabel#ActiveTabHint { color: #9fb5cf; font-size: 10px; font-weight: 750; }
QLabel#HeroEyebrow { color: #8bc7ff; font-size: 10px; font-weight: 950; letter-spacing: 2.8px; }
QLabel#HeroTitle { color: #ffffff; font-size: 44px; font-weight: 950; letter-spacing: -1.2px; }
QLabel#HeroSubtitle { color: #d9e7f7; font-size: 15px; font-weight: 500; }
QLabel#SignalPill {
    color: #dbeafe;
    background-color: #0b2443;
    border: 1px solid #315b91;
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 0.7px;
}
QLabel#MetricLabel { color: #aab7cc; font-size: 9px; font-weight: 950; letter-spacing: 1.3px; }
QLabel#MetricValue { color: #ffffff; font-size: 32px; font-weight: 950; }
QLabel#MetricSubtext { color: #9fb0c8; font-size: 9px; font-weight: 700; }
QLabel#Pill {
    color: #ffffff;
    background-color: #0f2a4f;
    border: 1px solid #4a90ff;
    border-radius: 10px;
    padding: 8px 13px;
    font-weight: 900;
}
QPushButton#NavButton {
    background-color: transparent;
    border: 1px solid transparent;
    color: #bfd0e6;
    font-size: 10px;
    font-weight: 850;
    padding: 8px 13px;
    border-radius: 10px;
}
QPushButton#NavButton:hover { background-color: #111f34; border: 1px solid #3d5878; color: #ffffff; }
QPushButton#NavButton:pressed { background-color: #1d4ed8; border: 1px solid #93c5fd; color: #ffffff; }
QLineEdit, QComboBox {
    background-color: #030814;
    border: 1px solid #52647e;
    padding: 11px 13px;
    border-radius: 10px;
    color: #f8fafc;
    selection-background-color: #2563eb;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #93c5fd; background-color: #0b1728; }
QComboBox::drop-down { border: 0px; width: 30px; }
QPushButton {
    background-color: #0b1728;
    color: #e5e7eb;
    border: 1px solid #3d506b;
    padding: 11px 15px;
    border-radius: 10px;
    font-weight: 850;
}
QPushButton:hover { background-color: #17263d; border: 1px solid #6e87a8; }
QPushButton:pressed { background-color: #050914; }
QPushButton#PrimaryButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2f6df6, stop:0.48 #2563eb, stop:1 #1d4ed8);
    border: 1px solid #a6d1ff;
    color: #ffffff;
    font-weight: 950;
}
QPushButton#DangerButton { background-color: #220d14; border: 1px solid #991b1b; color: #fecaca; }
QPushButton#DangerButton:hover { background-color: #3a141c; border: 1px solid #ef4444; }
QPushButton#QuietButton { background-color: #06101d; border: 1px solid #3d506b; color: #cbd5e1; }
QTableWidget {
    background-color: #030814;
    alternate-background-color: #0a1424;
    color: #e5e7eb;
    gridline-color: #172033;
    border: 1px solid #3c516d;
    border-radius: 12px;
    selection-background-color: #174ea6;
    selection-color: #ffffff;
}
QTableWidget::viewport { background-color: #030814; }
QTableWidget::item { padding: 8px; border-bottom: 1px solid #172033; }
QTableWidget::item:hover { background-color: #111f34; }
QTableWidget::item:selected { background-color: #174ea6; color: #ffffff; }
QHeaderView { background-color: #030814; }
QHeaderView::section {
    background-color: #101b2d;
    color: #d4e2f4;
    padding: 11px 10px;
    border: 0px;
    border-bottom: 1px solid #3c516d;
    border-right: 1px solid #22334a;
    font-weight: 900;
}
QHeaderView::section:vertical {
    background-color: #0b1728;
    color: #ffffff;
    border-bottom: 1px solid #26384f;
    border-right: 1px solid #3c516d;
    font-weight: 950;
}
QTableCornerButton::section {
    background-color: #101b2d;
    border: 0px;
    border-bottom: 1px solid #3c516d;
    border-right: 1px solid #3c516d;
}
QTabWidget::pane {
    border: 1px solid #3c516d;
    border-radius: 16px;
    background-color: #050b16;
    top: -1px;
}
QTabBar::tab {
    background-color: #06101d;
    color: #9fb0c8;
    padding: 10px 12px;
    margin-right: 4px;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    border: 1px solid #2f4158;
    font-size: 9px;
    font-weight: 900;
}
QTabBar::tab:selected { background-color: #173557; color: #ffffff; border: 1px solid #5aa6ff; border-bottom: 1px solid #173557; }
QTabBar::tab:hover:!selected { background-color: #0b1728; border: 1px solid #426183; color: #e5e7eb; }
QTextEdit {
    background-color: #030814;
    border: 1px solid #3c516d;
    border-radius: 12px;
    color: #e5e7eb;
    padding: 15px;
    line-height: 150%;
    selection-background-color: #2563eb;
}
QTextEdit#Hud {
    background-color: #020714;
    border: 1px solid #426183;
    border-radius: 14px;
    padding: 0px;
}
QScrollBar:vertical {
    background-color: #050b16;
    width: 16px;
    margin: 3px 2px 3px 2px;
    border: 1px solid #172033;
    border-radius: 8px;
}
QScrollBar::handle:vertical {
    background-color: #36577d;
    border: 2px solid #050b16;
    border-radius: 7px;
    min-height: 64px;
}
QScrollBar::handle:vertical:hover { background-color: #5f86b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal {
    background-color: #050b16;
    height: 16px;
    margin: 2px 3px 2px 3px;
    border: 1px solid #172033;
    border-radius: 8px;
}
QScrollBar::handle:horizontal {
    background-color: #36577d;
    border: 2px solid #050b16;
    border-radius: 7px;
    min-width: 64px;
}
QScrollBar::handle:horizontal:hover { background-color: #5f86b8; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: none; border: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
"""

FLAG_COLUMNS = {
    "Review Status", "Red Flag Result", "Action", "Data Confidence Flag",
    "Standalone Valuation Flag", "Standalone Business Flag", "Standalone Balance Flag",
    "Standalone Dilution Flag", "Overall Peer Flag", "Relative Valuation Flag",
    "Relative Quality Flag", "Relative Balance Flag", "Relative Dilution Flag",
    "Readiness", "Momentum Flag", "Drawdown Flag", "Volatility Flag",
}
SCORE_COLUMNS = {"Data Score", "Data Quality Score"}
DEFAULT_SEC_USER_AGENT = ""
DEFAULT_PEER_GROUPS = [
    "", "AI Hardware / Semiconductors", "Semiconductor Manufacturing", "Semiconductor Equipment",
    "Semiconductor IP", "AI Infrastructure / Servers", "SMR / Nuclear", "Uranium / Nuclear Fuel",
    "Grid / Electrification", "Robotics / Automation", "Defense Tech", "Space / Satellites",
    "Quantum Computing", "Cybersecurity", "Cloud / AI Software", "Battery / Energy Storage",
    "Advanced Manufacturing", "Other / Custom",
]
TAB_HINTS = {
    "Overview": "Executive signal board, decision buckets, and research alerts.",
    "Master Watchlist": "Screener entry view with data readiness, red flags, peer group, and market behavior.",
    "Data Quality": "Completeness, freshness, currency warnings, and repair actions.",
    "Peer Comparison": "Relative valuation, quality, and balance-sheet context by peer group.",
    "API Cache": "Raw SEC and Finnhub rows used by the normalized model.",
    "Market Data": "Latest normalized market and fundamental snapshot.",
    "Historical Fundamentals": "Multi-year SEC annual fundamentals and trend metrics.",
    "Price Trends": "Returns, drawdown, momentum, and volatility metrics from candles.",
    "Price History": "Stored daily open, high, low, close, adjusted close, and volume.",
    "Model Readiness": "Missing/weak field checks and next action guidance.",
    "Research Guide": "Saved five-step screener workflow and risk/reward blueprint.",
}
DEFAULT_TAB_ORDER = list(TAB_HINTS.keys())
TAB_ORDER_SETTING = "workspace_tab_order"


def apply_windows_dark_title_bar(window: QMainWindow) -> None:
    if sys.platform != "win32":
        return
    try:
        hwnd = int(window.winId())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


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


def score_colors(value):
    try:
        score = float(str(value).strip())
    except Exception:
        return None, None
    if score >= 80:
        return QColor("#0d3a24"), QColor("#8ff0b2")
    if score >= 65:
        return QColor("#233a12"), QColor("#bef264")
    if score >= 50:
        return QColor("#40320b"), QColor("#fde68a")
    return QColor("#40161b"), QColor("#fca5a5")


def html_escape(value) -> str:
    return html.escape("" if value is None else str(value))


def flag_html_style(text: str) -> tuple[str, str, str]:
    text = text or ""
    if text.startswith("GREEN"):
        return "#0d3a24", "#8ff0b2", "#1f8f52"
    if text.startswith("YELLOW"):
        return "#40320b", "#fde68a", "#a87b19"
    if text.startswith("RED"):
        return "#40161b", "#fca5a5", "#9f2b3b"
    if text.startswith("GRAY"):
        return "#1f2937", "#cbd5e1", "#526074"
    if text.startswith("PURPLE"):
        return "#311b52", "#d8b4fe", "#7c3aed"
    return "#111f34", "#dbeafe", "#426183"


def score_html_style(value) -> tuple[str, str, str]:
    try:
        score = float(str(value).strip())
    except Exception:
        return "#1f2937", "#cbd5e1", "#526074"
    if score >= 80:
        return "#0d3a24", "#8ff0b2", "#1f8f52"
    if score >= 65:
        return "#233a12", "#bef264", "#65a30d"
    if score >= 50:
        return "#40320b", "#fde68a", "#a87b19"
    return "#40161b", "#fca5a5", "#9f2b3b"


def hud_pill(text: str) -> str:
    bg, fg, border = flag_html_style(text)
    return (
        f"<span style='display:inline-block; background:{bg}; color:{fg}; border:1px solid {border}; "
        f"border-radius:10px; padding:4px 8px; font-weight:800; white-space:nowrap;'>{html_escape(text)}</span>"
    )


def hud_score(value) -> str:
    bg, fg, border = score_html_style(value)
    return (
        f"<span style='display:inline-block; min-width:34px; text-align:center; background:{bg}; color:{fg}; "
        f"border:1px solid {border}; border-radius:10px; padding:4px 8px; font-weight:900;'>{html_escape(value)}</span>"
    )


def hud_ticker_chip(ticker: str, flag: str = "") -> str:
    bg, fg, border = flag_html_style(flag)
    return (
        f"<span style='display:inline-block; background:{bg}; color:{fg}; border:1px solid {border}; "
        f"border-radius:9px; padding:3px 7px; margin:2px 3px 2px 0; font-weight:900;'>{html_escape(ticker)}</span>"
    )


def polish_table(table: QTableWidget, sticky_ticker: bool = False) -> None:
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setMouseTracking(True)
    table.setSortingEnabled(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setHighlightSections(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    table.horizontalHeader().setMinimumSectionSize(72)
    table.verticalHeader().setDefaultSectionSize(34)
    table.verticalHeader().setVisible(sticky_ticker)
    if sticky_ticker:
        table.verticalHeader().setFixedWidth(74)
        table.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        table.verticalHeader().setStyleSheet(
            "QHeaderView { background-color: #030814; }"
            "QHeaderView::section { background-color: #0b1728; color: #ffffff; border-right: 1px solid #3c516d; border-bottom: 1px solid #26384f; font-weight: 950; }"
        )
    table.setColumnWidth(0, 92)


def set_row_ticker_header(table: QTableWidget, row: int, ticker: str) -> None:
    item = QTableWidgetItem(str(ticker or ""))
    item.setTextAlignment(Qt.AlignCenter)
    table.setVerticalHeaderItem(row, item)


def make_metric_card(label: str, value: str, subtext: str) -> tuple[QWidget, QLabel, QLabel]:
    card = QWidget()
    card.setObjectName("MiniCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(5)
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
        nav_layout.setContentsMargins(22, 12, 22, 12)
        nav_layout.setSpacing(13)
        brand = QLabel("HedgeFund-Like")
        brand.setObjectName("Brand")
        nav_layout.addWidget(brand)
        for label, tab_target in [
            ("Overview", "Overview"),
            ("Watchlist", "Master Watchlist"),
            ("Quality", "Data Quality"),
            ("Peers", "Peer Comparison"),
            ("Data", "API Cache"),
            ("Guide", "Research Guide"),
            ("Settings", "__settings__"),
        ]:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, target=tab_target: self.navigate_top_nav(target))
            nav_layout.addWidget(button)
        nav_layout.addStretch()
        pill = QLabel("LOCAL-FIRST · PRIVATE DATA")
        pill.setObjectName("Pill")
        nav_layout.addWidget(pill)
        root_layout.addWidget(nav)

        main = QWidget()
        main.setObjectName("Workspace")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(30, 26, 30, 26)
        main_layout.setSpacing(20)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = self.build_left_panel()
        self.center_tabs = QTabWidget()
        self.center_tabs.setObjectName("WorkspaceTabs")
        self.center_tabs.setDocumentMode(True)
        self.center_tabs.tabBar().setMovable(True)
        self.center_tabs.tabBar().setUsesScrollButtons(False)
        self.center_tabs.tabBar().setExpanding(False)
        self.center_tabs.tabBar().setElideMode(Qt.ElideRight)
        self.build_overview_tab(self.center_tabs)
        self.build_data_tabs(self.center_tabs)
        self.build_research_guide_tab(self.center_tabs)
        self.restore_tab_order()
        self.center_tabs.currentChanged.connect(self.update_active_tab_header)
        self.center_tabs.tabBar().tabMoved.connect(lambda from_index, to_index: self.save_tab_order())
        right = self.build_right_panel()

        splitter.addWidget(left)
        center_shell = QWidget()
        center_shell_layout = QVBoxLayout(center_shell)
        center_shell_layout.setContentsMargins(0, 0, 0, 0)
        center_shell_layout.setSpacing(10)
        tab_title_bar = QWidget()
        tab_title_bar.setObjectName("TabTitleBar")
        tab_title_layout = QVBoxLayout(tab_title_bar)
        tab_title_layout.setContentsMargins(16, 12, 16, 12)
        tab_title_layout.setSpacing(3)
        self.active_tab_title = QLabel()
        self.active_tab_title.setObjectName("ActiveTabTitle")
        self.active_tab_hint = QLabel()
        self.active_tab_hint.setObjectName("ActiveTabHint")
        self.active_tab_hint.setWordWrap(True)
        tab_title_layout.addWidget(self.active_tab_title)
        tab_title_layout.addWidget(self.active_tab_hint)
        center_shell_layout.addWidget(tab_title_bar)
        center_shell_layout.addWidget(self.center_tabs, 1)
        self.update_active_tab_header()

        splitter.addWidget(center_shell)
        splitter.addWidget(right)
        splitter.setSizes([390, 1040, 330])
        main_layout.addWidget(splitter)
        root_layout.addWidget(main)
        self.setCentralWidget(root)

        self.selected_ticker = None
        self.refresh_all_tables()

    def build_left_panel(self) -> QWidget:
        left = QWidget()
        left.setObjectName("ControlPanel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(14)
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
        polish_table(self.watchlist_table, sticky_ticker=False)
        left_layout.addWidget(self.watchlist_table, 3)

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
        self.peer_group_input.addItems(DEFAULT_PEER_GROUPS)
        self.sec_user_agent = QLineEdit(get_setting("sec_user_agent", DEFAULT_SEC_USER_AGENT))
        self.finnhub_api_key = QLineEdit(get_setting("finnhub_api_key", ""))
        self.price_lookback_years_input = QLineEdit(get_setting("price_lookback_years", "3"))
        self.sec_user_agent.setPlaceholderText("SEC User-Agent; local only")
        self.finnhub_api_key.setPlaceholderText("Finnhub API key; local only")
        self.finnhub_api_key.setEchoMode(QLineEdit.Password)
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
            ("Repair Missing Data", self.repair_missing_data_clicked, "PrimaryButton"),
            ("Rebuild SEC History", self.rebuild_history_clicked, "QuietButton"),
            ("Refresh Price History", self.refresh_price_history_clicked, "QuietButton"),
            ("Save API Settings", self.save_api_settings, "QuietButton"),
            ("Delete Selected Ticker", self.delete_selected_ticker_clicked, "DangerButton"),
        ]:
            button = QPushButton(text)
            button.setObjectName(style_name)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(fn)
            action_layout.addWidget(button)
        left_layout.addWidget(action_group, 2)
        return left

    def build_right_panel(self) -> QWidget:
        right = QWidget()
        right.setObjectName("DecisionPanel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(14)
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
            "The Overview tab sorts names into data, red-flag, and peer-review workflow buckets."
        )
        right_layout.addWidget(self.details)
        return right

    def find_tab_index(self, tab_name: str) -> int:
        for idx in range(self.center_tabs.count()):
            if self.center_tabs.tabText(idx) == tab_name:
                return idx
        return -1

    def navigate_top_nav(self, tab_target: str) -> None:
        if tab_target == "__settings__":
            self.sec_user_agent.setFocus()
            self.details.setText("Settings are stored only in your local tech_screener.db file. Enter or update the SEC User-Agent and Finnhub API key in the left setup panel.")
            return
        tab_index = self.find_tab_index(tab_target)
        if tab_index >= 0:
            self.center_tabs.setCurrentIndex(tab_index)
            return

    def current_tab_order(self) -> list[str]:
        return [self.center_tabs.tabText(idx) for idx in range(self.center_tabs.count())]

    def save_tab_order(self) -> None:
        set_setting(TAB_ORDER_SETTING, "|".join(self.current_tab_order()))

    def restore_tab_order(self) -> None:
        saved = get_setting(TAB_ORDER_SETTING, "")
        if not saved:
            return
        desired = [name for name in saved.split("|") if name]
        desired.extend(name for name in DEFAULT_TAB_ORDER if name not in desired)
        for target_index, tab_name in enumerate(desired):
            current_index = self.find_tab_index(tab_name)
            if current_index >= 0 and current_index != target_index:
                self.center_tabs.tabBar().moveTab(current_index, target_index)

    def update_active_tab_header(self) -> None:
        if not hasattr(self, "active_tab_title"):
            return
        tab_name = self.center_tabs.tabText(self.center_tabs.currentIndex()) if self.center_tabs.count() else ""
        self.active_tab_title.setText(tab_name)
        hint = TAB_HINTS.get(tab_name, "")
        self.active_tab_hint.setText(f"{hint} Drag tab labels to rearrange them; your order is saved locally.")

    def build_overview_tab(self, tabs: QTabWidget) -> None:
        overview = QWidget()
        layout = QVBoxLayout(overview)
        layout.setContentsMargins(22, 24, 22, 22)
        layout.setSpacing(20)

        hero = QWidget()
        hero.setObjectName("PreviewShell")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(38, 34, 38, 34)
        hero_layout.setSpacing(18)
        eyebrow = QLabel("SCREEN. RANK. RESEARCH. REPEAT.")
        eyebrow.setObjectName("HeroEyebrow")
        eyebrow.setAlignment(Qt.AlignCenter)
        title = QLabel("Find asymmetric stock setups before the market prices them in.")
        title.setObjectName("HeroTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        subtitle = QLabel("Run SEC + Finnhub data through a local workflow for data checks, red flags, peer comparison, risk/reward, and decision handoff.")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        signal_row = QHBoxLayout()
        signal_row.setSpacing(10)
        signal_row.addStretch()
        for text in ["LOCAL SQLITE CACHE", "SEC + FINNHUB PIPELINE", "DATA / RED FLAG / PEER FLOW"]:
            signal = QLabel(text)
            signal.setObjectName("SignalPill")
            signal_row.addWidget(signal)
        signal_row.addStretch()
        hero_layout.addWidget(eyebrow)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        hero_layout.addLayout(signal_row)

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
        hero_layout.addLayout(metric_grid)
        layout.addWidget(hero)

        dashboard = QWidget()
        dashboard.setObjectName("DashboardCard")
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(20, 20, 20, 20)
        dashboard_layout.setSpacing(12)
        dash_title = QLabel("Signal Board")
        dash_title.setObjectName("PanelTitle")
        dash_hint = QLabel("Readable screening views stay separate from raw SEC, Finnhub, cache, and normalized data tabs.")
        dash_hint.setObjectName("PanelHint")
        self.hud = QTextEdit()
        self.hud.setObjectName("Hud")
        self.hud.setReadOnly(True)
        dashboard_layout.addWidget(dash_title)
        dashboard_layout.addWidget(dash_hint)
        dashboard_layout.addWidget(self.hud, 1)
        layout.addWidget(dashboard, 1)
        tabs.addTab(overview, "Overview")

    def build_data_tabs(self, tabs: QTabWidget) -> None:
        self.master_columns = ["Ticker", "Review Status", "Data Score", "Data Confidence Flag", "Red Flag Result", "Red Flags", "Watch Items", "Action", "Standalone Valuation Flag", "Standalone Business Flag", "Standalone Balance Flag", "Standalone Dilution Flag", "Company", "Peer Group", "Price", "Market Cap", "EV", "Revenue", "FCF", "Cash", "Debt", "Current Ratio", "Shares Out", "Diluted Shares", "Dilution 1Y", "Dilution 3Y", "EV/Revenue", "EV/FCF", "P/S", "P/E", "Beta", "52W High", "52W Low", "Momentum Flag", "Drawdown Flag", "Volatility Flag", "1M Return", "3M Return", "6M Return", "1Y Return", "3Y Return", "From 52W High", "90D Volatility", "Price Data Through", "Cash Runway", "Readiness", "Missing / Weak Areas", "Source Status"]
        self.master_table = QTableWidget()
        self.master_table.setColumnCount(len(self.master_columns))
        self.master_table.setHorizontalHeaderLabels(self.master_columns)
        polish_table(self.master_table, sticky_ticker=True)
        self.master_table.cellClicked.connect(lambda row, col: self.table_selection_changed(self.master_table, row))
        tabs.addTab(self.master_table, "Master Watchlist")

        data_quality_panel = QWidget()
        data_quality_panel.setObjectName("DataPanel")
        data_quality_layout = QVBoxLayout(data_quality_panel)
        data_quality_layout.setContentsMargins(16, 16, 16, 16)
        data_quality_layout.setSpacing(10)
        data_quality_tools = QHBoxLayout()
        data_quality_label = QLabel("Data Quality")
        data_quality_label.setObjectName("PanelTitle")
        data_quality_tools.addWidget(data_quality_label)
        self.data_quality_filter_input = QLineEdit()
        self.data_quality_filter_input.setPlaceholderText("Filter quality rows: missing, stale, currency, revenue, TSM")
        self.data_quality_filter_input.textChanged.connect(lambda _: self.refresh_data_quality_table(self.current_ticker() or None))
        data_quality_tools.addWidget(self.data_quality_filter_input, 1)
        self.data_quality_mode_input = QComboBox()
        self.data_quality_mode_input.addItems(["All Rows", "Needs Attention"])
        self.data_quality_mode_input.currentTextChanged.connect(lambda _: self.refresh_data_quality_table(self.current_ticker() or None))
        data_quality_tools.addWidget(self.data_quality_mode_input)
        data_quality_layout.addLayout(data_quality_tools)

        self.data_quality_summary_columns = ["Ticker", "Data Quality Score", "Data Quality Flag", "Complete Fields", "Warnings", "Missing / Red", "Currency Warnings", "Suggested Next Step", "Weakest Fields"]
        self.data_quality_summary_table = QTableWidget()
        self.data_quality_summary_table.setColumnCount(len(self.data_quality_summary_columns))
        self.data_quality_summary_table.setHorizontalHeaderLabels(self.data_quality_summary_columns)
        polish_table(self.data_quality_summary_table, sticky_ticker=True)
        self.data_quality_summary_table.cellClicked.connect(lambda row, col: self.table_selection_changed(self.data_quality_summary_table, row))
        data_quality_layout.addWidget(self.data_quality_summary_table, 1)

        self.data_quality_columns = ["Ticker", "Field", "Quality Status", "Value", "Source", "Freshness", "Suggested Action", "Notes"]
        self.data_quality_table = QTableWidget()
        self.data_quality_table.setColumnCount(len(self.data_quality_columns))
        self.data_quality_table.setHorizontalHeaderLabels(self.data_quality_columns)
        polish_table(self.data_quality_table, sticky_ticker=True)
        self.data_quality_table.cellClicked.connect(lambda row, col: self.table_selection_changed(self.data_quality_table, row))
        data_quality_layout.addWidget(self.data_quality_table, 3)
        tabs.addTab(data_quality_panel, "Data Quality")

        self.peer_columns = ["Ticker", "Peer Group", "Peer Count", "Overall Peer Flag", "Relative Valuation Flag", "Relative Quality Flag", "Relative Balance Flag", "Relative Dilution Flag", "EV/Revenue", "Peer Median EV/Revenue", "EV/FCF", "Peer Median EV/FCF", "P/S", "Peer Median P/S", "FCF Margin", "Peer Median FCF Margin", "Operating Margin", "Peer Median Operating Margin", "Gross Margin", "Peer Median Gross Margin", "Current Ratio", "Peer Median Current Ratio", "Dilution 1Y", "Peer Median Dilution 1Y", "Dilution 3Y", "Peer Median Dilution 3Y", "Readiness", "Missing / Weak Areas"]
        self.peer_table = QTableWidget()
        self.peer_table.setColumnCount(len(self.peer_columns))
        self.peer_table.setHorizontalHeaderLabels(self.peer_columns)
        polish_table(self.peer_table, sticky_ticker=True)
        self.peer_table.cellClicked.connect(lambda row, col: self.table_selection_changed(self.peer_table, row))
        tabs.addTab(self.peer_table, "Peer Comparison")

        cache_panel = QWidget()
        cache_panel.setObjectName("DataPanel")
        cache_layout = QVBoxLayout(cache_panel)
        cache_layout.setContentsMargins(16, 16, 16, 16)
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
        polish_table(self.cache_table, sticky_ticker=True)
        cache_layout.addWidget(self.cache_table)
        tabs.addTab(cache_panel, "API Cache")

        self.market_columns = ["ticker", "company", "peer_group", "price_per_share", "market_cap_raw", "enterprise_value_raw", "shares_out_raw", "diluted_shares_raw", "high_52w", "low_52w", "beta", "avg_volume_shares", "pe_ratio", "eps_market", "revenue_raw", "gross_profit_raw", "operating_income_raw", "ebitda_raw", "net_income_raw", "eps_diluted", "operating_cash_flow_raw", "capex_raw", "fcf_raw", "cash_raw", "debt_raw", "net_debt_raw", "current_ratio", "equity_raw", "sbc_raw", "rd_raw", "sga_raw", "dilution_1y", "dilution_3y", "source_status"]
        self.market_table = QTableWidget()
        self.market_table.setColumnCount(len(self.market_columns))
        self.market_table.setHorizontalHeaderLabels(self.market_columns)
        polish_table(self.market_table, sticky_ticker=True)
        self.market_table.cellClicked.connect(lambda row, col: self.table_selection_changed(self.market_table, row))
        tabs.addTab(self.market_table, "Market Data")

        self.history_columns = ["ticker", "fiscal_year", "period", "filed", "form", "revenue_raw", "revenue_growth_yoy", "gross_profit_raw", "gross_margin", "operating_income_raw", "operating_margin", "net_income_raw", "operating_cash_flow_raw", "capex_raw", "fcf_raw", "fcf_margin", "fcf_growth_yoy", "cash_raw", "debt_raw", "current_ratio", "equity_raw", "shares_raw", "dilution_yoy", "source_status", "source_notes"]
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(len(self.history_columns))
        self.history_table.setHorizontalHeaderLabels(self.history_columns)
        polish_table(self.history_table, sticky_ticker=True)
        self.history_table.cellClicked.connect(lambda row, col: self.table_selection_changed(self.history_table, row))
        tabs.addTab(self.history_table, "Historical Fundamentals")

        self.price_metrics_columns = ["ticker", "last_trade_date", "last_close", "lookback_days", "high_52w", "low_52w", "pct_from_52w_high", "pct_above_52w_low", "return_1m", "return_3m", "return_6m", "return_1y", "return_3y", "volatility_30d", "volatility_90d", "momentum_flag", "drawdown_flag", "volatility_flag", "source_status"]
        self.price_metrics_table = QTableWidget()
        self.price_metrics_table.setColumnCount(len(self.price_metrics_columns))
        self.price_metrics_table.setHorizontalHeaderLabels(self.price_metrics_columns)
        polish_table(self.price_metrics_table, sticky_ticker=True)
        self.price_metrics_table.cellClicked.connect(lambda row, col: self.table_selection_changed(self.price_metrics_table, row))
        tabs.addTab(self.price_metrics_table, "Price Trends")

        self.price_history_columns = ["ticker", "trade_date", "open", "high", "low", "close", "adjusted_close", "volume", "source"]
        self.price_history_table = QTableWidget()
        self.price_history_table.setColumnCount(len(self.price_history_columns))
        self.price_history_table.setHorizontalHeaderLabels(self.price_history_columns)
        polish_table(self.price_history_table, sticky_ticker=True)
        tabs.addTab(self.price_history_table, "Price History")

        self.readiness_columns = ["ticker", "company", "peer_group", "price_ok", "market_cap_ok", "shares_ok", "revenue_ok", "gross_profit_ok", "ebitda_ok", "fcf_ok", "cash_ok", "debt_ok", "liquidity_ok", "dilution_ok", "sbc_rd_sga_ok", "core_data_score", "readiness", "next_action", "missing_weak_areas"]
        self.readiness_table = QTableWidget()
        self.readiness_table.setColumnCount(len(self.readiness_columns))
        self.readiness_table.setHorizontalHeaderLabels(self.readiness_columns)
        polish_table(self.readiness_table, sticky_ticker=True)
        self.readiness_table.cellClicked.connect(lambda row, col: self.table_selection_changed(self.readiness_table, row))
        tabs.addTab(self.readiness_table, "Model Readiness")

    def build_research_guide_tab(self, tabs: QTabWidget) -> None:
        guide = QWidget()
        guide.setObjectName("DataPanel")
        layout = QVBoxLayout(guide)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Workflow Guide")
        title.setObjectName("PanelTitle")
        hint = QLabel("Saved five-step workflow for using the screener before leaving the app for company research.")
        hint.setObjectName("PanelHint")
        self.research_guide = QTextEdit()
        self.research_guide.setReadOnly(True)
        guide_path = Path(__file__).resolve().parents[2] / "docs" / "product_workflow_spec.txt"
        try:
            text = guide_path.read_text(encoding="utf-8")
        except Exception as exc:
            text = f"Workflow guide could not be loaded.\n\nExpected file:\n{guide_path}\n\nError:\n{exc}"
        self.research_guide.setPlainText(text)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.research_guide, 1)
        self.guide_tab_index = tabs.addTab(guide, "Research Guide")

    def closeEvent(self, event) -> None:
        self.save_api_settings_silent()
        super().closeEvent(event)

    def save_api_settings_silent(self) -> None:
        set_setting("sec_user_agent", self.sec_user_agent.text().strip())
        set_setting("finnhub_api_key", self.finnhub_api_key.text().strip())
        set_setting("price_lookback_years", str(self.price_lookback_years()))

    def save_api_settings(self) -> None:
        self.save_api_settings_silent()
        self.details.setText("API settings saved locally in tech_screener.db. They are not saved to GitHub.")

    def current_ticker(self) -> str:
        return (self.selected_ticker or self.ticker_input.text().strip().upper()).upper().strip()

    def price_lookback_years(self) -> int:
        try:
            years = int(float(self.price_lookback_years_input.text().strip()))
        except Exception:
            years = 3
        years = max(1, min(years, 10))
        if self.price_lookback_years_input.text().strip() != str(years):
            self.price_lookback_years_input.setText(str(years))
        return years

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
        result = QMessageBox.question(self, "Delete ticker", f"Delete {ticker} from the watchlist and remove its cached local data?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if result != QMessageBox.Yes:
            return
        delete_ticker(ticker, delete_cached_data=True)
        self.selected_ticker = None
        self.details.setText(f"Deleted {ticker} from the local watchlist and local cached data.")
        self.refresh_all_tables()

    def watchlist_clicked(self, row: int, col: int) -> None:
        item = self.watchlist_table.item(row, 0)
        if not item:
            return
        self.selected_ticker = item.text()
        self.details.setText(f"{self.selected_ticker}\n\nSelected. Run the full pipeline or inspect the screening and raw-data tabs.")
        self.refresh_all_tables(self.selected_ticker)

    def table_ticker(self, table: QTableWidget, row: int) -> str:
        header = table.verticalHeaderItem(row)
        if header and header.text().strip():
            return header.text().strip().upper()
        item = table.item(row, 0)
        return item.text().strip().upper() if item else ""

    def table_selection_changed(self, table: QTableWidget, row: int) -> None:
        ticker = self.table_ticker(table, row)
        if not ticker:
            return
        self.selected_ticker = ticker
        self.update_decision_brief(ticker)

    def update_decision_brief(self, ticker: str) -> None:
        master_rows = getattr(self, "_master_rows", None)
        if master_rows is None:
            master_rows = list_master_watchlist()
            self._master_rows = master_rows
        master = next((row for row in master_rows if row.get("Ticker") == ticker), None)
        quality_summary = next((row for row in list_data_quality_summary(ticker) if row.get("Ticker") == ticker), None)
        if not master:
            self.details.setText(f"{ticker}\n\nSelected. Run the pipeline to generate screening details.")
            return

        lines = [
            ticker,
            "",
            f"Review status: {master.get('Review Status', '')}",
            f"Data score: {master.get('Data Score', '')}  |  Data: {master.get('Data Confidence Flag', '')}",
            f"Red flags: {master.get('Red Flags', '')}",
            f"Watch items: {master.get('Watch Items', '')}",
            f"Action: {master.get('Action', '')}",
            "",
            "Standalone Red-Flag Checks",
            f"Valuation: {master.get('Standalone Valuation Flag', '')}",
            f"Business: {master.get('Standalone Business Flag', '')}",
            f"Balance: {master.get('Standalone Balance Flag', '')}",
            f"Dilution: {master.get('Standalone Dilution Flag', '')}",
            "",
            "Snapshot",
            f"Price: {master.get('Price', '')}  |  Market Cap: {master.get('Market Cap', '')}  |  EV: {master.get('EV', '')}",
            f"Revenue: {master.get('Revenue', '')}  |  FCF: {master.get('FCF', '')}",
            f"EV/Revenue: {master.get('EV/Revenue', '')}  |  EV/FCF: {master.get('EV/FCF', '')}  |  P/E: {master.get('P/E', '')}",
            f"Momentum: {master.get('Momentum Flag', '')}",
            f"Drawdown: {master.get('Drawdown Flag', '')}",
        ]
        if quality_summary:
            lines.extend([
                "",
                "Data Quality",
                f"{quality_summary.get('Data Quality Flag', '')}  |  Score {quality_summary.get('Data Quality Score', '')}",
                f"Weakest fields: {quality_summary.get('Weakest Fields', '')}",
                f"Next step: {quality_summary.get('Suggested Next Step', '')}",
            ])
        lines.extend(["", f"Readiness: {master.get('Readiness', '')}", f"Missing / Weak Areas: {master.get('Missing / Weak Areas', '')}"])
        self.details.setText("\n".join(lines))

    def refresh_price_history_for_ticker(self, ticker: str, key: str) -> tuple[int, str]:
        try:
            price_rows, source, note = refresh_price_history_rows(ticker, key, lookback_years=self.price_lookback_years())
            inserted = insert_price_history_rows(price_rows)
            recalculate_price_metrics_for_ticker(ticker)
            message = f"\nPrice history source: {source or 'none'}"
            if note:
                message += f"\nPrice history note: {note}"
            return inserted, message
        except Exception as exc:
            return 0, f"\nPrice history warning: {exc}"

    def rebuild_history_clicked(self) -> None:
        ticker = self.current_ticker()
        if not ticker:
            QMessageBox.warning(self, "No ticker selected", "Select a ticker or enter one.")
            return
        try:
            rows = rebuild_historical_fundamentals_for_ticker(ticker)
            self.selected_ticker = ticker
            self.details.setText(f"{ticker}\n\nHistorical fundamentals rebuilt from local SEC cache.\nHistorical fundamental years: {rows}")
            self.refresh_all_tables(ticker)
        except Exception as exc:
            QMessageBox.critical(self, "Historical rebuild failed", str(exc))

    def refresh_price_history_clicked(self) -> None:
        ticker = self.current_ticker()
        if not ticker:
            QMessageBox.warning(self, "No ticker selected", "Select a ticker or enter one.")
            return
        key = self.finnhub_api_key.text().strip()
        try:
            self.save_api_settings()
            self.details.setText(f"Refreshing price history for {ticker}...")
            QApplication.processEvents()
            price_rows, price_warning = self.refresh_price_history_for_ticker(ticker, key)
            normalize_market_data_for_ticker(ticker)
            calculate_model_readiness_for_ticker(ticker)
            self.selected_ticker = ticker
            self.details.setText(f"{ticker}\n\nPrice history refresh complete.\nDaily price candles: {price_rows}\nPrice trend metrics recalculated\nMarket Data normalized\nReadiness calculated{price_warning}")
            self.refresh_all_tables(ticker)
        except Exception as exc:
            QMessageBox.critical(self, "Price history refresh failed", str(exc))

    def repair_missing_data_clicked(self) -> None:
        key = self.finnhub_api_key.text().strip()
        try:
            self.save_api_settings()
            self.details.setText("Repairing missing data across active tickers...\n\nThis rebuilds SEC history from cache and refreshes price history from Finnhub when allowed, otherwise Yahoo chart fallback.")
            QApplication.processEvents()
            results = repair_all_missing_data(
                finnhub_key=key,
                lookback_years=self.price_lookback_years(),
                only_missing=True,
            )
            self.refresh_all_tables(self.selected_ticker)
            if not results:
                self.details.setText("Repair complete.\n\nNo missing-data targets found, or no cached/API data was available to repair.")
                return
            lines = ["Repair complete.", ""]
            total_history = sum(r.history_years for r in results)
            total_prices = sum(r.price_rows for r in results)
            lines.append(f"Tickers repaired: {len(results)}")
            lines.append(f"Historical years rebuilt: {total_history}")
            lines.append(f"Price candles stored: {total_prices}")
            lines.append("")
            for result in results:
                status = "OK" if not result.warning else f"WARN - {result.warning}"
                source = f", source {result.price_source}" if result.price_source else ""
                note = f" ({result.price_note})" if result.price_note else ""
                lines.append(f"{result.ticker}: history years {result.history_years}, price rows {result.price_rows}{source}{note}, {status}")
            self.details.setText("\n".join(lines))
        except Exception as exc:
            QMessageBox.critical(self, "Repair missing data failed", str(exc))

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
            history_rows = rebuild_historical_fundamentals_for_ticker(ticker)
            normalize_market_data_for_ticker(ticker)
            calculate_model_readiness_for_ticker(ticker)
            self.selected_ticker = ticker
            self.details.setText(f"{ticker}\n\nSEC refresh complete.\nRows: {len(rows)}\nOK rows: {sum(1 for r in rows if r.get('Status') == 'OK')}\nHistorical fundamental years: {history_rows}\nMarket Data normalized\nReadiness calculated")
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
            price_rows, price_warning = self.refresh_price_history_for_ticker(ticker, key)
            normalize_market_data_for_ticker(ticker)
            calculate_model_readiness_for_ticker(ticker)
            self.selected_ticker = ticker
            self.details.setText(f"{ticker}\n\nFinnhub refresh complete.\nRows: {len(rows)}\nOK rows: {sum(1 for r in rows if r.get('Status') == 'OK')}\nDaily price candles: {price_rows}\nMarket Data normalized\nReadiness calculated{price_warning}")
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
            history_rows = rebuild_historical_fundamentals_for_ticker(ticker)
            fh_rows = refresh_finnhub_rows(ticker, key)
            insert_api_cache_rows(fh_rows, replace_source_for_ticker=True)
            price_rows, price_warning = self.refresh_price_history_for_ticker(ticker, key)
            normalize_market_data_for_ticker(ticker)
            calculate_model_readiness_for_ticker(ticker)
            self.selected_ticker = ticker
            self.details.setText(f"{ticker}\n\nPipeline complete:\nSEC rows: {len(sec_rows)}\nFinnhub rows: {len(fh_rows)}\nHistorical fundamental years: {history_rows}\nDaily price candles: {price_rows}\nMarket Data normalized\nReadiness calculated{price_warning}")
            self.refresh_all_tables(ticker)
        except Exception as exc:
            QMessageBox.critical(self, "Pipeline failed", str(exc))
            self.details.setText(f"{ticker}\n\nPipeline failed:\n{exc}")

    def refresh_watchlist(self) -> None:
        rows = list_tickers()
        self.watchlist_table.setSortingEnabled(False)
        self.watchlist_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [row["ticker"], row["company"] or "", row["peer_group"] or row["category"] or ""]
            for c, val in enumerate(values):
                self.watchlist_table.setItem(r, c, QTableWidgetItem(str(val)))
        self.watchlist_table.setSortingEnabled(True)
        self.watchlist_table.resizeColumnsToContents()

    def refresh_cache_table(self, ticker=None) -> None:
        rows = list_api_cache(ticker=ticker, limit=500)
        query = self.cache_filter_input.text().strip().lower() if hasattr(self, "cache_filter_input") else ""
        if query:
            rows = [row for row in rows if query in " ".join(str(row[col] or "") for col in ["ticker", "source", "endpoint", "raw_field", "raw_value", "fiscal_year", "status", "sec_concept", "unit", "filed"]).lower()]
        self.cache_table.setSortingEnabled(False)
        self.cache_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            set_row_ticker_header(self.cache_table, r, row["ticker"])
            values = [row["ticker"], row["source"], row["endpoint"], row["raw_field"], row["raw_value"], row["fiscal_year"], row["status"], row["sec_concept"], row["unit"], row["filed"]]
            for c, val in enumerate(values):
                self.cache_table.setItem(r, c, QTableWidgetItem("" if val is None else str(val)))
        self.cache_table.setSortingEnabled(True)
        self.cache_table.setColumnHidden(0, True)
        self.cache_table.resizeColumnsToContents()

    def refresh_market_table(self, ticker=None) -> None:
        rows = list_market_data(ticker=ticker)
        self.market_table.setSortingEnabled(False)
        self.market_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            set_row_ticker_header(self.market_table, r, row["ticker"])
            for c, col in enumerate(self.market_columns):
                self.market_table.setItem(r, c, QTableWidgetItem(fmt(row[col])))
        self.market_table.setSortingEnabled(True)
        self.market_table.setColumnHidden(0, True)
        self.market_table.resizeColumnsToContents()

    def refresh_history_table(self, ticker=None) -> None:
        rows = list_historical_fundamentals(ticker=ticker)
        self.history_table.setSortingEnabled(False)
        self.history_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            set_row_ticker_header(self.history_table, r, row["ticker"])
            for c, col in enumerate(self.history_columns):
                self.history_table.setItem(r, c, QTableWidgetItem(fmt(row[col])))
        self.history_table.setSortingEnabled(True)
        self.history_table.setColumnHidden(0, True)
        self.history_table.resizeColumnsToContents()

    def refresh_price_metrics_table(self, ticker=None) -> None:
        rows = list_price_metrics(ticker=ticker)
        self.price_metrics_table.setSortingEnabled(False)
        self.price_metrics_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            set_row_ticker_header(self.price_metrics_table, r, row["ticker"])
            for c, col in enumerate(self.price_metrics_columns):
                self.price_metrics_table.setItem(r, c, QTableWidgetItem(fmt(row[col])))
        self.price_metrics_table.setSortingEnabled(True)
        self.price_metrics_table.setColumnHidden(0, True)
        self.price_metrics_table.resizeColumnsToContents()

    def refresh_price_history_table(self, ticker=None) -> None:
        rows = list_price_history(ticker=ticker)
        self.price_history_table.setSortingEnabled(False)
        self.price_history_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            set_row_ticker_header(self.price_history_table, r, row["ticker"])
            for c, col in enumerate(self.price_history_columns):
                self.price_history_table.setItem(r, c, QTableWidgetItem(fmt(row[col])))
        self.price_history_table.setSortingEnabled(True)
        self.price_history_table.setColumnHidden(0, True)
        self.price_history_table.resizeColumnsToContents()

    def refresh_readiness_table(self, ticker=None) -> None:
        rows = list_model_readiness(ticker=ticker)
        self.readiness_table.setSortingEnabled(False)
        self.readiness_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            set_row_ticker_header(self.readiness_table, r, row["ticker"])
            for c, col in enumerate(self.readiness_columns):
                self.readiness_table.setItem(r, c, QTableWidgetItem(fmt(row[col])))
        self.readiness_table.setSortingEnabled(True)
        self.readiness_table.setColumnHidden(0, True)
        self.readiness_table.resizeColumnsToContents()

    def apply_potential_colors(self, item: QTableWidgetItem, col: str, row: dict) -> None:
        bg = fg = None
        if col in SCORE_COLUMNS:
            bg, fg = score_colors(item.text())
        elif col in FLAG_COLUMNS or col in {"Flag", "Quality Status", "Data Quality Flag"}:
            bg, fg = flag_colors(item.text())
        if bg is not None:
            item.setBackground(bg)
            item.setForeground(fg)

    def refresh_data_quality_table(self, ticker=None) -> None:
        summary_rows = list_data_quality_summary(ticker=ticker)
        rows = list_data_quality(ticker=ticker)
        query = self.data_quality_filter_input.text().strip().lower() if hasattr(self, "data_quality_filter_input") else ""
        needs_attention = (
            hasattr(self, "data_quality_mode_input")
            and self.data_quality_mode_input.currentText() == "Needs Attention"
        )
        if query:
            summary_rows = [
                row for row in summary_rows
                if query in " ".join(str(value or "") for value in row.values()).lower()
            ]
            rows = [
                row for row in rows
                if query in " ".join(str(value or "") for value in row.values()).lower()
            ]
        if needs_attention:
            summary_rows = [row for row in summary_rows if not str(row.get("Data Quality Flag", "")).startswith("GREEN")]
            rows = [row for row in rows if not str(row.get("Quality Status", "")).startswith("GREEN")]

        self.data_quality_summary_table.setSortingEnabled(False)
        self.data_quality_summary_table.setRowCount(len(summary_rows))
        for r, row in enumerate(summary_rows):
            set_row_ticker_header(self.data_quality_summary_table, r, row.get("Ticker", ""))
            for c, col in enumerate(self.data_quality_summary_columns):
                text = str(row.get(col, ""))
                item = QTableWidgetItem(text)
                self.apply_potential_colors(item, col, row)
                self.data_quality_summary_table.setItem(r, c, item)
        self.data_quality_summary_table.setSortingEnabled(True)
        self.data_quality_summary_table.setColumnHidden(0, True)
        self.data_quality_summary_table.resizeColumnsToContents()
        self.data_quality_summary_table.setColumnWidth(7, 300)
        self.data_quality_summary_table.setColumnWidth(8, 360)

        self.data_quality_table.setSortingEnabled(False)
        self.data_quality_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            set_row_ticker_header(self.data_quality_table, r, row.get("Ticker", ""))
            for c, col in enumerate(self.data_quality_columns):
                text = str(row.get(col, ""))
                item = QTableWidgetItem(text)
                self.apply_potential_colors(item, col, row)
                self.data_quality_table.setItem(r, c, item)
        self.data_quality_table.setSortingEnabled(True)
        self.data_quality_table.setColumnHidden(0, True)
        self.data_quality_table.resizeColumnsToContents()
        self.data_quality_table.setColumnWidth(6, 260)
        self.data_quality_table.setColumnWidth(7, 420)

    def refresh_master_table(self) -> None:
        rows = list_master_watchlist()
        self._master_rows = rows
        self.master_table.setSortingEnabled(False)
        self.master_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            set_row_ticker_header(self.master_table, r, row.get("Ticker", ""))
            for c, col in enumerate(self.master_columns):
                text = str(row.get(col, ""))
                item = QTableWidgetItem(text)
                self.apply_potential_colors(item, col, row)
                if col == "Action":
                    bg, fg = flag_colors(str(row.get("Review Status", "")))
                    if bg is not None:
                        item.setBackground(bg)
                        item.setForeground(fg)
                self.master_table.setItem(r, c, item)
        self.master_table.setSortingEnabled(True)
        self.master_table.setColumnHidden(0, True)
        self.master_table.resizeColumnsToContents()

    def refresh_peer_table(self) -> None:
        rows = list_peer_comparison()
        self._peer_rows = rows
        self.peer_table.setSortingEnabled(False)
        self.peer_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            set_row_ticker_header(self.peer_table, r, row.get("Ticker", ""))
            for c, col in enumerate(self.peer_columns):
                text = str(row.get(col, ""))
                item = QTableWidgetItem(text)
                self.apply_potential_colors(item, col, row)
                self.peer_table.setItem(r, c, item)
        self.peer_table.setSortingEnabled(True)
        self.peer_table.setColumnHidden(0, True)
        self.peer_table.resizeColumnsToContents()

    def refresh_hud_panel(self) -> None:
        rows = getattr(self, "_master_rows", None)
        if rows is None:
            rows = list_master_watchlist()
            self._master_rows = rows

        peers = getattr(self, "_peer_rows", None)
        if peers is None:
            peers = list_peer_comparison()
            self._peer_rows = peers

        def count_matching(prefix: str) -> int:
            return sum(1 for r in rows if str(r.get("Review Status", "")).startswith(prefix))

        def data_score_value(row) -> int:
            try:
                return int(row.get("Data Score") or 0)
            except Exception:
                return 0

        def status_rank(row) -> int:
            status = str(row.get("Review Status", ""))
            if status.startswith("GREEN"):
                return 4
            if status.startswith("YELLOW"):
                return 3
            if status.startswith("GRAY"):
                return 2
            if status.startswith("RED"):
                return 1
            return 0

        ranked_rows = sorted(rows, key=lambda row: (status_rank(row), data_score_value(row), str(row.get("Ticker", ""))), reverse=True)
        top_rows = ranked_rows[:10]
        ready_rows = [r for r in ranked_rows if str(r.get("Review Status", "")).startswith("GREEN")]
        watch_rows = [r for r in ranked_rows if str(r.get("Review Status", "")).startswith("YELLOW")]
        need_data = [r for r in rows if str(r.get("Review Status", "")).startswith("GRAY")]
        red_flag_rows = [r for r in rows if str(r.get("Review Status", "")).startswith("RED")]
        cheapest = [p for p in peers if str(p.get("Relative Valuation Flag", "")).startswith("GREEN")]
        strongest = [
            p for p in peers
            if str(p.get("Relative Quality Flag", "")).startswith("GREEN")
            or str(p.get("Relative Balance Flag", "")).startswith("GREEN")
            or str(p.get("Relative Dilution Flag", "")).startswith("GREEN")
        ]
        warnings = need_data + red_flag_rows

        best_ready = ready_rows[0] if ready_rows else None
        highest_data = top_rows[0] if top_rows else None
        self.metric_total.setText(str(len(rows)))
        self.metric_deep_dive.setText(str(len(ready_rows)))
        self.metric_deep_dive_sub.setText(f"first: {best_ready['Ticker']}" if best_ready else "ready for peer gate")
        self.metric_watch.setText(str(count_matching("YELLOW")))
        self.metric_watch_sub.setText("needs context")
        self.metric_data.setText(str(count_matching("GRAY")))
        self.metric_data_sub.setText("fix before comparing")

        def chips_for(prefix: str) -> str:
            matches = [r for r in rows if str(r.get("Review Status", "")).startswith(prefix)]
            if not matches:
                return "<span style='color:#7f8fa8;'>None</span>"
            return " ".join(hud_ticker_chip(r["Ticker"], r.get("Review Status", "")) for r in matches[:18])

        def top_rows_html(items: list[dict]) -> str:
            if not items:
                return "<tr><td colspan='5' style='color:#8ea2bd; padding:12px;'>Add/select a ticker and run the pipeline.</td></tr>"
            body = []
            for idx, row in enumerate(items, start=1):
                body.append(
                    "<tr>"
                    f"<td style='color:#8ea2bd; font-weight:800;'>{idx}</td>"
                    f"<td style='font-weight:950; color:#ffffff;'>{html_escape(row['Ticker'])}</td>"
                    f"<td>{hud_score(row.get('Data Score', ''))}</td>"
                    f"<td>{hud_pill(str(row.get('Review Status', '')))}</td>"
                    f"<td style='color:#c7d7eb;'>{html_escape(row.get('Action', ''))}</td>"
                    "</tr>"
                )
            return "".join(body)

        def compact_list(title: str, items: list[str]) -> str:
            values = "".join(f"<li>{item}</li>" for item in items[:8])
            if not values:
                values = "<li style='color:#7f8fa8;'>None</li>"
            return (
                "<div class='panel'>"
                f"<div class='panel-title'>{html_escape(title)}</div>"
                f"<ul>{values}</ul>"
                "</div>"
            )

        headline_name = best_ready["Ticker"] if best_ready else (highest_data["Ticker"] if highest_data else "None")
        headline_score = best_ready.get("Data Score", "") if best_ready else (highest_data.get("Data Score", "") if highest_data else "")
        headline_label = "First ready for Peer Gate" if best_ready else "Highest data confidence"
        warnings_count = len(warnings)
        html_text = f"""
        <html>
        <head>
        <style>
            body {{
                margin: 0;
                background: #020714;
                color: #e5edf7;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 12px;
            }}
            .shell {{ padding: 18px; }}
            .hero {{
                background: #071426;
                border: 1px solid #426183;
                border-radius: 16px;
                padding: 18px;
                margin-bottom: 14px;
            }}
            .eyebrow {{
                color: #8bc7ff;
                font-size: 10px;
                letter-spacing: 2px;
                font-weight: 900;
                text-transform: uppercase;
            }}
            .headline {{
                color: #ffffff;
                font-size: 24px;
                font-weight: 950;
                margin-top: 6px;
            }}
            .subline {{
                color: #9fb5cf;
                margin-top: 5px;
            }}
            .tile-row {{ margin-top: 14px; }}
            .tile {{
                display: inline-block;
                width: 22%;
                min-width: 145px;
                background: #0a1628;
                border: 1px solid #2f4158;
                border-radius: 14px;
                padding: 12px;
                margin-right: 8px;
                vertical-align: top;
            }}
            .tile-label {{
                color: #9fb5cf;
                font-size: 10px;
                font-weight: 900;
                text-transform: uppercase;
            }}
            .tile-value {{
                color: #ffffff;
                font-size: 27px;
                font-weight: 950;
                margin-top: 3px;
            }}
            .tile-sub {{
                color: #9fb5cf;
                font-size: 11px;
                margin-top: 3px;
            }}
            .section-title {{
                color: #ffffff;
                font-size: 15px;
                font-weight: 950;
                margin: 16px 0 8px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: #030814;
                border: 1px solid #26384f;
                border-radius: 12px;
            }}
            th {{
                color: #aecaec;
                background: #101b2d;
                padding: 9px;
                text-align: left;
                font-weight: 900;
                border-bottom: 1px solid #26384f;
            }}
            td {{
                padding: 9px;
                border-bottom: 1px solid #172033;
            }}
            .bucket {{
                background: #07111f;
                border: 1px solid #2f4158;
                border-radius: 14px;
                padding: 12px;
                margin: 8px 0;
            }}
            .bucket-label {{
                color: #9fb5cf;
                font-size: 10px;
                font-weight: 900;
                text-transform: uppercase;
                margin-bottom: 8px;
            }}
            .panel {{
                display: inline-block;
                width: 48%;
                min-height: 120px;
                vertical-align: top;
                background: #07111f;
                border: 1px solid #2f4158;
                border-radius: 14px;
                padding: 12px;
                margin: 6px 6px 6px 0;
            }}
            .panel-title {{
                color: #ffffff;
                font-weight: 950;
                margin-bottom: 7px;
            }}
            ul {{
                margin: 0;
                padding-left: 18px;
                color: #c7d7eb;
            }}
            li {{ margin-bottom: 6px; }}
        </style>
        </head>
        <body>
        <div class="shell">
            <div class="hero">
                <div class="eyebrow">Workflow Signal Board</div>
                <div class="headline">{headline_label}: {html_escape(headline_name)} {hud_score(headline_score) if headline_score else ""}</div>
                <div class="subline">Color reads: green = ready for Peer Gate, yellow = needs context, gray = fix data, red = stop unless the thesis explains the risk.</div>
                <div class="tile-row">
                    <div class="tile"><div class="tile-label">Universe</div><div class="tile-value">{len(rows)}</div><div class="tile-sub">tracked tickers</div></div>
                    <div class="tile"><div class="tile-label">Peer Ready</div><div class="tile-value">{len(ready_rows)}</div><div class="tile-sub">{html_escape('first: ' + best_ready['Ticker']) if best_ready else 'green rows'}</div></div>
                    <div class="tile"><div class="tile-label">Watch</div><div class="tile-value">{len(watch_rows)}</div><div class="tile-sub">needs context</div></div>
                    <div class="tile"><div class="tile-label">Data / Red Flag</div><div class="tile-value">{warnings_count}</div><div class="tile-sub">warning rows</div></div>
                </div>
            </div>

            <div class="section-title">Current Workflow Queue</div>
            <table>
                <tr><th>#</th><th>Ticker</th><th>Data Score</th><th>Review Status</th><th>Action</th></tr>
                {top_rows_html(top_rows)}
            </table>

            <div class="section-title">Decision Buckets</div>
            <div class="bucket"><div class="bucket-label">Ready for Peer Gate</div>{chips_for("GREEN")}</div>
            <div class="bucket"><div class="bucket-label">Watchlist names</div>{chips_for("YELLOW")}</div>
            <div class="bucket"><div class="bucket-label">Fix data</div>{chips_for("GRAY")}</div>
            <div class="bucket"><div class="bucket-label">Red flag stop</div>{chips_for("RED")}</div>

            <div class="section-title">Research Alerts</div>
            {compact_list("Needs Better Data", [f"{html_escape(r['Ticker'])}: {html_escape(r.get('Data Confidence Flag', ''))}; {html_escape(r.get('Missing / Weak Areas', ''))}" for r in need_data])}
            {compact_list("Standalone Red Flags", [f"{html_escape(r['Ticker'])}: {html_escape(r.get('Red Flags', ''))}" for r in red_flag_rows])}
            {compact_list("Watch Items", [f"{html_escape(r['Ticker'])}: {html_escape(r.get('Watch Items', ''))}" for r in watch_rows])}
            {compact_list("Peer Signals", [f"{html_escape(p['Ticker'])}: {html_escape(p['Peer Group'])}; {html_escape(p.get('Relative Valuation Flag', ''))}" for p in cheapest[:8]] + [f"{html_escape(p['Ticker'])}: quality {html_escape(p.get('Relative Quality Flag', ''))}; balance {html_escape(p.get('Relative Balance Flag', ''))}; dilution {html_escape(p.get('Relative Dilution Flag', ''))}" for p in strongest[:8]])}
        </div>
        </body>
        </html>
        """
        self.hud.setHtml(html_text)

    def refresh_all_tables(self, ticker=None) -> None:
        self.refresh_watchlist()
        self.refresh_master_table()
        self.refresh_data_quality_table(ticker)
        self.refresh_peer_table()
        self.refresh_cache_table(ticker)
        self.refresh_market_table(ticker)
        self.refresh_history_table(ticker)
        self.refresh_price_metrics_table(ticker)
        self.refresh_price_history_table(ticker)
        self.refresh_readiness_table(ticker)
        self.refresh_hud_panel()


def run_app() -> None:
    init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    apply_windows_dark_title_bar(window)
    sys.exit(app.exec())
