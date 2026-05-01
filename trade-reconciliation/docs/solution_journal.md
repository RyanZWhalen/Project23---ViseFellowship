# Solution Journal

## Problem Summary
The goal is to reconcile Fidelity bookkeeping trade records against Vise submitted trades and lot records for a single trading day, then identify missing/extra records, quantity deltas, and notional differences.

## Inputs
- `data/raw/Bookkeeping-5.3.7.pdf`: Fidelity field layout and business rules for the bookkeeping file format.
- `data/raw/FIDELITY-20250729.txt`: Fixed-width Fidelity detail records used as the brokerage source of truth for this exercise.
- `data/raw/trades.csv`: Vise submitted day-trade records, including symbol, side, quantity, and per-share notional price.
- `data/raw/lots.csv`: Vise lot inventory used to validate whether sell quantities are covered by available lots.

## Parsing Plan
The parser reads each 1073-character detail line and applies the PDF-documented byte positions. Trade filtering uses these conditions:
- `record type == D`
- `KEY CODE` and `TRANSACTION TYPE` blank (trade records)
- `TRADE TYPE == T` (trade date records)
- valid buy/sell code and symbol present

For each accepted line, the parser extracts symbol, side, expanded quantity, amount, and price using implied decimal scaling.

## Data Normalization
All sources are mapped into a common `NormalizedTrade` shape:
- `symbol` standardized as uppercase source symbol text
- `side` standardized to `BUY` / `SELL`
- `quantity` as positive `Decimal`
- `notional` as positive `Decimal`
- `price` as `Decimal`

Fidelity signed fields are converted to absolute quantity/notional, with side represented independently by buy/sell code.

## Matching Logic
Reconciliation is performed at `(symbol, side)` granularity after normalization:
1. Aggregate total quantity and notional by `(symbol, side)` for Fidelity and Vise.
2. Compare keys and totals across both sources.
3. Emit discrepancy records for missing/extra keys, then quantity differences, then notional differences.

## Discrepancy Rules
- missing Fidelity trades: `(symbol, side)` exists in Vise but not in Fidelity.
- extra Fidelity trades: `(symbol, side)` exists in Fidelity but not in Vise.
- quantity mismatches: key exists in both but total quantity differs.
- notional mismatches: key exists in both, quantity matches, and absolute notional delta exceeds tolerance (`$0.01`).

## Aggregation Logic
- Ticker-level summary: per symbol, compute Fidelity vs Vise buy/sell notional totals and differences.
- Side-level summary: aggregate total buy and total sell notionals across all symbols for both sources.
- Discrepancy count summary: group discrepancy rows by type.

## Assumptions
- Input file consists exclusively of Fidelity detail records in this dataset (no separate header/trailer lines included).
- Symbol extraction from Fidelity uses `OPTION SYMBOL ID` field and strips left zero padding.
- Reconciliation is done by aggregated `(symbol, side)` totals rather than one-to-one fill matching.
- Vise `notional_share_price` is treated as executed price for notional computation.

## Issues Encountered
- Fidelity files in this sample are 1073 bytes per line while the PDF references a 1300-byte layout; required fields are still present in the available segment and parsed successfully.
- Multiple sell symbols are split across several Fidelity rows (for lot-level accounting), requiring aggregation prior to comparison.
- To support future large backfills and SLA-driven processing, a Rust core was added for high-throughput fixed-width parsing and aggregation, with Python fallback for environments without Rust tooling.

## Final Findings
Running the end-to-end workflow on the supplied sample data produced these findings:
- Fidelity parsed trade records: 132
- Vise parsed trade records: 122
- Discrepancy counts: 2 extra Fidelity trades, 1 missing Fidelity trade, 1 quantity mismatch, 120 notional mismatches
- Side-level notional differences:
  - BUY: Fidelity `42275.28` vs Vise `42411.91` (diff `-136.63`)
  - SELL: Fidelity `40830.60` vs Vise `40353.24` (diff `477.36`)

Key notable record-level observations:
- Symbol mapping mismatch appears for `BRK.B` (Vise) vs `BRKB` (Fidelity), yielding one missing and one extra trade.
- `CMCSA` sell side shows a quantity mismatch (Fidelity 8 vs Vise 7).
- Fidelity includes an extra `MSFT` sell not present in Vise input.

Artifacts are written to:
- `outputs/reconciliation_report.csv`
- `outputs/reconciliation_summary.json`
- `outputs/sample_console_output.txt`
