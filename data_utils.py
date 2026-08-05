"""Data fetching, ticker persistence, and strategy computation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

TICKERS_FILE = Path(__file__).with_name("tickers.txt")
START = "1990-01-01"


def load_tickers() -> list[str]:
    if not TICKERS_FILE.exists():
        return ["SPY", "QQQ", "DIA", "IWM"]
    return [
        line.strip().upper()
        for line in TICKERS_FILE.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def save_tickers(tickers: list[str]) -> None:
    TICKERS_FILE.write_text("\n".join(dict.fromkeys(tickers)) + "\n")


def dropdown_options(tickers: list[str]) -> list[dict[str, str]]:
    return [{"label": t, "value": t} for t in tickers]


def _flatten(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def _extract_symbol(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Pull one symbol's OHLCV from a yfinance download frame."""
    if isinstance(raw.columns, pd.MultiIndex):
        level0 = raw.columns.get_level_values(0)
        if symbol in level0:
            return raw[symbol].copy()
        # Single-ticker download sometimes uses Price as level 0
        if "Open" in level0 or "Close" in level0:
            return _flatten(raw)
    return raw.copy()


def _to_ohlc(df: pd.DataFrame) -> pd.DataFrame | None:
    df = _flatten(df).reset_index()
    if "Date" not in df.columns and "Datetime" in df.columns:
        df = df.rename(columns={"Datetime": "Date"})
    if not {"Date", "Open", "Close"}.issubset(df.columns):
        return None
    out = df[["Date", "Open", "Close"]].dropna()
    out["Date"] = pd.to_datetime(out["Date"]).dt.tz_localize(None)
    return out.sort_values("Date").reset_index(drop=True)


def calculate_daily_strategies(df: pd.DataFrame) -> pd.DataFrame:
    """Overnight / intraday / buy-hold returns and cumulative indices."""
    df = df.sort_values("Date").reset_index(drop=True)
    overnight = df["Open"] / df["Close"].shift(1) - 1
    intraday = df["Close"] / df["Open"] - 1
    buy_hold = df["Close"].pct_change()

    out = pd.DataFrame(
        {
            "Date": df["Date"],
            "overnight_return": overnight,
            "intraday_return": intraday,
            "buy_hold_return": buy_hold,
        }
    ).dropna()

    out["overnight_index"] = (1 + out["overnight_return"]).cumprod()
    out["intraday_index"] = (1 + out["intraday_return"]).cumprod()
    out["buy_hold_index"] = (1 + out["buy_hold_return"]).cumprod()
    return out


def fetch_symbol(symbol: str) -> pd.DataFrame | None:
    """Download one symbol and return strategy frame, or None on failure."""
    try:
        raw = yf.download(
            symbol,
            start=START,
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception as exc:
        print(f"  ✗ {symbol}: {exc}")
        return None

    ohlc = _to_ohlc(_extract_symbol(raw, symbol))
    if ohlc is None or ohlc.empty:
        print(f"  ✗ {symbol}: no usable OHLC")
        return None

    strategies = calculate_daily_strategies(ohlc)
    print(
        f"  ✓ {symbol}: {len(strategies)} days "
        f"({strategies['Date'].iloc[0].date()} → {strategies['Date'].iloc[-1].date()})"
    )
    return strategies


def load_all_data(tickers: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Batch-download tickers and precompute strategy series."""
    tickers = list(dict.fromkeys(tickers or load_tickers()))
    if not tickers:
        return {}

    print(f"Downloading {', '.join(tickers)}...")
    try:
        raw = yf.download(
            tickers,
            start=START,
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=True,
            group_by="ticker",
        )
    except Exception as exc:
        print(f"Batch download failed ({exc}); falling back to per-symbol")
        return {t: df for t in tickers if (df := fetch_symbol(t)) is not None}

    cache: dict[str, pd.DataFrame] = {}
    for symbol in tickers:
        try:
            ohlc = _to_ohlc(_extract_symbol(raw, symbol))
            if ohlc is None or ohlc.empty:
                print(f"  ✗ {symbol}: no usable OHLC")
                continue
            cache[symbol] = calculate_daily_strategies(ohlc)
            df = cache[symbol]
            print(
                f"  ✓ {symbol}: {len(df)} days "
                f"({df['Date'].iloc[0].date()} → {df['Date'].iloc[-1].date()})"
            )
        except Exception as exc:
            print(f"  ✗ {symbol}: {exc}")
    return cache


def refresh_cache(data_cache: dict[str, pd.DataFrame], tickers: list[str] | None = None) -> list[str]:
    """Reload all ticker data into an existing cache dict. Returns loaded symbols."""
    fresh = load_all_data(tickers or list(data_cache) or load_tickers())
    data_cache.clear()
    data_cache.update(fresh)
    return list(data_cache)


def calculate_date_range(period: str, data_cache: dict[str, pd.DataFrame]) -> tuple[str, str]:
    """Return (start, end) ISO dates for a named period."""
    latest = max((df["Date"].max() for df in data_cache.values() if not df.empty), default=pd.Timestamp.now())
    end = pd.Timestamp(latest)

    if period == "ytd":
        prev = [
            df.loc[df["Date"].dt.year == end.year - 1, "Date"].max()
            for df in data_cache.values()
            if not df.empty and (df["Date"].dt.year == end.year - 1).any()
        ]
        start = max(prev) if prev else pd.Timestamp(year=end.year, month=1, day=1)
    elif period in {"1y", "3y", "5y", "10y"}:
        start = end - pd.DateOffset(years=int(period[:-1]))
    else:
        start = end - pd.DateOffset(years=1)

    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def slice_range(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    mask = (df["Date"] >= start) & (df["Date"] <= end)
    return df.loc[mask]


def calculate_metrics(df: pd.DataFrame, start: str, end: str) -> dict[str, dict[str, float]]:
    filtered = slice_range(df, start, end)
    empty = {"return": 0.0, "sharpe": 0.0}
    if filtered.empty:
        return {"overnight": empty.copy(), "intraday": empty.copy(), "buy_hold": empty.copy()}

    def for_strategy(index_col: str, return_col: str) -> dict[str, float]:
        total = float(filtered[index_col].iloc[-1] / filtered[index_col].iloc[0] - 1) * 100
        rets = filtered[return_col]
        vol = float(rets.std())
        sharpe = float(rets.mean() / vol * (252**0.5)) if vol > 0 else 0.0
        return {"return": total, "sharpe": sharpe}

    return {
        "overnight": for_strategy("overnight_index", "overnight_return"),
        "intraday": for_strategy("intraday_index", "intraday_return"),
        "buy_hold": for_strategy("buy_hold_index", "buy_hold_return"),
    }


def get_cumulative_series(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Date", "overnight", "intraday", "buy_hold"])

    return pd.DataFrame(
        {
            "Date": df["Date"],
            "overnight": df["overnight_index"] / df["overnight_index"].iloc[0] - 1,
            "intraday": df["intraday_index"] / df["intraday_index"].iloc[0] - 1,
            "buy_hold": df["buy_hold_index"] / df["buy_hold_index"].iloc[0] - 1,
        }
    )
