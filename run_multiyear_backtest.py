"""
Multi-Year Backtesting Script
Automatically tests V2 strategy on all available years (2020-2024)
"""

import pandas as pd
import numpy as np
import yaml
import glob
import os
import sys
from datetime import datetime

from indicators_pro import calculate_professional_indicators
from strategy_pro_v2 import ProfessionalDAXStrategyV2
from backtest_engine import BacktestEngine
from performance import PerformanceAnalyzer


def load_config():
    """Load V2 configuration"""
    with open('config_professional_v2.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config


def find_year_files():
    """Find all available year data files"""
    # Look for files matching pattern: dax_YYYY_5m.csv
    pattern = 'data/dax_*_5m.csv'
    files = glob.glob(pattern)

    year_files = {}
    for filepath in files:
        # Extract year from filename
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

    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Standardize column names (handle different formats)
    if 'Open' in df.columns:
        df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})

    # Ensure required columns
    required = ['open', 'high', 'low', 'close']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Add volume if missing
    if 'volume' not in df.columns:
        print(f"  WARNING: No volume column, using constant 1000")
        df['volume'] = 1000

    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Remove duplicates and sort
    df = df[~df.index.duplicated(keep='first')]
    df = df.sort_index()

    # Validate data
    if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
        raise ValueError("ERROR: Negative or zero prices detected")

    if (df['high'] < df['low']).any():
        raise ValueError("ERROR: High < Low detected")

    print(f"  Loaded {len(df)} bars")
    print(f"  Date range: {df.index[0]} to {df.index[-1]}")

    return df


def run_year_backtest(year, data, config):
    """Run backtest for one year"""
    print(f"\n{'=' * 80}")
    print(f"YEAR {year} BACKTEST")
    print(f"{'=' * 80}")

    # Calculate indicators
    print("Calculating indicators...")
    data_with_indicators = calculate_professional_indicators(data, config)

    initial_length = len(data_with_indicators)
    data_with_indicators = data_with_indicators.dropna()
    dropped = initial_length - len(data_with_indicators)

    print(f"Dropped {dropped} initial bars with NaN")
    print(f"Using {len(data_with_indicators)} bars for backtest")

    # Generate signals
    print("Generating signals...")
    strategy = ProfessionalDAXStrategyV2(config)
    signals = strategy.generate_signals(data_with_indicators)

    num_signals = (signals['Signal'] != 0).sum()
    print(f"Generated {num_signals} signals")

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

    # Calculate combined metrics (accounting for partial exits)
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

    print(f"\n{year} RESULTS:")
    print(f"  Unique Trades: {unique_trades}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Total P&L: ${total_pnl:,.2f}")
    print(f"  Return: {return_pct:.2f}%")
    print(f"  Max Drawdown: {results['max_drawdown']:.2f}%")
    print(f"  Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")

    # Strategy breakdown
    strategy_breakdown = grouped.groupby('signal_type').agg({
        'pnl': ['count', 'sum', lambda x: (x > 0).sum() / len(x) * 100]
    }).round(2)

    print("\nStrategy breakdown:")
    for idx, row in strategy_breakdown.iterrows():
        trades = int(row['pnl']['count'])
        pnl = row['pnl']['sum']
        wr = row['pnl']['<lambda>']
        print(f"  {idx}: {trades} trades, {wr:.1f}% WR, ${pnl:,.2f}")

    return {
        'year': year,
        'unique_trades': unique_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'return_pct': return_pct,
        'max_drawdown': results['max_drawdown'],
        'sharpe_ratio': results.get('sharpe_ratio', 0),
        'profit_factor': results.get('profit_factor', 0),
        'trades_df': grouped,
        'full_results': results
    }


