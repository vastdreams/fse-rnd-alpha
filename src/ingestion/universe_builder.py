"""Build universe of companies from config."""
import yaml
from pathlib import Path
from typing import List, Dict
from config.settings import get_settings

settings = get_settings()


def load_universe_config() -> Dict:
    """Load universe configuration from config/universe.yml"""
    config_path = Path(__file__).parent.parent.parent / "config" / "universe.yml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_pilot_companies() -> List[Dict]:
    """Get pilot top 10 companies for testing."""
    config = load_universe_config()
    return config.get("pilot_top10", {}).get("companies", [])


def get_company_by_ticker(ticker: str) -> Dict | None:
    """Get company info by ticker from pilot universe."""
    companies = get_pilot_companies()
    for company in companies:
        if company.get("ticker") == ticker.upper():
            return company
    return None

