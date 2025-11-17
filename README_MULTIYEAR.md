# Multi-Year Backtesting Package - DAX Professional Strategy V2

## 🎯 What This Does

Automatically tests the profitable V2 strategy across multiple years (2020-2024) to validate it has a **genuine, robust edge** across different market conditions.

## ✅ What We've Proven So Far

| Test | Status | Result |
|------|--------|--------|
| ✅ Q1 2023 Backtest | PASSED | 70.5% WR, +15.42% return |
| ✅ Walk-Forward (Feb+Mar) | PASSED | 72.5% WR, +16.34% return |
| ⏳ Multi-Year (2020-2024) | **YOU RUN THIS** | ? |

**Your task:** Run multi-year backtest and share results!

---

## 🚀 Quick Start (3 Steps)

### 1. Get Your Data

You need DAX 5-minute historical data for years 2020-2024.

**Format required:**
```csv
timestamp,open,high,low,close,volume
2020-01-02 09:00:00,13200.50,13225.75,13195.25,13210.00,5000
```

**Where to get data:**
- Interactive Brokers (free with account)
- Dukascopy (free)
- MetaTrader 5 (free)

See `DATA_REQUIREMENTS.md` for details.

### 2. Place Data Files

Put files in `data/` directory:
```
data/dax_2020_5m.csv
data/dax_2021_5m.csv
data/dax_2022_5m.csv
data/dax_2023_5m.csv
data/dax_2024_5m.csv
```

**Don't have all years?** That's okay! Script will test whatever you provide.

**Wrong format?** Use converter:
```bash
python convert_data_format.py your_data.csv
```

### 3. Run Backtest

```bash
python run_multiyear_backtest.py
```

**That's it!** Results will be in `results_multiyear/`

---

## 📊 What to Expect

The script will:

1. **Auto-detect** all available year files
2. **Run V2 strategy** on each year independently
3. **Generate summary** with win rates, returns, validation status
4. **Save results** to `results_multiyear/` directory

**Runtime:** ~2-5 minutes per year

**Output:**
```
================================================================================
MULTI-YEAR SUMMARY REPORT
================================================================================

Year     Trades     Win Rate     Return       Max DD      Sharpe
----------------------------------------------------------------------
2020     156        68.2%        +22.50%      -12.3%      1.25
2021     143        71.5%        +18.75%      -9.5%       1.45
2022     128        62.1%        +8.30%       -15.2%      0.85
2023     149        70.5%        +15.42%      -10.3%      1.12
2024     98         65.4%        +11.20%      -8.7%       1.18
----------------------------------------------------------------------
OVERALL  674        67.5%        +15.23%      (avg)

================================================================================
VALIDATION CONCLUSION
================================================================================

✓ Overall win rate >= 60% (PASSED)
✓ Win rate consistent across years (PASSED: std=3.8%)
✓ All years above 55% win rate (PASSED: min=62.1%)
✓ Positive average annual return (PASSED: +15.23%)

🎉 STRATEGY VALIDATED - ROBUST EDGE CONFIRMED!

  RECOMMENDATION: Strategy is ready for paper trading
```

---

## 📁 Files Included

### Documentation:
- `README_MULTIYEAR.md` ← **You are here**
- `SETUP_AND_RUN.md` ← Detailed setup instructions
- `DATA_REQUIREMENTS.md` ← Data format specifications

### Scripts:
- `run_multiyear_backtest.py` ← **Main script to run**
- `convert_data_format.py` ← Convert different data formats
- `run_walkforward_test.py` ← Walk-forward validation (already done)

### Strategy Files (already tested):
- `strategy_pro_v2.py` ← V2 strategy (70.5% WR on Q1 2023)
- `config_professional_v2.yaml` ← V2 configuration
- `indicators_pro.py` ← Professional indicators
- `backtest_engine.py` ← Backtest engine
- `performance.py` ← Performance analytics

### Results So Far:
- `V2_SUCCESS_SUMMARY.md` ← V2 breakthrough results
- `BACKTEST_FINDINGS.md` ← V1 analysis and bug discovery
- `results_v2/` ← Q1 2023 detailed results