def generate_summary_report(yearly_results, output_dir='results_multiyear'):
    """Generate comprehensive summary report"""
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'=' * 80}")
    print("MULTI-YEAR SUMMARY REPORT")
    print(f"{'=' * 80}\n")

    # Summary table
    print(f"{'Year':<8} {'Trades':<10} {'Win Rate':<12} {'Return':<12} {'Max DD':<12} {'Sharpe':<10}")
    print("-" * 70)

    all_trades = []
    total_return = 0

    for result in yearly_results:
        year = result['year']
        trades = result['unique_trades']
        wr = result['win_rate']
        ret = result['return_pct']
        dd = result['max_drawdown']
        sharpe = result['sharpe_ratio']

        print(f"{year:<8} {trades:<10} {wr:>6.1f}%      {ret:>7.2f}%     {dd:>7.2f}%     {sharpe:>6.2f}")

        all_trades.append(result['trades_df'])
        total_return += ret

    # Calculate aggregate statistics
    combined_trades = pd.concat(all_trades, ignore_index=True)

    total_unique_trades = len(combined_trades)
    overall_win_rate = (combined_trades['pnl'] > 0).sum() / len(combined_trades) * 100
    overall_pnl = combined_trades['pnl'].sum()
    avg_annual_return = total_return / len(yearly_results)

    print("-" * 70)
    print(f"{'OVERALL':<8} {total_unique_trades:<10} {overall_win_rate:>6.1f}%      {avg_annual_return:>7.2f}%     {'(avg)':>7}      {'':>6}")

    # Detailed summary
    print(f"\n{'=' * 80}")
    print("AGGREGATE STATISTICS (All Years Combined)")
    print(f"{'=' * 80}\n")

    print(f"Total Unique Trades: {total_unique_trades}")
    print(f"Overall Win Rate: {overall_win_rate:.1f}%")
    print(f"Total P&L: ${overall_pnl:,.2f}")
    print(f"Average Annual Return: {avg_annual_return:.2f}%")
    print(f"Years Tested: {len(yearly_results)}")

    # Win rate consistency check
    win_rates = [r['win_rate'] for r in yearly_results]
    wr_mean = np.mean(win_rates)
    wr_std = np.std(win_rates)
    wr_min = np.min(win_rates)
    wr_max = np.max(win_rates)

    print(f"\nWin Rate Statistics:")
    print(f"  Mean: {wr_mean:.1f}%")
    print(f"  Std Dev: {wr_std:.1f}%")
    print(f"  Range: {wr_min:.1f}% - {wr_max:.1f}%")

    # Return consistency
    returns = [r['return_pct'] for r in yearly_results]
    ret_mean = np.mean(returns)
    ret_std = np.std(returns)

    print(f"\nReturn Statistics:")
    print(f"  Mean: {ret_mean:.2f}%")
    print(f"  Std Dev: {ret_std:.2f}%")
    print(f"  Positive Years: {sum(1 for r in returns if r > 0)}/{len(returns)}")

    # Validation conclusion
    print(f"\n{'=' * 80}")
    print("VALIDATION CONCLUSION")
    print(f"{'=' * 80}\n")

    # Criteria for robust strategy
    criteria_pass = []

    # 1. Overall win rate > 60%
    if overall_win_rate >= 60:
        print("✓ Overall win rate >= 60% (PASSED)")
        criteria_pass.append(True)
    else:
        print(f"✗ Overall win rate < 60% (FAILED: {overall_win_rate:.1f}%)")
        criteria_pass.append(False)

    # 2. Win rate consistency (std dev < 15%)
    if wr_std < 15:
        print(f"✓ Win rate consistent across years (PASSED: std={wr_std:.1f}%)")
        criteria_pass.append(True)
    else:
        print(f"✗ Win rate inconsistent (FAILED: std={wr_std:.1f}%)")
        criteria_pass.append(False)

    # 3. Minimum win rate > 55%
    if wr_min >= 55:
        print(f"✓ All years above 55% win rate (PASSED: min={wr_min:.1f}%)")
        criteria_pass.append(True)
    else:
        print(f"✗ Some years below 55% (FAILED: min={wr_min:.1f}%)")
        criteria_pass.append(False)

    # 4. Positive expectancy
    if avg_annual_return > 0:
        print(f"✓ Positive average annual return (PASSED: {avg_annual_return:.2f}%)")
        criteria_pass.append(True)
    else:
        print(f"✗ Negative average return (FAILED: {avg_annual_return:.2f}%)")
        criteria_pass.append(False)

    # Final verdict
    print()
    if all(criteria_pass):
        print("=" * 80)
        print("🎉 STRATEGY VALIDATED - ROBUST EDGE CONFIRMED!")
        print("=" * 80)
        print("\nThis strategy demonstrates:")
        print("  ✓ Consistent win rate across multiple years")
        print("  ✓ Positive returns across different market regimes")
        print("  ✓ Robust edge that generalizes to unseen data")
        print("\n  RECOMMENDATION: Strategy is ready for paper trading")
        print("=" * 80)
    elif sum(criteria_pass) >= 3:
        print("=" * 80)
        print("⚠️  STRATEGY PARTIALLY VALIDATED")
        print("=" * 80)
        print("\nStrategy shows promise but has some concerns.")
        print("Consider additional optimization or filtering.")
        print("=" * 80)
    else:
        print("=" * 80)
        print("❌ STRATEGY FAILED VALIDATION")
        print("=" * 80)
        print("\nStrategy does not demonstrate robust edge across years.")
        print("Requires significant redesign or may be fundamentally flawed.")
        print("=" * 80)

    # Save report
    report_path = os.path.join(output_dir, 'multiyear_summary.txt')
    with open(report_path, 'w') as f:
        f.write("MULTI-YEAR BACKTEST SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        for result in yearly_results:
            f.write(f"\nYear {result['year']}:\n")
            f.write(f"  Trades: {result['unique_trades']}\n")
            f.write(f"  Win Rate: {result['win_rate']:.1f}%\n")
            f.write(f"  Return: {result['return_pct']:.2f}%\n")
            f.write(f"  Max DD: {result['max_drawdown']:.2f}%\n")

        f.write(f"\n\nOverall:\n")
        f.write(f"  Total Trades: {total_unique_trades}\n")
        f.write(f"  Overall Win Rate: {overall_win_rate:.1f}%\n")
        f.write(f"  Avg Annual Return: {avg_annual_return:.2f}%\n")

    print(f"\nReport saved to: {report_path}")

    # Save combined trade log
    trades_path = os.path.join(output_dir, 'all_trades.csv')
    combined_trades.to_csv(trades_path, index=False)
    print(f"Combined trades saved to: {trades_path}")

    return {
        'overall_win_rate': overall_win_rate,
        'avg_annual_return': avg_annual_return,
        'validation_passed': all(criteria_pass)
    }


def main():
    """Main execution"""
    print("=" * 80)
    print("MULTI-YEAR BACKTESTING - DAX PROFESSIONAL STRATEGY V2")
    print("=" * 80)
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
        print("\nSee DATA_REQUIREMENTS.md for details.")
        sys.exit(1)

    print(f"\nFound {len(year_files)} year(s) to test:")
    for year, filepath in year_files.items():
        print(f"  {year}: {filepath}")

    # Load configuration
    print("\nLoading V2 configuration...")
    config = load_config()

    # Run backtest for each year
    yearly_results = []

    for year, filepath in year_files.items():
        try:
            # Load data
            data = load_year_data(filepath, config)

            # Run backtest
            result = run_year_backtest(year, data, config)

            if result:
                yearly_results.append(result)

                # Save individual year results
                output_dir = 'results_multiyear'
                os.makedirs(output_dir, exist_ok=True)

                year_file = os.path.join(output_dir, f'{year}_trades.csv')
                result['trades_df'].to_csv(year_file, index=False)
                print(f"Saved {year} results to: {year_file}")

        except Exception as e:
            print(f"\nERROR processing year {year}: {str(e)}")
            print("Skipping this year and continuing...")
            continue

    # Generate summary report
    if yearly_results:
        summary = generate_summary_report(yearly_results)

        print("\n" + "=" * 80)
        print("MULTI-YEAR BACKTEST COMPLETE")
        print("=" * 80)
        print(f"\nTested {len(yearly_results)} year(s)")
        print(f"Overall Win Rate: {summary['overall_win_rate']:.1f}%")
        print(f"Avg Annual Return: {summary['avg_annual_return']:.2f}%")
        print(f"Validation: {'PASSED ✓' if summary['validation_passed'] else 'FAILED ✗'}")
        print()
    else:
        print("\nERROR: No successful backtests completed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
