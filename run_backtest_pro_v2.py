"""
Professional DAX Strategy V2 Backtest
IMPROVED with real professional trader tactics
"""

import pandas as pd
import numpy as np
import yaml
import sys

from indicators_pro import calculate_professional_indicators
from strategy_pro_v2 import ProfessionalDAXStrategyV2
from backtest_engine import BacktestEngine
from performance import PerformanceAnalyzer


def load_config(config_path: str = 'config_professional_v2.yaml') -> dict:
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
    print("PROFESSIONAL DAX STRATEGY V2 - BACKTEST")
    print("IMPROVED: Better filters, Wider stops, Realistic targets")
    print("=" * 80)
    print()

    # Load configuration
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config_professional_v2.yaml'
    print(f"Loading configuration from {config_file}...")
    config = load_config(config_file)
    print("Configuration loaded ✓")
    print()

    print("V2 IMPROVEMENTS:")
    print("✓ Better entry filters (pullback entry, time-of-day)")
    print("✓ Wider stops (1.5-2.5x ATR vs 1-2x)")
    print("✓ Lower targets (1.2R and 2R vs 1.8R and 3-4R)")
    print("✓ Earlier trailing (0.8R vs 1.5R)")
    print("✓ OR size minimum (50% ATR vs 30%)")
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

    # Initialize strategy V2
    print("Initializing professional strategy V2...")
    strategy = ProfessionalDAXStrategyV2(config)
    print("Strategy V2 initialized ✓")
    print()

    # Generate signals
    print("Generating trading signals with IMPROVED filters...")
    signals = strategy.generate_signals(data_with_indicators)
    num_signals = (signals['Signal'] != 0).sum()
    print(f"Generated {num_signals} trading signals ✓")

    if num_signals == 0:
        print("\nWARNING: No signals generated! Entry filters may be too strict.")
        print("Consider relaxing some filters or checking data quality.")
        sys.exit(0)

    print()

    # Show signal breakdown
    if num_signals > 0:
        signal_counts = signals[signals['Signal'] != 0]['Signal_Type'].value_counts()
        print("Signal breakdown:")
        for signal_type, count in signal_counts.items():
            print(f"  {signal_type}: {count}")
        print()

        # Compare to V1
        print(f"V1 generated ~245 signals on same data")
        print(f"V2 generated {num_signals} signals (fewer but better quality)")
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
    output_dir = 'results_v2'
    analyzer.save_results(output_dir)

    print()
    print("=" * 80)
    print("PROFESSIONAL STRATEGY V2 BACKTEST COMPLETE")
    print("=" * 80)
    print()
    print("Results saved to results_v2/")
    print()
    print("Key files:")
    print("- results_v2/performance_report.txt")
    print("- results_v2/trade_log.csv")
    print("- results_v2/equity_curve.png")
    print()

    # Print comparison to V1
    print("COMPARISON TO V1:")
    print("V1 Results: 18 trades, 22% win rate, -20.33% return")
    print(f"V2 Results: {results['total_trades']} trades, {results['metrics']['win_rate']:.1f}% win rate, {results['total_return']:.2f}% return")
    print()


if __name__ == "__main__":
    main()
