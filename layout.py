"""Layout and callback definitions for the Dash application."""

from typing import Any, Dict, Tuple
from dash import html, dcc, Input, Output, State
import plotly.graph_objs as go
from datetime import datetime, timedelta
import pandas as pd
from data_utils import (
    get_index_choices,
    get_date_range_options,
    calculate_date_range,
    calculate_daily_strategies,
    calculate_metrics,
    get_cumulative_series,
)


def create_layout(app: Any, data_cache: Dict[str, pd.DataFrame]) -> html.Div:
    """
    Creates the main application layout with compact, professional design.
    
    Args:
        app: Dash application instance
        data_cache: Pre-loaded data for all symbols
        
    Returns:
        html.Div: Complete application layout
    """
    # Set default date range (last 2 years)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2 * 365)
    
    layout = html.Div(
        className="container",
        children=[
            # Header section
            html.Div(
                className="header",
                children=[
                    html.H1("Overnight vs Intraday Returns", className="title"),
                ]
            ),
            
            # Controls section
            html.Div(
                className="controls",
                children=[
                    html.Div(
                        className="control-group control-group-left",
                        children=[
                            html.Label("Index", className="control-label"),
                            dcc.Dropdown(
                                id="symbol-dropdown",
                                options=get_index_choices(),  # type: ignore
                                value="SPY",
                                clearable=False,
                                searchable=False,
                                className="custom-dropdown",
                            ),
                        ]
                    ),
                    html.Div(
                        className="control-group control-group-right",
                        children=[
                            html.Label("Period", className="control-label"),
                            html.Div(
                                className="period-controls",
                                children=[
                                    # Period buttons
                                    html.Div(
                                        className="period-buttons",
                                        children=[
                                            html.Button("YTD", id="btn-ytd", className="period-btn"),
                                            html.Button("1Y", id="btn-1y", className="period-btn period-btn-active"),
                                            html.Button("3Y", id="btn-3y", className="period-btn"),
                                            html.Button("5Y", id="btn-5y", className="period-btn"),
                                            html.Button("10Y", id="btn-10y", className="period-btn"),
                                            html.Button("Custom", id="btn-custom", className="period-btn"),
                                        ]
                                    ),
                                    # Date picker (initially hidden)
                                    dcc.DatePickerRange(
                                        id="date-range",
                                        start_date=start_date.strftime("%Y-%m-%d"),
                                        end_date=end_date.strftime("%Y-%m-%d"),
                                        display_format="YYYY-MM-DD",
                                        className="date-picker date-picker-hidden",
                                    ),
                                ]
                            ),
                        ]
                    ),
                ]
            ),
            
            # Hidden div to store current period
            html.Div(id="current-period", children="1y", style={"display": "none"}),
            
            # Graph section
            dcc.Loading(
                id="loading",
                type="default",
                children=[
                    dcc.Graph(
                        id="perf-graph",
                        className="graph",
                        config={"displayModeBar": False, "displaylogo": False}
                    )
                ],
            ),
            
            # Metrics section
            html.Div(id="metrics-container", className="metrics-container"),
        ]
    )

    register_callbacks(app, data_cache)
    return layout


