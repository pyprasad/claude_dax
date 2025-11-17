"""
Data Format Converter
Converts various DAX data formats to the required format for backtesting
"""

import pandas as pd
import sys
import os


def detect_columns(df):
    """Auto-detect column names"""
    columns = df.columns.str.lower()

    mapping = {}

    # Timestamp detection
    timestamp_options = ['timestamp', 'datetime', 'date', 'time', 'date_time']
    for opt in timestamp_options:
        matches = [col for col in df.columns if opt in col.lower()]
        if matches:
            mapping['timestamp'] = matches[0]
            break

    # Price columns (try common variations)
    price_options = {
        'open': ['open', 'o'],
        'high': ['high', 'h'],
        'low': ['low', 'l'],
        'close': ['close', 'c', 'last'],
        'volume': ['volume', 'vol', 'v']
    }

    for target, options in price_options.items():
        for opt in options:
            matches = [col for col in df.columns if col.lower() == opt or col.lower().endswith(opt)]
            if matches:
                mapping[target] = matches[0]
                break

    return mapping


def convert_file(input_file, output_file=None):
    """Convert data file to required format"""

    print(f"Loading: {input_file}")

    # Try to read with different encodings
    try:
        df = pd.read_csv(input_file)
    except UnicodeDecodeError:
        df = pd.read_csv(input_file, encoding='latin-1')

    print(f"Original columns: {list(df.columns)}")
    print(f"Original rows: {len(df)}")

    # Detect columns
    mapping = detect_columns(df)

    print(f"\nDetected mapping:")
    for target, source in mapping.items():
        print(f"  {target} <- {source}")

    # Check required columns
    required = ['timestamp', 'open', 'high', 'low', 'close']
    missing = [col for col in required if col not in mapping]

    if missing:
        print(f"\nERROR: Could not detect required columns: {missing}")
        print("\nAvailable columns:")
        for col in df.columns:
            print(f"  - {col}")
        print("\nPlease manually specify column mapping in the script.")
        return False

    # Rename columns
    rename_dict = {mapping[target]: target for target in mapping if target in mapping}
    df = df.rename(columns=rename_dict)

    # Keep only required columns
    keep_cols = ['timestamp', 'open', 'high', 'low', 'close']
    if 'volume' in df.columns:
        keep_cols.append('volume')

    df = df[keep_cols]

    # Convert timestamp to standard format
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Filter to main session hours (9:00-22:00 CET)
    df = df.set_index('timestamp')
    df['hour'] = df.index.hour

    # Keep main session
    df = df[(df['hour'] >= 9) & (df['hour'] <= 21)]
    df = df.drop('hour', axis=1)
    df = df.reset_index()

    # Remove duplicates
    df = df.drop_duplicates(subset='timestamp', keep='first')

    # Sort by timestamp
    df = df.sort_values('timestamp')

    # Add volume if missing
    if 'volume' not in df.columns:
        print("\nWARNING: No volume column found. Adding constant volume (1000)")
        df['volume'] = 1000

    # Validate data
    print("\nValidating data...")

    # Check for negative prices
    if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
        print("ERROR: Negative or zero prices detected!")
        return False

    # Check high >= low
    if (df['high'] < df['low']).any():
        print("ERROR: Some bars have high < low!")
        bad_rows = df[df['high'] < df['low']]
        print(f"Found {len(bad_rows)} bad rows")
        print("Fixing by swapping high and low...")
        df.loc[df['high'] < df['low'], ['high', 'low']] = df.loc[df['high'] < df['low'], ['low', 'high']].values

    # Final output
    print(f"\nProcessed data:")
    print(f"  Rows: {len(df)}")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Columns: {list(df.columns)}")

    # Determine output file
    if output_file is None:
        # Auto-generate output name
        base = os.path.basename(input_file)
        name, ext = os.path.splitext(base)

        # Try to extract year
        year = None
        for part in name.split('_'):
            if part.isdigit() and len(part) == 4 and 2020 <= int(part) <= 2024:
                year = part
                break

        if year:
            output_file = f"data/dax_{year}_5m.csv"
        else:
            output_file = f"data/dax_converted_5m.csv"

    # Save
    df.to_csv(output_file, index=False)
    print(f"\nSaved to: {output_file}")

    # Show sample
    print("\nFirst 3 rows:")
    print(df.head(3).to_string())

    return True


def manual_convert(input_file, output_file, column_mapping):
    """
    Manual conversion with explicit column mapping

    Example usage:
    manual_convert(
        'my_data.csv',
        'data/dax_2020_5m.csv',
        {
            'Date': 'timestamp',
            'O': 'open',
            'H': 'high',
            'L': 'low',
            'C': 'close',
            'Vol': 'volume'
        }
    )
    """
    df = pd.read_csv(input_file)
    df = df.rename(columns=column_mapping)

    # Apply same processing as auto-convert
    required = ['timestamp', 'open', 'high', 'low', 'close']
    df = df[required + (['volume'] if 'volume' in df.columns else [])]

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    df['hour'] = df.index.hour
    df = df[(df['hour'] >= 9) & (df['hour'] <= 21)]
    df = df.drop('hour', axis=1)
    df = df.reset_index()

    if 'volume' not in df.columns:
        df['volume'] = 1000

    df.to_csv(output_file, index=False)
    print(f"Converted and saved to: {output_file}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_data_format.py <input_file> [output_file]")
        print("\nExample:")
        print("  python convert_data_format.py my_dax_2020.csv")
        print("  python convert_data_format.py my_dax_2020.csv data/dax_2020_5m.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_file):
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)

    success = convert_file(input_file, output_file)

    if success:
        print("\n✓ Conversion successful!")
        print("\nYou can now run the backtest:")
        print("  python run_multiyear_backtest.py")
    else:
        print("\n✗ Conversion failed!")
        print("\nTry manual conversion by editing this script and using manual_convert()")
        sys.exit(1)


if __name__ == "__main__":
    main()
