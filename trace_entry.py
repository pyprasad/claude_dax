"""Trace exact entry timing"""
import pandas as pd
import yaml

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

# Find first signal
first_signal_idx = signals[signals['Signal'] != 0].index[0]
print(f"First signal timestamp: {first_signal_idx}")
print(f"Signal type: {signals.loc[first_signal_idx, 'Signal_Type']}")
print()

# Get this bar and surrounding bars
signal_loc = signals.index.get_loc(first_signal_idx)
prev_bar = signals.iloc[signal_loc - 1]
signal_bar = signals.iloc[signal_loc]
next_bar = signals.iloc[signal_loc + 1]

print("Previous bar (09:25):")
print(f"  Open: {prev_bar['open']:.2f}, High: {prev_bar['high']:.2f}, Low: {prev_bar['low']:.2f}, Close: {prev_bar['close']:.2f}")
print(f"  OR High: {prev_bar['or_high']:.2f}")
print()

print("Signal bar (09:30) - signal detected here:")
print(f"  Open: {signal_bar['open']:.2f}, High: {signal_bar['high']:.2f}, Low: {signal_bar['low']:.2f}, Close: {signal_bar['close']:.2f}")
print(f"  OR High: {signal_bar['or_high']:.2f}")
print(f"  Close > OR High? {signal_bar['close'] > signal_bar['or_high']}")
print()

print("Next bar (09:35) - should entry be here?:")
print(f"  Open: {next_bar['open']:.2f}, High: {next_bar['high']:.2f}, Low: {next_bar['low']:.2f}, Close: {next_bar['close']:.2f}")
print()

print("Trade log shows entry at 09:30:00 with price 15949.56")
print(f"This matches signal_bar open ({signal_bar['open']:.2f})")
print()
print("PROBLEM: Signal detected based on 09:30 close (15966.17)")
print("         But entry is at 09:30 open (15938.74) - impossible in real trading!")
print("         Open happens BEFORE close within the same bar")
