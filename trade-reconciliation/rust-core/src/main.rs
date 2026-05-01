use csv::ReaderBuilder;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::env;
use std::error::Error;
use std::fs;

#[derive(Clone)]
struct Trade {
    symbol: String,
    side: String,
    quantity: f64,
    notional: f64,
}

#[derive(Deserialize)]
struct ViseTradeRow {
    symbol_or_cusip: String,
    quantity: String,
    transaction_type: String,
    notional_share_price: String,
}

#[derive(Serialize)]
struct DiscrepancyRow {
    kind: String,
    symbol: String,
    side: String,
    vise_quantity: String,
    fidelity_quantity: String,
    vise_notional: String,
    fidelity_notional: String,
    quantity_diff: String,
    notional_diff: String,
    notes: String,
}

#[derive(Serialize)]
struct SideSummaryRow {
    side: String,
    fidelity_notional: String,
    vise_notional: String,
    notional_diff: String,
}

#[derive(Serialize)]
struct TickerSummaryRow {
    symbol: String,
    fidelity_buy_notional: String,
    vise_buy_notional: String,
    buy_notional_diff: String,
    fidelity_sell_notional: String,
    vise_sell_notional: String,
    sell_notional_diff: String,
}

#[derive(Serialize)]
struct OutputPayload {
    record_counts: BTreeMap<String, usize>,
    discrepancy_counts: BTreeMap<String, usize>,
    discrepancies: Vec<DiscrepancyRow>,
    side_level_notional_summary: Vec<SideSummaryRow>,
    ticker_level_notional_summary: Vec<TickerSummaryRow>,
}

fn slice(s: &str, start: usize, end: usize) -> &str {
    &s[start - 1..end]
}

fn parse_implied_decimal(raw: &str, scale: i32, sign: char) -> f64 {
    let parsed = raw.trim().parse::<f64>().unwrap_or(0.0);
    let value = parsed / 10f64.powi(scale);
    if sign == '-' {
        -value
    } else {
        value
    }
}

fn parse_fidelity(path: &str) -> Result<Vec<Trade>, Box<dyn Error>> {
    let content = fs::read_to_string(path)?;
    let mut trades: Vec<Trade> = Vec::new();
    for line in content.lines() {
        if line.len() < 751 {
            continue;
        }
        if slice(line, 1, 1) != "D" {
            continue;
        }
        if !slice(line, 21, 22).trim().is_empty() || !slice(line, 23, 25).trim().is_empty() {
            continue;
        }
        if slice(line, 329, 329) != "T" {
            continue;
        }
        let buy_sell = slice(line, 326, 326);
        let side = match buy_sell {
            "B" => "BUY",
            "S" => "SELL",
            _ => continue,
        };
        let symbol = slice(line, 367, 396).trim().trim_start_matches('0').to_string();
        if symbol.is_empty() {
            continue;
        }
        let quantity = parse_implied_decimal(
            slice(line, 718, 734),
            5,
            slice(line, 735, 735).chars().next().unwrap_or('+'),
        )
        .abs();
        let notional = parse_implied_decimal(
            slice(line, 736, 750),
            2,
            slice(line, 751, 751).chars().next().unwrap_or('+'),
        )
        .abs();
        trades.push(Trade {
            symbol,
            side: side.to_string(),
            quantity,
            notional,
        });
    }
    Ok(trades)
}

fn parse_vise(path: &str) -> Result<Vec<Trade>, Box<dyn Error>> {
    let mut reader = ReaderBuilder::new().from_path(path)?;
    let mut out: Vec<Trade> = Vec::new();
    for result in reader.deserialize::<ViseTradeRow>() {
        let row = result?;
        let quantity = row.quantity.parse::<f64>().unwrap_or(0.0);
        let price = row.notional_share_price.parse::<f64>().unwrap_or(0.0);
        out.push(Trade {
            symbol: row.symbol_or_cusip.trim().to_string(),
            side: row.transaction_type.trim().to_uppercase(),
            quantity,
            notional: quantity * price,
        });
    }
    Ok(out)
}

fn fmt_qty(v: f64) -> String {
    format!("{v:.5}")
}

fn fmt_money(v: f64) -> String {
    format!("{v:.2}")
}

fn aggregate_by_symbol_side(trades: &[Trade]) -> HashMap<(String, String), (f64, f64)> {
    let mut map: HashMap<(String, String), (f64, f64)> = HashMap::new();
    for t in trades {
        let key = (t.symbol.clone(), t.side.clone());
        let entry = map.entry(key).or_insert((0.0, 0.0));
        entry.0 += t.quantity;
        entry.1 += t.notional;
    }
    map
}

