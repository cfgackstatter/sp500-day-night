"""Layout and callback definitions for the Dash application."""

from typing import Any, Dict, Tuple
from dash import html, dcc, Input, Output
import plotly.graph_objs as go
from datetime import datetime, timedelta
import pandas as pd
from data_utils import (
    get_index_choices,
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
                            html.Label("Date Range", className="control-label"),
                            dcc.DatePickerRange(
                                id="date-range",
                                start_date=start_date.strftime("%Y-%m-%d"),
                                end_date=end_date.strftime("%Y-%m-%d"),
                                display_format="YYYY-MM-DD",
                                className="date-picker",
                            ),
                        ]
                    ),
                ]
            ),
            
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
    
    @app.callback(
        [Output("perf-graph", "figure"), Output("metrics-container", "children")],
        [
            Input("symbol-dropdown", "value"),
            Input("date-range", "start_date"),
            Input("date-range", "end_date"),
        ],
    )
    def update_dashboard(
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> Tuple[go.Figure, html.Div]:
        """
        Updates the graph and metrics based on selected symbol and date range.
        
        Args:
            symbol: Selected ticker symbol
            start_date: Start date for display range
            end_date: End date for display range
            
        Returns:
            Tuple of (Plotly figure, metrics HTML div)
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
    """
    Creates an empty figure with a centered message.
    
    Args:
        message: Text to display
        
    Returns:
        go.Figure: Empty Plotly figure with annotation
    """
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
    """
    Creates the performance comparison chart with monochrome styling.
    
    Args:
        data: DataFrame with Date and cumulative strategy columns
        
    Returns:
        go.Figure: Formatted Plotly figure with very dark, light, and medium dashed lines
    """
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
    """
    Creates the compact metrics display with matching border styles.
    
    Args:
        metrics: Dictionary with strategy performance metrics
        
    Returns:
        html.Div: Formatted metrics section
    """
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
