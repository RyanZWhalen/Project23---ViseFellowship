from pathlib import Path

from src.parser import parse_fidelity_file, parse_vise_lots, parse_vise_trades


def test_fidelity_parser_extracts_expected_record_count() -> None:
    root = Path(__file__).resolve().parents[1]
    records = parse_fidelity_file(root / "data" / "raw" / "FIDELITY-20250729.txt")
    assert len(records) == 132
    assert all(record.side in {"BUY", "SELL"} for record in records)
    assert all(record.symbol for record in records)


def test_vise_csv_parsers_extract_expected_counts() -> None:
    root = Path(__file__).resolve().parents[1]
    trades = parse_vise_trades(root / "data" / "raw" / "trades.csv")
    lots = parse_vise_lots(root / "data" / "raw" / "lots.csv")
    assert len(trades) == 122
    assert len(lots) == 48
