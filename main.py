import sys

from PySide6.QtWidgets import QApplication

from app.db import database
from app.db.settings_database import get_setting, set_setting

# Keep stock/watchlist/cache data in tech_screener.db, but route personal app
# settings such as API keys, SEC User-Agent, and UI preferences to personal_settings.db.
database.get_setting = get_setting
database.set_setting = set_setting

from app.db.database import init_db
from app.ui.main_window import DARK_STYLE, MainWindow, apply_windows_dark_title_bar

SEC_USER_AGENT_HELP = (
    "Format: Your Name your-email@example.com. "
    "Example: Sebastiaan Vriese savriese@gmail.com. "
    "Required by the SEC request policy; saved locally only."
)


def run_app() -> None:
    init_db()
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow()
    if hasattr(window, "sec_user_agent"):
        window.sec_user_agent.setPlaceholderText("Format: Your Name your-email@example.com")
        window.sec_user_agent.setToolTip(SEC_USER_AGENT_HELP)
    window.show()
    apply_windows_dark_title_bar(window)
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
