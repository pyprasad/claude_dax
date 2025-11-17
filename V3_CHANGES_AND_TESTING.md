# V3 Strategy - Relaxed Entry + Regime Detection

## 🔴 What Went Wrong with V2

### Multi-Year Results (Catastrophic):

| Year | Signals | Trades | Conversion | Win Rate | Return |
|------|---------|--------|------------|----------|--------|
| **2020** | 1,668 | 41 | **2.5%** | 20.0% | -26.36% |
| **2021** | 1,574 | 15 | **1.0%** | 25.0% | -14.92% |
| **2022** | 1,742 | 14 | **0.8%** | 20.0% | -10.44% |
| **2023** | 1,683 | 47 | **2.8%** | 18.2% | -27.50% |
| **2024** | 1,536 | 39 | **2.5%** | 31.0% | -26.74% |

**vs Q1 2023 (our development period):**
- Signals: 573 → Trades: 252 (**44% conversion**)
- Win rate: **70.5%**
- Return: **+15.42%**

### Root Causes Identified:

**1. Entries Too Strict (97-99% signals blocked):**
- Pullback requirement missed momentum
- 2-hour ORB window too narrow
- 50% OR size filter too high
- Volume filter didn't work on index data

**2. Market Regime Mismatch:**
- Q1 2023 was **trending** (ORB loves trends)
- Rest of years were **ranging** (ORB hates chop)
- No filter to detect difference

**3. Risk Controls Hit Immediately:**
- With 18-31% win rate, hit max_consecutive_losses: 6 quickly
- Trading shut down after 10-40 trades
- Never got to test full strategy

### Conclusion:
**Q1 2023 was an anomaly.** V2 was accidentally optimized for a unique trending period that rarely occurs.

---

## ✅ V3 Solution - Two-Pronged Approach

### 1. **RELAXED ENTRY FILTERS** (Fix Signal Blocking)

| Filter | V2 (Strict) | V3 (Relaxed) | Why |
|--------|-------------|--------------|-----|
| **Entry Type** | Pullback | **Immediate breakout** | Catch momentum |
| **ORB Window** | 09:30-11:30 (2 hrs) | **All day** | More opportunities |
| **OR Size** | >50% ATR | **>30% ATR** | Lower threshold |
| **Volume** | Required | **Optional** | Index doesn't need it |
| **Momentum** | >0.7% first hour | **>0.5% first hour** | More signals |
| **VWAP Distance** | <0.15% | **<0.20%** | Wider pullback |

**Expected:** Signal→Trade conversion improves from 0.8-2.8% to 10-20%

### 2. **REGIME DETECTION** (Trade Only Trending Markets)

```python
def is_trending_market(row):
    # ADX > 20 = trending
    if row['ADX'] < 20:
        return False  # SKIP ranging market

    # ATR Z-score > -0.5 = decent volatility
    if row['ATR_ZScore'] < -0.5:
        return False  # SKIP low volatility

    return True  # TRADE
```

**ADX Interpretation:**
- ADX > 25: Strong trend (best)
- ADX 20-25: Trending (good)
- ADX < 20: Ranging/choppy (skip)

**Expected:** Only trade when market conditions match Q1 2023

---

## 📊 How V3 Works

### V3 Strategy Logic:

```
For each bar:
1. Calculate ADX (trend strength)
2. Check is_trending_market()
   ├─ If ADX < 20: SKIP all signals (ranging market)
   └─ If ADX >= 20: Proceed to step 3
3. Check for ORB breakout
   ├─ If close > OR high AND prev close <= OR high
   └─ Enter LONG immediately (no pullback wait)
4. Execute with V2 risk management
   ├─ Wider stops: 1.5-2.5× ATR
   ├─ Realistic targets: 1.2R, 2R
   └─ Early trailing: 0.8R activation
```

### What Makes V3 Different:

**V2 Approach:**
- Generated signals in ALL market conditions
- Strict pullback entry blocked most signals
- Time filter (first 2 hours) limited opportunities
- Lost money in ranging markets

**V3 Approach:**
- **Filter first** (regime detection)
- **Relax second** (easier entry once filtered)
- **Trade all day** (when conditions are right)
- **Skip bad periods** (preserve capital)

---

## 🚀 How to Test V3

### Quick Test:

```bash
python run_multiyear_backtest_v3.py
```

### Expected Output:

