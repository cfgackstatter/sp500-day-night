"""Data fetching and strategy computation utilities."""

from typing import Dict, List, Any, Tuple
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def get_index_choices() -> List[Dict[str, Any]]:
    """
    Returns dropdown choices for major index ETFs.
    
    Returns:
        List of dictionaries with 'label' and 'value' keys for Dash dropdown.
    """
    return [
        {"label": "S&P 500 (SPY)", "value": "SPY"},
        {"label": "NASDAQ 100 (QQQ)", "value": "QQQ"},
        {"label": "Dow Jones (DIA)", "value": "DIA"},
        {"label": "Russell 2000 (IWM)", "value": "IWM"},
    ]


def load_all_data() -> Dict[str, pd.DataFrame]:
    """
    Loads maximum available historical daily data for all symbols at startup.
    Downloads as much history as possible for each symbol.
    
    Returns:
        Dictionary mapping symbol to DataFrame with Date, Open, Close columns.
    """
    symbols = [choice["value"] for choice in get_index_choices()]
    data_cache = {}
    
    # Download maximum available data (30+ years back)
    end_date = datetime.now()
    start_date = datetime(1990, 1, 1)  # Start from 1990 to get maximum history
    
    for symbol in symbols:
        try:
            print(f"Downloading {symbol} (maximum history)...")
            df = yf.download(
                symbol,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval="1d",
                progress=False,
                auto_adjust=True,
            )
            
            if df is not None and not df.empty:
                df = df.reset_index()
                # Ensure we have Date, Open, Close columns
                if "Date" in df.columns and "Open" in df.columns and "Close" in df.columns:
                    data_cache[symbol] = df[["Date", "Open", "Close"]].copy()
                    first_date = df["Date"].iloc[0].strftime("%Y-%m-%d")
                    last_date = df["Date"].iloc[-1].strftime("%Y-%m-%d")
                    print(f"  ✓ {symbol}: {len(df)} days loaded ({first_date} to {last_date})")
                else:
                    print(f"  ✗ {symbol}: Missing required columns")
            else:
                print(f"  ✗ {symbol}: No data returned")
                
        except Exception as e:
            print(f"  ✗ {symbol}: Error - {str(e)}")
    
    return data_cache


def get_date_range_options(data_cache: Dict[str, pd.DataFrame]) -> List[Dict[str, str]]:
    """
    Returns pre-defined date range options based on available data.
    
    Args:
        data_cache: Dictionary of loaded data for all symbols
        
    Returns:
        List of date range options for dropdown
    """
    if not data_cache:
        return [{"label": "Custom", "value": "custom"}]
    
    # Find the latest date across all symbols (most recent data)
    latest_dates = []
    for df in data_cache.values():
        if not df.empty:
            latest_dates.append(df["Date"].max())
    
    if not latest_dates:
        return [{"label": "Custom", "value": "custom"}]
    
    current_date = max(latest_dates)
    
    # Calculate year-to-date start (last trading day of previous year)
    ytd_year = current_date.year
    prev_year_end = None
    
    # Find the last trading day of previous year across all symbols
    for df in data_cache.values():
        if not df.empty:
            prev_year_data = df[df["Date"].dt.year == (ytd_year - 1)]
            if not prev_year_data.empty:
                last_day_prev_year = prev_year_data["Date"].max()
                if prev_year_end is None or last_day_prev_year > prev_year_end:
                    prev_year_end = last_day_prev_year
    
    return [
        {"label": "YTD", "value": "ytd"},
        {"label": "1Y", "value": "1y"},
        {"label": "3Y", "value": "3y"}, 
        {"label": "5Y", "value": "5y"},
        {"label": "10Y", "value": "10y"},
        {"label": "Custom", "value": "custom"}
    ]


