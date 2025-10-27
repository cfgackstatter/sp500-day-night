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
    Calculates cumulative returns for overnight, intraday, and buy-and-hold strategies.
    
    Strategy definitions for day t:
    - Overnight (t): Return from Close(t-1) to Open(t)
    - Intraday (t): Return from Open(t) to Close(t)
    - Buy & Hold (t): Return from Close(t-1) to Close(t)
    
    Args:
        df: DataFrame with Date, Open, Close columns
        
    Returns:
        DataFrame with Date and daily return columns (not cumulative yet)
    """
    df = df.copy()
    df = df.sort_values("Date").reset_index(drop=True)
    
    # Calculate daily returns for each strategy
    # Overnight: (Open_t - Close_t-1) / Close_t-1
    df["overnight_return"] = (df["Open"] - df["Close"].shift(1)) / df["Close"].shift(1)
    
    # Intraday: (Close_t - Open_t) / Open_t
    df["intraday_return"] = (df["Close"] - df["Open"]) / df["Open"]
    
    # Buy & Hold: (Close_t - Close_t-1) / Close_t-1
    df["buy_hold_return"] = df["Close"].pct_change()
    
    # Fill NaN values in first row
    df = df.fillna(0)
    
    # Keep daily returns for later cumulative calculation
    result = df[["Date", "overnight_return", "intraday_return", "buy_hold_return"]].copy()
    
    return result


def calculate_metrics(df: pd.DataFrame, start_date: str, end_date: str) -> Dict[str, float]:
    """
    Calculates performance metrics for the selected date range.
    Properly compounds returns only within the selected date range.
    
    Args:
        df: DataFrame with Date and daily return columns
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Dictionary with cumulative performance metrics (%) for each strategy
    """
    # Filter by date range
    mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)
    filtered = df[mask].copy()
    
    if filtered.empty:
        return {
            "overnight": 0.0,
            "intraday": 0.0,
            "buy_hold": 0.0,
        }
    
    # Calculate cumulative returns within the filtered range
    # Compound returns: (1+r1)*(1+r2)*...*(1+rn) - 1
    
    # Convert Series to numpy array, compute product, then convert to Python float
    overnight_returns = filtered["overnight_return"].to_numpy()
    intraday_returns = filtered["intraday_return"].to_numpy()
    buy_hold_returns = filtered["buy_hold_return"].to_numpy()
    
    # Use item() to extract scalar as Python float
    overnight_cumulative = float((1 + overnight_returns).prod().item()) - 1.0
    intraday_cumulative = float((1 + intraday_returns).prod().item()) - 1.0
    buy_hold_cumulative = float((1 + buy_hold_returns).prod().item()) - 1.0
    
    return {
        "overnight": overnight_cumulative * 100.0,  # Convert to percentage
        "intraday": intraday_cumulative * 100.0,
        "buy_hold": buy_hold_cumulative * 100.0,
    }


def get_cumulative_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts daily returns to cumulative return series.
    
    Args:
        df: DataFrame with Date and daily return columns
        
    Returns:
        DataFrame with Date and cumulative return columns
    """
    df = df.copy()
    
    # Calculate cumulative returns (compound growth from start)
    df["overnight"] = (1 + df["overnight_return"]).cumprod() - 1
    df["intraday"] = (1 + df["intraday_return"]).cumprod() - 1
    df["buy_hold"] = (1 + df["buy_hold_return"]).cumprod() - 1
    
    return df[["Date", "overnight", "intraday", "buy_hold"]]
