"""
Main Backtest Execution Script
Runs the full ARI strategy backtest
"""

import pandas as pd
import numpy as np
import yaml
import sys
import os
from datetime import datetime

from indicators import calculate_all_indicators
from strategy import ARIStrategy
from backtest_engine import BacktestEngine
from performance import PerformanceAnalyzer


def load_config(config_path: str = 'config.yaml') -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_data(config: dict) -> pd.DataFrame:
    """
    Load OHLCV data from CSV

    Expected CSV format:
    timestamp,open,high,low,close,volume
    2024-01-01 09:00:00,18000.5,18050.2,17980.1,18020.3,1500
    ...
    """
    filepath = config['data']['filepath']

    if not os.path.exists(filepath):
        print(f"ERROR: Data file not found: {filepath}")
        print("\nPlease provide a CSV file with the following format:")
        print("timestamp,open,high,low,close,volume")
        print("2024-01-01 09:00:00,18000.5,18050.2,17980.1,18020.3,1500")
        print("...")
        print("\nYou can use any timeframe data (1min, 5min, 15min, etc.)")
        sys.exit(1)

    print(f"Loading data from {filepath}...")

    # Read CSV
    df = pd.read_csv(filepath)

    # Parse timestamp
    date_col = config['data']['date_column']
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col)

    # Rename columns to standard names
    col_map = config['data']['ohlcv_columns']
    df = df.rename(columns={
        col_map['open']: 'open',
        col_map['high']: 'high',
        col_map['low']: 'low',
        col_map['close']: 'close',
        col_map['volume']: 'volume'
    })

    # Keep only OHLCV
    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Remove any duplicates and sort
    df = df[~df.index.duplicated(keep='first')]
    df = df.sort_index()

    print(f"Loaded {len(df)} bars")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    print(f"Timeframe: {config['data']['timeframe']}")

    return df


def validate_data(df: pd.DataFrame) -> bool:
    """Validate data quality"""
    print("\nValidating data...")

    # Check for missing values
    missing = df.isnull().sum()
    if missing.any():
        print("WARNING: Missing values detected:")
        print(missing[missing > 0])
        return False

    # Check for negative prices
    if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
        print("ERROR: Negative or zero prices detected")
        return False

    # Check high >= low
    if (df['high'] < df['low']).any():
        print("ERROR: High < Low detected in some bars")
        return False

    # Check volume
    if (df['volume'] < 0).any():
        print("ERROR: Negative volume detected")
        return False

    print("Data validation passed ✓")
    return True


def main():
    """Main execution function"""
    print("=" * 80)
    print("ADAPTIVE REGIME INTRADAY (ARI) STRATEGY - BACKTEST")
    print("=" * 80)
    print()

    # Load configuration (allow command line override)
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'
    print(f"Loading configuration from {config_file}...")
    config = load_config(config_file)
    print("Configuration loaded ✓")
    print()

    # Load data
    data = load_data(config)

    # Validate data
    if not validate_data(data):
        print("\nData validation failed. Please fix data issues and try again.")
        sys.exit(1)

    # Calculate indicators
    print("\nCalculating technical indicators...")
    data_with_indicators = calculate_all_indicators(data, config)
    print(f"Calculated {len([col for col in data_with_indicators.columns if col not in data.columns])} indicators ✓")

    # Drop initial NaN rows (from indicator calculation)
    initial_length = len(data_with_indicators)
    data_with_indicators = data_with_indicators.dropna()
    dropped = initial_length - len(data_with_indicators)
    print(f"Dropped {dropped} initial bars with NaN values")
    print(f"Using {len(data_with_indicators)} bars for backtest")
    print()

    # Initialize strategy
    print("Initializing strategy...")
    strategy = ARIStrategy(config)
    print("Strategy initialized ✓")
    print()

    # Generate signals
    print("Generating trading signals...")
    signals = strategy.generate_signals(data_with_indicators)
    num_signals = (signals['Signal'] != 0).sum()
    print(f"Generated {num_signals} trading signals ✓")
    print()

    # Show signal breakdown
    if num_signals > 0:
        signal_counts = signals[signals['Signal'] != 0]['Signal_Type'].value_counts()
        print("Signal breakdown:")
        for signal_type, count in signal_counts.items():
            print(f"  {signal_type}: {count}")
        print()

    # Run backtest
    print("Running backtest simulation...")
    print("-" * 80)
    backtest = BacktestEngine(config)
    results = backtest.run_backtest(signals, strategy)
    print("-" * 80)
    print()

    # Check if backtest produced results
    if 'error' in results:
        print(f"ERROR: {results['error']}")
        sys.exit(1)

    # Analyze performance
    print("Analyzing performance...")
    analyzer = PerformanceAnalyzer(results)

    # Print performance report
    print()
    report = analyzer.print_performance_report()
    print(report)

    # Save results
    print("\nSaving results...")
    analyzer.save_results('results')

    print()
    print("=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Review the performance report in results/performance_report.txt")
    print("2. Examine trade log in results/trade_log.csv")
    print("3. Analyze equity curve in results/equity_curve.png")
    print("4. Check trade analysis plots in results/trade_analysis.png")
    print()
    print("If results are promising, proceed to optimization phase.")
    print()


if __name__ == "__main__":
    main()
