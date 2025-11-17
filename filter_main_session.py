"""
Filter DAX data to main session only (08:00-22:00 CET)
Use this if your CSV has 24-hour data but you want only main session
"""

import pandas as pd
import sys


def filter_main_session(input_file, output_file="data/dax_2019_5m_main_session.csv"):
    """
    Filter to main DAX session (08:00-22:00 CET / 07:00-21:00 UTC winter / 06:00-20:00 UTC summer)
    """
    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)

    # Parse datetime
    date_col = None
    for col in ['Datetime', 'datetime', 'timestamp', 'Date', 'date']:
        if col in df.columns:
            date_col = col
            break

    if date_col is None:
        print("ERROR: Could not find datetime column")
        return

    df[date_col] = pd.to_datetime(df[date_col])

    print(f"Original data: {len(df)} bars")
    print(f"Date range: {df[date_col].min()} to {df[date_col].max()}")

    # Extract hour (in UTC)
    df['hour_utc'] = df[date_col].dt.tz_localize(None).dt.hour

    print("\nHourly distribution (UTC):")
    hourly = df.groupby('hour_utc').size().sort_index()
    for hour, count in hourly.items():
        bar = '█' * (count // 1000)
        print(f"  {hour:02d}:00 - {count:5d} bars {bar}")

    # Filter to main session
    # DAX main session: 08:00-22:00 CET
    # In UTC: varies by DST, but roughly 06:00-21:00
    # To be safe, use 06:00-21:00 UTC

    print("\nFiltering to main session (06:00-21:00 UTC)...")
    main_session = df[(df['hour_utc'] >= 6) & (df['hour_utc'] < 21)].copy()

    # Drop helper column
    main_session = main_session.drop('hour_utc', axis=1)

    print(f"Filtered data: {len(main_session)} bars")
    print(f"Date range: {main_session[date_col].min()} to {main_session[date_col].max()}")
    print(f"Removed: {len(df) - len(main_session)} bars ({(len(df) - len(main_session))/len(df)*100:.1f}%)")

    # Save
    main_session.to_csv(output_file, index=False)
    print(f"\n✓ Saved to: {output_file}")
    print("\nNow update your config.yaml:")
    print(f'  filepath: "{output_file}"')
    print("\nAnd run backtest again!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        input_file = "data/dax_2019_5m.csv"
    else:
        input_file = sys.argv[1]

    filter_main_session(input_file)
