# ARI Strategy - Detailed Usage Guide

Complete step-by-step guide for using the Adaptive Regime Intraday Strategy

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Understanding the Configuration](#understanding-the-configuration)
4. [Running Your First Backtest](#running-your-first-backtest)
5. [Interpreting Results](#interpreting-results)
6. [Optimization Workflow](#optimization-workflow)
7. [Using Real Market Data](#using-real-market-data)
8. [Parameter Tuning Guide](#parameter-tuning-guide)
9. [Common Issues & Troubleshooting](#common-issues--troubleshooting)
10. [Best Practices](#best-practices)

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- 2GB free disk space (for results and data)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `pandas` - Data manipulation
- `numpy` - Numerical computations
- `matplotlib` - Plotting
- `seaborn` - Statistical visualization
- `pyyaml` - Configuration management

### Step 2: Verify Installation

```bash
python -c "import pandas, numpy, matplotlib, yaml; print('All dependencies installed!')"
```

---

## Quick Start

### 1. Generate Sample Data

If you don't have market data yet, generate synthetic data:

```bash
python generate_sample_data.py
```

**Output**:
- Creates `data/DAX_5min.csv` with 60 days of realistic 5-minute bars
- Includes different market regimes (trending, ranging, volatile)

### 2. Run Backtest

```bash
python run_backtest.py
```

**Output**:
- Console: Real-time backtest progress and summary
- `results/performance_report.txt` - Detailed metrics
- `results/trade_log.csv` - All trades
- `results/equity_curve.png` - Visual performance
- `results/trade_analysis.png` - Statistical analysis
- `results/monthly_returns.png` - Monthly heatmap

### 3. Review Results

```bash
# View performance report
cat results/performance_report.txt

# Open trade log in spreadsheet
# (Use Excel, Google Sheets, or LibreOffice)
open results/trade_log.csv
```

---

## Understanding the Configuration

The `config.yaml` file controls all strategy behavior.

### Data Section

```yaml
data:
  filepath: "data/DAX_5min.csv"  # Path to your data file
  date_column: "timestamp"        # Name of date/time column
  timeframe: "5min"               # Bar timeframe
```

**What to Change**:
- `filepath`: Your CSV file location
- `date_column`: If your timestamp column has a different name
- Column mappings: If your CSV uses different column names

### Session Section

```yaml
session:
  start_time: "09:00"    # DAX opens 09:00 CET
  end_time: "22:00"      # DAX closes 22:00 CET
  entry_cutoff: "16:00"  # No new entries after 4 PM
  skip_first_minutes: 15 # Avoid opening volatility
```

**Index-Specific Settings**:

| Index | Start Time | End Time | Timezone |
|-------|-----------|----------|----------|
| DAX | 09:00 | 22:00 | CET |
| S&P 500 | 09:30 | 16:00 | EST |
| NASDAQ | 09:30 | 16:00 | EST |
| FTSE | 08:00 | 16:30 | GMT |
| Nikkei 225 | 09:00 | 15:00 | JST |

### Strategy Parameters

#### Regime Detection

```yaml
strategy:
  adx_period: 14                    # ADX calculation period
  adx_momentum_threshold: 25        # Above = momentum mode
  adx_ranging_threshold: 20         # Below = mean-reversion mode
```

**Tuning Guide**:
- **Higher ADX thresholds** (30/25): Fewer but higher-quality momentum trades
- **Lower ADX thresholds** (20/15): More trades but more false signals
- **Recommended range**: 20-30 for momentum, 15-25 for ranging

#### Risk Management

```yaml
  risk:
    risk_per_trade_pct: 1.0          # Risk 1% per trade
    momentum_stop_atr_mult: 2.0      # Stop = 2 × ATR
    mean_reversion_stop_atr_mult: 1.5 # Tighter stop for MR
```

**Position Sizing Example**:
- Account: $100,000
- Risk per trade: 1% = $1,000
- ATR: 120 points
- Stop: 2 × ATR = 240 points
- Position size: $1,000 / 240 = 4.17 → **4 contracts**

**Tuning Guide**:
- **Conservative**: 0.5% risk, 2.5× ATR stop
- **Moderate**: 1.0% risk, 2.0× ATR stop
- **Aggressive**: 1.5% risk, 1.5× ATR stop

---

## Running Your First Backtest

### Step-by-Step Execution

**1. Prepare Your Data**

```bash
# Option A: Use sample data
python generate_sample_data.py

# Option B: Use your own data (see "Using Real Market Data" section)
```

**2. Review Configuration**

```bash
# Open config.yaml in text editor
nano config.yaml  # or vim, code, etc.

# Verify:
# - Data filepath is correct
# - Session times match your index
# - Risk parameters align with your goals
```

**3. Run Backtest**

```bash
python run_backtest.py
```

**4. Monitor Progress**

You'll see console output like:
```
Loading configuration...
Configuration loaded ✓

Loading data from data/DAX_5min.csv...
Loaded 5040 bars
Date range: 2024-01-01 to 2024-03-15

Calculating technical indicators...
Calculated 15 indicators ✓

Generating trading signals...
Generated 234 trading signals ✓

Running backtest simulation...
Backtest complete. Total trades: 187
```

**5. Review Results**

See "Interpreting Results" section below.

---

## Interpreting Results

### Performance Report

Open `results/performance_report.txt`:

```
OVERALL PERFORMANCE
--------------------------------------------------
Initial Capital:        $100,000.00
Final Equity:           $118,450.00
Total P&L:              $18,450.00
Total Return:           18.45%
CAGR:                   35.22%
Max Drawdown:           8.34%
```

**Key Metrics Explained**:

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| Win Rate | >50% | 45-50% | <45% |
| Profit Factor | >2.0 | 1.5-2.0 | <1.5 |
| Max Drawdown | <10% | 10-15% | >15% |
| Sharpe Ratio | >2.0 | 1.0-2.0 | <1.0 |
| Expectancy | >$100 | $50-100 | <$50 |

### Trade Log Analysis

Open `results/trade_log.csv` in spreadsheet software:

**Columns**:
- `entry_time` / `exit_time`: Trade timing
- `signal_type`: MOMENTUM_LONG, MEAN_REV_LONG, etc.
- `entry_price` / `exit_price`: Execution prices
- `pnl`: Profit/Loss in currency
- `pnl_pct`: P&L as % of account
- `exit_reason`: TP1, TP2, STOP_LOSS, etc.
- `mae` / `mfe`: Max Adverse/Favorable Excursion
- `holding_time`: Minutes in trade

**Analysis Tips**:

1. **Filter by Signal Type**
   - Which regime performs best?
   - Should you disable underperforming modes?

2. **Analyze Exit Reasons**
   - Too many stop losses? → Widen stops or improve entry
   - Too many TP1s, few TP2s? → Adjust targets
   - Many REGIME_CHANGE exits? → ADX thresholds may be too close

3. **MAE/MFE Analysis**
   - If MAE >> stop distance: Stops too tight
   - If MFE >> targets: Targets too conservative

### Equity Curve

View `results/equity_curve.png`:

**Healthy Equity Curve**:
- ✅ Smooth upward slope
- ✅ Drawdowns < 15%
- ✅ Recovers quickly from losses
- ✅ No long flat periods

**Warning Signs**:
- ⚠️ Large sudden drops (check for parameter overfitting)
- ⚠️ Long sideways periods (strategy not working in that regime)
- ⚠️ Most gains in one period (not robust)

### Trade Analysis Plots

View `results/trade_analysis.png`:

**P&L Distribution** (top-left):
- Should be right-skewed (positive expectancy)
- Long right tail = occasional big wins
- Small losses, big wins = ideal

**Cumulative P&L** (top-right):
- Should be steadily increasing
- Check for periods of drawdown

**MAE vs MFE Scatter** (bottom-left):
- Winners (green) should have high MFE, low MAE
- Losers (red) should cluster near origin
- If losers have high MAE: stops too wide

**Win Rate by Signal Type** (bottom-right):
- Compare performance across regimes
- Disable modes with <40% win rate

---

## Optimization Workflow

### Why Optimize?

Default parameters may not be optimal for your:
- Specific index (DAX vs S&P500 have different characteristics)
- Timeframe (5min vs 15min)
- Market regime (2024 may differ from 2023)

### Walk-Forward Optimization

**CRITICAL**: Always use walk-forward, NEVER in-sample optimization!

```bash
python optimizer.py
```

**What It Does**:

1. **Splits data** into train/test folds (e.g., 3 folds)
2. **Tests 50+ parameter combinations** on training data
3. **Validates best parameters** on out-of-sample test data
4. **Selects robust parameters** that work across all folds

**Output**:
```
WALK-FORWARD OPTIMIZATION
================================================================================

Testing 50 parameter combinations
Using 3 walk-forward folds

Fold 1/3
  Train: 2024-01-01 to 2024-02-15 (3360 bars)
  Test:  2024-02-16 to 2024-03-01 (1120 bars)
  Best training fitness: 245.32
  Out-of-sample fitness: 198.67
  Test trades: 45, Win rate: 51.1%, Return: 6.23%

...

Best Parameter Set:
  adx_momentum_threshold: 25
  adx_ranging_threshold: 20
  rsi_min: 50
  ...

Optimized configuration saved to config_optimized.yaml
```

### Using Optimized Parameters

```bash
# Rename optimized config
mv config_optimized.yaml config.yaml

# Re-run backtest with new parameters
python run_backtest.py
```

### Optimization Best Practices

**DO**:
- ✅ Use walk-forward (out-of-sample validation)
- ✅ Test on unseen data after optimization
- ✅ Prefer simple parameter ranges (not 0.01 precision)
- ✅ Require minimum number of trades (>30 per fold)
- ✅ Balance multiple objectives (returns, drawdown, robustness)

**DON'T**:
- ❌ Optimize on all your data (overfitting!)
- ❌ Cherry-pick best single fold
- ❌ Over-optimize (100+ parameters)
- ❌ Ignore out-of-sample degradation
- ❌ Optimize until you get "perfect" results

---

## Using Real Market Data

### Data Requirements

**Format**: CSV file with columns:
```
timestamp,open,high,low,close,volume
```

**Quality Checklist**:
- [ ] No missing bars (gaps filled)
- [ ] Correct timezone (matching your session config)
- [ ] Reasonable prices (no obvious errors)
- [ ] Volume data present (zeros acceptable for indices)
- [ ] High >= Low for all bars
- [ ] Dates in ascending order

### Data Sources

**Free Sources**:
- Yahoo Finance (daily/hourly, limited intraday)
- Alpha Vantage (API, 5 calls/min limit)
- IEX Cloud (historical data, free tier)

**Paid Sources**:
- Interactive Brokers (with account)
- Polygon.io ($200/month, high quality)
- QuantConnect (data included with subscription)
- Norgate Data (EOD + intraday)

### Loading Your Data

**1. Update config.yaml**:

```yaml
data:
  filepath: "data/my_data.csv"
  date_column: "timestamp"  # or "date", "datetime", etc.
  ohlcv_columns:
    open: "open"
    high: "high"
    low: "low"
    close: "close"
    volume: "volume"
```

**2. If your columns have different names**:

```yaml
  ohlcv_columns:
    open: "Open"      # Capital O
    high: "High"
    low: "Low"
    close: "Close"
    volume: "Vol"     # Different name
```

**3. Verify data loads correctly**:

```bash
python run_backtest.py
# Check console output:
# "Loaded 5040 bars"
# "Date range: ..."
```

---

## Parameter Tuning Guide

### ADX Thresholds

**Effect**: Controls regime switching sensitivity

| Setting | ADX Momentum | ADX Ranging | Effect |
|---------|--------------|-------------|--------|
| Strict | 30 | 15 | Fewer trades, higher quality |
| Default | 25 | 20 | Balanced |
| Loose | 20 | 25 | More trades, more whipsaws |

**Tune if**:
- Too many trades → Increase thresholds
- Too few trades → Decrease thresholds
- Frequent regime switching → Widen gap between thresholds

### RSI Parameters

**Momentum RSI Min** (default: 50):
- Higher (55) → Only enter well-established momentum
- Lower (45) → Enter earlier in trend

**Mean-Reversion RSI2** (default: 10/90):
- Extreme (5/95) → Fewer, higher-quality reversals
- Moderate (15/85) → More reversal attempts

### Stop Loss Multipliers

**Momentum** (default: 2.0× ATR):
- Tighter (1.5×) → Lower risk, more stopped out
- Wider (2.5×) → Higher risk, more room to breathe

**Mean-Reversion** (default: 1.5× ATR):
- Should be tighter than momentum
- Range: 1.0× - 2.0×

### Risk Per Trade

| Account Size | Conservative | Moderate | Aggressive |
|--------------|--------------|----------|------------|
| < $50k | 0.5% | 1.0% | 1.5% |
| $50k - $200k | 0.75% | 1.0% | 2.0% |
| > $200k | 1.0% | 1.5% | 2.5% |

**Never exceed 2% risk per trade!**

---

## Common Issues & Troubleshooting

### No Trades Generated

**Symptoms**: "Generated 0 trading signals"

**Causes**:
1. ADX thresholds too strict
2. Insufficient data (indicators need warmup)
3. Time filters too restrictive
4. Volatility filters blocking all trades

**Solutions**:
```yaml
# Loosen ADX
adx_momentum_threshold: 20  # was 25
adx_ranging_threshold: 25   # was 20

# Check you have enough data
# Minimum: 200+ bars after indicators calculated

# Widen time window
entry_cutoff: "18:00"  # was "16:00"
```

### Poor Win Rate (<40%)

**Causes**:
1. Stops too tight
2. Wrong regime detection
3. Data quality issues

**Solutions**:
```yaml
# Widen stops
momentum_stop_atr_mult: 2.5  # was 2.0
mean_reversion_stop_atr_mult: 2.0  # was 1.5

# Require stronger confirmation
rsi_min: 55  # was 50
```

### Large Drawdowns (>15%)

**Causes**:
1. Position sizing too aggressive
2. No volatility filters
3. Consecutive losses not limited

**Solutions**:
```yaml
# Reduce risk
risk_per_trade_pct: 0.5  # was 1.0

# Enforce stricter controls
controls:
  max_consecutive_losses: 2  # was 3
  daily_loss_limit_pct: 1.5  # was 2.0
```

### Data Validation Failed

**Error**: "High < Low detected"

**Solution**:
```python
# Check data in Python
import pandas as pd
df = pd.read_csv('data/your_data.csv')

# Find problematic bars
bad_bars = df[df['high'] < df['low']]
print(bad_bars)

# Fix or remove
df = df[df['high'] >= df['low']]
df.to_csv('data/fixed_data.csv', index=False)
```

---

## Best Practices

### Backtesting

1. **Use sufficient data**: Minimum 6 months, ideally 1-2 years
2. **Include different regimes**: Bull, bear, sideways markets
3. **Check for look-ahead bias**: Strategy only uses past data
4. **Model slippage realistically**: 0.5× ATR is reasonable
5. **Include all costs**: Commissions, spreads, financing

### Optimization

1. **Always walk-forward**: Never in-sample only
2. **Reserve test set**: 20% of data never used in optimization
3. **Limit parameters**: Don't optimize >10 parameters
4. **Use wide ranges**: Test [1.5, 2.0, 2.5], not [1.98, 1.99, 2.00]
5. **Multi-objective**: Optimize for robustness, not just returns

### Live Trading Preparation

1. **Paper trade first**: Minimum 3 months
2. **Start small**: 10-25% of planned size
3. **Monitor slippage**: Track actual vs expected
4. **Review daily**: Check trades match backtest logic
5. **Have kill switch**: Plan to stop if exceeding drawdown

### Risk Management

1. **Never exceed 2% per trade**
2. **Cap daily loss** at 2-3% of account
3. **Limit total exposure**: Max 5% at risk simultaneously
4. **Diversify**: Don't trade one index only
5. **Review monthly**: Adjust parameters if regime changes

---

## Next Steps

### After Your First Successful Backtest

1. **Run on different data**
   - Test on different index (S&P500 instead of DAX)
   - Test on different timeframe (15min instead of 5min)
   - Test on different period (2023 vs 2024)

2. **Perform walk-forward optimization**
   - Run `optimizer.py`
   - Validate on out-of-sample data
   - Check robustness across folds

3. **Sensitivity analysis**
   - Vary each parameter ±20%
   - Check if performance degrades gracefully
   - Avoid cliff edges (small change = big difference)

4. **Monte Carlo simulation**
   - Randomize trade order
   - Estimate confidence intervals
   - Understand luck vs skill

5. **Regime analysis**
   - Identify when strategy works/fails
   - Add regime filters if needed
   - Consider disabling underperforming modes

### Before Live Trading

- [ ] 6+ months of paper trading
- [ ] Out-of-sample test passed
- [ ] Risk controls tested
- [ ] Execution system validated
- [ ] Emergency procedures documented
- [ ] Position sizing double-checked
- [ ] Slippage/commissions verified
- [ ] Psychological preparation complete

---

## Support & Resources

### Documentation
- `README.md` - Overview and features
- `USAGE_GUIDE.md` - This document
- Code comments - Inline explanations

### Getting Help
1. Check this guide first
2. Review code comments
3. Open GitHub issue
4. Consult recommended books (see README)

### Learning Resources
- **Books**: See README "Further Reading" section
- **Papers**: Strategy foundations in academic research
- **Blogs**: QuantStart, Systematic Trading, QuantConnect

---

**Good luck with your algorithmic trading journey!**

Remember: This is a tool, not a guaranteed profit machine. Use proper risk management, validate thoroughly, and trade responsibly.
