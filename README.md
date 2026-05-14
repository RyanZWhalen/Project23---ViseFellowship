# Project23---ViseFellowship

## Overview (interview pitch)

This repository is a **trade reconciliation exercise**: for a single trading day, it checks whether **Fidelity’s fixed-width bookkeeping file** lines up with **Vise’s internal CSV trades** (`trades.csv`) and whether **reported sells are plausible against lot inventory** (`lots.csv`). The pipeline parses both sides into a common trade shape, aggregates by **symbol and side (buy vs. sell)**, then classifies gaps such as missing or extra buckets, **quantity mismatches**, and **notional mismatches** within a small tolerance. It writes a **CSV discrepancy report**, a **JSON summary** (counts, side- and ticker-level notionals, lot warnings, which engine ran), and a **captured console log**. An optional **`rust-core`** path (invoked automatically when `cargo` is available) can accelerate parsing and reconciliation on large inputs; otherwise the same behavior runs in **pure Python**, with lot validation always handled in Python.

## Project location

All implementation files live in:

- `trade-reconciliation/`

See the full project documentation here:

- `trade-reconciliation/README.md`

## Quick start

```bash
cd trade-reconciliation
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

## Outputs

After running `python -m src.main`, generated artifacts are available in:

- `trade-reconciliation/outputs/reconciliation_report.csv`
- `trade-reconciliation/outputs/reconciliation_summary.json`
- `trade-reconciliation/outputs/sample_console_output.txt`

## Original Problem: Key Insights

The original reconciliation question asked for differences across:

- share quantities bought/sold
- missing or extra trades
- notional differences by ticker and by side (buy vs. sell)

Using the provided inputs (`FIDELITY-20250729.txt`, `trades.csv`, `lots.csv`), the key findings were:

- Fidelity parsed trade records: `132`
- Vise parsed trade records from `trades.csv`: `122`
- Discrepancy counts:
  - `extra_fidelity_trade`: `2`
  - `missing_fidelity_trade`: `1`
  - `quantity_mismatch`: `1`
  - `notional_mismatch`: `120`
- Side-level notional differences:
  - BUY: Fidelity `42275.28` vs Vise `42411.91` (diff `-136.63`)
  - SELL: Fidelity `40830.60` vs Vise `40353.24` (diff `477.36`)

## CSV Inputs and How They Were Used

- `trades.csv`
  - Vise submitted trades (`symbol_or_cusip`, `quantity`, `transaction_type`, `notional_share_price`)
  - Used as the primary comparison set against Fidelity-trade aggregates.
- `lots.csv`
  - Vise lot inventory (`symbol_or_cusip`, `purchase_date`, `quantity`)
  - Used to check whether sell quantities are covered by available lots.

Notable examples discovered during reconciliation:

- Symbol-format mismatch: `BRK.B` (Vise in `trades.csv`) vs `BRKB` (Fidelity), which appears as one missing and one extra trade.
- Quantity mismatch on `CMCSA` sell side.
- Extra Fidelity sell activity for `MSFT` not present in `trades.csv`.
