# Static S&P 500 consensus forecasts and historical returns data (updated Dec 2024).

# Sources: Goldman Sachs, JP Morgan, Morgan Stanley, Bank of America
SP500_CONSENSUS_FORECASTS = {
    2020: {
        "level": 3756,
        "return_pct": 16.3,
        "type": "actual",
        "source": "S&P Dow Jones Indices"
    },
    2021: {
        "level": 4766,
        "return_pct": 26.9,
        "type": "actual",
        "source": "S&P Dow Jones Indices"
    },
    2022: {
        "level": 3839,
        "return_pct": -19.4,
        "type": "actual",
        "source": "S&P Dow Jones Indices"
    },
    2023: {
        "level": 4769,
        "return_pct": 24.2,
        "type": "actual",
        "source": "S&P Dow Jones Indices"
    },
    2024: {
        "level": 5880,
        "return_pct": 23.3,
        "type": "actual",
        "source": "S&P Dow Jones Indices (YTD Dec)"
    },
    2025: {
        "low": 5800,
        "mid": 6500,
        "high": 7000,
        "return_low": -1.4,
        "return_mid": 10.5,
        "return_high": 19.0,
        "type": "forecast",
        "source": "Goldman Sachs, JP Morgan, Morgan Stanley Average",
        "notes": "Consensus: soft landing, Fed rate cuts, AI productivity gains"
    },
    2026: {
        "low": 6100,
        "mid": 7150,
        "high": 8000,
        "return_low": 5.2,
        "return_mid": 10.0,
        "return_high": 14.3,
        "type": "forecast",
        "source": "5-year forward projections average",
        "notes": "Based on 10% long-term earnings growth assumption"
    },
    2027: {
        "low": 6400,
        "mid": 7865,
        "high": 9000,
        "return_low": 4.9,
        "return_mid": 10.0,
        "return_high": 12.5,
        "type": "forecast",
        "source": "Extrapolated from bank 5-year targets",
        "notes": "Assumes continued earnings expansion"
    },
    2028: {
        "low": 6700,
        "mid": 8650,
        "high": 10000,
        "return_low": 4.7,
        "return_mid": 10.0,
        "return_high": 11.1,
        "type": "forecast",
        "source": "Long-term projection models",
        "notes": "Reversion toward historical mean returns"
    },
    2029: {
        "low": 7000,
        "mid": 9515,
        "high": 11000,
        "return_low": 4.5,
        "return_mid": 10.0,
        "return_high": 10.0,
        "type": "forecast",
        "source": "Long-term projection models",
        "notes": "Assumes 8-10% annual earnings growth"
    },
    2030: {
        "low": 7300,
        "mid": 10467,
        "high": 12000,
        "return_low": 4.3,
        "return_mid": 10.0,
        "return_high": 9.1,
        "type": "forecast",
        "source": "10-year forward estimates",
        "notes": "Based on historical equity risk premium"
    },
}

FORECAST_SOURCES = [
    {
        "name": "Goldman Sachs",
        "division": "Global Investment Research",
        "frequency": "Quarterly",
        "last_update": "2024-11-15",
        "methodology": "Top-down earnings model with macro overlay",
    },
    {
        "name": "JP Morgan",
        "division": "Asset Management",
        "frequency": "Quarterly",
        "last_update": "2024-11-20",
        "methodology": "Fair value model based on earnings and rates",
    },
    {
        "name": "Morgan Stanley",
        "division": "Wealth Management",
        "frequency": "Monthly",
        "last_update": "2024-12-01",
        "methodology": "Cycle analysis with valuation framework",
    },
    {
        "name": "Bank of America",
        "division": "Global Research",
        "frequency": "Quarterly",
        "last_update": "2024-11-18",
        "methodology": "Bottom-up earnings aggregation",
    },
]

SP500_HISTORICAL_RETURNS = {
    2000: -10.1, 2001: -13.0, 2002: -23.4, 2003: 26.4, 2004: 9.0,
    2005: 3.0, 2006: 13.6, 2007: 3.5, 2008: -38.5, 2009: 23.5,
    2010: 12.8, 2011: 0.0, 2012: 13.4, 2013: 29.6, 2014: 11.4,
    2015: -0.7, 2016: 9.5, 2017: 19.4, 2018: -6.2, 2019: 28.9,
    2020: 16.3, 2021: 26.9, 2022: -19.4, 2023: 24.2, 2024: 23.3,
}
