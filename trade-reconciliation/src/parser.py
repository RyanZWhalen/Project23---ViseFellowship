import csv
from decimal import Decimal
from pathlib import Path

from .models import LotRecord, NormalizedTrade
from .utils import parse_implied_decimal


def _slice(record: str, start: int, end: int) -> str:
    return record[start - 1 : end]


def parse_fidelity_file(path: Path) -> list[NormalizedTrade]:
    records: list[NormalizedTrade] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line or _slice(line, 1, 1) != "D":
            continue
        if _slice(line, 21, 22).strip() or _slice(line, 23, 25).strip():
            # Exclude non-trade bookkeeping and memo records.
            continue
        if _slice(line, 329, 329) != "T":
            continue

        symbol = _slice(line, 367, 396).strip().lstrip("0")
        buy_sell = _slice(line, 326, 326)
        side = "BUY" if buy_sell == "B" else "SELL" if buy_sell == "S" else ""
        if not symbol or not side:
            continue

        quantity = abs(parse_implied_decimal(_slice(line, 718, 734), 5, _slice(line, 735, 735)))
        notional = abs(parse_implied_decimal(_slice(line, 736, 750), 2, _slice(line, 751, 751)))
        price = abs(parse_implied_decimal(_slice(line, 434, 451), 9, _slice(line, 452, 452)))
        if price == 0 and quantity != 0:
            price = notional / quantity

        records.append(
            NormalizedTrade(
                source="fidelity",
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                notional=notional,
                record_id=f"fidelity_line_{line_no}",
            )
        )
    return records


def parse_vise_trades(path: Path) -> list[NormalizedTrade]:
    records: list[NormalizedTrade] = []
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for index, row in enumerate(reader, start=1):
            quantity = Decimal(row["quantity"])
            price = Decimal(row["notional_share_price"])
            records.append(
                NormalizedTrade(
                    source="vise",
                    symbol=row["symbol_or_cusip"].strip(),
                    side=row["transaction_type"].strip().upper(),
                    quantity=quantity,
                    price=price,
                    notional=quantity * price,
                    record_id=f"vise_trade_{index}",
                )
            )
    return records


def parse_vise_lots(path: Path) -> list[LotRecord]:
    lots: list[LotRecord] = []
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            lots.append(
                LotRecord(
                    symbol=row["symbol_or_cusip"].strip(),
                    purchase_date=row["purchase_date"].strip(),
                    quantity=Decimal(row["quantity"]),
                )
            )
    return lots
