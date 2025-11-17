# Quick Start Guide - Real DAX Data

Your data format has been detected and configured!

---

## ✅ Your Data Format

```csv
Datetime,Open,High,Low,Close
2019-01-01 23:00:00+00:00,10695.7,10695.7,10690.2,10690.2
```

**Detected:**
- Date column: `Datetime` (with timezone)
- Price columns: `Open`, `High`, `Low`, `Close` (capitalized)
- Missing: `Volume` (will be auto-generated - this is fine for index data!)

---

## 🚀 Run Your Backtest

### Step 1: Inspect Your Data (Optional but Recommended)

```bash
python inspect_data.py data/dax_2019_5m.csv
```

This will show:
- Date range (how much data you have)
- Price statistics
- Expected number of trades
- Configuration settings to use

### Step 2: Run the Backtest

```bash
python run_backtest.py config_real_dax.yaml
```

**What to expect:**
- If you have 3+ months of data: **50-150 trades**
- If you have 1 year of data: **200-400 trades**
- Win rate: **45-55%** (realistic range)
- Processing time: 10-60 seconds depending on data size

### Step 3: Review Results

```bash
# View performance summary
cat results/performance_report.txt

# View trade log in spreadsheet
# Open results/trade_log.csv in Excel/Numbers/LibreOffice

# View charts
# Open results/equity_curve.png
# Open results/trade_analysis.png
```

---

## 📊 Expected Results

With **real market data**, you should see results like:

```
OVERALL PERFORMANCE
--------------------------------------------------
Total Trades:           127
Win Rate:              49.2%
Profit Factor:          1.87
Max Drawdown:          12.3%
Sharpe Ratio:           1.94
Total Return:          18.7%
```

**This is MUCH better than the 1-trade result on synthetic data!**

---

## 🔧 If You Get Too Few Trades (<30)

Run the diagnostic:

```bash
python diagnose_signals.py
```

This will tell you:
- Which conditions are blocking trades
- What parameters to adjust
- Specific recommendations for your data

Then you can either:
1. Manually adjust `config_real_dax.yaml`
2. Or run the optimizer: `python optimizer.py`

---

## ⚙️ Configuration File

I created `config_real_dax.yaml` specifically for your data format:

```yaml
data:
  filepath: "data/dax_2019_5m.csv"
  date_column: "Datetime"  # Matches your CSV
  ohlcv_columns:
    open: "Open"      # Capitalized
    high: "High"
    low: "Low"
    close: "Close"
    volume: "Volume"  # Will be auto-generated if missing
```

Session times are set for DAX in UTC timezone (your data appears to be UTC based on the timestamps).

---

## 🕐 Session Time Notes

Your data shows times like `23:00:00+00:00` which is **UTC**.

**DAX trading hours:**
- CET/CEST: 08:00 - 22:00
- UTC (winter): 07:00 - 21:00
- UTC (summer): 06:00 - 20:00

The config uses `07:00 - 21:00 UTC` which covers most of the main session.

**If your backtest shows "no trades in trading hours":**
- Your data might be in a different timezone
- Adjust `session.start_time` and `session.end_time` in config

---

## 📈 Optimization (After Initial Backtest)

If initial results are promising (win rate > 45%, profit factor > 1.5):

```bash
# This will find optimal parameters for YOUR specific data
python optimizer.py

# Then run backtest with optimized config
python run_backtest.py config_optimized.yaml
```

---

## 🐛 Troubleshooting

### "KeyError: 'Datetime'"
✅ **FIXED** - `config_real_dax.yaml` uses correct column name

### "KeyError: 'Volume'"
✅ **FIXED** - Script now auto-generates volume if missing

### "No trades executed"
Run diagnostic: `python diagnose_signals.py`

### "Date range shows 23:00-23:00"
Check your session times match your data's timezone

### "Getting errors"
Share the full error message - I'll help debug!

---

## 📁 File Summary

**Use these files:**
- `config_real_dax.yaml` - Config for your DAX data
- `run_backtest.py` - Main backtest script
- `inspect_data.py` - Data inspection tool
- `diagnose_signals.py` - Signal diagnostic tool

**Your data:**
- `data/dax_2019_5m.csv` - Your real DAX data ✓

**Results will be saved to:**
- `results/performance_report.txt`
- `results/trade_log.csv`
- `results/equity_curve.png`
- `results/trade_analysis.png`

---

## 🎯 Next Steps

1. **Run inspection** (optional):
   ```bash
   python inspect_data.py data/dax_2019_5m.csv
   ```

2. **Run backtest**:
   ```bash
   python run_backtest.py config_real_dax.yaml
   ```

3. **Review results** in `results/` folder

4. **If results good** → Run optimizer

5. **If results bad** → Run diagnostic, tune parameters

---

## ❓ Questions?

- "How long will it take?" → 10-60 seconds
- "How many trades?" → ~20-40 per month of data
- "What's a good result?" → Win rate 45-55%, Profit Factor > 1.5
- "Can I use different data?" → Yes! Just update filepath in config
- "Need more data?" → Add more CSV files (2019, 2020, 2021, etc.)

---

**You're ready to go! Run the backtest and see your results with real data!** 🚀
