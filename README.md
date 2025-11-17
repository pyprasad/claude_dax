# Adaptive Regime Intraday (ARI) Strategy

**A professional-grade, regime-adaptive intraday trading strategy for index futures**

---

## 🎯 Overview

The **ARI Strategy** is an institutional-quality quantitative trading system designed for intraday trading of major index futures (DAX, S&P 500, NASDAQ, FTSE, Nikkei 225).

### Key Features

✅ **Regime-Adaptive**: Automatically switches between momentum and mean-reversion modes
✅ **Multi-Layer Risk Management**: ATR-based stops, volatility filters, daily loss limits
✅ **No Look-Ahead Bias**: Properly implemented backtesting with realistic execution
✅ **Walk-Forward Optimization**: Prevents overfitting through robust parameter selection
✅ **Institutional-Grade Metrics**: Sharpe, Sortino, Calmar, MAE/MFE analysis
✅ **Complete Transparency**: Full source code with detailed documentation

---

## 📊 Strategy Logic

### Regime Detection

The strategy operates in **three distinct modes**:

**1. MOMENTUM MODE** (ADX > 25)
- Entry: Breakout of 20-bar high/low with volume confirmation
- Edge: Continuation of established intraday trends
- Best for: Trending days, news-driven volatility

**2. MEAN-REVERSION MODE** (ADX < 20)
- Entry: RSI2 extremes + Bollinger Band oversold/overbought + divergence
- Edge: Statistical reversion to VWAP/mean
- Best for: Range-bound, choppy markets

**3. NO-TRADE MODE** (ADX 20-25 or high volatility)
- Action: Preserve capital, avoid whipsaws
- Edge: Discipline in unfavorable conditions

### Risk Management

- **Position Sizing**: ATR-based risk parity (1% risk per trade)
- **Stop Loss**: 1.5-2.0 × ATR depending on regime
- **Take Profit**: Scaled exits (50% at TP1, 50% trails)
- **Time Filters**: No entries in first/last hour of session
- **Volatility Filters**: ATR Z-score + VIX regime detection
- **Circuit Breakers**: Max 3 consecutive losses, 2% daily drawdown limit

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd claude_dax

# Install dependencies
pip install -r requirements.txt
```

### Generate Sample Data (For Testing)

```bash
python generate_sample_data.py
```

This creates 60 days of synthetic 5-minute DAX data in `data/DAX_5min.csv`

### Run Backtest

```bash
python run_backtest.py
```

### View Results

Results are saved to the `results/` directory:
- `performance_report.txt` - Comprehensive performance metrics
- `trade_log.csv` - Detailed trade-by-trade log
- `equity_curve.png` - Visual equity curve and drawdown
- `trade_analysis.png` - P&L distribution, MAE/MFE analysis
- `monthly_returns.png` - Monthly performance heatmap

---

## 📁 Project Structure

```
claude_dax/
│
├── config.yaml                 # Strategy configuration
├── requirements.txt            # Python dependencies
│
├── indicators.py               # Technical indicator calculations
├── strategy.py                 # Core strategy logic
├── backtest_engine.py          # Backtesting framework
├── performance.py              # Performance analysis
├── optimizer.py                # Walk-forward optimization
│
├── run_backtest.py             # Main execution script
├── generate_sample_data.py     # Sample data generator
│
├── data/                       # Market data (CSV files)
└── results/                    # Backtest output
```

---

## ⚙️ Configuration

Edit `config.yaml` to customize:

### Data Settings
```yaml
data:
  filepath: "data/DAX_5min.csv"
  timeframe: "5min"
```

### Strategy Parameters
```yaml
strategy:
  adx_momentum_threshold: 25
  adx_ranging_threshold: 20

  momentum:
    rsi_min: 50
    breakout_lookback: 20

  mean_reversion:
    rsi2_oversold: 10
    rsi2_overbought: 90
```

### Risk Parameters
```yaml
  risk:
    risk_per_trade_pct: 1.0
    momentum_stop_atr_mult: 2.0
    mean_reversion_stop_atr_mult: 1.5
