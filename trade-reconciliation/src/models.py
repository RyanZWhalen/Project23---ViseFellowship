from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True)
class NormalizedTrade:
    source: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    notional: Decimal
    record_id: str

    def to_dict(self) -> dict:
        data = asdict(self)
        return {k: str(v) if isinstance(v, Decimal) else v for k, v in data.items()}


@dataclass(frozen=True)
class LotRecord:
    symbol: str
    purchase_date: str
    quantity: Decimal


@dataclass(frozen=True)
class Discrepancy:
    kind: str
    symbol: str
    side: str
    vise_quantity: Decimal
    fidelity_quantity: Decimal
    vise_notional: Decimal
    fidelity_notional: Decimal
    quantity_diff: Decimal
    notional_diff: Decimal
    notes: str

    def to_dict(self) -> dict:
        data = asdict(self)
        return {k: str(v) if isinstance(v, Decimal) else v for k, v in data.items()}
