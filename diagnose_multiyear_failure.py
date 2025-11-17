"""
Diagnostic script to understand why multi-year backtest is failing
Compares Q1 2023 (working) vs Full 2023 (failing)
"""

import pandas as pd
import yaml
from indicators_pro import calculate_professional_indicators
from strategy_pro_v2 import ProfessionalDAXStrategyV2
from backtest_engine import BacktestEngine

def load_config():
    with open('config_professional_v2.yaml', 'r') as f:
        return yaml.safe_load(f)

def run_diagnostic():
    config = load_config()

    print("=" * 80)
    print("DIAGNOSTIC: Q1 2023 vs Full Year 2023")
    print("=" * 80)
    print()

    # Load full year data
    print("Loading full year 2023 data...")
    df_full = pd.read_csv('data/dax_2023_5m.csv')
    df_full['timestamp'] = pd.to_datetime(df_full['timestamp'])
    df_full = df_full.set_index('timestamp')
    df_full = df_full.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'})
    df_full = df_full[['open', 'high', 'low', 'close', 'volume']]

    print(f"Full year bars: {len(df_full)}")
    print(f"Date range: {df_full.index[0]} to {df_full.index[-1]}")

    # Extract Q1
    df_q1 = df_full[(df_full.index.month >= 1) & (df_full.index.month <= 3)]
    print(f"\nQ1 bars: {len(df_q1)}")
    print(f"Q1 date range: {df_q1.index[0]} to {df_q1.index[-1]}")

    # Check session hours
    print("\n" + "=" * 80)
    print("SESSION HOURS ANALYSIS")
    print("=" * 80)

    print("\nFull year hour distribution:")
    print(df_full.index.hour.value_counts().sort_index())

    print("\nQ1 hour distribution:")
    print(df_q1.index.hour.value_counts().sort_index())

    # Check data quality
    print("\n" + "=" * 80)
    print("DATA QUALITY CHECK")
    print("=" * 80)

    print("\nFull year:")
    print(f"  Price range: {df_full['close'].min():.2f} - {df_full['close'].max():.2f}")
    print(f"  Avg ATR proxy: {(df_full['high'] - df_full['low']).mean():.2f}")

    print("\nQ1:")
    print(f"  Price range: {df_q1['close'].min():.2f} - {df_q1['close'].max():.2f}")
    print(f"  Avg ATR proxy: {(df_q1['high'] - df_q1['low']).mean():.2f}")

    # Run both backtests
    print("\n" + "=" * 80)
    print("BACKTEST COMPARISON")
    print("=" * 80)

    for name, data in [("Q1 2023", df_q1), ("Full 2023", df_full)]:
        print(f"\n--- {name} ---")

        # Calculate indicators
        data_ind = calculate_professional_indicators(data, config)
        data_ind = data_ind.dropna()

        # Generate signals
        strategy = ProfessionalDAXStrategyV2(config)
        signals = strategy.generate_signals(data_ind)

        num_signals = (signals['Signal'] != 0).sum()
        print(f"Signals generated: {num_signals}")

        # Run backtest
        backtest = BacktestEngine(config)
        results = backtest.run_backtest(signals, strategy)

        if 'error' not in results:
            trades_df = results['trades_df']
            grouped = trades_df.groupby('entry_time').agg({'pnl': 'sum'}).reset_index()

            print(f"Trades executed: {len(grouped)}")
            print(f"Signals → Trades: {len(grouped)}/{num_signals} ({len(grouped)/num_signals*100:.1f}%)")
            print(f"Win rate: {(grouped['pnl'] > 0).sum() / len(grouped) * 100:.1f}%")
            print(f"Return: {(results['final_equity'] - results['initial_capital']) / results['initial_capital'] * 100:.2f}%")

            # Check why trades were blocked
            print(f"\nRisk control analysis:")
            print(f"  Total trades in backtest object: {backtest.total_trades}")
            print(f"  Consecutive losses hit: {backtest.consecutive_losses}")
            print(f"  Max consecutive losses: {config['strategy']['controls']['max_consecutive_losses']}")
        else:
            print(f"ERROR: {results['error']}")

    # Compare specific months
    print("\n" + "=" * 80)
    print("MONTHLY BREAKDOWN - 2023")
    print("=" * 80)

    for month in range(1, 13):
        df_month = df_full[df_full.index.month == month]
        if len(df_month) == 0:
            continue

        data_ind = calculate_professional_indicators(df_month, config)
        data_ind = data_ind.dropna()

        strategy = ProfessionalDAXStrategyV2(config)
        signals = strategy.generate_signals(data_ind)

        num_signals = (signals['Signal'] != 0).sum()

        if num_signals > 0:
            backtest = BacktestEngine(config)
            results = backtest.run_backtest(signals, strategy)

            if 'error' not in results:
                trades_df = results['trades_df']
                grouped = trades_df.groupby('entry_time').agg({'pnl': 'sum'}).reset_index()
                wr = (grouped['pnl'] > 0).sum() / len(grouped) * 100 if len(grouped) > 0 else 0
                ret = (results['final_equity'] - results['initial_capital']) / results['initial_capital'] * 100

                month_name = pd.Timestamp(2023, month, 1).strftime('%B')
                print(f"{month_name:12s}: {num_signals:4d} signals → {len(grouped):3d} trades ({len(grouped)/num_signals*100:5.1f}%), WR: {wr:5.1f}%, Return: {ret:7.2f}%")

if __name__ == "__main__":
    run_diagnostic()
