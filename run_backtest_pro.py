"""
Professional DAX Strategy Backtest
Uses Opening Range Breakout + VWAP + Momentum
"""

import pandas as pd
import numpy as np
import yaml
import sys

from indicators_pro import calculate_professional_indicators
from strategy_pro import ProfessionalDAXStrategy
from backtest_engine import BacktestEngine
from performance import PerformanceAnalyzer


def load_config(config_path: str = 'config_professional.yaml') -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_data(config: dict) -> pd.DataFrame:
    """Load OHLCV data from CSV"""
    filepath = config['data']['filepath']

    print(f"Loading data from {filepath}...")
    df = pd.read_csv(filepath)

    # Parse timestamp
    date_col = config['data']['date_column']
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col)

    # Rename columns
    col_map = config['data']['ohlcv_columns']
    rename_dict = {
        col_map['open']: 'open',
        col_map['high']: 'high',
        col_map['low']: 'low',
        col_map['close']: 'close',
    }

    if col_map['volume'] in df.columns:
        rename_dict[col_map['volume']] = 'volume'

    df = df.rename(columns=rename_dict)

    # Add volume if missing
    if 'volume' not in df.columns:
        print("WARNING: Volume column not found. Using constant volume (1000).")
        df['volume'] = 1000

    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Remove duplicates and sort
    df = df[~df.index.duplicated(keep='first')]
    df = df.sort_index()

    print(f"Loaded {len(df)} bars")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    print(f"Timeframe: {config['data']['timeframe']}")

    return df


def main():
    """Main execution function"""
    print("=" * 80)
    print("PROFESSIONAL DAX INTRADAY STRATEGY - BACKTEST")
    print("Opening Range Breakout + VWAP + Momentum")
    print("=" * 80)
    print()

    # Load configuration
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config_professional.yaml'
    print(f"Loading configuration from {config_file}...")
    config = load_config(config_file)
    print("Configuration loaded ✓")
    print()

    # Load data
    data = load_data(config)

    print("\nValidating data...")
    # Quick validation
    if (data[['open', 'high', 'low', 'close']] <= 0).any().any():
        print("ERROR: Negative or zero prices detected")
        sys.exit(1)

    if (data['high'] < data['low']).any():
        print("ERROR: High < Low detected")
        sys.exit(1)

    print("Data validation passed ✓")

    # Calculate professional indicators
    print("\nCalculating professional indicators...")
    print("(ORB, VWAP, First Hour Momentum, EMAs, ATR)")
    data_with_indicators = calculate_professional_indicators(data, config)

    # Drop initial NaN rows
    initial_length = len(data_with_indicators)
    data_with_indicators = data_with_indicators.dropna()
    dropped = initial_length - len(data_with_indicators)
    print(f"Calculated indicators ✓")
    print(f"Dropped {dropped} initial bars with NaN values")
    print(f"Using {len(data_with_indicators)} bars for backtest")
    print()

    # Initialize strategy
    print("Initializing professional strategy...")
    strategy = ProfessionalDAXStrategy(config)
    print("Strategy initialized ✓")
    print()

    # Generate signals
    print("Generating trading signals...")
    print("(ORB breakouts, VWAP pullbacks, Momentum continuation)")
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

    # Check results
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
    output_dir = 'results_pro'
    analyzer.save_results(output_dir)

    print()
    print("=" * 80)
    print("PROFESSIONAL STRATEGY BACKTEST COMPLETE")
    print("=" * 80)
    print()
    print("Results saved to results_pro/")
    print()
    print("Key files:")
    print("- results_pro/performance_report_pro.txt")
    print("- results_pro/trade_log_pro.csv")
    print("- results_pro/equity_curve_pro.png")
    print()


if __name__ == "__main__":
    main()
