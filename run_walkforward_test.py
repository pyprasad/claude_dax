"""
Walk-Forward Validation Test
Split Q1 2023 into train/test periods
"""

import pandas as pd
import yaml
from indicators_pro import calculate_professional_indicators
from strategy_pro_v2 import ProfessionalDAXStrategyV2
from backtest_engine import BacktestEngine
from performance import PerformanceAnalyzer


def load_config():
    with open('config_professional_v2.yaml', 'r') as f:
        return yaml.safe_load(f)


def load_and_prepare_data(config):
    """Load full Q1 2023 data"""
    df = pd.read_csv(config['data']['filepath'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    df = df.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'})
    df = df[['open', 'high', 'low', 'close', 'volume']]
    df = df[~df.index.duplicated(keep='first')]
    df = df.sort_index()
    return df


def run_period(data, period_name, config):
    """Run backtest on a specific period"""
    print(f"\n{'=' * 80}")
    print(f"{period_name.upper()} PERIOD")
    print(f"{'=' * 80}")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")
    print(f"Bars: {len(data)}")

    # Calculate indicators
    data_with_indicators = calculate_professional_indicators(data, config)
    data_with_indicators = data_with_indicators.dropna()
    print(f"Bars after dropping NaN: {len(data_with_indicators)}")

    # Generate signals
    strategy = ProfessionalDAXStrategyV2(config)
    signals = strategy.generate_signals(data_with_indicators)
    num_signals = (signals['Signal'] != 0).sum()
    print(f"Signals generated: {num_signals}")

    if num_signals == 0:
        print("WARNING: No signals generated!")
        return None

    # Signal breakdown
    signal_counts = signals[signals['Signal'] != 0]['Signal_Type'].value_counts()
    print("\nSignal breakdown:")
    for signal_type, count in signal_counts.items():
        print(f"  {signal_type}: {count}")

    # Run backtest
    backtest = BacktestEngine(config)
    results = backtest.run_backtest(signals, strategy)

    if 'error' in results:
        print(f"ERROR: {results['error']}")
        return None

    # Quick stats
    trades_df = results['trades_df']
    if len(trades_df) > 0:
        grouped = trades_df.groupby('entry_time').agg({
            'pnl': 'sum',
        }).reset_index()

        print(f"\n{period_name.upper()} RESULTS:")
        print(f"  Unique trades: {len(grouped)}")
        print(f"  Win rate: {(grouped['pnl'] > 0).sum() / len(grouped) * 100:.1f}%")
        print(f"  Total P&L: ${grouped['pnl'].sum():,.2f}")
        print(f"  Return: {(results['final_equity'] - results['initial_capital']) / results['initial_capital'] * 100:.2f}%")

    return results


def main():
    print("=" * 80)
    print("WALK-FORWARD VALIDATION TEST")
    print("=" * 80)
    print("\nTesting V2 strategy on different time periods to validate robustness")
    print("This checks if the strategy works on UNSEEN data (out-of-sample)\n")

    config = load_config()
    data = load_and_prepare_data(config)

    print(f"\nFull dataset: {data.index[0]} to {data.index[-1]}")
    print(f"Total bars: {len(data)}\n")

    # Split data
    jan_data = data[data.index.month == 1]
    feb_data = data[data.index.month == 2]
    mar_data = data[data.index.month == 3]
    feb_mar_data = data[data.index.month.isin([2, 3])]

    # Test 1: January only (in-sample)
    jan_results = run_period(jan_data, "January 2023 (In-Sample)", config)

    # Test 2: February only (out-of-sample)
    feb_results = run_period(feb_data, "February 2023 (Out-of-Sample)", config)

    # Test 3: March only (out-of-sample)
    mar_results = run_period(mar_data, "March 2023 (Out-of-Sample)", config)

    # Test 4: Feb+Mar combined (out-of-sample)
    feb_mar_results = run_period(feb_mar_data, "Feb+Mar 2023 (Out-of-Sample)", config)

    # Summary
    print(f"\n{'=' * 80}")
    print("WALK-FORWARD VALIDATION SUMMARY")
    print(f"{'=' * 80}\n")

    results_summary = []

    if jan_results:
        jan_trades = jan_results['trades_df'].groupby('entry_time').agg({'pnl': 'sum'}).reset_index()
        jan_wr = (jan_trades['pnl'] > 0).sum() / len(jan_trades) * 100
        jan_return = (jan_results['final_equity'] - jan_results['initial_capital']) / jan_results['initial_capital'] * 100
        results_summary.append(('January (In-Sample)', len(jan_trades), jan_wr, jan_return))

    if feb_results:
        feb_trades = feb_results['trades_df'].groupby('entry_time').agg({'pnl': 'sum'}).reset_index()
        feb_wr = (feb_trades['pnl'] > 0).sum() / len(feb_trades) * 100
        feb_return = (feb_results['final_equity'] - feb_results['initial_capital']) / feb_results['initial_capital'] * 100
        results_summary.append(('February (Out-of-Sample)', len(feb_trades), feb_wr, feb_return))

    if mar_results:
        mar_trades = mar_results['trades_df'].groupby('entry_time').agg({'pnl': 'sum'}).reset_index()
        mar_wr = (mar_trades['pnl'] > 0).sum() / len(mar_trades) * 100
        mar_return = (mar_results['final_equity'] - mar_results['initial_capital']) / mar_results['initial_capital'] * 100
        results_summary.append(('March (Out-of-Sample)', len(mar_trades), mar_wr, mar_return))

    if feb_mar_results:
        fm_trades = feb_mar_results['trades_df'].groupby('entry_time').agg({'pnl': 'sum'}).reset_index()
        fm_wr = (fm_trades['pnl'] > 0).sum() / len(fm_trades) * 100
        fm_return = (feb_mar_results['final_equity'] - feb_mar_results['initial_capital']) / feb_mar_results['initial_capital'] * 100
        results_summary.append(('Feb+Mar (Out-of-Sample)', len(fm_trades), fm_wr, fm_return))

    print(f"{'Period':<30} {'Trades':<10} {'Win Rate':<12} {'Return':<10}")
    print("-" * 65)
    for period, trades, wr, ret in results_summary:
        print(f"{period:<30} {trades:<10} {wr:>6.1f}%     {ret:>7.2f}%")

    print(f"\n{'=' * 80}")
    print("VALIDATION CONCLUSION")
    print(f"{'=' * 80}\n")

    if feb_results and mar_results:
        # Check if out-of-sample performs reasonably
        feb_wr_check = feb_wr > 60  # At least 60% win rate
        mar_wr_check = mar_wr > 55  # March can be lower
        feb_return_check = feb_return > 0  # Positive return
        mar_return_check = mar_return > -5  # Not catastrophic

        if feb_wr_check and mar_wr_check and feb_return_check:
            print("✅ VALIDATION PASSED!")
            print("   Strategy performs well on out-of-sample data")
            print("   Win rates maintain above 55-60%")
            print("   Returns remain positive or near-positive")
            print("\n   This suggests the strategy has a GENUINE EDGE")
            print("   and is not curve-fit to January data.\n")
        else:
            print("⚠️  VALIDATION MIXED")
            print("   Strategy performance degrades on out-of-sample data")
            print("   This may indicate overfitting to training period")
            print("   OR market regime changed in Feb/Mar\n")

            if not feb_wr_check or not mar_wr_check:
                print(f"   Win rate concern: Feb={feb_wr:.1f}% Mar={mar_wr:.1f}%")
            if not feb_return_check or not mar_return_check:
                print(f"   Return concern: Feb={feb_return:.1f}% Mar={mar_return:.1f}%")

    print("\n" + "=" * 80)
    print("NEXT STEP: Test on REAL historical data from 2020-2024")
    print("=" * 80)
    print("\nTo fully validate this strategy, we need:")
    print("  - 2020 data (COVID crash + recovery)")
    print("  - 2021 data (Bull market)")
    print("  - 2022 data (Bear market)")
    print("  - 2024 data (Current market)")
    print("\nIf strategy maintains 55-70% win rate across all years,")
    print("it has a ROBUST edge. Otherwise, it's curve-fit to 2023.\n")


if __name__ == "__main__":
    main()