fn run_core(fidelity: &[Trade], vise: &[Trade], tolerance: f64) -> OutputPayload {
    let f_agg = aggregate_by_symbol_side(fidelity);
    let v_agg = aggregate_by_symbol_side(vise);
    let mut all_keys: BTreeSet<(String, String)> = BTreeSet::new();
    for k in f_agg.keys() {
        all_keys.insert(k.clone());
    }
    for k in v_agg.keys() {
        all_keys.insert(k.clone());
    }

    let mut discrepancies: Vec<DiscrepancyRow> = Vec::new();
    let mut discrepancy_counts: BTreeMap<String, usize> = BTreeMap::new();
    for (symbol, side) in &all_keys {
        let f = f_agg.get(&(symbol.clone(), side.clone()));
        let v = v_agg.get(&(symbol.clone(), side.clone()));
        let (f_qty, f_notional) = f.copied().unwrap_or((0.0, 0.0));
        let (v_qty, v_notional) = v.copied().unwrap_or((0.0, 0.0));
        let qty_diff = f_qty - v_qty;
        let notional_diff = f_notional - v_notional;

        let (kind, note) = if f.is_none() {
            ("missing_fidelity_trade", "Present in Vise but missing in Fidelity.")
        } else if v.is_none() {
            ("extra_fidelity_trade", "Present in Fidelity but missing in Vise.")
        } else if qty_diff.abs() > 1e-9 {
            ("quantity_mismatch", "Quantity totals differ after normalization.")
        } else if notional_diff.abs() > tolerance {
            ("notional_mismatch", "Notional totals differ beyond tolerance.")
        } else {
            continue;
        };

        *discrepancy_counts.entry(kind.to_string()).or_insert(0) += 1;
        discrepancies.push(DiscrepancyRow {
            kind: kind.to_string(),
            symbol: symbol.clone(),
            side: side.clone(),
            vise_quantity: fmt_qty(v_qty),
            fidelity_quantity: fmt_qty(f_qty),
            vise_notional: v_notional.to_string(),
            fidelity_notional: f_notional.to_string(),
            quantity_diff: fmt_qty(qty_diff),
            notional_diff: notional_diff.to_string(),
            notes: note.to_string(),
        });
    }

    let mut side_totals: HashMap<String, (f64, f64)> = HashMap::new();
    for t in fidelity {
        let entry = side_totals.entry(t.side.clone()).or_insert((0.0, 0.0));
        entry.0 += t.notional;
    }
    for t in vise {
        let entry = side_totals.entry(t.side.clone()).or_insert((0.0, 0.0));
        entry.1 += t.notional;
    }
    let side_level_notional_summary = vec!["BUY", "SELL"]
        .iter()
        .map(|side| {
            let (f_total, v_total) = side_totals.get(*side).copied().unwrap_or((0.0, 0.0));
            SideSummaryRow {
                side: side.to_string(),
                fidelity_notional: fmt_money(f_total),
                vise_notional: fmt_money(v_total),
                notional_diff: fmt_money(f_total - v_total),
            }
        })
        .collect::<Vec<_>>();

    let symbols = all_keys
        .iter()
        .map(|(symbol, _)| symbol.clone())
        .collect::<BTreeSet<_>>();
    let mut ticker_level_notional_summary: Vec<TickerSummaryRow> = Vec::new();
    for symbol in symbols {
        let f_buy = f_agg
            .get(&(symbol.clone(), "BUY".to_string()))
            .map(|x| x.1)
            .unwrap_or(0.0);
        let v_buy = v_agg
            .get(&(symbol.clone(), "BUY".to_string()))
            .map(|x| x.1)
            .unwrap_or(0.0);
        let f_sell = f_agg
            .get(&(symbol.clone(), "SELL".to_string()))
            .map(|x| x.1)
            .unwrap_or(0.0);
        let v_sell = v_agg
            .get(&(symbol.clone(), "SELL".to_string()))
            .map(|x| x.1)
            .unwrap_or(0.0);
        ticker_level_notional_summary.push(TickerSummaryRow {
            symbol: symbol.clone(),
            fidelity_buy_notional: fmt_money(f_buy),
            vise_buy_notional: fmt_money(v_buy),
            buy_notional_diff: fmt_money(f_buy - v_buy),
            fidelity_sell_notional: fmt_money(f_sell),
            vise_sell_notional: fmt_money(v_sell),
            sell_notional_diff: fmt_money(f_sell - v_sell),
        });
    }

    let mut record_counts = BTreeMap::new();
    record_counts.insert("fidelity_trade_records".to_string(), fidelity.len());
    record_counts.insert("vise_trade_records".to_string(), vise.len());

    OutputPayload {
        record_counts,
        discrepancy_counts,
        discrepancies,
        side_level_notional_summary,
        ticker_level_notional_summary,
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 4 {
        return Err("Usage: cargo run -- <fidelity_txt> <trades_csv> <out_json>".into());
    }
    let fidelity = parse_fidelity(&args[1])?;
    let vise = parse_vise(&args[2])?;
    let out = run_core(&fidelity, &vise, 0.01);
    fs::write(&args[3], serde_json::to_string_pretty(&out)?)?;
    Ok(())
}
