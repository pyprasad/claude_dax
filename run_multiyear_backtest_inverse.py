"""
Multi-Year Backtesting Script - V4 INVERSE ORB
Tests FADE FALSE BREAKOUTS strategy (inverted V3 signals)

Hypothesis: If V3 is wrong 78% of time, inverting should yield 78% win rate
"""

import pandas as pd
import numpy as np
import yaml
import glob
import os
import sys
from datetime import datetime

from indicators_pro import calculate_professional_indicators
from strategy_inverse_orb import InverseORBStrategy
from backtest_engine import BacktestEngine
from performance import PerformanceAnalyzer


def load_config():
    """Load V4 Inverse configuration"""
    with open('config_inverse_orb.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config


def find_year_files():
    """Find all available year data files"""
    pattern = 'data/dax_*_5m.csv'
    files = glob.glob(pattern)

    year_files = {}
    for filepath in files:
        filename = os.path.basename(filepath)
        parts = filename.split('_')
        if len(parts) >= 2:
            try:
                year = int(parts[1])
                if 2020 <= year <= 2024:
                    year_files[year] = filepath
            except ValueError:
                continue

    return dict(sorted(year_files.items()))


def load_year_data(filepath, config):
    """Load and prepare data for one year"""
    print(f"  Loading: {filepath}")

    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Standardize column names
    if 'Open' in df.columns:
        df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})

    required = ['open', 'high', 'low', 'close']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    if 'volume' not in df.columns:
        print(f"  WARNING: No volume column, using constant 1000")
        df['volume'] = 1000

    df = df[['open', 'high', 'low', 'close', 'volume']]
    df = df[~df.index.duplicated(keep='first')]
    df = df.sort_index()

    if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
        raise ValueError("ERROR: Negative or zero prices detected")

    if (df['high'] < df['low']).any():
        raise ValueError("ERROR: High < Low detected")

    print(f"  Loaded {len(df)} bars")
    print(f"  Date range: {df.index[0]} to {df.index[-1]}")

    return df


def run_year_backtest(year, data, config):
    """Run V4 INVERSE backtest for one year"""
    print(f"\n{'=' * 80}")
    print(f"YEAR {year} BACKTEST - V4 INVERSE ORB (FADE FALSE BREAKOUTS)")
    print(f"{'=' * 80}")

    # Calculate indicators (includes ADX)
    print("Calculating indicators (including ADX for regime detection)...")
    data_with_indicators = calculate_professional_indicators(data, config)

    initial_length = len(data_with_indicators)
    data_with_indicators = data_with_indicators.dropna()
    dropped = initial_length - len(data_with_indicators)

    print(f"Dropped {dropped} initial bars with NaN")
    print(f"Using {len(data_with_indicators)} bars for backtest")

    # Check regime statistics
    if 'ADX' in data_with_indicators.columns:
        trending = (data_with_indicators['ADX'] > 20).sum()
        trending_pct = trending / len(data_with_indicators) * 100
        print(f"\nRegime analysis:")
        print(f"  Trending bars (ADX > 20): {trending}/{len(data_with_indicators)} ({trending_pct:.1f}%)")
        print(f"  Avg ADX: {data_with_indicators['ADX'].mean():.1f}")

    # Generate INVERSE signals (V4)
    print("\n🔄 Generating V4 INVERSE signals (fading V3 breakouts)...")
    strategy = InverseORBStrategy(config)
    signals = strategy.generate_signals(data_with_indicators)

    num_signals = (signals['Signal'] != 0).sum()
    print(f"Generated {num_signals} INVERSE signals")

    # Check how many signals were in trending regime
    if 'Regime_Trending' in signals.columns:
        trending_signals = signals[(signals['Signal'] != 0) & (signals['Regime_Trending'] == True)]
        print(f"  Signals in trending regime: {len(trending_signals)}/{num_signals}")

    if num_signals == 0:
        print("WARNING: No signals generated!")
        return None

    # Signal breakdown
    signal_counts = signals[signals['Signal'] != 0]['Signal_Type'].value_counts()
    print("\nSignal breakdown:")
    for signal_type, count in signal_counts.items():
        print(f"  {signal_type}: {count}")

    # Run backtest
    print("\nRunning backtest...")
    backtest = BacktestEngine(config)
    results = backtest.run_backtest(signals, strategy)

    if 'error' in results:
        print(f"ERROR: {results['error']}")
        return None

    # Calculate combined metrics
    trades_df = results['trades_df']
    grouped = trades_df.groupby('entry_time').agg({
        'pnl': 'sum',
        'signal_type': 'first'
    }).reset_index()

    # Summary stats
    unique_trades = len(grouped)
    wins = (grouped['pnl'] > 0).sum()
    losses = (grouped['pnl'] < 0).sum()
    win_rate = wins / unique_trades * 100 if unique_trades > 0 else 0
    total_pnl = grouped['pnl'].sum()
    return_pct = (results['final_equity'] - results['initial_capital']) / results['initial_capital'] * 100

    print(f"\n{year} V4 INVERSE RESULTS:")
    print(f"  Unique Trades: {unique_trades}")
    print(f"  Signals → Trades: {unique_trades}/{num_signals} ({unique_trades/num_signals*100:.1f}% conversion)")
    print(f"  Win Rate: {win_rate:.1f}% {'✅' if win_rate > 55 else '⚠️'}")
    print(f"  Total P&L: ${total_pnl:,.2f}")
    print(f"  Return: {return_pct:.2f}% {'✅' if return_pct > 0 else '❌'}")
    print(f"  Max Drawdown: {results['max_drawdown']:.2f}%")

    # Strategy breakdown
    print("\nStrategy breakdown:")
    for strategy_type in grouped['signal_type'].unique():
        strat_trades = grouped[grouped['signal_type'] == strategy_type]
        count = len(strat_trades)
        total_pnl = strat_trades['pnl'].sum()
        wr = (strat_trades['pnl'] > 0).sum() / len(strat_trades) * 100
        print(f"  {strategy_type}: {count} trades, {wr:.1f}% WR, ${total_pnl:,.2f}")

    return {
        'year': year,
        'unique_trades': unique_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'return_pct': return_pct,
        'max_drawdown': results['max_drawdown'],
        'trades_df': grouped,
        'full_results': results,
        'signal_count': num_signals,
        'conversion_rate': unique_trades/num_signals*100 if num_signals > 0 else 0
    }


