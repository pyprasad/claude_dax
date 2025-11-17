"""
Professional DAX Trading Indicators
Used by institutional and professional intraday traders
"""

import pandas as pd
import numpy as np
from datetime import time


def vwap_intraday(high: pd.Series, low: pd.Series, close: pd.Series,
                  volume: pd.Series, reset_daily: bool = True) -> pd.Series:
    """
    Intraday VWAP - resets each day
    This is THE institutional benchmark
    """
    typical_price = (high + low + close) / 3

    if reset_daily:
        # Reset VWAP each day
        date = close.index.date
        cumsum_tpv = (typical_price * volume).groupby(date).cumsum()
        cumsum_vol = volume.groupby(date).cumsum()
    else:
        cumsum_tpv = (typical_price * volume).cumsum()
        cumsum_vol = volume.cumsum()

    vwap = cumsum_tpv / cumsum_vol
    return vwap


def opening_range(data: pd.DataFrame, minutes: int = 30,
                  session_start_hour: int = 6) -> pd.DataFrame:
    """
    Calculate opening range (first N minutes of session)

    Returns DataFrame with:
    - or_high: High of opening range
    - or_low: Low of opening range
    - or_mid: Midpoint
    - or_size: Size of range
    - in_or: Whether current bar is in opening range period
    """
    result = data.copy()

    # Identify session start (first bar of each day at session start hour)
    result['date'] = result.index.date
    result['hour'] = result.index.hour
    result['minute'] = result.index.minute

    # Calculate minutes since session start
    session_start_time = session_start_hour * 60  # Convert to minutes
    result['time_minutes'] = result['hour'] * 60 + result['minute']
    result['minutes_since_start'] = result['time_minutes'] - session_start_time

    # Mark bars in opening range
    result['in_or'] = (result['minutes_since_start'] >= 0) & \
                      (result['minutes_since_start'] < minutes)

    # Calculate OR high/low for each day
    or_high = result[result['in_or']].groupby('date')['high'].transform('max')
    or_low = result[result['in_or']].groupby('date')['low'].transform('min')

    # Forward fill for rest of day
    result['or_high'] = result.groupby('date')['high'].transform(
        lambda x: x[result.loc[x.index, 'in_or']].max() if result.loc[x.index, 'in_or'].any() else np.nan
    )
    result['or_low'] = result.groupby('date')['low'].transform(
        lambda x: x[result.loc[x.index, 'in_or']].min() if result.loc[x.index, 'in_or'].any() else np.nan
    )

    # Fill forward for entire day
    result['or_high'] = result.groupby('date')['or_high'].ffill()
    result['or_low'] = result.groupby('date')['or_low'].ffill()

    result['or_mid'] = (result['or_high'] + result['or_low']) / 2
    result['or_size'] = result['or_high'] - result['or_low']

    # Clean up temporary columns
    result = result.drop(['date', 'hour', 'minute', 'time_minutes',
                         'minutes_since_start'], axis=1)

    return result[['or_high', 'or_low', 'or_mid', 'or_size', 'in_or']]


def first_hour_momentum(data: pd.DataFrame, session_start_hour: int = 6) -> pd.Series:
    """
    Calculate first hour price change (%)
    Positive = bullish day, Negative = bearish day
    """
    df = data.copy()
    df['date'] = df.index.date
    df['hour'] = df.index.hour

    # Get first bar and bar at hour 1
    first_bar = df[df['hour'] == session_start_hour].groupby('date')['open'].first()
    hour1_bar = df[df['hour'] == session_start_hour + 1].groupby('date')['close'].first()

    # Calculate % change
    first_hour_change = ((hour1_bar - first_bar) / first_bar * 100)

    # Map back to original index
    df['first_hour_pct'] = df['date'].map(first_hour_change)
    df['first_hour_pct'] = df.groupby('date')['first_hour_pct'].ffill()

    return df['first_hour_pct']


def previous_day_levels(data: pd.DataFrame) -> pd.DataFrame:
    """
    Previous day high, low, close
    Key support/resistance levels
    """
    result = data.copy()
    result['date'] = result.index.date

    # Calculate previous day levels
    daily = result.groupby('date').agg({
        'high': 'max',
        'low': 'min',
        'close': 'last'
    })

    daily = daily.shift(1)  # Shift to previous day
    daily.columns = ['prev_high', 'prev_low', 'prev_close']

    # Map back
    result = result.join(daily, on='date')
    result = result.drop('date', axis=1)

    return result[['prev_high', 'prev_low', 'prev_close']]


def ema(series: pd.Series, period: int) -> pd.Series:
    """Fast EMA for trend detection"""
    return series.ewm(span=period, adjust=False).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range"""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def calculate_professional_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Calculate all indicators for professional DAX trading

    Focus on:
    - VWAP (institutional anchor)
    - Opening Range (ORB setups)
    - First hour momentum (day direction)
    - Previous day levels (support/resistance)
    - EMAs (trend)
    - ATR (stops/targets)
    """
    data = df.copy()

    # Core indicators
    data['VWAP'] = vwap_intraday(data['high'], data['low'], data['close'],
                                  data['volume'], reset_daily=True)

    # Opening Range (30 min by default)
    session_start = int(config['session']['start_time'].split(':')[0])
    or_data = opening_range(data, minutes=30, session_start_hour=session_start)
    for col in or_data.columns:
        data[col] = or_data[col]

    # First hour momentum
    data['first_hour_pct'] = first_hour_momentum(data, session_start_hour=session_start)

    # Previous day levels
    prev_levels = previous_day_levels(data)
    for col in prev_levels.columns:
        data[col] = prev_levels[col]

    # EMAs for trend
    data['EMA_20'] = ema(data['close'], 20)
    data['EMA_50'] = ema(data['close'], 50)

    # ATR for stops/targets
    data['ATR'] = atr(data['high'], data['low'], data['close'], 14)

    # ATR Z-score (for volatility filtering)
    atr_mean = data['ATR'].rolling(window=100).mean()
    atr_std = data['ATR'].rolling(window=100).std()
    data['ATR_ZScore'] = (data['ATR'] - atr_mean) / atr_std

    # Trend direction (simple: price vs EMAs)
    data['uptrend'] = data['close'] > data['EMA_50']
    data['strong_uptrend'] = (data['close'] > data['EMA_20']) & \
                              (data['EMA_20'] > data['EMA_50'])
    data['downtrend'] = data['close'] < data['EMA_50']
    data['strong_downtrend'] = (data['close'] < data['EMA_20']) & \
                                (data['EMA_20'] < data['EMA_50'])

    # VWAP position
    data['above_vwap'] = data['close'] > data['VWAP']
    data['below_vwap'] = data['close'] < data['VWAP']
    data['vwap_distance'] = (data['close'] - data['VWAP']) / data['VWAP'] * 100

    # ORB breakout flags
    data['orb_long_signal'] = data['close'] > data['or_high']
    data['orb_short_signal'] = data['close'] < data['or_low']

    return data
