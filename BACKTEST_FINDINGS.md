# DAX Professional Strategy - Backtest Findings & Analysis

## Executive Summary

After developing and testing a professional DAX intraday strategy based on institutional tactics (Opening Range Breakout + VWAP + Momentum), we discovered and fixed a **critical lookahead bias** in the backtest engine. The corrected results show the strategy is **not profitable** on Q1 2023 data.

## Critical Bug Fixed: Lookahead Bias

### The Problem
The original backtest engine had a severe forward-looking bias:
- **Signal detection:** Based on bar N's close price (e.g., 09:30 close breaking above OR high)
- **Entry execution:** At bar N's open price (e.g., 09:30 open)
- **Why this is impossible:** In a 5-minute bar, the OPEN happens BEFORE the CLOSE

**Example from real backtest:**
- Signal at 2023-01-04 09:30 when close = 15,966.17 (broke above OR high of 15,952.24)
- Entry was at 09:30 open = 15,938.74
- This gave us an entry price **below the breakout level** - impossible in real trading!

### The Fix
Changed backtest_engine.py to use **previous bar's signal** for **current bar's entry:**
```python
# OLD (wrong):
if current_row['Signal'] != 0:
    entry_price = current_row['open']  # Same bar!

# NEW (correct):
if prev_row['Signal'] != 0:
    entry_price = current_row['open']  # Next bar!
```

Now the realistic flow is:
1. Bar N close breaks above OR high → Signal detected
2. Bar N+1 open → Entry executed
3. Entry price matches next bar after breakout (realistic)

## Strategy Performance (Q1 2023)

### Data
- Period: January 2 - March 31, 2023 (3 months)
- Instrument: DAX Index
- Timeframe: 5-minute bars
- Session: 09:00-22:00 CET (main session only)
- Total bars: 9,984 (after dropping NaN)

### Results

**Overall Performance:**
- Initial Capital: $100,000
- Final Equity: $79,673
- Total Return: **-20.33%**
- Max Drawdown: 20.33%
- Sharpe Ratio: -12.25

**Trade Statistics:**
- Total Unique Trades: **18**
- Total Trade Rows: 26 (includes 8 TP1 partial exits)
- Winning Trades: 4
- Losing Trades: 14
- **Win Rate: 22.2%**
- Profit Factor: 0.02

**Risk/Reward:**
- Average Win: $55.11
- Average Loss: $-1,467.67
- **Win/Loss Ratio: 0.04** (winning trades are 1/27th the size of losing trades!)
- Largest Win: $118.92
- Largest Loss: $-2,398.22

**Trade Breakdown:**
- ORB_LONG: 8 trades, 25% win rate, -$8,740 loss
- ORB_SHORT: 9 trades, 22% win rate, -$10,443 loss
- VWAP_LONG: 1 trade, 0% win rate, -$1,145 loss

**Exit Reasons:**
- Stop Loss Only: 9 trades (50%)
- TP1 Hit Then Stop: 8 trades (44%)
- Session End: 1 trade (6%)

### Key Findings

1. **Stops Hit Almost Every Trade**
   - 17 out of 18 trades (94%) hit stop-loss
   - Only 1 trade exited at session end
   - Even when TP1 was hit (8 trades), most ended as net losses

2. **Poor Risk/Reward Profile**
   - Need ~75% win rate to breakeven with 1:27 win/loss ratio
   - Actual win rate was only 22%
   - Mathematically impossible to profit with this combination

3. **Average Holding Time: 39.8 Minutes**
   - Winners held 15-20 minutes on average
   - Losers also exited quickly (stops too tight or entries too poor)

4. **Partial Exit System Not Helping**
   - 8 trades hit TP1 (first target)
   - Of those 8, only 4 ended as net winners
   - Suggests the move to TP2 rarely happens

## Root Cause Analysis

### Why is the Strategy Losing?

1. **Stops Too Tight**
   - ORB stop at OR low/high (or 1× ATR)
   - VWAP stop at 1.5× ATR
   - Momentum stop at 2× ATR
   - DAX average ATR in Q1 2023: ~23 points
   - Getting whipsawed out of positions before they can develop

2. **Targets Too Ambitious**
   - ORB target: 2× OR size
   - VWAP target: 3× ATR (TP2)
   - Momentum target: 4× ATR (TP2)
   - Most moves don't reach these levels before reversing

3. **Entry Quality Issues**
   - ORB entries trigger on ANY close above OR high
   - Many are marginal breakouts that fail immediately
   - No volume confirmation, no momentum confirmation
   - Entering false breakouts

