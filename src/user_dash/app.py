"""Dash user app - modern factor analysis dashboard."""
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import requests
from flask import request as flask_request
from src.logging.logger import get_logger

logger = get_logger(__name__)

# Get API base URL from Flask request context
def get_api_url():
    """Get API base URL."""
    try:
        if flask_request:
            base_url = f"{flask_request.scheme}://{flask_request.host}"
            return base_url
    except:
        pass
    # Fallback to default port (will be overridden by actual request)
    from config.settings import get_settings
    settings = get_settings()
    return f"http://localhost:{settings.SERVER_PORT}"

# Modern color palette
COLORS = {
    "primary": "#6366f1",  # Indigo
    "secondary": "#8b5cf6",  # Purple
    "success": "#10b981",  # Green
    "warning": "#f59e0b",  # Amber
    "danger": "#ef4444",  # Red
    "dark": "#1f2937",  # Dark gray
    "light": "#f9fafb",  # Light gray
    "text": "#111827",  # Text dark
    "text_light": "#6b7280",  # Text light
}


def create_user_dash(server=None):
    """Create Dash app with modern design."""
    app = dash.Dash(
        __name__,
        server=server,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
        ],
        suppress_callback_exceptions=True,
    )
    
    app.title = "R&D Factor Analysis"
    
    # Layout
    app.layout = create_layout()
    
    # Callbacks
    register_callbacks(app)
    
    return app


def create_layout():
    """Create main layout."""
    return dbc.Container(
        fluid=True,
        style={"padding": 0, "fontFamily": "'Inter', sans-serif"},
        children=[
            # Navigation
            create_navbar(),
            
            # Main content
            dbc.Container(
                fluid=True,
                style={"padding": "2rem", "backgroundColor": COLORS["light"], "minHeight": "100vh"},
                children=[
                    dcc.Location(id="url", refresh=False),
                    html.Div(id="page-content"),
                ],
            ),
        ],
    )


def create_navbar():
    """Create navigation bar."""
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand(
                    "R&D Alpha",
                    className="ms-2",
                    style={"fontSize": "1.5rem", "fontWeight": 700, "color": COLORS["primary"]},
                ),
                dbc.Nav(
                    [
                        dbc.NavLink("Overview", href="/", active="exact", id="nav-overview"),
                        dbc.NavLink("Companies", href="/companies", active="exact", id="nav-companies"),
                        dbc.NavLink("Backtests", href="/backtests", active="exact", id="nav-backtests"),
                        dbc.NavLink("Statistics", href="/statistics", active="exact", id="nav-statistics"),
                    ],
                    navbar=True,
                    className="ms-auto",
                ),
            ],
            fluid=True,
        ),
        color="white",
        dark=False,
        style={"boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "marginBottom": "1rem"},
    )


def create_home_page():
    """Create home/overview page."""
    return [
        html.Div(
            [
                html.H2(
                    "R&D Factor Analysis",
                    style={"fontWeight": 700, "marginBottom": "0.5rem", "color": COLORS["text"]},
                ),
                html.P(
                    "Explore R&D intensity and narrative factors across companies",
                    style={"color": COLORS["text_light"], "marginBottom": "2rem"},
                ),
            ],
            style={"marginBottom": "2rem"},
        ),
        # Factor summary cards
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H6("Total Companies", className="text-muted"),
                                        html.H2(id="total-companies", children="0", style={"fontWeight": 700}),
                                    ]
                                ),
                            ],
                            className="mb-3",
                            style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H6("Avg R&D Intensity", className="text-muted"),
                                        html.H2(id="avg-rd-intensity", children="0%", style={"fontWeight": 700}),
                                    ]
                                ),
                            ],
                            className="mb-3",
                            style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H6("Avg Tone Score", className="text-muted"),
                                        html.H2(id="avg-tone", children="0.0", style={"fontWeight": 700}),
                                    ]
                                ),
                            ],
                            className="mb-3",
                            style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H6("Total R&D Mentions", className="text-muted"),
                                        html.H2(id="total-mentions", children="0", style={"fontWeight": 700}),
                                    ]
                                ),
                            ],
                            className="mb-3",
                            style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                        ),
                    ],
                    md=3,
                ),
            ],
            className="mb-4",
        ),
        # R&D Intensity Chart
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("R&D Intensity by Company", style={"fontWeight": 600}),
                                dbc.CardBody(
                                    [
                                        dcc.Graph(id="rd-intensity-chart"),
                                    ]
                                ),
                            ],
                            style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                        ),
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("R&D Tone Score Distribution", style={"fontWeight": 600}),
                                dbc.CardBody(
                                    [
                                        dcc.Graph(id="tone-distribution-chart"),
                                    ]
                                ),
                            ],
                            style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                        ),
                    ],
                    md=6,
                ),
            ],
            className="mb-4",
        ),
        # Top companies table
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("Top R&D Companies", style={"fontWeight": 600}),
                                dbc.CardBody(
                                    [
                                        html.Div(id="top-companies-table"),
                                    ]
                                ),
                            ],
                            style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                        ),
                    ],
                ),
            ],
        ),
    ]