def register_callbacks(app: Any, data_cache: Dict[str, pd.DataFrame]) -> None:
    """
    Registers all application callbacks for interactivity.
    
    Args:
        app: Dash application instance
        data_cache: Pre-loaded data for all symbols
    """
    
    # Callback to handle period button clicks
    @app.callback(
        [Output("current-period", "children"),
         Output("date-range", "className"),
         Output("date-range", "start_date"),
         Output("date-range", "end_date"),
         Output("btn-ytd", "className"),
         Output("btn-1y", "className"),
         Output("btn-3y", "className"),
         Output("btn-5y", "className"),
         Output("btn-10y", "className"),
         Output("btn-custom", "className")],
        [Input("btn-ytd", "n_clicks"),
         Input("btn-1y", "n_clicks"),
         Input("btn-3y", "n_clicks"),
         Input("btn-5y", "n_clicks"),
         Input("btn-10y", "n_clicks"),
         Input("btn-custom", "n_clicks")],
        [State("current-period", "children")]
    )
    def update_period_selection(ytd_clicks, y1_clicks, y3_clicks, y5_clicks, y10_clicks, custom_clicks, current_period):
        """Handle period button clicks and update date range."""
        from dash import callback_context
        
        if not callback_context.triggered:
            # Default to 1Y on startup
            start_date, end_date = calculate_date_range("1y", data_cache)
            return ("1y", "date-picker date-picker-hidden", start_date, end_date,
                    "period-btn", "period-btn period-btn-active", "period-btn", 
                    "period-btn", "period-btn", "period-btn")
        
        button_id = callback_context.triggered[0]["prop_id"].split(".")[0]
        
        # Map button IDs to periods
        period_map = {
            "btn-ytd": "ytd",
            "btn-1y": "1y", 
            "btn-3y": "3y",
            "btn-5y": "5y",
            "btn-10y": "10y",
            "btn-custom": "custom"
        }
        
        selected_period = period_map.get(button_id, current_period)
        
        # Calculate date range for selected period
        if selected_period != "custom":
            start_date, end_date = calculate_date_range(selected_period, data_cache)
            date_picker_class = "date-picker date-picker-hidden"
        else:
            # Keep current dates for custom mode
            start_date, end_date = calculate_date_range("1y", data_cache)
            date_picker_class = "date-picker"
        
        # Set active button classes
        button_classes = {
            "btn-ytd": "period-btn period-btn-active" if selected_period == "ytd" else "period-btn",
            "btn-1y": "period-btn period-btn-active" if selected_period == "1y" else "period-btn",
            "btn-3y": "period-btn period-btn-active" if selected_period == "3y" else "period-btn",
            "btn-5y": "period-btn period-btn-active" if selected_period == "5y" else "period-btn",
            "btn-10y": "period-btn period-btn-active" if selected_period == "10y" else "period-btn",
            "btn-custom": "period-btn period-btn-active" if selected_period == "custom" else "period-btn"
        }
        
        return (selected_period, date_picker_class, start_date, end_date,
                button_classes["btn-ytd"], button_classes["btn-1y"], button_classes["btn-3y"],
                button_classes["btn-5y"], button_classes["btn-10y"], button_classes["btn-custom"])
    
    # Main dashboard callback
    @app.callback(
        [Output("perf-graph", "figure"), Output("metrics-container", "children")],
        [Input("symbol-dropdown", "value"),
         Input("date-range", "start_date"),
         Input("date-range", "end_date")],
    )
    def update_dashboard(
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> Tuple[go.Figure, html.Div]:
        """
        Updates the graph and metrics based on selected symbol and date range.
        """
        # Validate inputs
        if not symbol or symbol not in data_cache:
            empty_fig = create_empty_figure("No data available")
            return empty_fig, html.Div()
        
        if not start_date or not end_date:
            empty_fig = create_empty_figure("Select date range")
            return empty_fig, html.Div()
        
        try:
            # Get cached data
            df = data_cache[symbol].copy()
            
            # Calculate daily strategy returns
            daily_returns = calculate_daily_strategies(df)
            
            # Filter by selected date range
            mask = (daily_returns["Date"] >= start_date) & (daily_returns["Date"] <= end_date)
            filtered_returns = daily_returns[mask].copy()
            
            if filtered_returns.empty:
                empty_fig = create_empty_figure("No data in range")
                return empty_fig, html.Div()
            
            # Convert to cumulative series for plotting
            cumulative_data = get_cumulative_series(filtered_returns)
            
            # Calculate metrics for the selected range
            metrics = calculate_metrics(daily_returns, start_date, end_date)
            
            # Create figure
            fig = create_performance_figure(cumulative_data)
            
            # Create metrics display
            metrics_div = create_metrics_display(metrics)
            
            return fig, metrics_div
            
        except Exception as e:
            print(f"Error in callback: {str(e)}")
            empty_fig = create_empty_figure(f"Error: {str(e)}")
            return empty_fig, html.Div()


def create_empty_figure(message: str) -> go.Figure:
    """Creates an empty figure with a centered message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=13, color="#999"),
    )
    fig.update_layout(
        template="plotly_white",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=350,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


def create_performance_figure(data: pd.DataFrame) -> go.Figure:
    """Creates the performance comparison chart with monochrome styling."""
    fig = go.Figure()
    
    # Monochrome palette: very dark, very light, medium gray
    colors = {
        "overnight": "#1a1a1a",    # Very dark gray (almost black)
        "intraday": "#d0d0d0",     # Very light gray
        "buy_hold": "#808080",     # Medium gray
    }
    
    # Add overnight strategy trace (very dark gray, solid)
    fig.add_trace(
        go.Scatter(
            x=data["Date"],
            y=data["overnight"] * 100,
            mode="lines",
            name="Overnight",
            line=dict(color=colors["overnight"], width=2.5),
            hovertemplate="<b>Overnight</b><br>%{y:.2f}%<extra></extra>",
        )
    )
    
    # Add intraday strategy trace (very light gray, solid)
    fig.add_trace(
        go.Scatter(
            x=data["Date"],
            y=data["intraday"] * 100,
            mode="lines",
            name="Intraday",
            line=dict(color=colors["intraday"], width=2.5),
            hovertemplate="<b>Intraday</b><br>%{y:.2f}%<extra></extra>",
        )
    )
    
    # Add buy-and-hold strategy trace (medium gray, DASHED)
    fig.add_trace(
        go.Scatter(
            x=data["Date"],
            y=data["buy_hold"] * 100,
            mode="lines",
            name="Buy & Hold",
            line=dict(color=colors["buy_hold"], width=2.5, dash="dash"),  # Dashed line
            hovertemplate="<b>Buy & Hold</b><br>%{y:.2f}%<extra></extra>",
        )
    )
    
    # Update layout - compact and professional
    fig.update_layout(
        template="plotly_white",
        showlegend=False,  # Remove legend (colors match metrics below)
        xaxis=dict(
            showgrid=True,
            gridcolor="#f0f0f0",
            zeroline=False,
            title="",
        ),
        yaxis=dict(
            title="Cumulative Return (%)",
            showgrid=True,
            gridcolor="#f0f0f0",
            zeroline=True,
            zerolinecolor="#d0d0d0",
            zerolinewidth=1,
            title_font=dict(size=12),
        ),
        hovermode="x unified",
        height=350,
        margin=dict(t=15, b=40, l=60, r=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    
    return fig


def create_metrics_display(metrics: Dict[str, float]) -> html.Div:
    """Creates the compact metrics display with matching border styles."""
    return html.Div(
        className="metrics-grid",
        children=[
            # Overnight metric (very dark gray solid border)
            html.Div(
                className="metric-card metric-card-overnight",
                children=[
                    html.Div("Overnight", className="metric-label"),
                    html.Div(f"{metrics['overnight']:+.2f}%", className="metric-value"),
                    html.Div("Close → Open", className="metric-subtitle"),
                ]
            ),
            # Intraday metric (very light gray solid border)
            html.Div(
                className="metric-card metric-card-intraday",
                children=[
                    html.Div("Intraday", className="metric-label"),
                    html.Div(f"{metrics['intraday']:+.2f}%", className="metric-value"),
                    html.Div("Open → Close", className="metric-subtitle"),
                ]
            ),
            # Buy & Hold metric (medium gray dashed border)
            html.Div(
                className="metric-card metric-card-buyhold",
                children=[
                    html.Div("Buy & Hold", className="metric-label"),
                    html.Div(f"{metrics['buy_hold']:+.2f}%", className="metric-value"),
                    html.Div("Close → Close", className="metric-subtitle"),
                ]
            ),
        ]
    )
