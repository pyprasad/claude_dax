# Multi-Year Backtesting - Data Requirements

## Required Data Files

Place the following files in the `data/` directory:

```
data/
├── dax_2020_5m.csv
├── dax_2021_5m.csv
├── dax_2022_5m.csv
├── dax_2023_5m.csv  (we already have Q1)
└── dax_2024_5m.csv
```

## Data Format Required

Each CSV file must have the following columns (case-sensitive):

```csv
timestamp,open,high,low,close,volume
2020-01-02 09:00:00,13200.50,13225.75,13195.25,13210.00,5000
2020-01-02 09:05:00,13210.25,13230.00,13205.50,13228.75,4500
...
```

### Column Specifications:

| Column | Type | Description | Required |
|--------|------|-------------|----------|
| `timestamp` | datetime | Format: YYYY-MM-DD HH:MM:SS | Yes |
| `open` | float | Opening price | Yes |
| `high` | float | High price | Yes |
| `low` | float | Low price | Yes |
| `close` | float | Closing price | Yes |
| `volume` | int | Volume (can be omitted, will use 1000) | Optional |

### Important Requirements:

1. **Timeframe:** 5-minute bars only
2. **Session Hours:** Main DAX session (09:00-22:00 CET/CEST)
3. **Timezone:** Preferably UTC or CET (script will handle both)
4. **No Gaps:** Continuous data (weekends excluded automatically)
5. **No Duplicates:** Each timestamp should appear only once

## Data Quality Checks

The script will automatically:
- ✓ Remove duplicate timestamps
- ✓ Sort by timestamp
- ✓ Validate high >= low
- ✓ Validate all prices > 0
- ✓ Add volume if missing (constant 1000)
- ✓ Filter to main session hours

## Recommended Data Sources

### Free Sources:
1. **Interactive Brokers** (with account)
   - TWS -> Market Data -> Historical Data
   - Export as CSV

2. **Dukascopy**
   - https://www.dukascopy.com/swiss/english/marketwatch/historical/
   - Free historical tick data
   - Can be resampled to 5-min

3. **MetaTrader 5**
   - With any broker offering DAX
   - Export historical data
   - Set timeframe to M5 (5-min)

### Paid Sources:
1. **Polygon.io** - $99/month
2. **Alpha Vantage** - Premium tier
3. **Quandl** - Various pricing

## Expected Data Volumes

| Year | Approx Bars | File Size | Trading Days |
|------|-------------|-----------|--------------|
| 2020 | ~40,000 | ~3-5 MB | ~250 |
| 2021 | ~40,000 | ~3-5 MB | ~250 |
| 2022 | ~40,000 | ~3-5 MB | ~250 |
| 2023 | ~40,000 | ~3-5 MB | ~250 |
| 2024 | ~30,000 | ~2-4 MB | ~200 (partial year) |

## Validation Before Running

Before running the multi-year backtest, verify your data:

```bash
# Check file exists
ls -lh data/dax_2020_5m.csv

# Check format (first 5 rows)
head -5 data/dax_2020_5m.csv

# Check date range
head -2 data/dax_2020_5m.csv && tail -2 data/dax_2020_5m.csv

# Count rows
wc -l data/dax_2020_5m.csv
```

Expected output:
```
timestamp,open,high,low,close,volume
2020-01-02 09:00:00,...
```

## What If I Don't Have All Years?

The script will handle missing years gracefully:
- It will test only the years you provide
- Results will show which years were tested
- Minimum recommended: At least 2-3 years for validation

## Once Data is Ready

Simply run:
```bash
python run_multiyear_backtest.py
```

The script will:
1. Scan `data/` directory for year files
2. Run V2 strategy on each year
3. Generate comparison report
4. Save detailed results for each year
5. Create summary charts

Results will be saved to:
```
results_multiyear/
├── 2020_results.csv
├── 2021_results.csv
├── ...
├── summary_report.txt
└── comparison_chart.png
```

## Need Help?

If you need help:
1. Getting data from a specific source
2. Converting data formats
3. Troubleshooting data issues

Just let me know which source you're using and I can provide specific instructions.
