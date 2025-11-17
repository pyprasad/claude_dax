"""
Technical Indicators for ARI Strategy
Optimized, vectorized implementations using pandas/numpy
"""

import pandas as pd
import numpy as np


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range"""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi_values = 100 - (100 / (1 + rs))
    return rsi_values


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index"""
    # Calculate True Range
    tr = atr(high, low, close, period=1)

    # Directional Movement
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)

    # Smoothed averages
    atr_smooth = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr_smooth)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_smooth)

    # ADX calculation
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_values = dx.rolling(window=period).mean()

    return adx_values


def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> tuple:
    """Bollinger Bands - returns (upper, middle, lower)"""
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Volume Weighted Average Price (intraday)"""
    typical_price = (high + low + close) / 3
    cumulative_tp_volume = (typical_price * volume).cumsum()
    cumulative_volume = volume.cumsum()
    return cumulative_tp_volume / cumulative_volume


def rolling_high(series: pd.Series, period: int) -> pd.Series:
    """Rolling highest value"""
    return series.rolling(window=period).max()


def rolling_low(series: pd.Series, period: int) -> pd.Series:
    """Rolling lowest value"""
    return series.rolling(window=period).min()


def z_score(series: pd.Series, period: int) -> pd.Series:
    """Z-score normalization"""
    mean = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    return (series - mean) / std


def calculate_all_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Calculate all required indicators for the strategy

    Args:
        df: DataFrame with OHLCV data
        config: Strategy configuration dictionary

    Returns:
        DataFrame with all indicators added
    """
    data = df.copy()

    # Extract parameters
    adx_period = config['strategy']['adx_period']
    fast_ma = config['strategy']['fast_ma_period']
    slow_ma = config['strategy']['slow_ma_period']
    atr_period = config['strategy']['risk']['atr_period']
    rsi_period = config['strategy']['momentum']['rsi_period']
    rsi2_period = config['strategy']['mean_reversion']['rsi2_period']
    bb_period = config['strategy']['mean_reversion']['bb_period']
    bb_std = config['strategy']['mean_reversion']['bb_std']

    # Core indicators
    data['ATR'] = atr(data['high'], data['low'], data['close'], atr_period)
    data['ADX'] = adx(data['high'], data['low'], data['close'], adx_period)
    data['RSI'] = rsi(data['close'], rsi_period)
    data['RSI2'] = rsi(data['close'], rsi2_period)

    # Moving Averages
    data['SMA_50'] = sma(data['close'], fast_ma)
    data['SMA_200'] = sma(data['close'], slow_ma)

    # Bollinger Bands
    data['BB_Upper'], data['BB_Middle'], data['BB_Lower'] = bollinger_bands(
        data['close'], bb_period, bb_std
    )

    # VWAP
    data['VWAP'] = vwap(data['high'], data['low'], data['close'], data['volume'])

    # Volume indicators
    volume_ma = config['strategy']['momentum']['volume_ma_period']
    data['Volume_MA'] = sma(data['volume'], volume_ma)

    # Breakout levels
    breakout_period = config['strategy']['momentum']['breakout_lookback']
    data['Rolling_High'] = rolling_high(data['high'], breakout_period)
    data['Rolling_Low'] = rolling_low(data['low'], breakout_period)

    # ATR expansion check
    atr_exp_period = config['strategy']['momentum']['atr_expansion_period']
    data['ATR_MA'] = sma(data['ATR'], atr_exp_period)

    # ATR Z-score for volatility filter
    zscore_period = config['strategy']['volatility']['atr_zscore_period']
    data['ATR_ZScore'] = z_score(data['ATR'], zscore_period)

    # Regime detection helpers
    data['Trend_Up'] = data['SMA_50'] > data['SMA_200']
    data['Price_Above_MA200'] = data['close'] > data['SMA_200']

    # Bullish/Bearish candle
    data['Bullish_Candle'] = data['close'] > data['open']
    data['Bearish_Candle'] = data['close'] < data['open']

    return data


def detect_rsi_divergence(rsi: pd.Series, price: pd.Series, lookback: int = 5) -> tuple:
    """
    Detect bullish/bearish RSI divergence

    Returns:
        (bullish_divergence, bearish_divergence) as boolean Series
    """
    # Bullish: Price making lower low, but RSI making higher low
    price_lower_low = (price < price.shift(lookback)) & (price.shift(lookback) == price.rolling(lookback*2).min())
    rsi_higher_low = (rsi > rsi.shift(lookback))
    bullish_div = price_lower_low & rsi_higher_low

    # Bearish: Price making higher high, but RSI making lower high
    price_higher_high = (price > price.shift(lookback)) & (price.shift(lookback) == price.rolling(lookback*2).max())
    rsi_lower_high = (rsi < rsi.shift(lookback))
    bearish_div = price_higher_high & rsi_lower_high

    return bullish_div, bearish_div
