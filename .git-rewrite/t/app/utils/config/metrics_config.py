# app/config/metrics_config.py

# Financial metrics configuration with correct field names
METRICS_MAP = {
    "total revenues": "is_sales_and_services_revenues",
    "operating cash flow": "cf_cash_from_oper",
    "net income": "is_net_income",
    "earnings per share": "eps",
    "operating margin": "oper_margin",
    "capital expenditures": "cf_cap_expenditures",
    "return on invested capital": "return_on_inv_capital",
    "diluted shares": "is_sh_for_diluted_eps"  # Updated metric name
}

METRICS_TO_FETCH = list(METRICS_MAP.keys())

# Metrics that should include CAGR calculation
CAGR_METRICS = {
    "total revenues",
    "operating cash flow",
    "net income",
    "earnings per share"
}

# Analysis defaults
ANALYSIS_DEFAULTS = {
    'lookback_days': 365,
    'crossover_days': 180
}