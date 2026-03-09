from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

TRANSIENT_HINTS = ('timeout', 'temporar', 'unavailable', '429', 'rate limit', 'connection reset', 'network')
PERMANENT_HINTS = ('invalid', 'insufficient', 'notional', 'balance', 'denied', 'forbidden', 'unauthorized', 'auth')
MARKET_HINTS = ('slippage', 'price moved', 'stale', 'partial', 'cancel')


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def classify_error_category(order: dict[str, Any]) -> str:
    if order.get('error_category'):
        return str(order['error_category'])
    text = str(order.get('last_error') or '').lower()
    if any(h in text for h in TRANSIENT_HINTS):
        return 'transient'
    if any(h in text for h in PERMANENT_HINTS):
        return 'permanent'
    if any(h in text for h in MARKET_HINTS):
        return 'market'
    status = str(order.get('order_status') or '').lower()
    if status == 'partial':
        return 'market'
    if status in {'failed', 'cancelled'}:
        return 'transient'
    return 'unknown'


@dataclass
class ReplacePlan:
    source_order_id: str
    replace_reason: str
    next_retry_count: int
    requested_quantity: float | None
    requested_notional: float | None
    error_category: str


def should_replace_order(order: dict[str, Any], profile: dict[str, Any], now: datetime | None = None) -> ReplacePlan | None:
    lifecycle = profile.get('lifecycle', {})
    retry_limits = lifecycle.get('retry_limits_by_category', {})
    retry_count = int(order.get('retry_count') or 0)
    category = classify_error_category(order)
    max_retries = int(retry_limits.get(category, lifecycle.get('max_retries', 0)))
    if category == 'permanent' or retry_count >= max_retries:
        return None
    now = now or datetime.now(timezone.utc)
    stale_seconds = int(lifecycle.get('stale_after_seconds', 120))
    submitted_at = _parse_dt(order.get('submitted_at')) or now
    age_seconds = max((now - submitted_at).total_seconds(), 0.0)
    status = str(order.get('order_status') or '').lower()

    if status in {'failed', 'cancelled'}:
        if age_seconds < stale_seconds and category == 'transient':
            return None
        return ReplacePlan(order['order_id'], status, retry_count + 1, _to_float(order.get('requested_quantity')), _to_float(order.get('requested_notional')), category)

    if status == 'partial' and lifecycle.get('enable_partial_replace', True):
        requested_qty = _to_float(order.get('requested_quantity'))
        executed_qty = _to_float(order.get('executed_quantity')) or 0.0
        residual_qty = None
        if requested_qty is not None:
            residual_qty = max(requested_qty - executed_qty, 0.0)
            if residual_qty <= 0:
                return None
        requested_notional = _to_float(order.get('requested_notional'))
        if requested_notional is not None and requested_qty and requested_qty > 0:
            requested_notional = requested_notional * max((requested_qty - executed_qty), 0.0) / requested_qty
        if age_seconds >= stale_seconds or category == 'market':
            return ReplacePlan(order['order_id'], 'partial_residual', retry_count + 1, residual_qty, requested_notional, 'market')
    return None


def _to_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
