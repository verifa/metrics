# =========================================================
# Constants
# =========================================================

import logging
import os

TEMPO_CONFIG_PATH = os.environ.get("TEMPO_CONFIG_PATH", "/tempo")
TEMPO_DAILY_HOURS = os.environ.get("TEMPO_DAILY_HOURS", 8)

TEMPO_LOG_LEVEL = os.environ.get("TEMPO_LOG_LEVEL", "WARNING")
if TEMPO_LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    logging.basicConfig(level=logging.getLevelName(TEMPO_LOG_LEVEL))
else:
    logging.warning("%s {} is not a valid log level, using default: WARNING", TEMPO_LOG_LEVEL)

NOTION_KEY = os.environ.get("NOTION_KEY", "")
NOTION_FINANCIAL_DATABASE_ID = os.environ.get("NOTION_FINANCIAL_DATABASE_ID", "")
NOTION_WORKINGHOURS_DATABASE_ID = os.environ.get("NOTION_WORKINGHOURS_DATABASE_ID", "")
NOTION_ALLOCATION_DATABASE_ID = os.environ.get("NOTION_ALLOCATIONS_DATABASE_ID", "")
NOTION_CREW_DATABASE_ID = os.environ.get("NOTION_CREW_DATABASE_ID", "")
NOTION_RATES_DATABASE_ID = os.environ.get("NOTION_RATES_DATABASE_ID", "")

COLOR_HEAD = "#ad9ce3"
COLOR_ONE = "#ccecef"
COLOR_TWO = "#fc9cac"

# Configure tabs to show in the UI
SHOWTAB_BILLABLE = False
SHOWTAB_COMPARISON = True
SHOWTAB_INTERNAL = False
SHOWTAB_POPULAR_PROJECTS = False
SHOWTAB_PAYING_PROJECTS = True
SHOWTAB_PROJECTS = True
SHOWTAB_FINANCE = True
SHOWTAB_RATES = False
SHOWTAB_ROLLING_INCOME = True
SHOWTAB_NORMALISED_WORKTIME = True
