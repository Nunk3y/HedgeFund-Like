from app.db import database
from app.db.settings_database import get_setting, set_setting

# Keep stock/watchlist/cache data in tech_screener.db, but route personal app
# settings such as API keys, SEC User-Agent, and UI preferences to personal_settings.db.
database.get_setting = get_setting
database.set_setting = set_setting

from app.ui.main_window import run_app

if __name__ == "__main__":
    run_app()