4. **Market Conditions - Q1 2023**
   - May have been a particularly choppy/ranging period
   - Trend-following strategies underperform in ranging markets
   - Need to test on different periods to confirm

## What Worked vs What Didn't

### What Worked ✓
- Backtest infrastructure is solid (after fixing lookahead bias)
- Indicator calculations are correct (VWAP, OR, EMAs, ATR)
- Signal generation logic is clear and testable
- Performance analysis is comprehensive

### What Didn't Work ✗
- Entry quality: Too many false breakouts
- Stop placement: Too tight, getting whipsawed
- Target placement: Too ambitious, rarely reached
- Win rate: 22% far too low for this risk/reward
- Overall strategy concept doesn't work on this data period

## Recommendations

### Option 1: Fix the Current Strategy
To make this approach potentially profitable, would need:

**Tighter Entry Filters:**
- Add volume confirmation (breakout on high volume)
- Add momentum confirmation (strong candle, not marginal break)
- Add trend confirmation (only trade with higher timeframe trend)
- Reduce false breakouts by 50-70%

**Better Stop Placement:**
- Widen stops to 2-3× ATR minimum
- Use structural levels (swing highs/lows) not just ATR
- Give trades room to breathe

**Realistic Targets:**
- Lower TP1 to 1× ATR (instead of current)
- Lower TP2 to 2× ATR (instead of 3-4× ATR)
- Take profits sooner, compound over more trades

**Expected Outcome:** Might achieve 35-40% win rate with 1:2 risk/reward (breakeven to slight profit)

### Option 2: Different Strategy Approach

The institutional ORB + VWAP approach may not suit systematic/algorithmic trading. Consider:

**Alternative Approaches:**
1. **Pure mean-reversion** on DAX (fade extremes, not breakouts)
2. **Market making** (capture bid-ask spread, not directional)
3. **Statistical arbitrage** (DAX vs DAX futures, or DAX vs sector components)
4. **News-based** (trade DAX reaction to news events)

### Option 3: Different Instrument/Market

DAX may not be ideal for retail systematic trading:
- Dominated by institutional HFT
- Wide spreads during main session
- Prone to false breakouts and whipsaws
- Better instruments for retail systematic traders:
  - S&P 500 futures (more trending, institutional favorite)
  - NASDAQ futures (tech-driven, clearer trends)
  - FX majors (EUR/USD, GBP/USD - tight spreads)

### Option 4: Accept Results and Move On

**Reality Check:**
- Not every strategy works on every market/period
- Q1 2023 may simply be a bad period for this approach
- Professional traders have 30-40% of strategies that don't work
- The testing process itself is valuable - we learned what doesn't work

## Technical Improvements Made

### 1. Lookahead Bias Fix (CRITICAL)
- Changed entry from same-bar to next-bar
- Prevents impossible entry prices
- Results now reflect realistic trading

### 2. Compatibility Fixes
- Added `atr_zscore` parameter to position sizing
- Changed stops/targets to return `tp1` and `tp2`
- Added `Regime` column for compatibility
- Added `min_profit_lock_r` config parameter

### 3. Data Handling
- Updated config for available data files
- Adjusted session times to match data
- Proper column mapping and type handling

### 4. Diagnostic Tools
- `diagnose_orb.py` - Analyzes ORB entries and next-bar behavior
- `trace_entry.py` - Traces exact timing of entry vs signal
- Helped identify and confirm the lookahead bias

## Next Steps

1. **Test on Different Time Periods**
   - Try 2020, 2021, 2022, 2024 data
   - Identify if Q1 2023 was anomaly or representative

2. **Test on Different Instruments**
   - Run same strategy on S&P 500, NASDAQ
   - Compare performance across markets

3. **Implement Entry Filters**
   - Add volume/momentum confirmation
   - Reduce signal count but increase quality

4. **Optimize Stop/Target Levels**
   - Run parameter sweep on stop/target multiples
   - Find optimal risk/reward for this approach

5. **Consider Alternative Strategies**
   - Research mean-reversion approaches for DAX
   - Look into statistical arbitrage opportunities

## Conclusion

We successfully:
- ✓ Built professional DAX intraday strategy from scratch
- ✓ Implemented comprehensive backtest framework
- ✓ Discovered and fixed critical lookahead bias
- ✓ Generated realistic performance results
- ✓ Identified why strategy doesn't work

The strategy shows a **22% win rate with 1:27 risk/reward**, resulting in **-20% return** over 3 months. This is not profitable and needs significant modifications or should be abandoned in favor of alternative approaches.

The most valuable outcome: We now have a **correct, bias-free backtest engine** and understand what doesn't work on DAX, which is just as important as finding what does work.