def create_companies_page():
    """Create companies page."""
    return [
        html.Div(
            [
                html.H2("Companies", style={"fontWeight": 700, "marginBottom": "0.5rem"}),
                html.P("Explore R&D factors by company", style={"color": COLORS["text_light"], "marginBottom": "2rem"}),
            ],
            style={"marginBottom": "2rem"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.InputGroup(
                            [
                                dbc.Input(
                                    id="company-search",
                                    placeholder="Search companies...",
                                    type="text",
                                ),
                            ],
                            className="mb-3",
                        ),
                    ],
                    md=6,
                ),
            ],
        ),
        html.Div(id="company-cards-grid"),
    ]


def create_company_detail_page(ticker):
    """Create comprehensive company detail page."""
    return [
        html.Div(
            [
                html.Div(
                    [
                        dbc.Button("← Back to Companies", href="/companies", color="link", className="mb-2"),
                        html.H2(f"{ticker} - Company Details", style={"fontWeight": 700, "marginBottom": "0.5rem"}),
                        html.P("Comprehensive financial and R&D analysis", style={"color": COLORS["text_light"]}),
                    ],
                ),
            ],
            style={"marginBottom": "2rem"},
        ),
        dbc.Tabs(
            [
                dbc.Tab(label="Overview", tab_id="overview"),
                dbc.Tab(label="Financial Statements", tab_id="financials"),
                dbc.Tab(label="R&D Analysis", tab_id="rd"),
                dbc.Tab(label="Documents", tab_id="documents"),
                dbc.Tab(label="Price Data", tab_id="prices"),
            ],
            id="company-tabs",
            active_tab="overview",
            className="mb-3",
        ),
        html.Div(id="company-tab-content"),
    ]


def create_statistics_page():
    """Create comprehensive statistics page."""
    return [
        html.Div(
            [
                html.H2("Database Statistics", style={"fontWeight": 700, "marginBottom": "0.5rem"}),
                html.P("Comprehensive data overview and counters", style={"color": COLORS["text_light"], "marginBottom": "2rem"}),
            ],
            style={"marginBottom": "2rem"},
        ),
        html.Div(id="statistics-content"),
    ]


def create_backtests_page():
    """Create backtests page."""
    return [
        html.Div(
            [
                html.H2("Backtests", style={"fontWeight": 700, "marginBottom": "0.5rem"}),
                html.P("Run and analyze factor backtests", style={"color": COLORS["text_light"], "marginBottom": "2rem"}),
            ],
            style={"marginBottom": "2rem"},
        ),
        # Run backtest card
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("Run New Backtest", style={"fontWeight": 600}),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        dbc.Label("Factor"),
                                                        dbc.Select(
                                                            id="backtest-factor",
                                                            options=[
                                                                {"label": "R&D Combined", "value": "RND_v1_combined"},
                                                                {"label": "R&D Numeric", "value": "RND_v1_numeric"},
                                                                {"label": "R&D Text", "value": "RND_v1_text"},
                                                            ],
                                                            value="RND_v1_combined",
                                                        ),
                                                    ],
                                                    md=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Label("Start Year"),
                                                        dbc.Input(id="backtest-start-year", type="number", value=2020),
                                                    ],
                                                    md=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Label("End Year"),
                                                        dbc.Input(id="backtest-end-year", type="number", value=2023),
                                                    ],
                                                    md=4,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Button(
                                            "Run Backtest",
                                            id="run-backtest-btn",
                                            color="primary",
                                            className="w-100",
                                        ),
                                        html.Div(id="backtest-status", className="mt-3"),
                                    ]
                                ),
                            ],
                            style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                            className="mb-4",
                        ),
                    ],
                ),
            ],
        ),
        # Backtest results
        html.Div(id="backtest-results"),
    ]


