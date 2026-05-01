from collections import defaultdict
from decimal import Decimal

from .models import Discrepancy, LotRecord, NormalizedTrade


def aggregate_by_symbol_side(trades: list[NormalizedTrade]) -> dict[tuple[str, str], dict[str, Decimal]]:
    agg: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(
        lambda: {"quantity": Decimal("0"), "notional": Decimal("0")}
    )
    for trade in trades:
        key = (trade.symbol, trade.side)
        agg[key]["quantity"] += trade.quantity
        agg[key]["notional"] += trade.notional
    return dict(agg)


def validate_sell_quantities_against_lots(
    trades: list[NormalizedTrade], lots: list[LotRecord]
) -> list[dict[str, str]]:
    lot_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for lot in lots:
        lot_totals[lot.symbol] += lot.quantity

    sell_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for trade in trades:
        if trade.side == "SELL":
            sell_totals[trade.symbol] += trade.quantity

    warnings: list[dict[str, str]] = []
    for symbol, sold in sorted(sell_totals.items()):
        available = lot_totals.get(symbol, Decimal("0"))
        if sold > available:
            warnings.append(
                {
                    "symbol": symbol,
                    "message": "Sell quantity exceeds provided lot quantity.",
                    "sold_quantity": str(sold),
                    "lot_quantity": str(available),
                }
            )
    return warnings


def reconcile_trades(
    fidelity_trades: list[NormalizedTrade],
    vise_trades: list[NormalizedTrade],
    *,
    notional_tolerance: Decimal = Decimal("0.01"),
) -> list[Discrepancy]:
    fidelity = aggregate_by_symbol_side(fidelity_trades)
    vise = aggregate_by_symbol_side(vise_trades)
    keys = sorted(set(fidelity) | set(vise))

    discrepancies: list[Discrepancy] = []
    for symbol, side in keys:
        f_qty = fidelity.get((symbol, side), {}).get("quantity", Decimal("0"))
        v_qty = vise.get((symbol, side), {}).get("quantity", Decimal("0"))
        f_notional = fidelity.get((symbol, side), {}).get("notional", Decimal("0"))
        v_notional = vise.get((symbol, side), {}).get("notional", Decimal("0"))

        qty_diff = f_qty - v_qty
        notional_diff = f_notional - v_notional

        if (symbol, side) not in fidelity:
            kind = "missing_fidelity_trade"
            note = "Present in Vise but missing in Fidelity."
        elif (symbol, side) not in vise:
            kind = "extra_fidelity_trade"
            note = "Present in Fidelity but missing in Vise."
        elif qty_diff != 0:
            kind = "quantity_mismatch"
            note = "Quantity totals differ after normalization."
        elif abs(notional_diff) > notional_tolerance:
            kind = "notional_mismatch"
            note = "Notional totals differ beyond tolerance."
        else:
            continue

        discrepancies.append(
            Discrepancy(
                kind=kind,
                symbol=symbol,
                side=side,
                vise_quantity=v_qty,
                fidelity_quantity=f_qty,
                vise_notional=v_notional,
                fidelity_notional=f_notional,
                quantity_diff=qty_diff,
                notional_diff=notional_diff,
                notes=note,
            )
        )
    return discrepancies
