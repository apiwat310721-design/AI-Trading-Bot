"""Claude-powered XAUUSD trading analysis agent."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

SIGNAL_HISTORY: list[dict[str, Any]] = []


class XAUUSDAgent:
    """Analyze XAUUSD market data with Claude and return a structured signal."""

    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None
        self.primary_model = "claude-opus-4-5"
        self.fallback_model = "claude-3-5-sonnet-20241022"

    def analyze(self, market_data: dict[str, Any]) -> dict[str, Any]:
        if not market_data.get("success"):
            return self._error_signal(f"Market data unavailable: {market_data.get('error', 'unknown error')}", market_data)
        if not self.client:
            return self._error_signal("ANTHROPIC_API_KEY is not configured", market_data)

        prompt = self._build_prompt(market_data)
        last_error: Exception | None = None
        for model in (self.primary_model, self.fallback_model):
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=700,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = "\n".join(block.text for block in response.content if getattr(block, "type", None) == "text")
                signal = self._parse_response(text, market_data, model)
                self._remember(signal)
                return signal
            except Exception as exc:  # noqa: BLE001 - fallback and graceful response required
                last_error = exc
                if model == self.fallback_model:
                    break
        return self._error_signal(f"Claude API error: {last_error}", market_data)

    def _build_prompt(self, market_data: dict[str, Any]) -> str:
        indicators = market_data.get("indicators", {})
        return f"""
You are an expert XAUUSD (Gold/USD) intraday trading analyst. Analyze the following 5-minute market data and produce one concise trading signal.

Current market:
- Symbol: {market_data.get('symbol')}
- Current price: ${market_data.get('current_price'):.2f}
- 24h price change: {market_data.get('price_change_pct_24h'):.2f}%
- Data timestamp: {market_data.get('timestamp')}

Technical indicators:
- RSI (14): {indicators.get('rsi_14')} ({indicators.get('rsi_status')}; <30 oversold bullish, >70 overbought bearish)
- MACD: {indicators.get('macd')} | Signal line: {indicators.get('macd_signal')} | Histogram: {indicators.get('macd_histogram')} | Status: {indicators.get('macd_status')}
- Bollinger Bands (20, 2): Upper {indicators.get('bollinger_upper')}, Mid {indicators.get('bollinger_mid')}, Lower {indicators.get('bollinger_lower')}, Position {indicators.get('bollinger_position_pct')}%
- SMA 50: {indicators.get('sma_50')} | SMA 200: {indicators.get('sma_200')} | SMA status: {indicators.get('sma_status')}
- Support: {indicators.get('support')} | Resistance: {indicators.get('resistance')}
- Recent swing highs: {indicators.get('recent_swing_highs')}
- Recent swing lows: {indicators.get('recent_swing_lows')}

Respond ONLY as valid JSON with this exact schema:
{{
  "signal": "BUY" | "SELL" | "WAIT",
  "confidence": 0-100,
  "reasoning": "2-3 sentences explaining the setup and risk.",
  "entry_price": number,
  "stop_loss": number,
  "take_profit": number
}}
Do not include markdown, extra keys, or investment disclaimers.
""".strip()

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract the first complete JSON object from Claude output.

        Tries markdown code fences first, then falls back to brace-counting so a
        greedy regex cannot accidentally capture multiple JSON-like blocks.
        """
        # 1. Prefer an explicit ```json ... ``` or ``` ... ``` block.
        block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if block:
            return block.group(1)

        # 2. Walk the string from the first '{' and count depth to find the
        #    matching '}', correctly handling strings and escape sequences.
        start = text.find("{")
        if start == -1:
            raise ValueError("Claude response did not contain JSON")
        depth = 0
        in_string = False
        escape = False
        for i, ch in enumerate(text[start:], start):
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start: i + 1]
        raise ValueError("Claude response JSON was not properly closed")

    def _parse_response(self, text: str, market_data: dict[str, Any], model: str) -> dict[str, Any]:
        parsed = json.loads(self._extract_json(text))
        current_price = float(market_data.get("current_price") or 0)

        signal = str(parsed.get("signal", "WAIT")).upper()
        if signal not in {"BUY", "SELL", "WAIT"}:
            signal = "WAIT"

        result = {
            "success": True,
            "signal": signal,
            "confidence": max(0, min(100, int(float(parsed.get("confidence", 0))))),
            "reasoning": str(parsed.get("reasoning", "No reasoning provided.")),
            "entry_price": self._price(parsed.get("entry_price"), current_price),
            "stop_loss": self._price(parsed.get("stop_loss"), current_price),
            "take_profit": self._price(parsed.get("take_profit"), current_price),
            "model": model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_data": market_data,
        }
        return result

    @staticmethod
    def _price(value: Any, fallback: float) -> float:
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return round(fallback, 2)

    def _error_signal(self, message: str, market_data: dict[str, Any]) -> dict[str, Any]:
        current_price = market_data.get("current_price") or 0
        result = {
            "success": False,
            "signal": "WAIT",
            "confidence": 0,
            "reasoning": message,
            "entry_price": self._price(current_price, 0),
            "stop_loss": self._price(current_price, 0),
            "take_profit": self._price(current_price, 0),
            "model": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_data": market_data,
            "error": message,
        }
        self._remember(result)
        return result

    @staticmethod
    def _remember(signal: dict[str, Any]) -> None:
        SIGNAL_HISTORY.insert(0, signal)
        del SIGNAL_HISTORY[10:]


def get_signal_history() -> list[dict[str, Any]]:
    return SIGNAL_HISTORY
