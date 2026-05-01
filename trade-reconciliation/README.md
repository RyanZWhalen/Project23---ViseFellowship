# Trade Reconciliation

Small Python project for parsing Fidelity bookkeeping trades and reconciling them against Vise trade and lot records for a trading day.

## What it does

- Parses fixed-width Fidelity records from `data/raw/FIDELITY-20250729.txt` using field locations from `Bookkeeping-5.3.7.pdf`.
- Normalizes Fidelity and Vise trades into a common schema.
- Compares the two sources and flags:
  - missing Fidelity trades
  - extra Fidelity trades
  - quantity mismatches
  - notional mismatches
- Produces:
  - `outputs/reconciliation_report.csv`
  - `outputs/reconciliation_summary.json`
  - `outputs/sample_console_output.txt`

## Project Layout

```text
trade-reconciliation/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/
│   └── processed/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── parser.py
│   ├── models.py
│   ├── reconcile.py
│   ├── aggregation.py
│   └── utils.py
├── outputs/
├── tests/
└── docs/
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m src.main
```

## Test

```bash
pytest
```
