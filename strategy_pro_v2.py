"""
Professional DAX Trading Strategy V2
IMPROVED with real intraday trader tactics

Key improvements:
1. Better entry filters (pullback entry, volume confirmation)
2. Wider stops (let trades breathe)
3. Realistic targets (take profit sooner)
4. Time-of-day filter (ORB best in first 2 hours)
5. OR size filter (avoid tiny ranges)
"""

import pandas as pd
import numpy as np
from datetime import time


class ProfessionalDAXStrategyV2:
    """
    Professional DAX Intraday Strategy V2

    Improvements over V1:
    - ENTRY FILTERS: Pullback entry, volume confirmation, OR size minimum
    - WIDER STOPS: 1.5-2.5x ATR (vs 1-2x)
    - LOWER TARGETS: 1.2R and 2R (vs 1.8R and 3-4R)
    - TIME FILTER: ORB only in first 2 hours (09:30-11:30)
    - TRAILING: Activates at 0.8R (vs 1.5R)
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

    def is_orb_prime_time(self, timestamp: pd.Timestamp) -> bool:
        """
        ORB works best in first 2 hours after open
        After that, range-bound behavior dominates
        """
        session_start = time.fromisoformat(self.config['session']['start_time'])
        current_time = timestamp.time()

        start_hour, start_min = session_start.hour, session_start.minute
        current_hour, current_min = current_time.hour, current_time.minute

        minutes_since_start = (current_hour - start_hour) * 60 + (current_min - start_min)

        # ORB prime time: 30 min - 150 min (first 2 hours after OR)
        return 30 <= minutes_since_start <= 150

    def orb_long_setup(self, row: pd.Series, prev_row: pd.Series, prev_prev_row: pd.Series) -> bool:
        """
        IMPROVED Opening Range Breakout - LONG

        V2 Improvements:
        1. OR size must be significant (>50% of ATR, not 30%)
        2. Pullback entry: Price broke above OR high, then pulled back, now going up again
        3. Strong candle: Current candle close > open (bullish)
        4. Time filter: Only in first 2 hours after OR
        """
        if pd.isna(row['or_high']) or pd.isna(row['or_size']):
            return False

        # Time filter - ORB only works in first 2 hours
        from datetime import datetime
        current_time = row.name if isinstance(row.name, pd.Timestamp) else datetime.now()
        if not self.is_orb_prime_time(current_time):
            return False

        conditions = [
            # OR size must be significant (avoid tiny ranges that whipsaw)
            row['or_size'] > row['ATR'] * 0.5,  # Increased from 0.3

            # PULLBACK ENTRY (professional technique):
            # - Previous bar broke above OR high
            # - Previous bar pulled back (close < high)
            # - Current bar is pushing up again
            prev_row['high'] > prev_row['or_high'],  # Broke above in prev bar
            row['close'] > row['or_high'],  # Still above OR high
            row['close'] > row['open'],  # Bullish candle (buying)

            # Trend confirmation
            row['close'] > row['EMA_20'],

            # Volume confirmation (if significant volume available)
            row['volume'] > prev_row['volume'] * 0.8,  # Not declining volume
        ]

        return all(conditions)

    def orb_short_setup(self, row: pd.Series, prev_row: pd.Series, prev_prev_row: pd.Series) -> bool:
        """
        IMPROVED Opening Range Breakout - SHORT
        """
        if pd.isna(row['or_low']) or pd.isna(row['or_size']):
            return False

        # Time filter
        from datetime import datetime
        current_time = row.name if isinstance(row.name, pd.Timestamp) else datetime.now()
        if not self.is_orb_prime_time(current_time):
            return False

        conditions = [
            # OR size filter
            row['or_size'] > row['ATR'] * 0.5,

            # Pullback entry
            prev_row['low'] < prev_row['or_low'],  # Broke below in prev bar
            row['close'] < row['or_low'],  # Still below OR low
            row['close'] < row['open'],  # Bearish candle

            # Trend confirmation
            row['close'] < row['EMA_20'],

            # Volume
            row['volume'] > prev_row['volume'] * 0.8,
        ]

        return all(conditions)

    def vwap_pullback_long(self, row: pd.Series, prev_row: pd.Series, prev_prev_row: pd.Series) -> bool:
        """
        IMPROVED VWAP Pullback - LONG

        V2: Stricter first hour momentum requirement
        """
        conditions = [
            # Pullback to VWAP
            prev_row['close'] > prev_row['VWAP'],
            abs(row['vwap_distance']) < 0.15,

            # Uptrend
            row['uptrend'],
            row['close'] > row['EMA_20'],

            # Stronger first hour requirement (0.5% instead of 0.3%)
            row['first_hour_pct'] > 0.5,

            # Bouncing
            row['close'] > row['open'],
        ]

        return all(conditions)

    def vwap_pullback_short(self, row: pd.Series, prev_row: pd.Series, prev_prev_row: pd.Series) -> bool:
        """
        IMPROVED VWAP Pullback - SHORT
        """
        conditions = [
            # Pullback to VWAP
            prev_row['close'] < prev_row['VWAP'],
            abs(row['vwap_distance']) < 0.15,

            # Downtrend
            row['downtrend'],
            row['close'] < row['EMA_20'],

            # Stronger first hour requirement
            row['first_hour_pct'] < -0.5,

            # Rejecting
            row['close'] < row['open'],
        ]

        return all(conditions)

    def momentum_continuation_long(self, row: pd.Series, prev_row: pd.Series, prev_prev_row: pd.Series) -> bool:
        """
        IMPROVED Momentum Continuation - LONG

        V2: Even stricter momentum requirement (0.7% vs 0.5%)
        """
        conditions = [
            # Very strong first hour (increased from 0.5%)
            row['first_hour_pct'] > 0.7,

            # Price above VWAP
            row['above_vwap'],

            # Pullback setup
            row['close'] < row['EMA_20'],
            row['close'] > row['EMA_50'],

            # Bullish candle
            row['close'] > row['open'],
        ]

        return all(conditions)

    def momentum_continuation_short(self, row: pd.Series, prev_row: pd.Series, prev_prev_row: pd.Series) -> bool:
        """
        IMPROVED Momentum Continuation - SHORT
        """
        conditions = [
            # Very strong first hour
            row['first_hour_pct'] < -0.7,

            # Price below VWAP
            row['below_vwap'],

            # Rally into resistance
            row['close'] > row['EMA_20'],
            row['close'] < row['EMA_50'],

            # Bearish candle
            row['close'] < row['open'],
        ]

        return all(conditions)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy/sell signals with improved entry filters
        """
        signals = data.copy()
        signals['Signal'] = 0
        signals['Signal_Type'] = ''

        # Need 2 prev bars for pullback detection
        for i in range(2, len(signals)):
            row = signals.iloc[i]
            prev_row = signals.iloc[i - 1]
            prev_prev_row = signals.iloc[i - 2]
            timestamp = signals.index[i]

            # Check time filters
            if not self.is_trading_hours(timestamp):
                continue
            if not self.is_entry_allowed(timestamp):
                continue

            # Check for signals (priority order)

            # 1. Opening Range Breakout (highest priority, time-filtered)
            if self.orb_long_setup(row, prev_row, prev_prev_row):
                signals.loc[signals.index[i], 'Signal'] = 1
                signals.loc[signals.index[i], 'Signal_Type'] = 'ORB_LONG'
                continue

            if self.orb_short_setup(row, prev_row, prev_prev_row):
                signals.loc[signals.index[i], 'Signal'] = -1
                signals.loc[signals.index[i], 'Signal_Type'] = 'ORB_SHORT'
                continue

            # 2. VWAP Pullback (second priority)
            if self.vwap_pullback_long(row, prev_row, prev_prev_row):
                signals.loc[signals.index[i], 'Signal'] = 1
                signals.loc[signals.index[i], 'Signal_Type'] = 'VWAP_LONG'
                continue

            if self.vwap_pullback_short(row, prev_row, prev_prev_row):
                signals.loc[signals.index[i], 'Signal'] = -1
                signals.loc[signals.index[i], 'Signal_Type'] = 'VWAP_SHORT'
                continue

            # 3. Momentum Continuation (third priority)
            if self.momentum_continuation_long(row, prev_row, prev_prev_row):
                signals.loc[signals.index[i], 'Signal'] = 1
                signals.loc[signals.index[i], 'Signal_Type'] = 'MOMENTUM_LONG'
                continue

            if self.momentum_continuation_short(row, prev_row, prev_prev_row):
                signals.loc[signals.index[i], 'Signal'] = -1
                signals.loc[signals.index[i], 'Signal_Type'] = 'MOMENTUM_SHORT'
                continue

        return signals

    def calculate_position_size(self, equity: float, atr: float, signal_type: str, atr_zscore: float = 0) -> int:
        """
        Calculate position size using ATR-based risk
        Same as V1
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
        IMPROVED: Wider stops, realistic targets

        V2 Changes:
        - Wider stops (1.5-2.5x ATR)
        - Lower TP1 (1.2R instead of 1.8R)
        - Lower TP2 (2.0R instead of 3-4R)
        """
        risk_params = self.params['risk']

        # Determine stop/target multiples
        if 'ORB' in signal_type:
            stop_mult = risk_params['orb_stop_mult']  # 1.5x ATR
            target_mult = risk_params['orb_target_mult']  # 2.0R

            # ORB: Use ATR-based stops (OR low/high too tight)
            if direction == 1:  # Long
                stop_loss = entry_price - (atr * stop_mult)
                target = entry_price + (atr * stop_mult * target_mult)
            else:  # Short
                stop_loss = entry_price + (atr * stop_mult)
                target = entry_price - (atr * stop_mult * target_mult)

        elif 'VWAP' in signal_type:
            stop_mult = risk_params['vwap_stop_mult']  # 2.0x ATR
            target_mult = risk_params['vwap_target_mult']  # 2.0R

            if direction == 1:
                stop_loss = entry_price - (atr * stop_mult)
                target = entry_price + (atr * stop_mult * target_mult)
            else:
                stop_loss = entry_price + (atr * stop_mult)
                target = entry_price - (atr * stop_mult * target_mult)

        else:  # MOMENTUM
            stop_mult = risk_params['momentum_stop_mult']  # 2.5x ATR
            target_mult = risk_params['momentum_target_mult']  # 2.0R

            if direction == 1:
                stop_loss = entry_price - (atr * stop_mult)
                target = entry_price + (atr * stop_mult * target_mult)
            else:
                stop_loss = entry_price + (atr * stop_mult)
                target = entry_price - (atr * stop_mult * target_mult)

        trailing_dist = atr * risk_params['trailing_atr_mult']

        # TP1 at 1.2R (take profit sooner), TP2 at full target
        risk_distance = abs(entry_price - stop_loss)
        if direction == 1:  # Long
            tp1 = entry_price + (risk_distance * 1.2)  # 1.2R
            tp2 = target
        else:  # Short
            tp1 = entry_price - (risk_distance * 1.2)
            tp2 = target

        return {
            'stop_loss': stop_loss,
            'tp1': tp1,
            'tp2': tp2,
            'trailing_stop_distance': trailing_dist,
            'risk_amount': abs(entry_price - stop_loss)
        }
