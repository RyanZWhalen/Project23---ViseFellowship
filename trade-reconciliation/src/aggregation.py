from collections import defaultdict
from decimal import Decimal

from .models import Discrepancy, NormalizedTrade
from .reconcile import aggregate_by_symbol_side
from .utils import quantize_money


def ticker_level_notional_summary(
    fidelity_trades: list[NormalizedTrade], vise_trades: list[NormalizedTrade]
) -> list[dict]:
    fidelity = aggregate_by_symbol_side(fidelity_trades)
    vise = aggregate_by_symbol_side(vise_trades)

    symbols = sorted({key[0] for key in fidelity} | {key[0] for key in vise})
    rows: list[dict] = []
    for symbol in symbols:
        f_buy = fidelity.get((symbol, "BUY"), {}).get("notional", Decimal("0"))
        f_sell = fidelity.get((symbol, "SELL"), {}).get("notional", Decimal("0"))
        v_buy = vise.get((symbol, "BUY"), {}).get("notional", Decimal("0"))
        v_sell = vise.get((symbol, "SELL"), {}).get("notional", Decimal("0"))
        rows.append(
            {
                "symbol": symbol,
                "fidelity_buy_notional": str(quantize_money(f_buy)),
                "vise_buy_notional": str(quantize_money(v_buy)),
                "buy_notional_diff": str(quantize_money(f_buy - v_buy)),
                "fidelity_sell_notional": str(quantize_money(f_sell)),
                "vise_sell_notional": str(quantize_money(v_sell)),
                "sell_notional_diff": str(quantize_money(f_sell - v_sell)),
            }
        )
    return rows


def side_level_notional_summary(
    fidelity_trades: list[NormalizedTrade], vise_trades: list[NormalizedTrade]
) -> list[dict]:
    totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"fidelity": Decimal("0"), "vise": Decimal("0")})
    for trade in fidelity_trades:
        totals[trade.side]["fidelity"] += trade.notional
    for trade in vise_trades:
        totals[trade.side]["vise"] += trade.notional

    rows = []
    for side in ("BUY", "SELL"):
        f_total = totals[side]["fidelity"]
        v_total = totals[side]["vise"]
        rows.append(
            {
                "side": side,
                "fidelity_notional": str(quantize_money(f_total)),
                "vise_notional": str(quantize_money(v_total)),
                "notional_diff": str(quantize_money(f_total - v_total)),
            }
        )
    return rows


def discrepancy_counts(discrepancies: list[Discrepancy]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in discrepancies:
        counts[item.kind] += 1
    return dict(sorted(counts.items()))
