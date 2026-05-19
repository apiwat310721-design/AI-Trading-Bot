"""Real-time XAUUSD price feed and technical indicators."""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

SYMBOL = "XAUUSD=X"
FALLBACK_SYMBOLS = ("GC=F", "MGC=F")
INTERVAL = "5m"
PERIOD = "5d"


def _clean_float(value: Any, decimals: int = 2) -> float | None:
    """Convert pandas/numpy values to rounded JSON-safe floats."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return round(numeric, decimals)


def _download_history(retries: int = 1) -> tuple[pd.DataFrame, str]:
    """Download recent gold candles, retrying once and falling back if XAUUSD=X is unavailable."""
    last_error: Exception | None = None
    for symbol in (SYMBOL, *FALLBACK_SYMBOLS):
        for attempt in range(retries + 1):
            try:
                data = yf.download(
                    symbol,
                    period=PERIOD,
                    interval=INTERVAL,
                    progress=False,
                    auto_adjust=False,
                    threads=False,
                )
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                data = data.dropna(subset=["Close"])
                if not data.empty:
                    return data, symbol
                last_error = ValueError(f"No gold data returned from yfinance for {symbol}")
            except Exception as exc:  # noqa: BLE001 - converted to error state for callers
                last_error = exc
            if attempt < retries:
                time.sleep(1)
    raise RuntimeError(str(last_error or "Unable to fetch market data"))


def _calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _calculate_macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd = ema_12 - ema_26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram


def _support_resistance(data: pd.DataFrame, window: int = 3, lookback: int = 120) -> dict[str, Any]:
    recent = data.tail(lookback).copy()
    highs = recent["High"]
    lows = recent["Low"]

    swing_highs: list[float] = []
    swing_lows: list[float] = []
    for idx in range(window, len(recent) - window):
        high_slice = highs.iloc[idx - window : idx + window + 1]
        low_slice = lows.iloc[idx - window : idx + window + 1]
        current_high = highs.iloc[idx]
        current_low = lows.iloc[idx]
        if current_high == high_slice.max():
            swing_highs.append(float(current_high))
        if current_low == low_slice.min():
            swing_lows.append(float(current_low))

    current_price = float(data["Close"].iloc[-1])
    resistance_candidates = [level for level in swing_highs if level >= current_price]
    support_candidates = [level for level in swing_lows if level <= current_price]

    resistance = min(resistance_candidates, default=max(swing_highs, default=float(highs.max())))
    support = max(support_candidates, default=min(swing_lows, default=float(lows.min())))

    return {
        "support": _clean_float(support),
        "resistance": _clean_float(resistance),
        "recent_swing_highs": [_clean_float(x) for x in sorted(swing_highs, reverse=True)[:3]],
        "recent_swing_lows": [_clean_float(x) for x in sorted(swing_lows)[:3]],
    }


def get_market_data() -> dict[str, Any]:
    """Return current XAUUSD price and technical indicators as a structured dict."""
    try:
        data, source_symbol = _download_history(retries=1)
        if len(data) < 50:
            raise RuntimeError("Not enough candle data to calculate indicators")

        close = data["Close"]
        current_price = float(close.iloc[-1])
        previous_24h_index = max(0, len(close) - 288)
        previous_24h_price = float(close.iloc[previous_24h_index])
        price_change_pct = ((current_price - previous_24h_price) / previous_24h_price) * 100

        rsi = _calculate_rsi(close)
        macd, macd_signal, macd_histogram = _calculate_macd(close)
        bb_mid = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        bb_upper = bb_mid + (2 * bb_std)
        bb_lower = bb_mid - (2 * bb_std)
        sma_50 = close.rolling(window=50).mean()
        sma_200 = close.rolling(window=200).mean()
        levels = _support_resistance(data)

        bb_position = None
        if not pd.isna(bb_upper.iloc[-1]) and not pd.isna(bb_lower.iloc[-1]) and bb_upper.iloc[-1] != bb_lower.iloc[-1]:
            bb_position = ((current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])) * 100

        macd_status = "bullish" if macd.iloc[-1] > macd_signal.iloc[-1] else "bearish"
        if len(macd) >= 2:
            if macd.iloc[-2] <= macd_signal.iloc[-2] and macd.iloc[-1] > macd_signal.iloc[-1]:
                macd_status = "bullish crossover"
            elif macd.iloc[-2] >= macd_signal.iloc[-2] and macd.iloc[-1] < macd_signal.iloc[-1]:
                macd_status = "bearish crossover"

        sma_status = "neutral"
        if not pd.isna(sma_50.iloc[-1]) and not pd.isna(sma_200.iloc[-1]):
            sma_status = "bullish" if sma_50.iloc[-1] > sma_200.iloc[-1] else "bearish"

        return {
            "success": True,
            "symbol": SYMBOL,
            "source_symbol": source_symbol,
            "timestamp": data.index[-1].isoformat(),
            "current_price": _clean_float(current_price),
            "price_change_pct_24h": _clean_float(price_change_pct),
            "indicators": {
                "rsi_14": _clean_float(rsi.iloc[-1]),
                "rsi_status": "oversold" if rsi.iloc[-1] < 30 else "overbought" if rsi.iloc[-1] > 70 else "neutral",
                "macd": _clean_float(macd.iloc[-1], 4),
                "macd_signal": _clean_float(macd_signal.iloc[-1], 4),
                "macd_histogram": _clean_float(macd_histogram.iloc[-1], 4),
                "macd_status": macd_status,
                "bollinger_upper": _clean_float(bb_upper.iloc[-1]),
                "bollinger_mid": _clean_float(bb_mid.iloc[-1]),
                "bollinger_lower": _clean_float(bb_lower.iloc[-1]),
                "bollinger_position_pct": _clean_float(bb_position),
                "sma_50": _clean_float(sma_50.iloc[-1]),
                "sma_200": _clean_float(sma_200.iloc[-1]),
                "sma_status": sma_status,
                "support": levels["support"],
                "resistance": levels["resistance"],
                "recent_swing_highs": levels["recent_swing_highs"],
                "recent_swing_lows": levels["recent_swing_lows"],
            },
        }
    except Exception as exc:  # noqa: BLE001 - public API should return graceful error state
        return {
            "success": False,
            "symbol": SYMBOL,
            "source_symbol": None,
            "error": str(exc),
            "current_price": None,
            "price_change_pct_24h": None,
            "indicators": {},
        }


if __name__ == "__main__":
    import json

    print(json.dumps(get_market_data(), indent=2))