def calculate_date_range(period: str, data_cache: Dict[str, pd.DataFrame]) -> Tuple[str, str]:
    """
    Calculates start and end dates for predefined periods.
    
    Args:
        period: Period string (ytd, 1y, 3y, 5y, 10y)
        data_cache: Dictionary of loaded data
        
    Returns:
        Tuple of (start_date, end_date) as strings
    """
    if not data_cache:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
    
    # Find the latest date across all symbols
    latest_dates = []
    for df in data_cache.values():
        if not df.empty:
            latest_dates.append(df["Date"].max())
    
    current_date = max(latest_dates) if latest_dates else datetime.now()
    
    if period == "ytd":
        # Find last trading day of previous year
        ytd_year = current_date.year
        prev_year_end = None
        
        for df in data_cache.values():
            if not df.empty:
                prev_year_data = df[df["Date"].dt.year == (ytd_year - 1)]
                if not prev_year_data.empty:
                    last_day_prev_year = prev_year_data["Date"].max()
                    if prev_year_end is None or last_day_prev_year > prev_year_end:
                        prev_year_end = last_day_prev_year
        
        start_date = prev_year_end if prev_year_end else datetime(ytd_year, 1, 1)
        
    elif period == "1y":
        start_date = current_date - timedelta(days=365)
    elif period == "3y":
        start_date = current_date - timedelta(days=3 * 365)
    elif period == "5y":
        start_date = current_date - timedelta(days=5 * 365)
    elif period == "10y":
        start_date = current_date - timedelta(days=10 * 365)
    else:
        # Default to 2 years
        start_date = current_date - timedelta(days=2 * 365)
    
    return start_date.strftime("%Y-%m-%d"), current_date.strftime("%Y-%m-%d")


def calculate_daily_strategies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates daily returns and cumulative indices for all strategies.
    
    Args:
        df: DataFrame with Date, Open, Close columns
        
    Returns:
        DataFrame with Date, daily returns, and cumulative indices
    """
    df = df.copy()
    df = df.sort_values("Date").reset_index(drop=True)
    
    # Calculate daily returns
    df["overnight_return"] = (df["Open"] - df["Close"].shift(1)) / df["Close"].shift(1)
    df["intraday_return"] = (df["Close"] - df["Open"]) / df["Open"]
    df["buy_hold_return"] = df["Close"].pct_change()
    
    # Fill NaN values in first row
    df = df.fillna(0)
    
    # Calculate cumulative indices (starting at 1.0)
    df["overnight_index"] = (1 + df["overnight_return"]).cumprod()
    df["intraday_index"] = (1 + df["intraday_return"]).cumprod()
    df["buy_hold_index"] = (1 + df["buy_hold_return"]).cumprod()
    
    return df


def calculate_metrics(df: pd.DataFrame, start_date: str, end_date: str) -> Dict[str, float]:
    """
    Calculates performance metrics for the selected date range.
    
    Args:
        df: DataFrame with Date and cumulative indices
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Dictionary with cumulative performance metrics (%) for each strategy
    """
    # Filter by date range
    mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)
    filtered = df[mask].copy()
    
    if filtered.empty:
        return {"overnight": 0.0, "intraday": 0.0, "buy_hold": 0.0}
    
    # Get start and end values
    start_overnight = filtered["overnight_index"].iloc[0]
    start_intraday = filtered["intraday_index"].iloc[0]
    start_buy_hold = filtered["buy_hold_index"].iloc[0]
    
    end_overnight = filtered["overnight_index"].iloc[-1]
    end_intraday = filtered["intraday_index"].iloc[-1]
    end_buy_hold = filtered["buy_hold_index"].iloc[-1]
    
    # Calculate total returns as (end_index / start_index - 1) * 100
    return {
        "overnight": (end_overnight / start_overnight - 1) * 100,
        "intraday": (end_intraday / start_intraday - 1) * 100,
        "buy_hold": (end_buy_hold / start_buy_hold - 1) * 100,
    }


def get_cumulative_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts indices to cumulative return series starting from 0%.
    
    Args:
        df: DataFrame with Date and index columns
        
    Returns:
        DataFrame with Date and cumulative return columns for plotting
    """
    if df.empty:
        return pd.DataFrame(columns=["Date", "overnight", "intraday", "buy_hold"])
    
    df = df.copy()
    
    # Get the starting values (first row indices)
    start_overnight = df["overnight_index"].iloc[0]
    start_intraday = df["intraday_index"].iloc[0]
    start_buy_hold = df["buy_hold_index"].iloc[0]
    
    # Calculate cumulative returns: (index_t / index_start) - 1
    df["overnight"] = (df["overnight_index"] / start_overnight) - 1
    df["intraday"] = (df["intraday_index"] / start_intraday) - 1
    df["buy_hold"] = (df["buy_hold_index"] / start_buy_hold) - 1
    
    return df[["Date", "overnight", "intraday", "buy_hold"]]
