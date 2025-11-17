"""
Diagnose why ORB strategy is losing
"""
import pandas as pd
import yaml

# Load data and config
with open('config_professional.yaml', 'r') as f:
    config = yaml.safe_load(f)

from indicators_pro import calculate_professional_indicators
from strategy_pro import ProfessionalDAXStrategy

# Load data
df = pd.read_csv('data/DAX_5min_realistic.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')
df = df.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'})
df = df[['open', 'high', 'low', 'close', 'volume']]

# Calculate indicators
data = calculate_professional_indicators(df, config)
data = data.dropna()

# Generate signals
strategy = ProfessionalDAXStrategy(config)
signals = strategy.generate_signals(data)

# Look at first ORB signal on 2023-01-04
jan4_data = signals[signals.index.date == pd.to_datetime('2023-01-04').date()]

print("=== 2023-01-04 Analysis ===")
print(f"\nSession start: {jan4_data.index[0]}")
print(f"Number of bars: {len(jan4_data)}")

# Show opening range period
or_period = jan4_data[jan4_data['in_or'] == True]
print(f"\nOpening Range (first 30 min):")
print(f"  Start: {or_period.index[0]}")
print(f"  End: {or_period.index[-1]}")
print(f"  OR High: {or_period.iloc[-1]['or_high']:.2f}")
print(f"  OR Low: {or_period.iloc[-1]['or_low']:.2f}")
print(f"  OR Size: {or_period.iloc[-1]['or_size']:.2f}")
print(f"  ATR: {or_period.iloc[-1]['ATR']:.2f}")

# Find ORB signals
orb_signals = jan4_data[jan4_data['Signal'] != 0]
print(f"\nORB Signals on 2023-01-04: {len(orb_signals)}")

for idx, row in orb_signals.iterrows():
    print(f"\n{idx} - {row['Signal_Type']} Signal:")
    print(f"  Entry Price (open next bar): {row['open']:.2f}")
    print(f"  Close when signal: {row['close']:.2f}")
    print(f"  OR High: {row['or_high']:.2f}")
    print(f"  OR Low: {row['or_low']:.2f}")
    print(f"  ATR: {row['ATR']:.2f}")
    print(f"  EMA_20: {row['EMA_20']:.2f}")

    # Show what happened next (next 30 bars)
    signal_idx = signals.index.get_loc(idx)
    next_30 = signals.iloc[signal_idx:signal_idx+30]

    print(f"  Next 30 bars:")
    print(f"    High: {next_30['high'].max():.2f}")
    print(f"    Low: {next_30['low'].min():.2f}")
    print(f"    Range: {next_30['high'].max() - next_30['low'].min():.2f}")

# Check if data looks realistic
print(f"\n=== Data Quality Check ===")
print(f"Price range on 2023-01-04: {jan4_data['low'].min():.2f} - {jan4_data['high'].max():.2f}")
print(f"Average ATR: {jan4_data['ATR'].mean():.2f}")
print(f"Average volume: {jan4_data['volume'].mean():.0f}")
