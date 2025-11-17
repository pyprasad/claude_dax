"""
Generate MORE REALISTIC Market Data
Includes actual intraday patterns, momentum, and mean-reversion setups
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_realistic_intraday_data(days=90, initial_price=18000):
    """
    Generate realistic intraday data with actual tradable patterns
    """
    np.random.seed(42)

    data = []
    current_price = initial_price
    current_date = datetime(2023, 1, 2, 9, 0)  # Start on a Monday

    print("Generating realistic market data with tradable patterns...")

    for day in range(days):
        # Skip weekends
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue

        print(f"  Generating day {day+1}/{days}...", end='\r')

        # Determine day regime (each day has a character)
        day_type = np.random.choice(['trending_up', 'trending_down', 'ranging', 'volatile'],
                                   p=[0.25, 0.15, 0.45, 0.15])

        # Opening gap
        gap = np.random.uniform(-0.008, 0.012) if day > 0 else 0
        session_open = current_price * (1 + gap)
        current_price = session_open

        # Generate full trading session (09:00 - 22:00 = 13 hours = 156 5-min bars)
        session_bars = 156

        for bar in range(session_bars):
            hour = 9 + (bar * 5) // 60
            minute = (bar * 5) % 60
            timestamp = current_date.replace(hour=hour, minute=minute)

            # Intraday patterns
            if bar < 12:  # First hour - higher volatility
                volatility = 0.0015
                drift_mult = 1.5
            elif hour == 12:  # Lunch hour - lower volatility
                volatility = 0.0005
                drift_mult = 0.3
            elif bar > session_bars - 24:  # Last 2 hours - moderate volatility
                volatility = 0.001
                drift_mult = 0.8
            else:  # Mid-day
                volatility = 0.001
                drift_mult = 1.0

            # Create tradable patterns based on day type
            if day_type == 'trending_up':
                # Create breakout opportunities
                if bar % 30 == 0:  # Every 2.5 hours, create a breakout setup
                    # Consolidation then breakout
                    drift = 0.002 * drift_mult
                    vol = volatility * 0.5
                else:
                    drift = 0.0008 * drift_mult
                    vol = volatility

            elif day_type == 'trending_down':
                if bar % 30 == 0:
                    drift = -0.002 * drift_mult
                    vol = volatility * 0.5
                else:
                    drift = -0.0008 * drift_mult
                    vol = volatility

            elif day_type == 'ranging':
                # Create mean-reversion setups
                # Oscillate around VWAP
                distance_from_open = current_price - session_open
                mean_revert_force = -distance_from_open / session_open * 0.001
                drift = mean_revert_force + np.random.uniform(-0.0003, 0.0003)
                vol = volatility * 0.8

            else:  # volatile
                drift = np.random.uniform(-0.003, 0.003) * drift_mult
                vol = volatility * 2.0

            # Generate OHLC
            returns = drift + vol * np.random.randn()
            close = current_price * (1 + returns)

            # Add intrabar volatility
            intrabar_range = abs(np.random.randn() * vol * current_price)
            high = max(current_price, close) + intrabar_range * np.random.uniform(0.3, 1.0)
            low = min(current_price, close) - intrabar_range * np.random.uniform(0.3, 1.0)
            open_price = current_price + (close - current_price) * np.random.uniform(-0.2, 0.5)

            # Ensure OHLC consistency
            high = max(high, open_price, close)
            low = min(low, open_price, close)

            # Volume patterns
            if bar < 12:  # Opening hour
                base_volume = 2000
            elif hour == 12:  # Lunch
                base_volume = 600
            elif bar > session_bars - 24:  # Closing hours
                base_volume = 1500
            else:
                base_volume = 1000

            # Add volume spikes on breakouts/reversals
            if day_type in ['trending_up', 'trending_down'] and bar % 30 == 0:
                base_volume *= 2.5

            volume = int(base_volume * (1 + np.random.uniform(-0.4, 0.8)))

            data.append({
                'timestamp': timestamp,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })

            current_price = close

        # Move to next day
        current_date += timedelta(days=1)

    print(f"\n  Generated {len(data)} bars")

    df = pd.DataFrame(data)
    return df


def main():
    print("=" * 80)
    print("REALISTIC DATA GENERATOR")
    print("=" * 80)
    print()

    # Generate 90 days of data
    df = generate_realistic_intraday_data(days=90, initial_price=18000)

    # Save
    import os
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/DAX_5min_realistic.csv', index=False)

    print(f"\n✓ Realistic data saved to data/DAX_5min_realistic.csv")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Price range: {df['close'].min():.2f} to {df['close'].max():.2f}")
    print(f"  Total bars: {len(df)}")
    print()
    print("To use this data:")
    print("  1. Update config.yaml: filepath: 'data/DAX_5min_realistic.csv'")
    print("  2. Run: python run_backtest.py config.yaml")
    print()


if __name__ == "__main__":
    main()
