from datetime import datetime, timezone
from pathlib import Path

from .aggregation import discrepancy_counts, side_level_notional_summary, ticker_level_notional_summary
from .parser import parse_fidelity_file, parse_vise_lots, parse_vise_trades
from .reconcile import reconcile_trades, validate_sell_quantities_against_lots
from .rust_bridge import run_rust_core
from .utils import write_csv, write_json


def run(data_dir: Path, outputs_dir: Path) -> dict:
    fidelity_path = data_dir / "FIDELITY-20250729.txt"
    trades_path = data_dir / "trades.csv"
    lots_path = data_dir / "lots.csv"
    project_root = Path(__file__).resolve().parents[1]

    rust_payload = run_rust_core(fidelity_path, trades_path, project_root)
    lots = parse_vise_lots(lots_path)
    lot_warnings = validate_sell_quantities_against_lots(parse_vise_trades(trades_path), lots)

    if rust_payload:
        write_csv(outputs_dir / "reconciliation_report.csv", rust_payload["discrepancies"])
        summary = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "engine": "rust",
            "record_counts": {
                **rust_payload["record_counts"],
                "vise_lot_records": len(lots),
            },
            "discrepancy_counts": rust_payload["discrepancy_counts"],
            "side_level_notional_summary": rust_payload["side_level_notional_summary"],
            "ticker_level_notional_summary": rust_payload["ticker_level_notional_summary"],
            "lot_warnings": lot_warnings,
        }
        write_json(outputs_dir / "reconciliation_summary.json", summary)
        return summary

    fidelity_trades = parse_fidelity_file(fidelity_path)
    vise_trades = parse_vise_trades(trades_path)

    discrepancies = reconcile_trades(fidelity_trades, vise_trades)
    lot_warnings = validate_sell_quantities_against_lots(vise_trades, lots)

    write_csv(outputs_dir / "reconciliation_report.csv", [d.to_dict() for d in discrepancies])

    side_summary = side_level_notional_summary(fidelity_trades, vise_trades)
    ticker_summary = ticker_level_notional_summary(fidelity_trades, vise_trades)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": "python",
        "record_counts": {
            "fidelity_trade_records": len(fidelity_trades),
            "vise_trade_records": len(vise_trades),
            "vise_lot_records": len(lots),
        },
        "discrepancy_counts": discrepancy_counts(discrepancies),
        "side_level_notional_summary": side_summary,
        "ticker_level_notional_summary": ticker_summary,
        "lot_warnings": lot_warnings,
    }
    write_json(outputs_dir / "reconciliation_summary.json", summary)
    return summary


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "raw"
    outputs_dir = root / "outputs"

    summary = run(data_dir, outputs_dir)

    lines = [
        "Trade reconciliation complete.",
        f"Engine: {summary.get('engine', 'python')}",
        f"Fidelity records: {summary['record_counts']['fidelity_trade_records']}",
        f"Vise records: {summary['record_counts']['vise_trade_records']}",
        f"Discrepancy types: {summary['discrepancy_counts']}",
        "Side-level notional summary:",
    ]
    for row in summary["side_level_notional_summary"]:
        lines.append(
            f"  {row['side']}: fidelity={row['fidelity_notional']} "
            f"vise={row['vise_notional']} diff={row['notional_diff']}"
        )
    console_output = "\n".join(lines)
    print(console_output)
    (outputs_dir / "sample_console_output.txt").write_text(console_output, encoding="utf-8")


if __name__ == "__main__":
    main()