def main():
    """Main execution"""
    print("=" * 80)
    print("MULTI-YEAR BACKTESTING - V4 INVERSE ORB (FADE FALSE BREAKOUTS)")
    print("=" * 80)
    print("\n🔄 V4 Strategy:")
    print("  - INVERTS all V3 signals (V3 says BUY → V4 SELLS)")
    print("  - Hypothesis: If V3 is wrong 78% of time, inverting should win 78%")
    print("  - Fades false breakouts instead of chasing them")
    print("  - Keeps V3 regime detection (ADX > 20)")
    print()

    # Find available year files
    print("Scanning for data files...")
    year_files = find_year_files()

    if not year_files:
        print("\nERROR: No year data files found!")
        print("\nExpected files in data/ directory:")
        print("  - dax_2020_5m.csv")
        print("  - dax_2021_5m.csv")
        print("  - dax_2022_5m.csv")
        print("  - dax_2023_5m.csv")
        print("  - dax_2024_5m.csv")
        sys.exit(1)

    print(f"\nFound {len(year_files)} year(s) to test:")
    for year, filepath in year_files.items():
        print(f"  {year}: {filepath}")

    # Load configuration
    print("\nLoading V4 Inverse configuration...")
    config = load_config()
    print(f"  Regime filter: {'ENABLED' if config['strategy']['use_regime_filter'] else 'DISABLED'}")
    print(f"  ADX threshold: {config['strategy']['regime']['adx_threshold']}")

    # Run backtest for each year
    yearly_results = []

    for year, filepath in year_files.items():
        try:
            data = load_year_data(filepath, config)
            result = run_year_backtest(year, data, config)

            if result:
                yearly_results.append(result)

                # Save individual year results
                output_dir = 'results_inverse'
                os.makedirs(output_dir, exist_ok=True)

                year_file = os.path.join(output_dir, f'{year}_trades_inverse.csv')
                result['trades_df'].to_csv(year_file, index=False)
                print(f"Saved {year} results to: {year_file}")

        except Exception as e:
            print(f"\nERROR processing year {year}: {str(e)}")
            import traceback
            traceback.print_exc()
            print("Skipping this year and continuing...")
            continue

    # Summary
    if yearly_results:
        print(f"\n{'=' * 80}")
        print("V4 INVERSE MULTI-YEAR SUMMARY")
        print(f"{'=' * 80}\n")

        print(f"{'Year':<8} {'Signals':<10} {'Trades':<10} {'Conv%':<8} {'WR%':<8} {'Return%':<10}")
        print("-" * 70)

        all_trades = []
        for result in yearly_results:
            print(f"{result['year']:<8} {result['signal_count']:<10} {result['unique_trades']:<10} "
                  f"{result['conversion_rate']:<8.1f} {result['win_rate']:<8.1f} {result['return_pct']:<10.2f}")
            all_trades.append(result['trades_df'])

        # Aggregate
        combined = pd.concat(all_trades, ignore_index=True)
        overall_wr = (combined['pnl'] > 0).sum() / len(combined) * 100
        overall_pnl = combined['pnl'].sum()
        avg_return = np.mean([r['return_pct'] for r in yearly_results])

        print("-" * 70)
        print(f"{'OVERALL':<8} {'-':<10} {len(combined):<10} {'-':<8} {overall_wr:<8.1f} {avg_return:<10.2f}")

        print(f"\n{'=' * 80}")
        print("V4 INVERSE vs V3 COMPARISON")
        print(f"{'=' * 80}")
        print(f"\nV3 Results (2020-2024): 22.4% WR, -75.42% avg return")
        print(f"V4 INVERSE Results:     {overall_wr:.1f}% WR, {avg_return:.2f}% avg return")
        print()

        # Validation
        if overall_wr >= 55 and avg_return > 5:
            print("✅ V4 INVERSE SUCCESS: Hypothesis confirmed! Fading works!")
            print("   Next step: Optimize parameters and prepare for deployment")
        elif overall_wr >= 50 and avg_return > 0:
            print("⚠️  V4 INVERSE PARTIAL SUCCESS: Positive but needs optimization")
            print("   Win rate inverted as expected but returns modest")
        else:
            print("❌ V4 INVERSE FAILED: Hypothesis rejected")
            print("   Next step: Build pure mean-reversion strategy OR test different market")

        print(f"\n{'=' * 80}")
        print("HYPOTHESIS TEST RESULTS")
        print(f"{'=' * 80}")
        print(f"\nExpected WR if hypothesis true: ~78% (inverse of V3's 22%)")
        print(f"Actual WR: {overall_wr:.1f}%")
        print(f"Hypothesis: {'CONFIRMED ✅' if overall_wr > 60 else 'REJECTED ❌'}")

    else:
        print("\nERROR: No successful backtests completed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
