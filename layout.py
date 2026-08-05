"""Layout and callbacks for the Dash application."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objs as go
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from data_utils import (
    calculate_date_range,
    calculate_metrics,
    dropdown_options,
    fetch_symbol,
    get_cumulative_series,
    load_tickers,
    refresh_cache,
    save_tickers,
    slice_range,
)

PERIODS = ("ytd", "1y", "3y", "5y", "10y", "custom")
COLORS = {"overnight": "#1a1a1a", "intraday": "#d0d0d0", "buy_hold": "#808080"}


def create_layout(app: Dash, data_cache: dict[str, pd.DataFrame]) -> html.Div:
    tickers = list(data_cache) or load_tickers()
    start, end = calculate_date_range("1y", data_cache)

    layout = html.Div(
        className="container",
        children=[
            html.Div(className="header", children=[html.H1("Day vs Night Returns", className="title")]),
            html.Div(
                className="controls",
                children=[
                    html.Div(
                        className="control-group control-group-left",
                        children=[
                            html.Label("Ticker", className="control-label"),
                            dcc.Dropdown(
                                id="symbol-dropdown",
                                options=dropdown_options(tickers),
                                value=tickers[0] if tickers else None,
                                clearable=False,
                                searchable=True,
                                className="custom-dropdown",
                            ),
                            html.Div(
                                className="ticker-manage",
                                children=[
                                    dcc.Input(
                                        id="ticker-input",
                                        type="text",
                                        placeholder="Add ticker",
                                        debounce=True,
                                        className="ticker-input",
                                    ),
                                    html.Button("Add", id="btn-add", className="ticker-btn"),
                                    html.Button("Remove", id="btn-remove", className="ticker-btn"),
                                    html.Button("Refresh", id="btn-refresh", className="ticker-btn ticker-btn-refresh"),
                                ],
                            ),
                            html.Div(id="ticker-status", className="ticker-status"),
                        ],
                    ),
                    html.Div(
                        className="control-group control-group-right",
                        children=[
                            html.Label("Period", className="control-label"),
                            html.Div(
                                className="period-controls",
                                children=[
                                    html.Div(
                                        className="period-buttons",
                                        children=[
                                            html.Button(
                                                p.upper(),
                                                id=f"btn-{p}",
                                                className="period-btn"
                                                + (" period-btn-active" if p == "1y" else ""),
                                            )
                                            for p in PERIODS
                                        ],
                                    ),
                                    dcc.DatePickerRange(
                                        id="date-range",
                                        start_date=start,
                                        end_date=end,
                                        display_format="YYYY-MM-DD",
                                        className="date-picker date-picker-hidden",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(id="current-period", children="1y", style={"display": "none"}),
            dcc.Store(id="data-revision", data=0),
            dcc.Loading(
                id="loading",
                type="default",
                children=[
                    dcc.Graph(
                        id="perf-graph",
                        className="graph",
                        config={"displayModeBar": False, "displaylogo": False},
                    )
                ],
            ),
            html.Div(id="metrics-container", className="metrics-container"),
        ],
    )
    register_callbacks(app, data_cache)
    return layout


def _period_classes(active: str) -> list[str]:
    return [
        "period-btn period-btn-active" if p == active else "period-btn"
        for p in PERIODS
    ]


def register_callbacks(app: Dash, data_cache: dict[str, pd.DataFrame]) -> None:
    @app.callback(
        Output("current-period", "children"),
        Output("date-range", "className"),
        Output("date-range", "start_date"),
        Output("date-range", "end_date"),
        *[Output(f"btn-{p}", "className") for p in PERIODS],
        *[Input(f"btn-{p}", "n_clicks") for p in PERIODS],
        State("current-period", "children"),
        State("date-range", "start_date"),
        State("date-range", "end_date"),
        prevent_initial_call=False,
    )
    def update_period(*args: Any):
        current, start, end = args[-3], args[-2], args[-1]
        triggered = ctx.triggered_id
        period = triggered.removeprefix("btn-") if triggered else (current or "1y")

        if period == "custom":
            # Keep whatever dates are currently selected
            start = start or calculate_date_range("1y", data_cache)[0]
            end = end or calculate_date_range("1y", data_cache)[1]
            picker_class = "date-picker"
        else:
            start, end = calculate_date_range(period, data_cache)
            picker_class = "date-picker date-picker-hidden"

        return period, picker_class, start, end, *_period_classes(period)

    @app.callback(
        Output("symbol-dropdown", "options"),
        Output("symbol-dropdown", "value"),
        Output("ticker-status", "children"),
        Output("ticker-input", "value"),
        Output("data-revision", "data"),
        Input("btn-add", "n_clicks"),
        Input("btn-remove", "n_clicks"),
        Input("btn-refresh", "n_clicks"),
        State("ticker-input", "value"),
        State("symbol-dropdown", "value"),
        State("data-revision", "data"),
        prevent_initial_call=True,
    )
    def manage_tickers(_add, _remove, _refresh, new_ticker, current, revision):
        tickers = list(data_cache) or load_tickers()
        revision = (revision or 0) + 1

        if ctx.triggered_id == "btn-add":
            symbol = (new_ticker or "").strip().upper()
            if not symbol:
                return no_update, no_update, "Enter a ticker symbol", no_update, no_update
            if symbol in data_cache:
                return dropdown_options(tickers), symbol, f"{symbol} already loaded", "", no_update
            df = fetch_symbol(symbol)
            if df is None:
                return no_update, no_update, f"Could not load {symbol}", no_update, no_update
            data_cache[symbol] = df
            tickers = list(data_cache)
            save_tickers(tickers)
            return dropdown_options(tickers), symbol, f"Added {symbol}", "", revision

        if ctx.triggered_id == "btn-remove":
            if not current or current not in data_cache:
                return no_update, no_update, "Nothing to remove", no_update, no_update
            if len(data_cache) <= 1:
                return no_update, no_update, "Keep at least one ticker", no_update, no_update
            del data_cache[current]
            tickers = list(data_cache)
            save_tickers(tickers)
            return dropdown_options(tickers), tickers[0], f"Removed {current}", no_update, revision

        loaded = refresh_cache(data_cache, load_tickers())
        if not loaded:
            return [], None, "Refresh failed — no data", no_update, revision
        save_tickers(loaded)
        selected = current if current in loaded else loaded[0]
        return dropdown_options(loaded), selected, f"Refreshed {len(loaded)} tickers", no_update, revision

    @app.callback(
        Output("perf-graph", "figure"),
        Output("metrics-container", "children"),
        Input("symbol-dropdown", "value"),
        Input("date-range", "start_date"),
        Input("date-range", "end_date"),
        Input("data-revision", "data"),
    )
    def update_dashboard(symbol: str | None, start: str | None, end: str | None, _revision):
        if not symbol or symbol not in data_cache:
            return _empty_figure("No data available"), html.Div()
        if not start or not end:
            return _empty_figure("Select date range"), html.Div()

        try:
            df = data_cache[symbol]
            filtered = slice_range(df, start, end)
            if filtered.empty:
                return _empty_figure("No data in range"), html.Div()
            return (
                _performance_figure(get_cumulative_series(filtered)),
                _metrics_display(calculate_metrics(df, start, end)),
            )
        except Exception as exc:
            print(f"Error in callback: {exc}")
            return _empty_figure(f"Error: {exc}"), html.Div()


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
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


def _performance_figure(data: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for key, name, dash in (
        ("overnight", "Overnight", "solid"),
        ("intraday", "Intraday", "solid"),
        ("buy_hold", "Buy & Hold", "dash"),
    ):
        fig.add_trace(
            go.Scatter(
                x=data["Date"],
                y=data[key] * 100,
                mode="lines",
                name=name,
                line=dict(color=COLORS[key], width=2.5, dash=dash),
                hovertemplate=f"<b>{name}</b><br>%{{y:.2f}}%<extra></extra>",
            )
        )
    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0", zeroline=False, title=""),
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


def _metrics_display(metrics: dict[str, dict[str, float]]) -> html.Div:
    cards = (
        ("overnight", "Overnight", "Close → Open", "metric-card-overnight"),
        ("intraday", "Intraday", "Open → Close", "metric-card-intraday"),
        ("buy_hold", "Buy & Hold", "Close → Close", "metric-card-buyhold"),
    )
    return html.Div(
        className="metrics-grid",
        children=[
            html.Div(
                className=f"metric-card {css}",
                children=[
                    html.Div(label, className="metric-label"),
                    html.Div(f"{metrics[key]['return']:+.2f}%", className="metric-value"),
                    html.Div(f"Sharpe {metrics[key]['sharpe']:.2f}", className="metric-sharpe"),
                    html.Div(subtitle, className="metric-subtitle"),
                ],
            )
            for key, label, subtitle, css in cards
        ],
    )
