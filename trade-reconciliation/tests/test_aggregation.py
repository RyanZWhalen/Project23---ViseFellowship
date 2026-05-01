from decimal import Decimal

from src.aggregation import side_level_notional_summary
from src.models import NormalizedTrade


def test_side_level_notional_summary_computes_differences() -> None:
    fidelity = [
        NormalizedTrade("fidelity", "AAA", "BUY", Decimal("2"), Decimal("10"), Decimal("20"), "f1"),
        NormalizedTrade("fidelity", "BBB", "SELL", Decimal("1"), Decimal("5"), Decimal("5"), "f2"),
    ]
    vise = [
        NormalizedTrade("vise", "AAA", "BUY", Decimal("2"), Decimal("9"), Decimal("18"), "v1"),
        NormalizedTrade("vise", "BBB", "SELL", Decimal("1"), Decimal("4"), Decimal("4"), "v2"),
    ]
    summary = side_level_notional_summary(fidelity, vise)

    by_side = {row["side"]: row for row in summary}
    assert by_side["BUY"]["notional_diff"] == "2.00"
    assert by_side["SELL"]["notional_diff"] == "1.00"