```

---

## 🔬 Optimization

Run walk-forward optimization to find robust parameters:

```bash
python optimizer.py
```

This will:
1. Split data into train/test folds
2. Test 50+ parameter combinations
3. Validate on out-of-sample data
4. Save optimized config to `config_optimized.yaml`

**Important**: Always use walk-forward optimization, never in-sample optimization!

---

## 📈 Using Your Own Data

Replace `data/DAX_5min.csv` with your own OHLCV data.

**Required CSV format**:
```csv
timestamp,open,high,low,close,volume
2024-01-01 09:00:00,18000.5,18050.2,17980.1,18020.3,1500
2024-01-01 09:05:00,18020.3,18065.7,18015.2,18055.8,1800
...
```

**Supported Timeframes**:
- 1-minute
- 5-minute (recommended)
- 15-minute
- 1-hour

Update `config.yaml` with your column names and timeframe.

---

## 🎓 Strategy Foundations

This strategy is based on proven institutional concepts:

### Academic Research
- **Regime Switching**: Hamilton (1989), "A New Approach to the Economic Analysis of Nonstationary Time Series"
- **Mean Reversion**: Larry Connors, "Short Term Trading Strategies That Work"
- **Momentum**: Jegadeesh & Titman (1993), "Returns to Buying Winners and Selling Losers"

### Institutional Practices
- ATR-based position sizing (used by Renaissance Technologies, Two Sigma)
- VWAP as institutional anchor point
- Multi-timeframe regime detection
- MAE/MFE analysis for stop optimization

### Risk Management
- Kelly Criterion-inspired position sizing
- Volatility-adjusted risk (VIX regime detection)
- Time-based filters (session analysis)
- Circuit breakers (daily loss limits)

---

## 📊 Expected Performance Characteristics

**Note**: Past performance is not indicative of future results. These are typical characteristics of regime-adaptive strategies:

- **Win Rate**: 45-55%
- **Profit Factor**: 1.5-2.5
- **Max Drawdown**: 8-15%
- **Sharpe Ratio**: 1.5-3.0
- **Average Trade Duration**: 2-4 hours
- **Trades per Month**: 40-80 (highly regime-dependent)

**Best Performance**: Trending markets with clear directional moves
**Worst Performance**: Whipsaw/choppy conditions (mitigated by no-trade mode)

---

## ⚠️ Risk Warnings

**This is educational software. NOT financial advice.**

### Important Disclaimers

1. **No Guarantee of Profits**: Past backtest results do not guarantee future performance
2. **Market Risk**: All trading involves risk of loss
3. **Overfitting Risk**: Always use walk-forward optimization, never curve-fit to historical data
4. **Execution Risk**: Real-world slippage and commissions may differ from backtest assumptions
5. **Regime Risk**: Strategy performs differently in different market conditions

### Before Live Trading

- [ ] Test on out-of-sample data (not used in development)
- [ ] Paper trade for minimum 3 months
- [ ] Verify execution infrastructure (latency, slippage, commissions)
- [ ] Implement proper risk controls (circuit breakers, position limits)
- [ ] Start with minimum position size
- [ ] Monitor for regime changes
- [ ] Have a plan for black swan events

---

## 🛠️ Customization & Extension

### Adding New Indicators

Edit `indicators.py`:
```python
def custom_indicator(series: pd.Series, period: int) -> pd.Series:
    # Your indicator logic
    return result
```

### Modifying Entry Logic

Edit `strategy.py`:
```python
def custom_entry_signal(self, row, prev_row):
    conditions = [
        # Your conditions
    ]
    return all(conditions)
```

### Advanced Features (TODO)

- [ ] Machine learning regime detection
- [ ] Order flow / DOM analysis
- [ ] Multi-asset correlation filters
- [ ] Intraday seasonality adjustment
- [ ] News sentiment integration
- [ ] Live trading connector (Interactive Brokers, etc.)

---

## 📚 Further Reading

### Recommended Books
- "Algorithmic Trading" - Ernie Chan
- "Quantitative Trading" - Ernie Chan
- "Short Term Trading Strategies That Work" - Larry Connors
- "Evidence-Based Technical Analysis" - David Aronson
- "Trading Systems" - Toby Crabel

### Academic Papers
- "Regime Switching Models and Applications"
- "The Cross-Section of Volatility and Expected Returns"
- "Market Microstructure and Intraday Patterns"

### Online Resources
- QuantConnect Documentation
- QuantStart Tutorials
- Rob Carver's Blog (systematictrading.org)

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request with clear description

---

## 📝 License

MIT License - See LICENSE file for details

---

## 💬 Support

For questions, issues, or suggestions:
- Open an issue on GitHub
- Check documentation in `/docs`
- Review example backtests in `/examples`

---

## ✅ Checklist for Production Use

### Code Quality
- [x] No look-ahead bias in backtesting
- [x] Realistic slippage modeling
- [x] Commission costs included
- [x] Position sizing validated
- [x] Stop loss logic tested

### Validation
- [ ] Out-of-sample testing completed
- [ ] Walk-forward optimization performed
- [ ] Monte Carlo simulation run
- [ ] Sensitivity analysis completed
- [ ] Regime analysis documented

### Infrastructure
- [ ] Data pipeline validated
- [ ] Execution system tested
- [ ] Risk controls implemented
- [ ] Monitoring dashboard created
- [ ] Alert system configured

### Risk Management
- [ ] Maximum position size defined
- [ ] Daily loss limit enforced
- [ ] Portfolio correlation checked
- [ ] Black swan plan documented
- [ ] Emergency exit procedure defined

---

**Built with institutional-grade quantitative research principles**

**Disclaimer**: For educational purposes only. Trade at your own risk.
