"""
Generate Sample Market Data for Testing
Creates realistic synthetic OHLCV data with different market regimes
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os


class SyntheticDataGenerator:
    """Generate realistic synthetic market data"""

    def __init__(self, initial_price: float = 18000, seed: int = 42):
        self.initial_price = initial_price
        np.random.seed(seed)

    def generate_regime_data(self, num_bars: int, regime: str, current_price: float) -> pd.DataFrame:
        """
        Generate data for a specific market regime

        Args:
            num_bars: Number of bars to generate
            regime: 'trending_up', 'trending_down', 'ranging', 'volatile'
            current_price: Starting price

        Returns:
            DataFrame with OHLCV data
        """
        data = []
        price = current_price

        for i in range(num_bars):
            if regime == 'trending_up':
                # Uptrend: positive drift, moderate volatility
                drift = np.random.uniform(0.0005, 0.002)
                volatility = np.random.uniform(0.003, 0.008)

            elif regime == 'trending_down':
                # Downtrend: negative drift, higher volatility
                drift = np.random.uniform(-0.002, -0.0005)
                volatility = np.random.uniform(0.004, 0.010)

            elif regime == 'ranging':
                # Range-bound: minimal drift, low volatility
                drift = np.random.uniform(-0.0003, 0.0003)
                volatility = np.random.uniform(0.002, 0.005)

            else:  # volatile
                # High volatility: random drift, high volatility
                drift = np.random.uniform(-0.003, 0.003)
                volatility = np.random.uniform(0.008, 0.015)

            # Generate returns
            returns = drift + volatility * np.random.randn()

            # Calculate new close
            close = price * (1 + returns)

            # Generate high/low around close
            high_offset = abs(np.random.randn() * volatility * price)
            low_offset = abs(np.random.randn() * volatility * price)

            high = close + high_offset
            low = close - low_offset

            # Ensure high > low
            if high < low:
                high, low = low, high

            # Generate open (somewhere between previous close and current close)
            open_price = price + (close - price) * np.random.uniform(0, 0.5)

            # Ensure OHLC consistency
            high = max(high, open_price, close)
            low = min(low, open_price, close)

            # Generate volume (with some randomness)
            base_volume = 1000
            if regime == 'volatile':
                base_volume = 2000
            elif regime == 'ranging':
                base_volume = 800

            volume = int(base_volume * (1 + np.random.uniform(-0.3, 0.5)))

            data.append({
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })

            # Update price for next bar
            price = close

        return pd.DataFrame(data), price

    def generate_full_dataset(self, days: int = 60, bars_per_day: int = 84) -> pd.DataFrame:
        """
        Generate full dataset with mixed regimes

        Args:
            days: Number of trading days
            bars_per_day: Bars per day (84 for 5-min bars in ~7hr session)

        Returns:
            DataFrame with timestamp and OHLCV
        """
        print("Generating synthetic market data...")

        # Define regime sequence (mix of market conditions)
        total_bars = days * bars_per_day
        regime_length = total_bars // 8  # Switch regime every ~7-8 days

        regimes = [
            'trending_up',
            'ranging',
            'trending_up',
            'volatile',
            'trending_down',
            'ranging',
            'trending_up',
            'ranging'
        ]

        all_data = []
        current_price = self.initial_price
        current_time = datetime(2024, 1, 1, 9, 0)  # Start date

        for regime in regimes:
            regime_data, current_price = self.generate_regime_data(
                regime_length,
                regime,
                current_price
            )

            # Add timestamps
            timestamps = []
            temp_time = current_time
            for _ in range(len(regime_data)):
                timestamps.append(temp_time)
                temp_time += timedelta(minutes=5)

                # Skip weekends and overnight
                if temp_time.hour >= 22:  # End of session
                    temp_time = temp_time.replace(hour=9, minute=0)
                    temp_time += timedelta(days=1)

                    # Skip weekends
                    while temp_time.weekday() >= 5:
                        temp_time += timedelta(days=1)

            regime_data['timestamp'] = timestamps
            all_data.append(regime_data)
            current_time = temp_time

        # Combine all regimes
        full_data = pd.concat(all_data, ignore_index=True)

        print(f"Generated {len(full_data)} bars")
        print(f"Date range: {full_data['timestamp'].min()} to {full_data['timestamp'].max()}")
        print(f"Price range: {full_data['close'].min():.2f} to {full_data['close'].max():.2f}")

        return full_data

    def add_realistic_patterns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add realistic intraday patterns (opening gaps, lunch lulls, etc.)"""
        data = data.copy()

        for idx in range(1, len(data)):
            current_time = data.loc[idx, 'timestamp']
            prev_time = data.loc[idx - 1, 'timestamp']

            # Opening gap (new day)
            if current_time.date() != prev_time.date():
                gap_size = np.random.uniform(-0.005, 0.008)  # Slight upward bias
                data.loc[idx, 'open'] = data.loc[idx - 1, 'close'] * (1 + gap_size)
                data.loc[idx, 'close'] = data.loc[idx, 'open'] * (1 + np.random.uniform(-0.002, 0.002))
                data.loc[idx, 'high'] = max(data.loc[idx, 'open'], data.loc[idx, 'close']) * (1 + abs(np.random.randn() * 0.003))
                data.loc[idx, 'low'] = min(data.loc[idx, 'open'], data.loc[idx, 'close']) * (1 - abs(np.random.randn() * 0.003))

            # Lunch hour (12:00-13:00) - lower volume
            if 12 <= current_time.hour < 13:
                data.loc[idx, 'volume'] = int(data.loc[idx, 'volume'] * 0.6)

            # First hour - higher volume
            if current_time.hour == 9:
                data.loc[idx, 'volume'] = int(data.loc[idx, 'volume'] * 1.5)

            # Last hour - moderate increase
            if current_time.hour >= 21:
                data.loc[idx, 'volume'] = int(data.loc[idx, 'volume'] * 1.2)

        return data


def main():
    """Generate sample data for testing"""
    print("="*80)
    print("SYNTHETIC DATA GENERATOR")
    print("="*80)
    print()

    # Create data directory
    os.makedirs('data', exist_ok=True)

    # Generate data
    generator = SyntheticDataGenerator(initial_price=18000)

    # Generate 60 days of 5-minute data
    data = generator.generate_full_dataset(days=60, bars_per_day=84)

    # Add realistic patterns
    data = generator.add_realistic_patterns(data)

    # Reorder columns
    data = data[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    # Save to CSV
    output_path = 'data/DAX_5min.csv'
    data.to_csv(output_path, index=False)

    print(f"\nSample data saved to {output_path}")
    print("\nData statistics:")
    print(f"  Total bars: {len(data)}")
    print(f"  Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
    print(f"  Price range: {data['close'].min():.2f} to {data['close'].max():.2f}")
    print(f"  Avg volume: {data['volume'].mean():.0f}")
    print()
    print("You can now run the backtest:")
    print("  python run_backtest.py")
    print()


if __name__ == "__main__":
    main()
