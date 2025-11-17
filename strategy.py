"""
Adaptive Regime Intraday (ARI) Strategy
Main signal generation logic
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from indicators import detect_rsi_divergence


class ARIStrategy:
    """Adaptive Regime Intraday Strategy"""

    def __init__(self, config: dict):
        self.config = config
        self.strategy_params = config['strategy']
        self.session_params = config['session']

    def is_trading_hours(self, timestamp: pd.Timestamp) -> bool:
        """Check if within trading session"""
        session_start = time.fromisoformat(self.session_params['start_time'])
        session_end = time.fromisoformat(self.session_params['end_time'])
        current_time = timestamp.time()
        return session_start <= current_time <= session_end

    def is_entry_allowed(self, timestamp: pd.Timestamp) -> bool:
        """Check if new entries are allowed (not too late in session)"""
        entry_cutoff = time.fromisoformat(self.session_params['entry_cutoff'])
        skip_first = self.session_params['skip_first_minutes']
        session_start = time.fromisoformat(self.session_params['start_time'])

        current_time = timestamp.time()

        # Calculate session start + skip period
        start_dt = datetime.combine(timestamp.date(), session_start)
        skip_until = (start_dt + pd.Timedelta(minutes=skip_first)).time()

        return skip_until <= current_time <= entry_cutoff

    def detect_regime(self, row: pd.Series) -> str:
        """
        Detect market regime: MOMENTUM, MEAN_REVERSION, or NO_TRADE

        Args:
            row: Current bar data with indicators

        Returns:
            Regime string
        """
        adx = row['ADX']
        adx_momentum = self.strategy_params['adx_momentum_threshold']
        adx_ranging = self.strategy_params['adx_ranging_threshold']

        if pd.isna(adx):
            return 'NO_TRADE'

        if adx > adx_momentum:
            return 'MOMENTUM'
        elif adx < adx_ranging:
            return 'MEAN_REVERSION'
        else:
            return 'NO_TRADE'  # ADX in between = uncertainty

    def check_volatility_filter(self, row: pd.Series, vix: float = None) -> bool:
        """
        Check if volatility conditions allow trading

        Args:
            row: Current bar data
            vix: VIX/VDAX value (optional, if available)

        Returns:
            True if trading allowed
        """
        # ATR Z-score filter
        atr_zscore_threshold = self.strategy_params['volatility']['atr_zscore_threshold']
        if not pd.isna(row['ATR_ZScore']) and row['ATR_ZScore'] > atr_zscore_threshold:
            return False

        # VIX filter (if provided)
        if vix is not None:
            vix_extreme = self.strategy_params['volatility']['vix_extreme']
            if vix > vix_extreme:
                return False

        return True

    def momentum_long_signal(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """Check if momentum long entry conditions are met"""
        params = self.strategy_params['momentum']

        # All conditions must be true
        conditions = [
            # Regime
            row['ADX'] > self.strategy_params['adx_momentum_threshold'],

            # Trend filter
            row['SMA_50'] > row['SMA_200'],

            # Momentum
            row['RSI'] > params['rsi_min'],
            row['RSI'] < 70,  # Not overbought

            # Breakout
            row['close'] > prev_row['Rolling_High'],

            # Volume confirmation
            row['volume'] > row['Volume_MA'],

            # ATR expansion
            row['ATR'] > row['ATR_MA'] * params['atr_expansion_threshold'],
        ]

        return all(conditions)

    def momentum_short_signal(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """Check if momentum short entry conditions are met"""
        params = self.strategy_params['momentum']

        conditions = [
            # Regime
            row['ADX'] > self.strategy_params['adx_momentum_threshold'],

            # Trend filter
            row['SMA_50'] < row['SMA_200'],

            # Momentum
            row['RSI'] < (100 - params['rsi_min']),
            row['RSI'] > 30,  # Not oversold

            # Breakout
            row['close'] < prev_row['Rolling_Low'],

            # Volume confirmation
            row['volume'] > row['Volume_MA'],

            # ATR expansion
            row['ATR'] > row['ATR_MA'] * params['atr_expansion_threshold'],
        ]

        return all(conditions)

    def mean_reversion_long_signal(self, row: pd.Series, prev_row: pd.Series,
                                     rsi_divergence: bool = False) -> bool:
        """Check if mean-reversion long entry conditions are met"""
        params = self.strategy_params['mean_reversion']

        conditions = [
            # Regime
            row['ADX'] < self.strategy_params['adx_ranging_threshold'],

            # Trend bias (only counter-trend in uptrend)
            row['Price_Above_MA200'],

            # Oversold
            row['RSI2'] < params['rsi2_oversold'],

            # Bollinger Band position
            row['close'] < row['BB_Lower'],

            # Optional: confirmation candle
            row['Bullish_Candle'] if params['require_confirmation_candle'] else True,
        ]

        # Bullish divergence is a bonus, not required
        # But if present, it increases confidence
        if rsi_divergence:
            conditions.append(True)

        return all(conditions)

    def mean_reversion_short_signal(self, row: pd.Series, prev_row: pd.Series,
                                      rsi_divergence: bool = False) -> bool:
        """Check if mean-reversion short entry conditions are met"""
        params = self.strategy_params['mean_reversion']

        conditions = [
            # Regime
            row['ADX'] < self.strategy_params['adx_ranging_threshold'],

            # Trend bias (only counter-trend in downtrend)
            not row['Price_Above_MA200'],

            # Overbought
            row['RSI2'] > params['rsi2_overbought'],

            # Bollinger Band position
            row['close'] > row['BB_Upper'],

            # Optional: confirmation candle
            row['Bearish_Candle'] if params['require_confirmation_candle'] else True,
        ]

        if rsi_divergence:
            conditions.append(True)

        return all(conditions)

    def generate_signals(self, data: pd.DataFrame, vix_data: pd.Series = None) -> pd.DataFrame:
        """
        Generate buy/sell signals for the entire dataset

        Args:
            data: DataFrame with OHLCV and indicators
            vix_data: Optional VIX/VDAX Series aligned with data

        Returns:
            DataFrame with signal columns added
        """
        signals = data.copy()

        # Initialize signal columns
        signals['Signal'] = 0  # 0 = no signal, 1 = long, -1 = short
        signals['Signal_Type'] = ''  # MOMENTUM_LONG, MEAN_REV_LONG, etc.
        signals['Regime'] = ''

        # Detect RSI divergence for entire dataset
        bullish_div, bearish_div = detect_rsi_divergence(
            signals['RSI'],
            signals['close'],
            lookback=self.strategy_params['mean_reversion']['rsi_divergence_period']
        )

        # Iterate through data (skip first row, need previous bar)
        for i in range(1, len(signals)):
            row = signals.iloc[i]
            prev_row = signals.iloc[i - 1]
            timestamp = signals.index[i]

            # Check time filters
            if not self.is_trading_hours(timestamp):
                continue
            if not self.is_entry_allowed(timestamp):
                continue

            # Detect regime
            regime = self.detect_regime(row)
            signals.loc[signals.index[i], 'Regime'] = regime

            if regime == 'NO_TRADE':
                continue

            # Check volatility filter
            vix = vix_data[timestamp] if vix_data is not None and timestamp in vix_data.index else None
            if not self.check_volatility_filter(row, vix):
                continue

            # Check for signals based on regime
            if regime == 'MOMENTUM':
                if self.momentum_long_signal(row, prev_row):
                    signals.loc[signals.index[i], 'Signal'] = 1
                    signals.loc[signals.index[i], 'Signal_Type'] = 'MOMENTUM_LONG'
                elif self.momentum_short_signal(row, prev_row):
                    signals.loc[signals.index[i], 'Signal'] = -1
                    signals.loc[signals.index[i], 'Signal_Type'] = 'MOMENTUM_SHORT'

            elif regime == 'MEAN_REVERSION':
                has_bullish_div = bullish_div.iloc[i] if i < len(bullish_div) else False
                has_bearish_div = bearish_div.iloc[i] if i < len(bearish_div) else False

                if self.mean_reversion_long_signal(row, prev_row, has_bullish_div):
                    signals.loc[signals.index[i], 'Signal'] = 1
                    signals.loc[signals.index[i], 'Signal_Type'] = 'MEAN_REV_LONG'
                elif self.mean_reversion_short_signal(row, prev_row, has_bearish_div):
                    signals.loc[signals.index[i], 'Signal'] = -1
                    signals.loc[signals.index[i], 'Signal_Type'] = 'MEAN_REV_SHORT'

        return signals

    def calculate_position_size(self, equity: float, atr: float,
                                 signal_type: str, atr_zscore: float = 0) -> float:
        """
        Calculate position size using ATR-based risk parity

        Args:
            equity: Current account equity
            atr: Current ATR value
            signal_type: Type of signal (MOMENTUM_LONG, etc.)
            atr_zscore: ATR Z-score for volatility adjustment

        Returns:
            Position size (number of contracts)
        """
        risk_params = self.strategy_params['risk']

        # Base risk per trade
        risk_pct = risk_params['risk_per_trade_pct'] / 100

        # Adjust risk based on ATR Z-score
        if atr_zscore > 2.0:
            risk_pct *= 0.5
        elif atr_zscore > 1.5:
            risk_pct *= 0.75

        risk_amount = equity * risk_pct

        # Determine stop loss multiplier
        if 'MOMENTUM' in signal_type:
            stop_mult = risk_params['momentum_stop_atr_mult']
        else:
            stop_mult = risk_params['mean_reversion_stop_atr_mult']

        # Calculate stop distance
        stop_distance = atr * stop_mult

        # Position size
        point_value = self.config['backtest']['point_value']
        position_size = risk_amount / (stop_distance * point_value)

        return max(1, int(position_size))  # At least 1 contract

    def calculate_stops_and_targets(self, entry_price: float, atr: float,
                                      signal_type: str, direction: int) -> dict:
        """
        Calculate stop loss and take profit levels

        Args:
            entry_price: Entry price
            atr: Current ATR
            signal_type: Type of signal
            direction: 1 for long, -1 for short

        Returns:
            Dictionary with stop_loss, tp1, tp2, trailing_stop levels
        """
        risk_params = self.strategy_params['risk']

        # Stop loss
        if 'MOMENTUM' in signal_type:
            stop_mult = risk_params['momentum_stop_atr_mult']
            tp1_r = risk_params['momentum_tp1_r']
            tp2_r = risk_params['momentum_tp2_r']
        else:
            stop_mult = risk_params['mean_reversion_stop_atr_mult']
            tp1_r = risk_params['mean_reversion_tp_r']
            tp2_r = tp1_r * 1.5  # Scale up for TP2

        stop_distance = atr * stop_mult

        if direction == 1:  # Long
            stop_loss = entry_price - stop_distance
            tp1 = entry_price + (stop_distance * tp1_r)
            tp2 = entry_price + (stop_distance * tp2_r)
        else:  # Short
            stop_loss = entry_price + stop_distance
            tp1 = entry_price - (stop_distance * tp1_r)
            tp2 = entry_price - (stop_distance * tp2_r)

        trailing_stop_dist = atr * risk_params['trailing_atr_mult']

        return {
            'stop_loss': stop_loss,
            'tp1': tp1,
            'tp2': tp2,
            'trailing_stop_distance': trailing_stop_dist,
            'risk_amount': stop_distance
        }
