"""Data fetching and strategy computation utilities."""

from typing import Dict, List, Any
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
    Loads historical daily data for all available symbols at startup.
    Downloads 10 years of data for each symbol.
    
    Returns:
        Dictionary mapping symbol to DataFrame with Date, Open, Close columns.
    """
    symbols = [choice["value"] for choice in get_index_choices()]
    data_cache = {}
    
    # Download 10 years of daily data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10 * 365)
    
    for symbol in symbols:
        try:
            print(f"Downloading {symbol}...")
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
                    print(f"  ✓ {symbol}: {len(df)} days loaded")
                else:
                    print(f"  ✗ {symbol}: Missing required columns")
            else:
                print(f"  ✗ {symbol}: No data returned")
                
        except Exception as e:
            print(f"  ✗ {symbol}: Error - {str(e)}")
    
    return data_cache


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