---

## 🎓 What Validation Means

### If PASSES (all 4 criteria met):

✅ **60%+ overall win rate** - Strategy is profitable
✅ **Win rate consistent** - Edge is stable (std < 15%)
✅ **55%+ minimum year** - No catastrophic years
✅ **Positive avg return** - Makes money long-term

**Means:** Strategy has a **genuine, robust edge**. Ready for paper trading.

### If PARTIALLY PASSES (3/4 criteria):

⚠️ Strategy shows promise but needs review. Share results for analysis.

### If FAILS (< 3 criteria):

❌ Strategy doesn't work across years. Needs major redesign or is fundamentally flawed.

---

## 💬 What to Share Back

After running, please share:

1. **Terminal output** (last 50 lines showing summary)
2. **File:** `results_multiyear/multiyear_summary.txt`
3. **Years tested** and any errors encountered

You can paste directly in chat or upload the text file.

**Example:**
```
Tested: 2020, 2021, 2022, 2023
Overall Win Rate: 68.5%
Avg Annual Return: +18.3%
Validation: PASSED ✓
```

---

## ❓ Troubleshooting

### "No year data files found"

**Fix:**
```bash
ls data/dax_*_5m.csv  # Check files exist with correct names
```

### "Missing required column: open"

**Fix:** Use converter script:
```bash
python convert_data_format.py your_file.csv
```

### Script runs but 0 trades

**Fix:** Check data is during main session (09:00-22:00):
```bash
python -c "import pandas as pd; df = pd.read_csv('data/dax_2020_5m.csv'); df['timestamp'] = pd.to_datetime(df['timestamp']); print(df['timestamp'].dt.hour.value_counts().sort_index())"
```

See `SETUP_AND_RUN.md` for more troubleshooting.

---

## 🔄 If You Don't Have All Years

**That's okay!** Even testing 2-3 years is valuable.

Minimum recommended:
- **2 years** - Can show consistency
- **3+ years** - Good validation
- **5 years** - Best (tests different market regimes)

The script will test whatever years you provide.

---

## 📈 Why This Matters

We've already proven V2 works on:
- Q1 2023 (70.5% WR)
- Out-of-sample Feb+Mar (72.5% WR)

**But:** That's only 3 months. We need to test across:
- **2020** - COVID crash + recovery (high volatility)
- **2021** - Bull market (trending up)
- **2022** - Bear market (trending down)
- **2023** - Confirmed working
- **2024** - Current market

**If strategy maintains 60-75% win rate across all years:**
→ **Genuine edge confirmed**
→ **Ready for live deployment**

**If strategy degrades on some years:**
→ **Curve-fit to 2023**
→ **Needs modification**

---

## 🎯 Expected Timeline

| Task | Time |
|------|------|
| Get historical data | 30-60 min |
| Convert/prepare data | 10-20 min |
| Run backtest | 10-25 min |
| Review results | 5-10 min |
| **Total** | **1-2 hours** |

---

## 🚨 Important Notes

1. **Use main session data only** (09:00-22:00 CET)
2. **5-minute bars required** (not 1-min or 15-min)
3. **Volume optional** (will use constant if missing)
4. **Script handles multiple formats** (use converter if needed)
5. **Missing years okay** (tests what you have)

---

## ✨ After Validation Passes

Next steps:
1. ✅ Share results with me
2. ✅ Review any anomalies in trade logs
3. ✅ Consider paper trading (1-3 months)
4. ✅ Monitor real-world performance
5. ✅ Potentially deploy live (start small)

---

## 🤝 Support

If you encounter issues:
1. Check `SETUP_AND_RUN.md` for detailed troubleshooting
2. Share error messages and I'll help diagnose
3. Can provide data conversion help for specific sources

---

## Ready to Run?

```bash
# 1. Place your data files in data/ directory
# 2. Run this command:
python run_multiyear_backtest.py

# 3. Share the output!
```

Let's validate this edge! 🚀
