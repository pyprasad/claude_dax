"""
Backtesting Engine for ARI Strategy
Handles position management, order execution, and trade tracking
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import List, Dict, Optional


class Position:
    """Represents an open trading position"""

    def __init__(self, entry_time, entry_price, size, direction, signal_type,
                 stop_loss, tp1, tp2, trailing_stop_dist, atr):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.size = size
        self.direction = direction  # 1 = long, -1 = short
        self.signal_type = signal_type
        self.stop_loss = stop_loss
        self.tp1 = tp1
        self.tp2 = tp2
        self.trailing_stop_dist = trailing_stop_dist
        self.atr = atr

        self.current_size = size
        self.tp1_hit = False
        self.trailing_active = False
        self.trailing_stop = stop_loss
        self.highest_price = entry_price if direction == 1 else entry_price
        self.lowest_price = entry_price if direction == -1 else entry_price

        self.exit_time = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl = 0.0
        self.mae = 0.0  # Maximum Adverse Excursion
        self.mfe = 0.0  # Maximum Favorable Excursion

    def update_extremes(self, high, low):
        """Update highest/lowest prices for MAE/MFE tracking"""
        self.highest_price = max(self.highest_price, high)
        self.lowest_price = min(self.lowest_price, low)

        if self.direction == 1:  # Long
            self.mfe = max(self.mfe, self.highest_price - self.entry_price)
            self.mae = max(self.mae, self.entry_price - self.lowest_price)
        else:  # Short
            self.mfe = max(self.mfe, self.entry_price - self.lowest_price)
            self.mae = max(self.mae, self.highest_price - self.entry_price)

    def update_trailing_stop(self, current_price):
        """Update trailing stop if conditions met"""
        if not self.trailing_active:
            return

        if self.direction == 1:  # Long
            new_trail = current_price - self.trailing_stop_dist
            self.trailing_stop = max(self.trailing_stop, new_trail)
        else:  # Short
            new_trail = current_price + self.trailing_stop_dist
            self.trailing_stop = min(self.trailing_stop, new_trail)

    def check_exit(self, timestamp, open_price, high, low, close, regime) -> Optional[Dict]:
        """
        Check if position should be exited

        Returns:
            Exit info dict if exit triggered, None otherwise
        """
        # Check stop loss (using low for long, high for short)
        if self.direction == 1:
            if low <= self.stop_loss:
                return self._create_exit(timestamp, self.stop_loss, self.current_size, 'STOP_LOSS')
            # Check trailing stop
            if self.trailing_active and low <= self.trailing_stop:
                return self._create_exit(timestamp, self.trailing_stop, self.current_size, 'TRAILING_STOP')
        else:
            if high >= self.stop_loss:
                return self._create_exit(timestamp, self.stop_loss, self.current_size, 'STOP_LOSS')
            # Check trailing stop
            if self.trailing_active and high >= self.trailing_stop:
                return self._create_exit(timestamp, self.trailing_stop, self.current_size, 'TRAILING_STOP')

        # Check TP1 (use high for long, low for short)
        if not self.tp1_hit:
            if self.direction == 1 and high >= self.tp1:
                return self._create_exit(timestamp, self.tp1, self.current_size // 2, 'TP1')
            elif self.direction == -1 and low <= self.tp1:
                return self._create_exit(timestamp, self.tp1, self.current_size // 2, 'TP1')

        # Check TP2 (if TP1 already hit)
        if self.tp1_hit:
            if self.direction == 1 and high >= self.tp2:
                return self._create_exit(timestamp, self.tp2, self.current_size, 'TP2')
            elif self.direction == -1 and low <= self.tp2:
                return self._create_exit(timestamp, self.tp2, self.current_size, 'TP2')

        # Check regime change exit
        if self._should_exit_on_regime_change(regime):
            return self._create_exit(timestamp, close, self.current_size, 'REGIME_CHANGE')

        return None

    def _should_exit_on_regime_change(self, current_regime) -> bool:
        """Check if regime change should trigger exit"""
        if 'MOMENTUM' in self.signal_type and current_regime == 'MEAN_REVERSION':
            return True
        if 'MEAN_REV' in self.signal_type and current_regime == 'MOMENTUM':
            return True
        return False

    def _create_exit(self, timestamp, price, size, reason):
        """Create exit info dictionary"""
        return {
            'timestamp': timestamp,
            'price': price,
            'size': size,
            'reason': reason
        }

    def calculate_pnl(self, exit_price, size, commission, slippage):
        """Calculate P&L for this exit"""
        gross_pnl = (exit_price - self.entry_price) * self.direction * size
        total_commission = commission * 2 * size  # Entry + exit
        total_slippage = slippage * 2 * size
        net_pnl = gross_pnl - total_commission - total_slippage
        return net_pnl


class BacktestEngine:
    """Main backtesting engine"""

    def __init__(self, config: dict):
        self.config = config
        self.initial_capital = config['backtest']['initial_capital']
        self.equity = self.initial_capital
        self.peak_equity = self.initial_capital

        self.positions: List[Position] = []
        self.current_position: Optional[Position] = None
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []

        # Risk controls
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.trades_today = 0
        self.last_trade_date = None

        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

    def reset_daily_counters(self, current_date):
        """Reset daily tracking variables"""
        if self.last_trade_date != current_date:
            self.daily_loss = 0.0
            self.trades_today = 0
            self.last_trade_date = current_date

    def check_risk_controls(self, current_date) -> bool:
        """Check if risk controls allow trading"""
        self.reset_daily_counters(current_date)

        # Daily loss limit
        max_daily_loss = self.config['strategy']['controls']['daily_loss_limit_pct'] / 100
        if self.daily_loss < -self.initial_capital * max_daily_loss:
            return False

        # Consecutive losses
        max_consecutive = self.config['strategy']['controls']['max_consecutive_losses']
        if self.consecutive_losses >= max_consecutive:
            return False

        # Max positions
        max_positions = self.config['strategy']['controls']['max_positions']
        if self.current_position is not None:  # Already have a position
            return False

        return True

    def calculate_slippage(self, atr: float) -> float:
        """Calculate realistic slippage based on ATR"""
        slippage_mult = self.config['backtest']['slippage_atr_mult']
        return atr * slippage_mult

    def open_position(self, timestamp, signal_row, signal_type, direction,
                      position_size, stops_targets):
        """Open a new position"""
        entry_price = signal_row['open']  # Enter at next bar open
        atr = signal_row['ATR']
        slippage = self.calculate_slippage(atr)

        # Apply slippage
        if direction == 1:
            entry_price += slippage
        else:
            entry_price -= slippage

        # Create position
        position = Position(
            entry_time=timestamp,
            entry_price=entry_price,
            size=position_size,
            direction=direction,
            signal_type=signal_type,
            stop_loss=stops_targets['stop_loss'],
            tp1=stops_targets['tp1'],
            tp2=stops_targets['tp2'],
            trailing_stop_dist=stops_targets['trailing_stop_distance'],
            atr=atr
        )

        self.current_position = position
        self.positions.append(position)

    def close_position(self, exit_info, current_row):
        """Close current position"""
        if self.current_position is None:
            return

        pos = self.current_position
        exit_price = exit_info['price']
        exit_size = exit_info['size']
        exit_reason = exit_info['reason']

        # Apply slippage
        atr = current_row['ATR']
        slippage = self.calculate_slippage(atr)
        if pos.direction == 1:
            exit_price -= slippage
        else:
            exit_price += slippage

        # Calculate P&L
        commission = self.config['backtest']['commission_per_contract']
        point_value = self.config['backtest']['point_value']

        gross_pnl = (exit_price - pos.entry_price) * pos.direction * exit_size * point_value
        total_commission = commission * 2 * exit_size
        total_slippage = slippage * exit_size * point_value * 2
        net_pnl = gross_pnl - total_commission - total_slippage

        # Update equity
        self.equity += net_pnl
        self.peak_equity = max(self.peak_equity, self.equity)

        # Track daily loss
        if net_pnl < 0:
            self.daily_loss += net_pnl

        # Update consecutive losses/wins
        if net_pnl < 0:
            self.consecutive_losses += 1
            self.losing_trades += 1
        else:
            self.consecutive_losses = 0
            self.winning_trades += 1

        # Handle partial exit (TP1)
        if exit_reason == 'TP1':
            pos.tp1_hit = True
            pos.current_size -= exit_size
            pos.trailing_active = True
            pos.trailing_stop = pos.stop_loss  # Initialize trailing stop

            # Lock in minimum profit
            min_profit_r = self.config['strategy']['risk']['min_profit_lock_r']
            if pos.direction == 1:
                pos.stop_loss = max(pos.stop_loss, pos.entry_price + pos.atr * min_profit_r)
            else:
                pos.stop_loss = min(pos.stop_loss, pos.entry_price - pos.atr * min_profit_r)
        else:
            # Full exit
            pos.current_size = 0

        # Record trade
        trade_record = {
            'entry_time': pos.entry_time,
            'exit_time': exit_info['timestamp'],
            'signal_type': pos.signal_type,
            'direction': 'LONG' if pos.direction == 1 else 'SHORT',
            'entry_price': pos.entry_price,
            'exit_price': exit_price,
            'size': exit_size,
            'pnl': net_pnl,
            'pnl_pct': (net_pnl / self.initial_capital) * 100,
            'exit_reason': exit_reason,
            'mae': pos.mae,
            'mfe': pos.mfe,
            'holding_time': (exit_info['timestamp'] - pos.entry_time).total_seconds() / 60,  # minutes
            'equity': self.equity
        }
        self.trades.append(trade_record)
        self.total_trades += 1

        # If fully closed, clear current position
        if pos.current_size == 0:
            self.current_position = None

    def should_close_at_session_end(self, timestamp) -> bool:
        """Check if should close position at end of session"""
        session_end = time.fromisoformat(self.config['session']['end_time'])
        exit_buffer = self.config['session']['exit_buffer']

        # Calculate exit time (session_end - buffer)
        end_dt = datetime.combine(timestamp.date(), session_end)
        exit_time = (end_dt - pd.Timedelta(minutes=exit_buffer)).time()

        return timestamp.time() >= exit_time

    def run_backtest(self, signals_df, strategy) -> Dict:
        """
        Run full backtest simulation

        Args:
            signals_df: DataFrame with signals and indicators
            strategy: ARIStrategy instance

        Returns:
            Dictionary with backtest results
        """
        print("Starting backtest...")

        for i in range(1, len(signals_df)):
            current_row = signals_df.iloc[i]
            prev_row = signals_df.iloc[i - 1]
            timestamp = signals_df.index[i]
            current_date = timestamp.date()

            # Update equity curve
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': self.equity,
                'drawdown': (self.peak_equity - self.equity) / self.peak_equity * 100
            })

            # Manage existing position
            if self.current_position is not None:
                pos = self.current_position

                # Update MAE/MFE
                pos.update_extremes(current_row['high'], current_row['low'])

                # Update trailing stop
                pos.update_trailing_stop(current_row['close'])

                # Check for exit
                exit_info = pos.check_exit(
                    timestamp,
                    current_row['open'],
                    current_row['high'],
                    current_row['low'],
                    current_row['close'],
                    current_row['Regime']
                )

                if exit_info:
                    self.close_position(exit_info, current_row)

                # Force close at session end
                if self.current_position and self.should_close_at_session_end(timestamp):
                    exit_info = {
                        'timestamp': timestamp,
                        'price': current_row['close'],
                        'size': self.current_position.current_size,
                        'reason': 'SESSION_END'
                    }
                    self.close_position(exit_info, current_row)

            # Check for new entry signal on PREVIOUS bar (only if no position)
            # This prevents lookahead bias: signal detected at bar N close, entry at bar N+1 open
            if prev_row['Signal'] != 0 and self.current_position is None:
                if self.check_risk_controls(current_date):
                    signal_type = prev_row['Signal_Type']
                    direction = int(prev_row['Signal'])

                    # Calculate position size using prev bar's ATR (known at signal time)
                    position_size = strategy.calculate_position_size(
                        self.equity,
                        prev_row['ATR'],
                        signal_type,
                        prev_row['ATR_ZScore']
                    )

                    # Calculate stops and targets using current bar's open (entry price)
                    stops_targets = strategy.calculate_stops_and_targets(
                        current_row['open'],  # Enter at current bar open (next bar after signal)
                        prev_row['ATR'],
                        signal_type,
                        direction
                    )

                    # Open position (executed at current bar open, signal was on prev bar)
                    self.open_position(
                        timestamp,
                        current_row,
                        signal_type,
                        direction,
                        position_size,
                        stops_targets
                    )

        # Force close any remaining position at end
        if self.current_position is not None:
            last_row = signals_df.iloc[-1]
            exit_info = {
                'timestamp': signals_df.index[-1],
                'price': last_row['close'],
                'size': self.current_position.current_size,
                'reason': 'END_OF_DATA'
            }
            self.close_position(exit_info, last_row)

        print(f"Backtest complete. Total trades: {self.total_trades}")

        return self.generate_results()

    def generate_results(self) -> Dict:
        """Generate backtest results summary"""
        if len(self.trades) == 0:
            return {'error': 'No trades executed'}

        trades_df = pd.DataFrame(self.trades)
        equity_df = pd.DataFrame(self.equity_curve)

        # Calculate metrics
        total_pnl = trades_df['pnl'].sum()
        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] < 0]

        win_rate = len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0

        max_dd = equity_df['drawdown'].max()
        avg_holding_time = trades_df['holding_time'].mean()

        # Calculate CAGR
        start_date = trades_df['entry_time'].min()
        end_date = trades_df['exit_time'].max()
        years = (end_date - start_date).days / 365.25
        cagr = ((self.equity / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Expectancy
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

        results = {
            'total_trades': len(trades_df),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'total_return_pct': (total_pnl / self.initial_capital) * 100,
            'cagr': cagr,
            'max_drawdown': max_dd,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'expectancy': expectancy,
            'avg_holding_time_minutes': avg_holding_time,
            'initial_capital': self.initial_capital,
            'final_equity': self.equity,
            'trades_df': trades_df,
            'equity_df': equity_df
        }

        return results