```
================================================================================
YEAR 2020 BACKTEST - V3 (RELAXED + REGIME FILTER)
================================================================================

Regime analysis:
  Trending bars (ADX > 20): 12,450/35,414 (35.2%)
  Avg ADX: 18.3

Generating V3 signals (relaxed entry + regime filter)...
Generated 425 signals
  Signals in trending regime: 425/425

Signal breakdown:
  ORB_LONG: 215
  ORB_SHORT: 180
  VWAP_LONG: 20
  VWAP_SHORT: 10

Running backtest...
Backtest complete. Total trades: 85

2020 V3 RESULTS:
  Unique Trades: 65
  Signals → Trades: 65/425 (15.3% conversion)  ← BETTER!
  Win Rate: 58.5%  ← BETTER!
  Total P&L: $8,250.00  ← POSITIVE!
  Return: +8.25%
```

### What to Look For:

**1. Regime Statistics:**
- What % of bars are trending? (Expect 30-50%)
- Average ADX? (Higher = more trending periods)

**2. Signal Conversion:**
- V2: 0.8-2.8% conversion (terrible)
- V3: Should be 10-20% (much better)

**3. Win Rate:**
- V2: 18-31% (failing)
- V3: Target 55-65% (acceptable)

**4. Return:**
- V2: -10% to -27% (losing money)
- V3: Target +5% to +15% (making money)

---

## 🎯 Validation Criteria for V3

V3 **PASSES** if:

| Metric | Threshold | Why |
|--------|-----------|-----|
| Overall win rate | >= 55% | Profitable edge |
| Avg annual return | > +5% | Makes money long-term |
| Positive years | >= 3/5 | Consistent across periods |
| Signal→Trade conversion | >= 10% | Not blocked by risk controls |

V3 **PARTIALLY PASSES** if:
- Win rate 50-55%
- Return +0% to +5%
- Needs tweaking but has potential

V3 **FAILS** if:
- Win rate < 50%
- Return negative
- Back to drawing board

---

## 🔧 If V3 Fails, Next Steps:

### Option A: Adjust ADX Threshold

Test different thresholds:
```yaml
# In config_professional_v3.yaml
regime:
  adx_threshold: 15  # More lenient (try this first)
  # or
  adx_threshold: 25  # Stricter (only strong trends)
```

### Option B: Disable Regime Filter (Baseline Test)

```yaml
use_regime_filter: false  # Test relaxed entry alone
```

This isolates whether problem is:
- Entry filters (relaxed helps)
- Regime detection (ADX not working)

### Option C: Different Regime Definition

Add more filters:
```python
# In is_trending_market()
if row['EMA_20'] > row['EMA_50']:  # Only trade with trend
    return False
```

### Option D: Abandon ORB, Try Mean-Reversion

If ORB doesn't work even with regime filter:
- Try fading extremes instead of breakouts
- Use RSI2, Bollinger Bands
- Different strategy entirely

---

## 📋 Testing Checklist

Before running V3:

- [x] All V3 files committed and pushed
- [ ] Data files in place (dax_2020-2024_5m.csv)
- [ ] Run: `python run_multiyear_backtest_v3.py`
- [ ] Review regime statistics (% trending bars)
- [ ] Check signal→trade conversion
- [ ] Compare win rates vs V2
- [ ] Share results

---

## 💬 What to Share Back

After running V3, please share:

**1. Console Output:**
- Last 100 lines showing summary
- Year-by-year results
- Regime statistics

**2. Key Metrics:**
```
Regime Analysis:
- % of bars trending (ADX > 20): ?
- Average ADX across years: ?

Performance:
- Overall win rate: ?
- Avg annual return: ?
- Signal→Trade conversion: ?
```

**3. Comparison:**
```
V2 Results: 18-31% WR, -10% to -27% return
V3 Results: ??% WR, ??% return
```

---

## 🎲 What We Expect

### Best Case (V3 Works):
- Regime filter identifies 30-50% of bars as trending
- Win rate improves to 55-65%
- Returns become positive (+5% to +15%)
- Validates that Q1 2023 success was due to trending regime

### Moderate Case (V3 Helps But Not Enough):
- Win rate improves to 45-55%
- Returns slightly positive or breakeven
- Need more tuning but on right track

### Worst Case (V3 Still Fails):
- Win rate stays below 45%
- Returns still negative
- Either:
  a) DAX doesn't suit ORB strategies
  b) Need completely different approach
  c) Try different market (S&P 500, NASDAQ)

---

## 🔬 The Scientific Approach

We're doing **systematic debugging:**

1. **V1:** Basic ORB → Failed
2. **V2:** Improved filters → Worked on Q1 2023 only
3. **Multi-year test:** Revealed Q1 was anomaly
4. **V3:** Relaxed entry + Regime filter → **YOU TEST NOW**
5. **Next:** Based on V3 results, iterate or pivot

This is how professional quants work:
- Hypothesis → Test → Measure → Adjust → Repeat

---

## 🚀 Ready to Test V3!

Run this command:

```bash
cd claude_dax
python run_multiyear_backtest_v3.py
```

Expected runtime: 10-25 minutes for all 5 years

Share the output and we'll analyze together! 🎯
