from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ExecutionDispatchRequest:
    decision_id: str
    signal_id: str
    strategy_name: str
    pair: str
    side: str
    action: str
    order_type: str
    stake_fraction: float
    entry_price: float | None = None
    metadata: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['metadata'] = self.metadata or {}
        return payload


@dataclass
class DispatchResult:
    status: str
    message: str
    remote_id: str | None = None
    response_payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrderStatusResult:
    remote_id: str
    order_status: str
    venue_order_id: str | None = None
    average_fill_price: float | None = None
    executed_quantity: float | None = None
    fee_amount: float | None = None
    last_error: str | None = None
    filled_at: str | None = None
    cancelled_at: str | None = None
    raw_response: dict[str, Any] | None = None


class BaseExecutionConnector:
    mode = 'base'

    def dispatch(self, request: ExecutionDispatchRequest) -> DispatchResult:  # pragma: no cover - interface
        raise NotImplementedError

    def fetch_order_status(self, order: dict[str, Any], profile: dict[str, Any]) -> OrderStatusResult:  # pragma: no cover - interface
        raise NotImplementedError


class DryRunConnector(BaseExecutionConnector):
    mode = 'dry_run'

    def dispatch(self, request: ExecutionDispatchRequest) -> DispatchResult:
        return DispatchResult(
            status='simulated',
            message='dry-run connector accepted request',
            remote_id=f"dryrun:{request.decision_id}",
            response_payload=request.to_payload(),
        )

    def fetch_order_status(self, order: dict[str, Any], profile: dict[str, Any]) -> OrderStatusResult:
        sim = profile.get('simulation', {})
        requested = float(order.get('requested_price') or 0.0)
        slippage_bps = float(sim.get('fill_slippage_bps', 5.0))
        fee_bps = float(sim.get('fee_bps', 10.0))
        quantity = float(sim.get('default_quantity', 1.0))
        fill_price = requested * (1 + slippage_bps / 10000.0) if requested > 0 else requested
        fee_amount = abs(fill_price * quantity) * fee_bps / 10000.0 if fill_price else 0.0
        now = datetime.now(timezone.utc).isoformat()
        return OrderStatusResult(
            remote_id=str(order.get('remote_id') or order.get('order_id')),
            order_status='filled',
            venue_order_id=str(order.get('remote_id') or order.get('order_id')),
            average_fill_price=round(fill_price, 8) if fill_price else requested,
            executed_quantity=quantity,
            fee_amount=round(fee_amount, 8),
            filled_at=now,
            raw_response={'mode': 'dry_run', 'filled_at': now, 'slippage_bps': slippage_bps, 'fee_bps': fee_bps},
        )


class FreqtradeWebhookConnector(BaseExecutionConnector):
    mode = 'webhook'

    def __init__(self, endpoint: str, token: str | None = None, timeout_seconds: int = 10, status_endpoint_template: str | None = None) -> None:
        self.endpoint = endpoint
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.status_endpoint_template = status_endpoint_template

    def _headers(self) -> dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def dispatch(self, request: ExecutionDispatchRequest) -> DispatchResult:
        body = json.dumps(request.to_payload()).encode('utf-8')
        req = urllib.request.Request(self.endpoint, data=body, headers=self._headers(), method='POST')
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:  # nosec B310
            raw = resp.read().decode('utf-8')
            parsed = json.loads(raw) if raw else {}
            return DispatchResult(
                status='submitted',
                message=f'http {resp.status}',
                remote_id=str(parsed.get('id') or parsed.get('order_id') or request.decision_id),
                response_payload=parsed,
            )

    def fetch_order_status(self, order: dict[str, Any], profile: dict[str, Any]) -> OrderStatusResult:
        template = self.status_endpoint_template or profile.get('connector', {}).get('status_endpoint_template')
        if not template:
            raise RuntimeError('status_endpoint_template is required for webhook status sync')
        remote_id = str(order.get('remote_id') or order.get('venue_order_id') or order.get('order_id'))
        encoded_id = urllib.parse.quote(remote_id, safe='')
        url = template.replace('{remote_id}', encoded_id)
        req = urllib.request.Request(url, headers=self._headers(), method='GET')
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:  # nosec B310
            raw = resp.read().decode('utf-8')
            parsed = json.loads(raw) if raw else {}
        status = str(parsed.get('order_status') or parsed.get('status') or 'submitted')
        return OrderStatusResult(
            remote_id=remote_id,
            order_status=status,
            venue_order_id=str(parsed.get('venue_order_id') or parsed.get('id') or remote_id),
            average_fill_price=_to_float(parsed.get('average_fill_price') or parsed.get('avg_fill_price')),
            executed_quantity=_to_float(parsed.get('executed_quantity') or parsed.get('filled_qty')),
            fee_amount=_to_float(parsed.get('fee_amount') or parsed.get('fee')),
            last_error=parsed.get('last_error') or parsed.get('error_message'),
            filled_at=parsed.get('filled_at'),
            cancelled_at=parsed.get('cancelled_at'),
            raw_response=parsed,
        )


class FileStatusConnector(BaseExecutionConnector):
    mode = 'file_status'

    def __init__(self, status_file: str | Path) -> None:
        self.status_file = Path(status_file)

    def dispatch(self, request: ExecutionDispatchRequest) -> DispatchResult:
        return DispatchResult(
            status='submitted',
            message='file-status connector recorded request',
            remote_id=f'file:{request.decision_id}',
            response_payload=request.to_payload(),
        )

    def fetch_order_status(self, order: dict[str, Any], profile: dict[str, Any]) -> OrderStatusResult:
        if not self.status_file.exists():
            raise FileNotFoundError(f'status file not found: {self.status_file}')
        payload = json.loads(self.status_file.read_text(encoding='utf-8'))
        remote_id = str(order.get('remote_id') or order.get('order_id'))
        item = payload.get(remote_id) or payload.get(str(order.get('decision_id')))
        if not item:
            return OrderStatusResult(remote_id=remote_id, order_status=str(order.get('order_status') or 'submitted'), raw_response={'status_file': str(self.status_file)})
        return OrderStatusResult(
            remote_id=remote_id,
            order_status=str(item.get('order_status') or item.get('status') or 'submitted'),
            venue_order_id=item.get('venue_order_id'),
            average_fill_price=_to_float(item.get('average_fill_price')),
            executed_quantity=_to_float(item.get('executed_quantity')),
            fee_amount=_to_float(item.get('fee_amount')),
            last_error=item.get('last_error'),
            filled_at=item.get('filled_at'),
            cancelled_at=item.get('cancelled_at'),
            raw_response=item,
        )


def _to_float(value: Any) -> float | None:
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_connector(profile: dict[str, Any]) -> BaseExecutionConnector:
    connector = profile.get('connector', {})
    mode = connector.get('mode', 'dry_run')
    if mode == 'webhook':
        return FreqtradeWebhookConnector(
            endpoint=connector['endpoint'],
            token=connector.get('token'),
            timeout_seconds=int(connector.get('timeout_seconds', 10)),
            status_endpoint_template=connector.get('status_endpoint_template'),
        )
    if mode == 'file_status':
        return FileStatusConnector(status_file=connector['status_file'])
    return DryRunConnector()
