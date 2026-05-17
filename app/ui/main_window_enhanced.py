import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.db.database import (
    add_ticker,
    delete_ticker,
    get_setting,
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
    polish_table,
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


def merged_peer_groups() -> list[str]:
    groups: list[str] = []
    for group in [*DEFAULT_PEER_GROUPS, *EXTRA_PEER_GROUPS]:
        if group not in groups:
            groups.append(group)
    return groups


class EnhancedMainWindow(MainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(1280, 820)

    def build_left_panel(self) -> QWidget:
        left = QWidget()
        left.setObjectName("ControlPanel")
        left.setMinimumWidth(500)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(14)
        left_title = QLabel("Watchlist Control")
        left_title.setObjectName("PanelTitle")
        left_hint = QLabel("Add tickers, assign peer groups, then run the full local pipeline.")
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
                "Enter your name and email in the SEC User-Agent field. It is saved only in your local database.",
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


def run_app() -> None:
    init_db()
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = EnhancedMainWindow()
    window.showMaximized()
    apply_windows_dark_title_bar(window)
    sys.exit(app.exec())
