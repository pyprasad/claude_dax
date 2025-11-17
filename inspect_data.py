"""
Quick Data Inspection Tool
Shows basic stats about your market data file
"""

import pandas as pd
import sys


def inspect_data(filepath):
    """Inspect and display data statistics"""
    print("=" * 80)
    print("DATA INSPECTION")
    print("=" * 80)
    print()

    # Load data
    print(f"Loading: {filepath}")
    df = pd.read_csv(filepath)

    print(f"\n✓ File loaded successfully\n")

    # Show structure
    print("COLUMN NAMES:")
    print("-" * 80)
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")

    # Show first few rows
    print("\nFIRST 5 ROWS:")
    print("-" * 80)
    print(df.head())

    # Parse datetime (try common column names)
    datetime_col = None
    for col in ['Datetime', 'datetime', 'timestamp', 'Date', 'date', 'Time', 'time']:
        if col in df.columns:
            datetime_col = col
            break

    if datetime_col:
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df = df.set_index(datetime_col)
        df = df.sort_index()

        print("\nDATE RANGE:")
        print("-" * 80)
        print(f"  Start: {df.index[0]}")
        print(f"  End:   {df.index[-1]}")
        print(f"  Total bars: {len(df):,}")

        # Calculate duration
        duration = df.index[-1] - df.index[0]
        print(f"  Duration: {duration.days} days ({duration.days/30:.1f} months)")

        # Trading days
        unique_days = df.index.date
        unique_days = pd.Series(unique_days).nunique()
        print(f"  Unique trading days: {unique_days}")

        # Average bars per day
        avg_bars = len(df) / unique_days
        print(f"  Average bars per day: {avg_bars:.0f}")

    # Price statistics
    price_cols = [col for col in df.columns if col in ['Close', 'close', 'Close_Price', 'Price']]
    if price_cols:
        price_col = price_cols[0]
        print(f"\nPRICE STATISTICS (using '{price_col}'):")
        print("-" * 80)
        print(f"  Min:    {df[price_col].min():,.2f}")
        print(f"  Max:    {df[price_col].max():,.2f}")
        print(f"  Mean:   {df[price_col].mean():,.2f}")
        print(f"  Median: {df[price_col].median():,.2f}")
        print(f"  Range:  {df[price_col].max() - df[price_col].min():,.2f} ({((df[price_col].max() - df[price_col].min()) / df[price_col].min() * 100):.1f}%)")

    # Check for missing values
    print("\nMISSING VALUES:")
    print("-" * 80)
    missing = df.isnull().sum()
    if missing.sum() == 0:
        print("  ✓ No missing values")
    else:
        for col, count in missing.items():
            if count > 0:
                print(f"  {col}: {count} ({count/len(df)*100:.2f}%)")

    # Check for volume
    volume_cols = [col for col in df.columns if 'volume' in col.lower() or 'vol' in col.lower()]
    if volume_cols:
        print(f"\n✓ Volume column found: {volume_cols[0]}")
    else:
        print("\n⚠️  WARNING: No volume column detected")
        print("   The strategy will use constant volume (acceptable for indices)")

    # Estimate expected trades
    print("\nEXPECTED BACKTEST STATISTICS:")
    print("-" * 80)
    if duration.days >= 60:
        expected_trades = int((duration.days / 30) * 20)  # ~20 trades per month
        print(f"  Expected trades: {expected_trades}-{expected_trades*2} (rough estimate)")
        print(f"  Trade frequency: ~20-40 per month")
        print(f"  ✓ Good sample size for backtesting")
    else:
        print(f"  ⚠️  Only {duration.days} days of data")
        print(f"     Recommended: At least 60 days (2+ months)")
        print(f"     Optimal: 90-180 days (3-6 months)")

    print("\n" + "=" * 80)
    print("CONFIGURATION HELPER")
    print("=" * 80)
    print("\nUse these settings in your config.yaml:")
    print("-" * 80)
    if datetime_col:
        print(f'  date_column: "{datetime_col}"')

    print("  ohlcv_columns:")
    for col in df.columns:
        col_lower = col.lower()
        if 'open' in col_lower:
            print(f'    open: "{col}"')
        elif 'high' in col_lower:
            print(f'    high: "{col}"')
        elif 'low' in col_lower:
            print(f'    low: "{col}"')
        elif 'close' in col_lower:
            print(f'    close: "{col}"')
        elif 'vol' in col_lower:
            print(f'    volume: "{col}"')

    print("\n" + "=" * 80)
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = "data/dax_2019_5m.csv"

    try:
        inspect_data(filepath)
    except FileNotFoundError:
        print(f"ERROR: File not found: {filepath}")
        print("\nUsage: python inspect_data.py <path_to_csv>")
        print("Example: python inspect_data.py data/dax_2019_5m.csv")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
