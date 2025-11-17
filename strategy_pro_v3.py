"""
Professional DAX Trading Strategy V3
RELAXED ENTRY FILTERS + REGIME DETECTION

Changes from V2:
1. Remove pullback requirement - enter on immediate breakout
2. Extend ORB window to full day (not just first 2 hours)
3. Lower OR size minimum to 30% ATR (from 50%)
4. Relax volume filter (optional instead of required)
5. Add REGIME DETECTION - only trade in trending markets
6. Keep V2's risk management (wider stops, realistic targets)
"""

import pandas as pd
import numpy as np
from datetime import time


class ProfessionalDAXStrategyV3:
    """
    Professional DAX Intraday Strategy V3

    V3 Improvements:
    - RELAXED ENTRY: Immediate breakout (no pullback wait)
    - ALL-DAY ORB: Not limited to first 2 hours
    - LOWER FILTERS: 30% OR size minimum (vs 50%)
    - REGIME FILTER: Only trade trending markets (ADX-based)
    - V2 RISK: Keep wider stops, realistic targets, early trailing
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

    def is_trending_market(self, row: pd.Series) -> bool:
        """
        V3 NEW: Regime detection
        Only trade when market is trending (like Q1 2023 was)

        Uses ADX and volatility to detect trending vs ranging
        """
        # Check if regime detection is enabled
        if not self.params.get('use_regime_filter', True):
            return True  # Trade always if disabled

        regime_params = self.params.get('regime', {})

        # ADX threshold (trending if > threshold)
        adx_threshold = regime_params.get('adx_threshold', 20)
        if 'ADX' in row.index and pd.notna(row['ADX']):
            if row['ADX'] < adx_threshold:
                return False  # Market is ranging, skip

        # Volatility threshold (need above-average volatility)
        vol_threshold = regime_params.get('atr_zscore_threshold', -0.5)
        if 'ATR_ZScore' in row.index and pd.notna(row['ATR_ZScore']):
            if row['ATR_ZScore'] < vol_threshold:
                return False  # Too low volatility

        return True

    def orb_long_setup(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        V3 RELAXED Opening Range Breakout - LONG

        Changes from V2:
        1. IMMEDIATE entry (no pullback wait)
        2. ALL DAY (no time filter)
        3. LOWER OR size minimum (30% vs 50%)
        4. OPTIONAL volume (not required)
        """
        if pd.isna(row['or_high']) or pd.isna(row['or_size']):
            return False

        # REGIME CHECK - only trade if trending
        if not self.is_trending_market(row):
            return False

        conditions = [
            # OR size must be significant (RELAXED: 30% vs 50%)
            row['or_size'] > row['ATR'] * 0.3,

            # IMMEDIATE BREAKOUT (V3 change - no pullback wait)
            row['close'] > row['or_high'],  # Just broke above
            prev_row['close'] <= prev_row['or_high'],  # Fresh breakout

            # Trend confirmation
            row['close'] > row['EMA_20'],

            # OPTIONAL volume (not strict)
            # Removed: volume requirement
        ]

        return all(conditions)

    def orb_short_setup(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        V3 RELAXED Opening Range Breakout - SHORT
        """
        if pd.isna(row['or_low']) or pd.isna(row['or_size']):
            return False

        # REGIME CHECK
        if not self.is_trending_market(row):
            return False

        conditions = [
            # OR size filter (RELAXED)
            row['or_size'] > row['ATR'] * 0.3,

            # IMMEDIATE BREAKOUT
            row['close'] < row['or_low'],
            prev_row['close'] >= prev_row['or_low'],

            # Trend confirmation
            row['close'] < row['EMA_20'],
        ]

        return all(conditions)

    def vwap_pullback_long(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        V3 RELAXED VWAP Pullback - LONG

        Relaxed: Lower first hour requirement
        """
        # REGIME CHECK
        if not self.is_trending_market(row):
            return False

        conditions = [
            # Pullback to VWAP
            prev_row['close'] > prev_row['VWAP'],
            abs(row['vwap_distance']) < 0.2,  # RELAXED: 0.2% vs 0.15%

            # Uptrend
            row['uptrend'],
            row['close'] > row['EMA_20'],

            # RELAXED first hour requirement (0.3% vs 0.5%)
            row['first_hour_pct'] > 0.3,

            # Bouncing
            row['close'] > row['open'],
        ]

        return all(conditions)

    def vwap_pullback_short(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        V3 RELAXED VWAP Pullback - SHORT
        """
        # REGIME CHECK
        if not self.is_trending_market(row):
            return False

        conditions = [
            # Pullback to VWAP
            prev_row['close'] < prev_row['VWAP'],
            abs(row['vwap_distance']) < 0.2,

            # Downtrend
            row['downtrend'],
            row['close'] < row['EMA_20'],

            # RELAXED first hour
            row['first_hour_pct'] < -0.3,

            # Rejecting
            row['close'] < row['open'],
        ]

        return all(conditions)

    def momentum_continuation_long(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        V3 RELAXED Momentum Continuation - LONG

        Relaxed: Lower momentum requirement (0.5% vs 0.7%)
        """
        # REGIME CHECK
        if not self.is_trending_market(row):
            return False

        conditions = [
            # RELAXED strong first hour (0.5% vs 0.7%)
            row['first_hour_pct'] > 0.5,

            # Price above VWAP
            row['above_vwap'],

            # Pullback setup
            row['close'] < row['EMA_20'],
            row['close'] > row['EMA_50'],

            # Bullish candle
            row['close'] > row['open'],
        ]

        return all(conditions)

    def momentum_continuation_short(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """
        V3 RELAXED Momentum Continuation - SHORT
        """
        # REGIME CHECK
        if not self.is_trending_market(row):
            return False

        conditions = [
            # RELAXED strong first hour
            row['first_hour_pct'] < -0.5,

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
        Generate buy/sell signals with RELAXED filters + REGIME DETECTION
        """
        signals = data.copy()
        signals['Signal'] = 0
        signals['Signal_Type'] = ''
        signals['Regime_Trending'] = False  # Track regime

        # Need 1 prev bar (not 2 like V2)
        for i in range(1, len(signals)):
            row = signals.iloc[i]
            prev_row = signals.iloc[i - 1]
            timestamp = signals.index[i]

            # Check time filters
            if not self.is_trading_hours(timestamp):
                continue
            if not self.is_entry_allowed(timestamp):
                continue

            # Mark if in trending regime
            signals.loc[signals.index[i], 'Regime_Trending'] = self.is_trending_market(row)

            # Check for signals (priority order)

            # 1. Opening Range Breakout (ALL DAY now, not time-filtered)
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
        Same as V2
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
        Same as V2 (wider stops, realistic targets)
        """
        risk_params = self.params['risk']

        # Determine stop/target multiples
        if 'ORB' in signal_type:
            stop_mult = risk_params['orb_stop_mult']  # 1.5x ATR
            target_mult = risk_params['orb_target_mult']  # 2.0R

            # ORB: Use ATR-based stops
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

        # TP1 at 1.2R, TP2 at full target
        risk_distance = abs(entry_price - stop_loss)
        if direction == 1:  # Long
            tp1 = entry_price + (risk_distance * 1.2)
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
