"""
Professional DAX Trading Strategy
Based on Opening Range Breakout + VWAP + Momentum

This is what real institutional and professional traders use.
NO mean-reversion - pure trend following and momentum.
"""

import pandas as pd
import numpy as np
from datetime import time


class ProfessionalDAXStrategy:
    """
    Professional DAX Intraday Strategy

    Three entry types:
    1. Opening Range Breakout (ORB)
    2. VWAP Pullback Continuation
    3. First Hour Momentum Follow

    Philosophy:
    - Trade WITH the trend, not against it
    - VWAP is institutional anchor - respect it
    - First hour sets the tone - follow it
    - Trends run further than you think
    """

    def __init__(self, config: dict):
        self.config = config
        self.params = config['strategy']

    def is_trading_hours(self, timestamp: pd.Timestamp) -> bool:
        """Check if within trading session"""
        session_start = time.fromisoformat(self.config['session']['start_time'])
        session_end = time.fromisoformat(self.config['session']['end_time'])
        current_time = timestamp.time()
        return session_start <= current_time <= session_end

    def is_entry_allowed(self, timestamp: pd.Timestamp) -> bool:
        """Check if new entries are allowed"""
        entry_cutoff = time.fromisoformat(self.config['session']['entry_cutoff'])
        current_time = timestamp.time()

        # Also check we're past opening range period
        session_start = time.fromisoformat(self.config['session']['start_time'])
        start_hour, start_min = session_start.hour, session_start.minute
        current_hour, current_min = current_time.hour, current_time.minute

        minutes_since_start = (current_hour - start_hour) * 60 + (current_min - start_min)

        # Must be past OR period (30 min) and before cutoff
        or_period = self.params.get('or_period_minutes', 30)
        return (minutes_since_start >= or_period) and (current_time <= entry_cutoff)

    def orb_long_setup(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        Opening Range Breakout - LONG

        Conditions:
        1. Close breaks above OR high
        2. OR size reasonable (not too tight)
        3. Not too late in session
        4. Volume confirmation (if available)
        """
        if pd.isna(row['or_high']) or pd.isna(row['or_size']):
            return False

        conditions = [
            # Breakout condition
            row['close'] > row['or_high'],
            prev_row['close'] <= prev_row['or_high'],  # Fresh breakout

            # OR size filter (avoid tight ranges that whipsaw)
            row['or_size'] > row['ATR'] * 0.3,  # OR must be at least 30% of ATR

            # Trend confirmation (optional but recommended)
            row['close'] > row['EMA_20'],  # Price above short EMA

            # Volume (if checking)
            # row['volume'] > row['Volume_MA'],  # Optional
        ]

        return all(conditions)

    def orb_short_setup(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        Opening Range Breakout - SHORT

        Mirror of long setup
        """
        if pd.isna(row['or_low']) or pd.isna(row['or_size']):
            return False

        conditions = [
            # Breakout condition
            row['close'] < row['or_low'],
            prev_row['close'] >= prev_row['or_low'],  # Fresh breakout

            # OR size filter
            row['or_size'] > row['ATR'] * 0.3,

            # Trend confirmation
            row['close'] < row['EMA_20'],
        ]

        return all(conditions)

    def vwap_pullback_long(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        VWAP Pullback - LONG

        Conditions:
        1. Strong uptrend (price well above VWAP earlier)
        2. Price pulls back to VWAP
        3. Bounce off VWAP (buy the dip)
        4. First hour was bullish
        """
        conditions = [
            # Was above VWAP, now touching it
            prev_row['close'] > prev_row['VWAP'],
            abs(row['vwap_distance']) < 0.15,  # Within 0.15% of VWAP

            # Uptrend
            row['uptrend'],
            row['close'] > row['EMA_20'],

            # First hour was bullish (optional but powerful)
            row['first_hour_pct'] > 0.3,  # First hour up >0.3%

            # Bouncing (bullish candle)
            row['close'] > row['open'],
        ]

        return all(conditions)

    def vwap_pullback_short(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        VWAP Pullback - SHORT

        Mirror of long setup in downtrend
        """
        conditions = [
            # Was below VWAP, now touching it
            prev_row['close'] < prev_row['VWAP'],
            abs(row['vwap_distance']) < 0.15,

            # Downtrend
            row['downtrend'],
            row['close'] < row['EMA_20'],

            # First hour was bearish
            row['first_hour_pct'] < -0.3,

            # Rejecting (bearish candle)
            row['close'] < row['open'],
        ]

        return all(conditions)

    def momentum_continuation_long(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        First Hour Momentum Continuation - LONG

        If first hour strong up, buy ANY pullback rest of day
        """
        conditions = [
            # Strong first hour
            row['first_hour_pct'] > 0.5,  # >0.5% up in first hour

            # Price above VWAP (staying strong)
            row['above_vwap'],

            # Pullback setup (RSI or price dip)
            row['close'] < row['EMA_20'],  # Slight pullback to EMA20
            row['close'] > row['EMA_50'],  # But still above EMA50

            # Bullish candle forming
            row['close'] > row['open'],
        ]

        return all(conditions)

    def momentum_continuation_short(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        First Hour Momentum Continuation - SHORT

        If first hour strong down, sell ANY rally rest of day
        """
        conditions = [
            # Strong first hour
            row['first_hour_pct'] < -0.5,

            # Price below VWAP
            row['below_vwap'],

            # Rally into resistance
            row['close'] > row['EMA_20'],
            row['close'] < row['EMA_50'],

            # Bearish candle forming
            row['close'] < row['open'],
        ]

        return all(conditions)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy/sell signals

        Returns DataFrame with Signal column:
        1 = Long, -1 = Short, 0 = No signal

        And Signal_Type column for identification
        """
        signals = data.copy()
        signals['Signal'] = 0
        signals['Signal_Type'] = ''

        for i in range(1, len(signals)):
            row = signals.iloc[i]
            prev_row = signals.iloc[i - 1]
            timestamp = signals.index[i]

            # Check time filters
            if not self.is_trading_hours(timestamp):
                continue
            if not self.is_entry_allowed(timestamp):
                continue

            # Check for signals (priority order)

            # 1. Opening Range Breakout (highest priority after OR period)
            if self.orb_long_setup(row, prev_row):
                signals.loc[signals.index[i], 'Signal'] = 1
                signals.loc[signals.index[i], 'Signal_Type'] = 'ORB_LONG'
                continue

            if self.orb_short_setup(row, prev_row):
                signals.loc[signals.index[i], 'Signal'] = -1
                signals.loc[signals.index[i], 'Signal_Type'] = 'ORB_SHORT'
                continue

            # 2. VWAP Pullback (second priority)
            if self.vwap_pullback_long(row, prev_row):
                signals.loc[signals.index[i], 'Signal'] = 1
                signals.loc[signals.index[i], 'Signal_Type'] = 'VWAP_LONG'
                continue

            if self.vwap_pullback_short(row, prev_row):
                signals.loc[signals.index[i], 'Signal'] = -1
                signals.loc[signals.index[i], 'Signal_Type'] = 'VWAP_SHORT'
                continue

            # 3. Momentum Continuation (third priority)
            if self.momentum_continuation_long(row, prev_row):
                signals.loc[signals.index[i], 'Signal'] = 1
                signals.loc[signals.index[i], 'Signal_Type'] = 'MOMENTUM_LONG'
                continue

            if self.momentum_continuation_short(row, prev_row):
                signals.loc[signals.index[i], 'Signal'] = -1
                signals.loc[signals.index[i], 'Signal_Type'] = 'MOMENTUM_SHORT'
                continue

        return signals

    def calculate_position_size(self, equity: float, atr: float, signal_type: str, atr_zscore: float = 0) -> int:
        """
        Calculate position size using ATR-based risk

        Professional approach: Risk same $ amount per trade
        Note: atr_zscore parameter included for compatibility but not used
        """
        risk_pct = self.params['risk']['risk_per_trade_pct'] / 100
        risk_amount = equity * risk_pct

        # Stop distance based on signal type
        if 'ORB' in signal_type:
            stop_mult = self.params['risk']['orb_stop_mult']
        elif 'VWAP' in signal_type:
            stop_mult = self.params['risk']['vwap_stop_mult']
        else:  # MOMENTUM
            stop_mult = self.params['risk']['momentum_stop_mult']

        stop_distance = atr * stop_mult
        point_value = self.config['backtest']['point_value']

        position_size = risk_amount / (stop_distance * point_value)
        return max(1, int(position_size))

    def calculate_stops_and_targets(self, entry_price: float, atr: float,
                                      signal_type: str, direction: int,
                                      or_high: float = None, or_low: float = None,
                                      or_size: float = None) -> dict:
        """
        Calculate stop loss and take profit levels

        Professional approach: Use structure (OR, VWAP, levels)
        """
        risk_params = self.params['risk']

        # Determine stop/target multiples based on signal type
        if 'ORB' in signal_type:
            stop_mult = risk_params['orb_stop_mult']
            target_mult = risk_params['orb_target_mult']

            # ORB uses the range itself
            if direction == 1:  # Long
                stop_loss = or_low if or_low else entry_price - (atr * stop_mult)
                target = entry_price + (or_size * target_mult) if or_size else entry_price + (atr * target_mult)
            else:  # Short
                stop_loss = or_high if or_high else entry_price + (atr * stop_mult)
                target = entry_price - (or_size * target_mult) if or_size else entry_price - (atr * target_mult)

        elif 'VWAP' in signal_type:
            stop_mult = risk_params['vwap_stop_mult']
            target_mult = risk_params['vwap_target_mult']

            if direction == 1:
                stop_loss = entry_price - (atr * stop_mult)
                target = entry_price + (atr * target_mult)
            else:
                stop_loss = entry_price + (atr * stop_mult)
                target = entry_price - (atr * target_mult)

        else:  # MOMENTUM
            stop_mult = risk_params['momentum_stop_mult']
            target_mult = risk_params['momentum_target_mult']

            if direction == 1:
                stop_loss = entry_price - (atr * stop_mult)
                target = entry_price + (atr * target_mult)
            else:
                stop_loss = entry_price + (atr * stop_mult)
                target = entry_price - (atr * target_mult)

        trailing_dist = atr * risk_params['trailing_atr_mult']

        # Calculate partial exit levels (tp1 at 60% of target, tp2 at full target)
        target_distance = abs(target - entry_price)
        if direction == 1:  # Long
            tp1 = entry_price + (target_distance * 0.6)
            tp2 = target
        else:  # Short
            tp1 = entry_price - (target_distance * 0.6)
            tp2 = target

        return {
            'stop_loss': stop_loss,
            'tp1': tp1,
            'tp2': tp2,
            'trailing_stop_distance': trailing_dist,
            'risk_amount': abs(entry_price - stop_loss)
        }
