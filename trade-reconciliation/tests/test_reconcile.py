from decimal import Decimal
from pathlib import Path

from src.parser import parse_fidelity_file, parse_vise_trades
from src.reconcile import reconcile_trades


def test_reconcile_finds_expected_discrepancy_types() -> None:
    root = Path(__file__).resolve().parents[1]
    fidelity = parse_fidelity_file(root / "data" / "raw" / "FIDELITY-20250729.txt")
    vise = parse_vise_trades(root / "data" / "raw" / "trades.csv")
    discrepancies = reconcile_trades(fidelity, vise, notional_tolerance=Decimal("0.01"))

    kinds = {item.kind for item in discrepancies}
    assert "extra_fidelity_trade" in kinds
    assert "quantity_mismatch" in kinds or "notional_mismatch" in kinds
    assert len(discrepancies) > 0