def register_callbacks(app):
    """Register Dash callbacks."""
    
    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname"),
    )
    def display_page(pathname):
        if pathname == "/companies":
            return create_companies_page()
        elif pathname == "/backtests":
            return create_backtests_page()
        elif pathname == "/statistics":
            return create_statistics_page()
        elif pathname and pathname.startswith("/companies/"):
            ticker = pathname.split("/")[-1]
            return create_company_detail_page(ticker)
        else:
            return create_home_page()
    
    @app.callback(
        [Output("total-companies", "children"),
         Output("avg-rd-intensity", "children"),
         Output("avg-tone", "children"),
         Output("total-mentions", "children"),
         Output("rd-intensity-chart", "figure"),
         Output("tone-distribution-chart", "figure"),
         Output("top-companies-table", "children")],
        Input("url", "pathname"),
    )
    def update_home_metrics(pathname):
        if pathname != "/":
            return "0", "0%", "0.0", "0", {}, {}, ""
        
        try:
            api_url = get_api_url()
            response = requests.get(f"{api_url}/api/factors/rd/summary")
            data = response.json() if response.status_code == 200 else []
        except:
            data = []
        
        if not data:
            return "0", "0%", "0.0", "0", {}, {}, ""
        
        df = pd.DataFrame(data)
        
        # Metrics
        total_companies = len(df["ticker"].unique()) if not df.empty else 0
        # Handle None values in rd_intensity
        if "rd_intensity" in df.columns:
            df["rd_intensity"] = pd.to_numeric(df["rd_intensity"], errors="coerce")
            avg_intensity = df["rd_intensity"].mean() * 100 if df["rd_intensity"].notna().any() else 0
        else:
            avg_intensity = 0
        avg_tone = df["rd_tone_score"].mean() if "rd_tone_score" in df.columns and not df.empty else 0
        total_mentions = df["rd_mentions"].sum() if "rd_mentions" in df.columns and not df.empty else 0
        
        # Charts
        intensity_fig = go.Figure()
        if "rd_intensity" in df.columns and "ticker" in df.columns and df["rd_intensity"].notna().any():
            intensity_data = df.groupby("ticker")["rd_intensity"].mean().sort_values(ascending=False)
            intensity_data = intensity_data[intensity_data.notna()]
            if not intensity_data.empty:
                intensity_fig.add_trace(
                    go.Bar(
                        x=intensity_data.index,
                        y=intensity_data.values * 100,
                        marker_color=COLORS["primary"],
                    )
                )
                intensity_fig.update_layout(
                    xaxis_title="Company",
                    yaxis_title="R&D Intensity (%)",
                    template="plotly_white",
                    height=300,
                )
            else:
                intensity_fig.add_annotation(
                    text="R&D Intensity data not available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        else:
            intensity_fig.add_annotation(
                text="R&D Intensity data not available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        tone_fig = go.Figure()
        if "rd_tone_score" in df.columns:
            tone_fig.add_trace(
                go.Histogram(
                    x=df["rd_tone_score"].dropna(),
                    nbinsx=20,
                    marker_color=COLORS["secondary"],
                )
            )
            tone_fig.update_layout(
                xaxis_title="Tone Score",
                yaxis_title="Frequency",
                template="plotly_white",
                height=300,
            )
        
        # Top companies table
        if not df.empty and "ticker" in df.columns:
            agg_dict = {
                "rd_tone_score": "mean",
                "rd_mentions": "sum",
            }
            if "rd_intensity" in df.columns:
                agg_dict["rd_intensity"] = "mean"
            
            top_df = df.groupby("ticker").agg(agg_dict)
            
            # Sort by tone score if intensity not available
            sort_col = "rd_intensity" if "rd_intensity" in top_df.columns and top_df["rd_intensity"].notna().any() else "rd_tone_score"
            top_df = top_df.sort_values(sort_col, ascending=False).head(10)
            
            table = dbc.Table.from_dataframe(
                top_df.reset_index(),
                striped=True,
                bordered=True,
                hover=True,
                responsive=True,
            )
        else:
            table = html.P("No data available")
        
        return (
            str(total_companies),
            f"{avg_intensity:.1f}%",
            f"{avg_tone:.2f}",
            str(int(total_mentions)),
            intensity_fig,
            tone_fig,
            table,
        )
    
    @app.callback(
        Output("company-cards-grid", "children"),
        [Input("url", "pathname"),
         Input("company-search", "value")],
    )
    def update_company_cards(pathname, search_value):
        if pathname != "/companies":
            return ""
        
        api_url = get_api_url()
        
        # First, try to get companies list
        try:
            companies_response = requests.get(f"{api_url}/api/companies/")
            companies_list = companies_response.json() if companies_response.status_code == 200 else []
        except Exception as e:
            logger.error(f"Error fetching companies list: {e}")
            companies_list = []
        
        if not companies_list:
            return html.Div([
                html.P("No companies found in database.", style={"color": COLORS["text_light"]}),
                html.P("Please run the data ingestion pipeline first:", style={"color": COLORS["text_light"], "marginTop": "1rem"}),
                html.Code("python scripts/run_full_pipeline.py", style={"backgroundColor": "#f5f5f5", "padding": "0.5rem", "display": "block"}),
            ])
        
        # Try to get R&D summary data for additional metrics
        rd_data = {}
        try:
            rd_response = requests.get(f"{api_url}/api/factors/rd/summary")
            if rd_response.status_code == 200:
                rd_list = rd_response.json()
                # Create a lookup dict by ticker
                for item in rd_list:
                    ticker = item.get("ticker")
                    if ticker:
                        rd_data[ticker] = item
        except Exception as e:
            logger.debug(f"Could not fetch R&D summary: {e}")
        
        # Filter by search if provided
        if search_value:
            companies_list = [c for c in companies_list if search_value.lower() in c.get("ticker", "").lower() or search_value.lower() in c.get("name", "").lower()]
        
        if not companies_list:
            return html.P(f"No companies found matching '{search_value}'", style={"color": COLORS["text_light"]})
        
        cards = []
        for company in companies_list:
            ticker = company.get("ticker", "N/A")
            name = company.get("name", "N/A")
            years_available = company.get("years_available", 0)
            
            # Get R&D data if available
            rd_info = rd_data.get(ticker, {})
            
            card_body = [
                html.H5(ticker, style={"fontWeight": 600}),
                html.P(name, style={"fontSize": "0.9rem", "color": COLORS["text_light"], "marginBottom": "0.5rem"}),
                html.Hr(),
            ]
            
            # Add years available
            card_body.append(html.P([
                html.Strong("Years Available: "),
                str(years_available),
            ]))
            
            # Add R&D metrics if available
            if rd_info:
                if rd_info.get("rd_intensity") is not None:
                    intensity = rd_info.get("rd_intensity", 0)
                    if isinstance(intensity, (int, float)) and not pd.isna(intensity):
                        card_body.append(html.P([
                            html.Strong("R&D Intensity: "),
                            f"{intensity*100:.2f}%",
                        ]))
                
                if rd_info.get("rd_tone_score") is not None:
                    tone = rd_info.get("rd_tone_score", 0)
                    if isinstance(tone, (int, float)) and not pd.isna(tone):
                        card_body.append(html.P([
                            html.Strong("Tone Score: "),
                            f"{tone:.2f}",
                        ]))
                
                if rd_info.get("rd_mentions") is not None:
                    mentions = rd_info.get("rd_mentions", 0)
                    if isinstance(mentions, (int, float)) and not pd.isna(mentions):
                        card_body.append(html.P([
                            html.Strong("Mentions: "),
                            str(int(mentions)),
                        ]))
            else:
                card_body.append(html.P([
                    html.Small("R&D data not yet extracted", style={"color": COLORS["text_light"], "fontStyle": "italic"}),
                ]))
            
            # Add "View Details" button
            card_body.append(html.Hr())
            card_body.append(
                dbc.Button(
                    "View Details",
                    href=f"/companies/{ticker}",
                    color="primary",
                    size="sm",
                    className="w-100",
                )
            )
            
            cards.append(
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(card_body),
                            ],
                            style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "marginBottom": "1rem", "height": "100%"},
                        ),
                    ],
                    md=4,
                )
            )
        
        return dbc.Row(cards)
    
    @app.callback(
        [Output("backtest-status", "children"),
         Output("backtest-results", "children")],
        [Input("run-backtest-btn", "n_clicks"),
         State("backtest-factor", "value"),
         State("backtest-start-year", "value"),
         State("backtest-end-year", "value")],
    )
    def run_backtest_callback(n_clicks, factor, start_year, end_year):
        if not n_clicks:
            return "", ""
        
        try:
            api_url = get_api_url()
            response = requests.post(
                f"{api_url}/api/backtests/run",
                json={
                    "factor_id": factor,
                    "universe": ["pilot_top10"],
                    "start_year": start_year,
                    "end_year": end_year,
                },
            )
            
            if response.status_code == 200:
                result = response.json()
                status = dbc.Alert(
                    f"Backtest started! ID: {result.get('id')}",
                    color="success",
                )
                
                # Get results
                results_response = requests.get(f"{api_url}/api/backtests/{result.get('id')}/results")
                if results_response.status_code == 200:
                    results_data = results_response.json()
                    if results_data:
                        results_df = pd.DataFrame(results_data)
                        results_table = dbc.Table.from_dataframe(results_df, striped=True, bordered=True, hover=True)
                        return status, dbc.Card([dbc.CardHeader("Results"), dbc.CardBody(results_table)])
                
                return status, ""
            else:
                return dbc.Alert("Error running backtest", color="danger"), ""
        except Exception as e:
            return dbc.Alert(f"Error: {str(e)}", color="danger"), ""
    
    @app.callback(
        Output("statistics-content", "children"),
        Input("url", "pathname"),
    )
    def update_statistics(pathname):
        if pathname != "/statistics":
            return ""
        
        api_url = get_api_url()
        try:
            response = requests.get(f"{api_url}/api/companies/stats/summary")
            stats = response.json() if response.status_code == 200 else {}
        except Exception as e:
            return dbc.Alert(f"Error loading statistics: {str(e)}", color="danger")
    
        # Unified filings snapshot (bounded for UI)
        unified_rows: list = []
        try:
            unified_resp = requests.get(f"{api_url}/api/unified/filings", params={"limit": 300})
            unified_payload = unified_resp.json() if unified_resp.status_code == 200 else {}
            unified_rows = unified_payload.get("rows", [])
        except Exception as e:
            logger.debug(f"Failed to load unified filings: {e}")
        
        companies_stats = stats.get("companies", {})
        years_stats = stats.get("company_years", {})
        reports_stats = stats.get("annual_reports", {})
        chunks_stats = stats.get("text_chunks", {})
        prices_stats = stats.get("prices", {})
        
        return [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Companies", style={"fontWeight": 600, "color": COLORS["primary"]}),
                                    dbc.CardBody(
                                        [
                                            html.H3(str(companies_stats.get("total", 0)), style={"fontWeight": 700, "color": COLORS["primary"]}),
                                            html.P("Total Companies", className="text-muted"),
                                            html.Hr(),
                                            html.P([html.Strong("With Financials: "), str(companies_stats.get("with_financials", 0))]),
                                            html.P([html.Strong("With Ratios: "), str(companies_stats.get("with_ratios", 0))]),
                                            html.P([html.Strong("With Text Factors: "), str(companies_stats.get("with_text_factors", 0))]),
                                        ]
                                    ),
                                ],
                                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "height": "100%"},
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Company Years", style={"fontWeight": 600, "color": COLORS["secondary"]}),
                                    dbc.CardBody(
                                        [
                                            html.H3(str(years_stats.get("total", 0)), style={"fontWeight": 700, "color": COLORS["secondary"]}),
                                            html.P("Total Company Years", className="text-muted"),
                                            html.Hr(),
                                            html.P([html.Strong("With Financials: "), str(years_stats.get("with_financials", 0))]),
                                            html.P([html.Strong("With Ratios: "), str(years_stats.get("with_ratios", 0))]),
                                            html.P([html.Strong("With Text Factors: "), str(years_stats.get("with_text_factors", 0))]),
                                        ]
                                    ),
                                ],
                                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "height": "100%"},
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Annual Reports", style={"fontWeight": 600, "color": COLORS["success"]}),
                                    dbc.CardBody(
                                        [
                                            html.H3(str(reports_stats.get("total", 0)), style={"fontWeight": 700, "color": COLORS["success"]}),
                                            html.P("Total Reports", className="text-muted"),
                                            html.Hr(),
                                            html.P([html.Strong("Total Size: "), f"{reports_stats.get('total_size_bytes', 0) / 1e9:.2f} GB"]),
                                        ]
                                    ),
                                ],
                                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "height": "100%"},
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Text Chunks", style={"fontWeight": 600, "color": COLORS["warning"]}),
                                    dbc.CardBody(
                                        [
                                            html.H3(str(chunks_stats.get("total", 0)), style={"fontWeight": 700, "color": COLORS["warning"]}),
                                            html.P("Total Text Chunks", className="text-muted"),
                                            html.Hr(),
                                            html.P("Extracted from annual reports for GPT analysis"),
                                        ]
                                    ),
                                ],
                                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "height": "100%"},
                            ),
                        ],
                        md=3,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Price Data", style={"fontWeight": 600}),
                                    dbc.CardBody(
                                        [
                                            html.H3(str(prices_stats.get("total_records", 0)), style={"fontWeight": 700}),
                                            html.P("Total Price Records", className="text-muted"),
                                            html.Hr(),
                                            html.P([html.Strong("Unique Tickers: "), str(prices_stats.get("unique_tickers", 0))]),
                                        ]
                                    ),
                                ],
                                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                            ),
                        ],
                        md=6,
                    ),
                ],
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Unified Filings (master reference)", style={"fontWeight": 600}),
                                    dbc.CardBody(
                                        [
                                            dbc.Button(
                                                "Download CSV",
                                                href="/api/unified/filings/export",
                                                color="primary",
                                                outline=True,
                                                size="sm",
                                                className="mb-3",
                                                external_link=True,
                                            ),
                                            dash_table.DataTable(
                                                id="unified-filings-table",
                                                columns=[
                                                    {"name": "Ticker", "id": "ticker"},
                                                    {"name": "CIK", "id": "cik"},
                                                    {"name": "Fiscal Year", "id": "fiscal_year"},
                                                    {"name": "File Format", "id": "file_format"},
                                                    {"name": "Size (MB)", "id": "file_size_mb"},
                                                    {"name": "Extraction Status", "id": "extraction_status"},
                                                    {"name": "Report Path", "id": "report_path"},
                                                    {"name": "CY ID", "id": "company_year_id"},
                                                    {"name": "AR ID", "id": "annual_report_id"},
                                                ],
                                                data=[
                                                    {
                                                        **row,
                                                        "file_size_mb": round((row.get("file_size_bytes") or 0) / 1e6, 2),
                                                    }
                                                    for row in unified_rows
                                                ],
                                                page_size=15,
                                                style_table={"overflowX": "auto"},
                                                style_cell={
                                                    "fontFamily": "Inter, sans-serif",
                                                    "fontSize": "12px",
                                                    "padding": "6px",
                                                    "maxWidth": 240,
                                                    "textOverflow": "ellipsis",
                                                },
                                                style_header={"fontWeight": 700},
                                                sort_action="native",
                                                filter_action="native",
                                            )
                                            if unified_rows
                                            else html.P("No unified filings found. Ingest data to populate this table."),
                                        ]
                                    ),
                                ],
                                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                            )
                        ],
                    ),
                ],
                className="mt-4",
            ),
        ]
    
    @app.callback(
        Output("company-tab-content", "children"),
        [Input("company-tabs", "active_tab"),
         Input("url", "pathname")],
    )
    def update_company_tab_content(active_tab, pathname):
        if not pathname or not pathname.startswith("/companies/"):
            return ""
        
        ticker = pathname.split("/")[-1]
        api_url = get_api_url()
        
        try:
            url = f"{api_url}/api/companies/{ticker}"
            logger.debug(f"Fetching company data from: {url}")
            response = requests.get(url, timeout=10)
            logger.debug(f"Response status: {response.status_code}")
            
            if response.status_code == 404:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", "Company not found")
                logger.warning(f"Company {ticker} not found: {error_msg}")
                return dbc.Alert(f"Company {ticker} not found. Error: {error_msg}", color="danger")
            elif response.status_code != 200:
                logger.error(f"API returned status {response.status_code} for {ticker}")
                return dbc.Alert(f"Error loading company data: HTTP {response.status_code}", color="danger")
            
            company_data = response.json()
            if not company_data or not company_data.get("company"):
                logger.warning(f"Empty company data returned for {ticker}")
                return dbc.Alert(f"Company {ticker} data is empty", color="warning")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error loading company {ticker}: {e}")
            return dbc.Alert(f"Error connecting to API: {str(e)}", color="danger")
        except Exception as e:
            logger.error(f"Unexpected error loading company data for {ticker}: {e}", exc_info=True)
            return dbc.Alert(f"Error loading company data: {str(e)}", color="danger")
        
        if active_tab == "overview":
            return create_company_overview_tab(company_data, api_url, ticker)
        elif active_tab == "financials":
            return create_company_financials_tab(company_data)
        elif active_tab == "rd":
            return create_company_rd_tab(company_data)
        elif active_tab == "documents":
            return create_company_documents_tab(company_data, api_url, ticker)
        elif active_tab == "prices":
            return create_company_prices_tab(company_data, api_url, ticker)
        return ""
    
    def create_company_overview_tab(company_data, api_url, ticker):
        """Create overview tab content."""
        company = company_data.get("company", {})
        years = company_data.get("years", [])
        
        # Get stats summary
        try:
            stats_response = requests.get(f"{api_url}/api/companies/stats/summary")
            stats = stats_response.json() if stats_response.status_code == 200 else {}
        except:
            stats = {}
        
        return [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Company Information", style={"fontWeight": 600}),
                                    dbc.CardBody(
                                        [
                                            html.P([html.Strong("Ticker: "), company.get("ticker", "N/A")]),
                                            html.P([html.Strong("Name: "), company.get("name", "N/A")]),
                                            html.P([html.Strong("CIK: "), company.get("cik", "N/A")]),
                                            html.P([html.Strong("Years Available: "), str(len(years))]),
                                        ]
                                    ),
                                ],
                                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                            ),
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Database Statistics", style={"fontWeight": 600}),
                                    dbc.CardBody(
                                        [
                                            html.P([html.Strong("Total Companies: "), str(stats.get("companies", {}).get("total", 0))]),
                                            html.P([html.Strong("Total Company Years: "), str(stats.get("company_years", {}).get("total", 0))]),
                                            html.P([html.Strong("Total Annual Reports: "), str(stats.get("annual_reports", {}).get("total", 0))]),
                                            html.P([html.Strong("Total Text Chunks: "), str(stats.get("text_chunks", {}).get("total", 0))]),
                                        ]
                                    ),
                                ],
                                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                            ),
                        ],
                        md=6,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Available Years", style={"fontWeight": 600}),
                                    dbc.CardBody(
                                        [
                                            html.Ul([
                                                html.Li(f"{y.get('fiscal_year')} - {y.get('filing_date', 'N/A')[:10] if y.get('filing_date') else 'N/A'}")
                                                for y in sorted(years, key=lambda x: x.get("fiscal_year", 0), reverse=True)
                                            ]),
                                        ]
                                    ),
                                ],
                                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                            ),
                        ],
                    ),
                ],
            ),
        ]
    
    def create_company_financials_tab(company_data):
        """Create financial statements tab."""
        years = company_data.get("years", [])
        
        if not years:
            return dbc.Alert("No financial data available", color="warning")
        
        tabs = []
        for year_data in sorted(years, key=lambda x: x.get("fiscal_year", 0), reverse=True):
            year = year_data.get("fiscal_year")
            financials = year_data.get("financials", {})
            ratios = year_data.get("ratios", {})
            
            if not financials:
                continue
            
            income = financials.get("income_statement", {})
            balance = financials.get("balance_sheet", {})
            cashflow = financials.get("cash_flow", {})
            
            tab_content = [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader("Income Statement", style={"fontWeight": 600}),
                                        dbc.CardBody(
                                            [
                                                dbc.Table(
                                                    [
                                                        html.Thead([html.Tr([html.Th("Item"), html.Th("Value ($M)")])]),
                                                        html.Tbody([
                                                            html.Tr([html.Td(k.replace("_", " ").title()), html.Td(f"${v/1e6:.2f}" if v else "N/A")])
                                                            for k, v in income.items() if v is not None
                                                        ]),
                                                    ],
                                                    striped=True,
                                                    bordered=True,
                                                    hover=True,
                                                ),
                                            ]
                                        ),
                                    ],
                                    style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                                    className="mb-3",
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader("Balance Sheet", style={"fontWeight": 600}),
                                        dbc.CardBody(
                                            [
                                                dbc.Table(
                                                    [
                                                        html.Thead([html.Tr([html.Th("Item"), html.Th("Value ($M)")])]),
                                                        html.Tbody([
                                                            html.Tr([html.Td(k.replace("_", " ").title()), html.Td(f"${v/1e6:.2f}" if v else "N/A")])
                                                            for k, v in balance.items() if v is not None
                                                        ]),
                                                    ],
                                                    striped=True,
                                                    bordered=True,
                                                    hover=True,
                                                ),
                                            ]
                                        ),
                                    ],
                                    style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                                    className="mb-3",
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader("Cash Flow", style={"fontWeight": 600}),
                                        dbc.CardBody(
                                            [
                                                dbc.Table(
                                                    [
                                                        html.Thead([html.Tr([html.Th("Item"), html.Th("Value ($M)")])]),
                                                        html.Tbody([
                                                            html.Tr([html.Td(k.replace("_", " ").title()), html.Td(f"${v/1e6:.2f}" if v else "N/A")])
                                                            for k, v in cashflow.items() if v is not None
                                                        ]),
                                                    ],
                                                    striped=True,
                                                    bordered=True,
                                                    hover=True,
                                                ),
                                            ]
                                        ),
                                    ],
                                    style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                                    className="mb-3",
                                ),
                            ],
                            md=4,
                        ),
                    ],
                ),
            ]
            
            if ratios:
                ratio_data = ratios.get("profitability", {})
                ratio_data.update(ratios.get("rd_specific", {}))
                if ratio_data:
                    tab_content.append(
                        dbc.Card(
                            [
                                dbc.CardHeader("Key Ratios", style={"fontWeight": 600}),
                                dbc.CardBody(
                                    [
                                        dbc.Table(
                                            [
                                                html.Thead([html.Tr([html.Th("Ratio"), html.Th("Value")])]),
                                                html.Tbody([
                                                    html.Tr([html.Td(k.replace("_", " ").title()), html.Td(f"{v:.4f}" if v else "N/A")])
                                                    for k, v in ratio_data.items() if v is not None
                                                ]),
                                            ],
                                            striped=True,
                                            bordered=True,
                                            hover=True,
                                        ),
                                    ]
                                ),
                            ],
                            style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                        ),
                    )
            
            tabs.append(dbc.Tab(tab_content, label=str(year), tab_id=f"year-{year}"))
        
        if not tabs:
            return dbc.Alert("No financial statements available", color="warning")
        
        return dbc.Tabs(tabs, active_tab=tabs[0].tab_id if tabs else None)
    
    def create_company_rd_tab(company_data):
        """Create R&D analysis tab."""
        years = company_data.get("years", [])
        
        rd_data = []
        for year_data in sorted(years, key=lambda x: x.get("fiscal_year", 0), reverse=True):
            rd_factors = year_data.get("rd_text_factors", {})
            if rd_factors:
                rd_data.append({
                    "year": year_data.get("fiscal_year"),
                    **rd_factors,
                })
        
        if not rd_data:
            return dbc.Alert("No R&D text factors available. Run the R&D extraction pipeline.", color="warning")
        
        return [
            dbc.Card(
                [
                    dbc.CardHeader("R&D Text Factors by Year", style={"fontWeight": 600}),
                    dbc.CardBody(
                        [
                            dbc.Table.from_dataframe(
                                pd.DataFrame(rd_data),
                                striped=True,
                                bordered=True,
                                hover=True,
                                responsive=True,
                            ),
                        ]
                    ),
                ],
                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                className="mb-3",
            ),
            *[
                dbc.Card(
                    [
                        dbc.CardHeader(f"R&D Key Paragraphs - {rd.get('year')}", style={"fontWeight": 600}),
                        dbc.CardBody(
                            [
                                html.Div([
                                    html.P([html.Strong(f"Paragraph {i+1}:"), html.Br(), para.get("text", "")[:500] + "..."])
                                    for i, para in enumerate(rd.get("key_paragraphs", [])[:5])
                                ]) if rd.get("key_paragraphs") else html.P("No key paragraphs available"),
                            ]
                        ),
                    ],
                    style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                    className="mb-3",
                )
                for rd in rd_data if rd.get("key_paragraphs")
            ],
        ]
    
    def create_company_documents_tab(company_data, api_url, ticker):
        """Create documents tab."""
        years = company_data.get("years", [])
        
        documents = []
        for year_data in sorted(years, key=lambda x: x.get("fiscal_year", 0), reverse=True):
            report = year_data.get("annual_report", {})
            if report:
                # Build full download URL
                year = year_data.get("fiscal_year")
                download_url = f"{api_url}/api/companies/{ticker}/reports/{year}/download"
                
                documents.append({
                    "year": year,
                    "format": report.get("file_format", "N/A"),
                    "size_mb": f"{report.get('file_size_bytes', 0) / 1e6:.2f}" if report.get("file_size_bytes") else "N/A",
                    "download_url": download_url,
                })
        
        if not documents:
            return dbc.Alert("No annual reports available", color="warning")
        
        return [
            dbc.Card(
                [
                    dbc.CardHeader("Available Annual Reports", style={"fontWeight": 600}),
                    dbc.CardBody(
                        [
                            dbc.Table(
                                [
                                    html.Thead([
                                        html.Tr([
                                            html.Th("Year"),
                                            html.Th("Format"),
                                            html.Th("Size (MB)"),
                                            html.Th("Actions"),
                                        ])
                                    ]),
                                    html.Tbody([
                                        html.Tr([
                                            html.Td(str(doc["year"])),
                                            html.Td(doc["format"]),
                                            html.Td(doc["size_mb"]),
                                            html.Td(
                                                html.A(
                                                    "Download",
                                                    href=doc["download_url"],
                                                    className="btn btn-primary btn-sm",
                                                    style={
                                                        "textDecoration": "none",
                                                        "color": "white",
                                                        "display": "inline-block",
                                                        "padding": "0.375rem 0.75rem",
                                                    },
                                                ) if doc["download_url"] else "N/A"
                                            ),
                                        ])
                                        for doc in documents
                                    ]),
                                ],
                                striped=True,
                                bordered=True,
                                hover=True,
                            ),
                        ]
                    ),
                ],
                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
            ),
        ]
    
    def create_company_prices_tab(company_data, api_url, ticker):
        """Create price data tab."""
        try:
            response = requests.get(f"{api_url}/api/companies/{ticker}/prices")
            if response.status_code != 200:
                return dbc.Alert("Price data not available", color="warning")
            prices = response.json()
        except:
            return dbc.Alert("Error loading price data", color="danger")
        
        if not prices:
            return dbc.Alert("No price data available", color="warning")
        
        df = pd.DataFrame(prices)
        df["date"] = pd.to_datetime(df["date"])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["close"],
            mode="lines",
            name="Close Price",
            line=dict(color=COLORS["primary"]),
        ))
        fig.update_layout(
            title="Stock Price Over Time",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            template="plotly_white",
            height=400,
        )
        
        return [
            dbc.Card(
                [
                    dbc.CardHeader("Price Chart", style={"fontWeight": 600}),
                    dbc.CardBody([dcc.Graph(figure=fig)]),
                ],
                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
                className="mb-3",
            ),
            dbc.Card(
                [
                    dbc.CardHeader("Price Data Table", style={"fontWeight": 600}),
                    dbc.CardBody(
                        [
                            dbc.Table.from_dataframe(
                                df.tail(100),
                                striped=True,
                                bordered=True,
                                hover=True,
                                responsive=True,
                            ),
                        ]
                    ),
                ],
                style={"border": "none", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)"},
            ),
        ]
