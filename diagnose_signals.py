"""
Diagnostic Tool - Analyze why signals aren't being generated
"""

import pandas as pd
import yaml
from indicators import calculate_all_indicators
from strategy import ARIStrategy


def diagnose_signals(config_path='config.yaml'):
    """Analyze signal generation and filter conditions"""

    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Load data
    filepath = config['data']['filepath']
    df = pd.read_csv(filepath)
    df[config['data']['date_column']] = pd.to_datetime(df[config['data']['date_column']])
    df = df.set_index(config['data']['date_column'])

    # Rename columns
    col_map = config['data']['ohlcv_columns']
    df = df.rename(columns={
        col_map['open']: 'open',
        col_map['high']: 'high',
        col_map['low']: 'low',
        col_map['close']: 'close',
        col_map['volume']: 'volume'
    })
    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Calculate indicators
    print("Calculating indicators...")
    data = calculate_all_indicators(df, config)
    data = data.dropna()

    print(f"\nTotal bars after indicators: {len(data)}\n")

    # Initialize strategy
    strategy = ARIStrategy(config)

    # Analyze regime distribution
    print("=" * 80)
    print("REGIME ANALYSIS")
    print("=" * 80)

    regime_counts = {}
    for i in range(len(data)):
        row = data.iloc[i]
        regime = strategy.detect_regime(row)
        regime_counts[regime] = regime_counts.get(regime, 0) + 1

    total = sum(regime_counts.values())
    print(f"\nRegime Distribution:")
    for regime, count in regime_counts.items():
        pct = (count / total) * 100
        print(f"  {regime:20s}: {count:5d} bars ({pct:5.1f}%)")

    # Analyze individual condition pass rates
    print("\n" + "=" * 80)
    print("MOMENTUM LONG CONDITION BREAKDOWN")
    print("=" * 80)

    momentum_conditions = {
        'ADX > threshold': 0,
        'SMA(50) > SMA(200)': 0,
        'RSI > 50 and < 70': 0,
        'Close > Rolling High': 0,
        'Volume > Average': 0,
        'ATR Expansion': 0,
        'Time Filter OK': 0,
        'ALL CONDITIONS': 0
    }

    for i in range(1, len(data)):
        row = data.iloc[i]
        prev_row = data.iloc[i-1]
        timestamp = data.index[i]

        params = config['strategy']['momentum']

        # Check each condition
        if row['ADX'] > config['strategy']['adx_momentum_threshold']:
            momentum_conditions['ADX > threshold'] += 1

        if row['SMA_50'] > row['SMA_200']:
            momentum_conditions['SMA(50) > SMA(200)'] += 1

        if row['RSI'] > params['rsi_min'] and row['RSI'] < 70:
            momentum_conditions['RSI > 50 and < 70'] += 1

        if row['close'] > prev_row['Rolling_High']:
            momentum_conditions['Close > Rolling High'] += 1

        if row['volume'] > row['Volume_MA']:
            momentum_conditions['Volume > Average'] += 1

        if row['ATR'] > row['ATR_MA'] * params['atr_expansion_threshold']:
            momentum_conditions['ATR Expansion'] += 1

        if strategy.is_entry_allowed(timestamp):
            momentum_conditions['Time Filter OK'] += 1

        # Check if ALL conditions pass
        if strategy.momentum_long_signal(row, prev_row) and strategy.is_entry_allowed(timestamp):
            momentum_conditions['ALL CONDITIONS'] += 1

    print(f"\nCondition Pass Rates (out of {len(data)-1} bars):")
    for condition, count in momentum_conditions.items():
        pct = (count / (len(data)-1)) * 100
        bar = '█' * int(pct / 2)
        print(f"  {condition:25s}: {count:5d} ({pct:5.1f}%) {bar}")

    # Mean Reversion Analysis
    print("\n" + "=" * 80)
    print("MEAN-REVERSION LONG CONDITION BREAKDOWN")
    print("=" * 80)

    mr_conditions = {
        'ADX < threshold': 0,
        'Price > SMA(200)': 0,
        'RSI2 < 10': 0,
        'Price < BB Lower': 0,
        'Bullish Candle': 0,
        'Time Filter OK': 0,
        'ALL CONDITIONS': 0
    }

    for i in range(1, len(data)):
        row = data.iloc[i]
        prev_row = data.iloc[i-1]
        timestamp = data.index[i]

        params = config['strategy']['mean_reversion']

        if row['ADX'] < config['strategy']['adx_ranging_threshold']:
            mr_conditions['ADX < threshold'] += 1

        if row['Price_Above_MA200']:
            mr_conditions['Price > SMA(200)'] += 1

        if row['RSI2'] < params['rsi2_oversold']:
            mr_conditions['RSI2 < 10'] += 1

        if row['close'] < row['BB_Lower']:
            mr_conditions['Price < BB Lower'] += 1

        if row['Bullish_Candle']:
            mr_conditions['Bullish Candle'] += 1

        if strategy.is_entry_allowed(timestamp):
            mr_conditions['Time Filter OK'] += 1

        if strategy.mean_reversion_long_signal(row, prev_row) and strategy.is_entry_allowed(timestamp):
            mr_conditions['ALL CONDITIONS'] += 1

    print(f"\nCondition Pass Rates (out of {len(data)-1} bars):")
    for condition, count in mr_conditions.items():
        pct = (count / (len(data)-1)) * 100
        bar = '█' * int(pct / 2)
        print(f"  {condition:25s}: {count:5d} ({pct:5.1f}%) {bar}")

    # ADX distribution
    print("\n" + "=" * 80)
    print("ADX DISTRIBUTION")
    print("=" * 80)

    adx_values = data['ADX'].dropna()
    print(f"\nADX Statistics:")
    print(f"  Mean:   {adx_values.mean():.2f}")
    print(f"  Median: {adx_values.median():.2f}")
    print(f"  Min:    {adx_values.min():.2f}")
    print(f"  Max:    {adx_values.max():.2f}")
    print(f"  25th %: {adx_values.quantile(0.25):.2f}")
    print(f"  75th %: {adx_values.quantile(0.75):.2f}")

    print(f"\nCurrent thresholds:")
    print(f"  Momentum threshold: {config['strategy']['adx_momentum_threshold']}")
    print(f"  Ranging threshold:  {config['strategy']['adx_ranging_threshold']}")

    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    print("\nBased on the analysis above:")

    if momentum_conditions['ALL CONDITIONS'] == 0:
        print("\n⚠️  NO MOMENTUM SIGNALS GENERATED")
        print("   Possible fixes:")
        print("   1. Lower ADX momentum threshold (try 20 instead of 25)")
        print("   2. Reduce ATR expansion requirement (try 1.1 instead of 1.2)")
        print("   3. Lower RSI min (try 45 instead of 50)")

    if mr_conditions['ALL CONDITIONS'] == 0:
        print("\n⚠️  NO MEAN-REVERSION SIGNALS GENERATED")
        print("   Possible fixes:")
        print("   1. Raise ADX ranging threshold (try 25 instead of 20)")
        print("   2. Increase RSI2 threshold (try 15 instead of 10)")
        print("   3. Relax BB requirement")

    if adx_values.mean() < config['strategy']['adx_momentum_threshold']:
        print(f"\n⚠️  AVERAGE ADX ({adx_values.mean():.1f}) < MOMENTUM THRESHOLD ({config['strategy']['adx_momentum_threshold']})")
        print(f"   Recommendation: Lower momentum threshold to {int(adx_values.quantile(0.75))}")

    print("\n" + "=" * 80)
    print("\nTo apply fixes, edit config.yaml and re-run backtest")
    print("Or use real market data which will have more realistic regime transitions")
    print("=" * 80)


if __name__ == "__main__":
    diagnose_signals()
