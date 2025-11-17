# Setup and Run Guide - Multi-Year Backtesting

## Quick Start (5 Steps)

### Step 1: Verify Python Environment

```bash
# Check Python version (requires 3.8+)
python --version

# Verify required packages are installed
pip install pandas numpy pyyaml matplotlib
```

### Step 2: Prepare Your Data

Place your DAX 5-minute data files in the `data/` directory with this naming:

```
data/dax_2020_5m.csv
data/dax_2021_5m.csv
data/dax_2022_5m.csv
data/dax_2023_5m.csv
data/dax_2024_5m.csv
```

**Required format:** See `DATA_REQUIREMENTS.md` for details.

Quick format check:
```bash
head -3 data/dax_2020_5m.csv
```

Should show:
```
timestamp,open,high,low,close,volume
2020-01-02 09:00:00,13200.50,13225.75,13195.25,13210.00,5000
...
```

### Step 3: Run Multi-Year Backtest

```bash
python run_multiyear_backtest.py
```

This will:
- Automatically detect all available year files
- Run V2 strategy on each year
- Generate comprehensive comparison report
- Save detailed results

**Expected runtime:** 2-5 minutes per year

### Step 4: Review Results

Results will be saved to `results_multiyear/`:

```
results_multiyear/
├── 2020_trades.csv         # All trades for 2020
├── 2021_trades.csv         # All trades for 2021
├── ...
├── all_trades.csv          # Combined all years
└── multiyear_summary.txt   # Summary report
```

### Step 5: Check Validation Status

At the end of the run, you'll see:

```
🎉 STRATEGY VALIDATED - ROBUST EDGE CONFIRMED!
```

Or:

```
⚠️  STRATEGY PARTIALLY VALIDATED
```

Or:

```
❌ STRATEGY FAILED VALIDATION
```

---

## Validation Criteria

The strategy PASSES validation if:

| Criterion | Threshold | Why Important |
|-----------|-----------|---------------|
| Overall win rate | >= 60% | Profitable even with small R:R |
| Win rate consistency | Std < 15% | Edge is stable across years |
| Minimum year win rate | >= 55% | No catastrophic years |
| Average annual return | > 0% | Makes money long-term |

---

## Troubleshooting

### Error: "No year data files found"

**Problem:** Script can't find your data files

**Solution:**
```bash
# Check files exist
ls -lh data/dax_*_5m.csv

# If files have different names, rename them:
mv data/my_dax_2020.csv data/dax_2020_5m.csv
```

### Error: "Missing required column: open"

**Problem:** Your CSV has different column names

**Solution:** Use the data converter script:
```bash
python convert_data_format.py data/your_file.csv
```

### Error: "High < Low detected"

**Problem:** Data quality issue

**Solution:** Check your source data for errors:
```bash
# Find problematic rows
python -c "
import pandas as pd
df = pd.read_csv('data/dax_2020_5m.csv')
bad = df[df['high'] < df['low']]
print(bad)
"
```

### Script runs but no trades

**Problem:** Data might be outside main session hours

**Solution:** Check your data timestamps:
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/dax_2020_5m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
print('Hours in data:')
print(df['timestamp'].dt.hour.value_counts().sort_index())
"
```

Expected: Hours 9-21 (main session)

---

## Alternative: Test Single Year

If you only have one year of data, you can still run:

```bash
# Copy your data to expected location
cp data/my_dax_data.csv data/dax_2023_5m.csv

# Run multi-year script (it will test only 2023)
python run_multiyear_backtest.py
```

Or use the original V2 script:

```bash
# Edit config_professional_v2.yaml to point to your file
# Then run:
python run_backtest_pro_v2.py
```

---

## What to Share Back

After running the backtest, please share:

1. **Terminal output** (copy-paste the summary section)
2. **Results file:** `results_multiyear/multiyear_summary.txt`
3. **Years tested:** Which years you had data for
4. **Any errors** encountered

Example:
```
Tested: 2020, 2021, 2022, 2023
Overall Win Rate: 68.5%
Avg Annual Return: +18.3%
Validation: PASSED ✓
```

---

## Advanced: Custom Data Sources

### If using Interactive Brokers:

1. TWS → Market Data → Historical Data
2. Symbol: DAX (or GER40)
3. Timeframe: 5 mins
4. Date range: Full year
5. Export to CSV
6. Save as `dax_YYYY_5m.csv`

### If using MetaTrader 5:

1. Open MT5
2. Market Watch → Right-click DAX → Chart
3. Set timeframe to M5
4. Tools → History Center
5. Export to CSV
6. Process with converter script (if needed)

### If using Dukascopy:

1. Visit: https://www.dukascopy.com/swiss/english/marketwatch/historical/
2. Select: DAX index
3. Timeframe: Tick data
4. Download and use their converter to 5-min bars

---

## Performance Tips

### For large datasets:

```bash
# Run with output suppression for speed
python run_multiyear_backtest.py > results.log 2>&1

# Check progress
tail -f results.log
```

### For faster testing:

Test one year first to verify everything works:
```bash
# Only keep one year file in data/
rm data/dax_202[1-4]_5m.csv

# Run
python run_multiyear_backtest.py
```

---

## Next Steps After Validation

### If validation PASSES:

1. **Review trade logs** - Check for any anomalies
2. **Paper trade** - Test on live data (paper account)
3. **Monitor for 1-3 months** - Verify real-world performance
4. **Consider live deployment** - Start with small size

### If validation FAILS:

1. **Share results** - I'll help diagnose issues
2. **Check data quality** - Verify data is correct
3. **Review failed years** - Which years failed and why?
4. **Consider strategy modifications** - May need adjustments

---

## Files You Need

These files must be in the repository:

```
claude_dax/
├── run_multiyear_backtest.py     ← Main script (CREATED)
├── config_professional_v2.yaml   ← V2 config (EXISTS)
├── strategy_pro_v2.py            ← V2 strategy (EXISTS)
├── indicators_pro.py             ← Indicators (EXISTS)
├── backtest_engine.py            ← Engine (EXISTS)
├── performance.py                ← Analytics (EXISTS)
└── data/
    ├── dax_2020_5m.csv          ← YOU PROVIDE
    ├── dax_2021_5m.csv          ← YOU PROVIDE
    ├── dax_2022_5m.csv          ← YOU PROVIDE
    ├── dax_2023_5m.csv          ← YOU PROVIDE
    └── dax_2024_5m.csv          ← YOU PROVIDE
```

All Python files are already in the repository. You only need to add data files.

---

## Questions?

Common questions:

**Q: Can I test just 2-3 years instead of all 5?**
A: Yes! Script will test whatever years you provide.

**Q: What if I have different column names?**
A: Use the converter script or manually rename columns to match.

**Q: Can I use data from different sources for different years?**
A: Yes, as long as format is consistent.

**Q: How long does it take to run?**
A: ~2-5 minutes per year. 5 years = 10-25 minutes total.

**Q: Will it work on Mac/Linux/Windows?**
A: Yes, Python is cross-platform.

---

Ready to run? Just execute:

```bash
python run_multiyear_backtest.py
```

And share the output!
