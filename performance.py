"""
Performance Analysis and Reporting
Advanced metrics, visualization, and statistics
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict
import os


class PerformanceAnalyzer:
    """Comprehensive performance analysis"""

    def __init__(self, results: Dict):
        self.results = results
        self.trades_df = results.get('trades_df')
        self.equity_df = results.get('equity_df')

    def print_performance_report(self) -> str:
        """Generate detailed performance report"""
        report = []
        report.append("=" * 80)
        report.append("ADAPTIVE REGIME INTRADAY (ARI) STRATEGY - BACKTEST RESULTS")
        report.append("=" * 80)
        report.append("")

        # Overall Performance
        report.append("OVERALL PERFORMANCE")
        report.append("-" * 80)
        report.append(f"Initial Capital:        ${self.results['initial_capital']:,.2f}")
        report.append(f"Final Equity:           ${self.results['final_equity']:,.2f}")
        report.append(f"Total P&L:              ${self.results['total_pnl']:,.2f}")
        report.append(f"Total Return:           {self.results['total_return_pct']:.2f}%")
        report.append(f"CAGR:                   {self.results['cagr']:.2f}%")
        report.append(f"Max Drawdown:           {self.results['max_drawdown']:.2f}%")
        report.append("")

        # Trade Statistics
        report.append("TRADE STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Trades:           {self.results['total_trades']}")
        report.append(f"Winning Trades:         {self.results['winning_trades']}")
        report.append(f"Losing Trades:          {self.results['losing_trades']}")
        report.append(f"Win Rate:               {self.results['win_rate']:.2f}%")
        report.append(f"Profit Factor:          {self.results['profit_factor']:.2f}")
        report.append(f"Expectancy:             ${self.results['expectancy']:.2f}")
        report.append("")

        # Win/Loss Analysis
        report.append("WIN/LOSS ANALYSIS")
        report.append("-" * 80)
        report.append(f"Average Win:            ${self.results['avg_win']:.2f}")
        report.append(f"Average Loss:           ${self.results['avg_loss']:.2f}")
        report.append(f"Avg Win/Avg Loss:       {abs(self.results['avg_win'] / self.results['avg_loss']):.2f}")
        report.append(f"Largest Win:            ${self.trades_df['pnl'].max():.2f}")
        report.append(f"Largest Loss:           ${self.trades_df['pnl'].min():.2f}")
        report.append("")

        # Holding Time
        report.append("HOLDING TIME")
        report.append("-" * 80)
        report.append(f"Average Holding Time:   {self.results['avg_holding_time_minutes']:.1f} minutes ({self.results['avg_holding_time_minutes']/60:.2f} hours)")
        report.append(f"Min Holding Time:       {self.trades_df['holding_time'].min():.1f} minutes")
        report.append(f"Max Holding Time:       {self.trades_df['holding_time'].max():.1f} minutes")
        report.append("")

        # Strategy Type Breakdown
        report.append("STRATEGY TYPE BREAKDOWN")
        report.append("-" * 80)
        for signal_type in self.trades_df['signal_type'].unique():
            type_trades = self.trades_df[self.trades_df['signal_type'] == signal_type]
            type_wins = len(type_trades[type_trades['pnl'] > 0])
            type_total = len(type_trades)
            type_winrate = (type_wins / type_total * 100) if type_total > 0 else 0
            type_pnl = type_trades['pnl'].sum()

            report.append(f"\n{signal_type}:")
            report.append(f"  Trades: {type_total}, Win Rate: {type_winrate:.1f}%, P&L: ${type_pnl:.2f}")

        report.append("")

        # Risk Metrics
        report.append("RISK METRICS")
        report.append("-" * 80)
        sharpe = self.calculate_sharpe_ratio()
        sortino = self.calculate_sortino_ratio()
        calmar = self.calculate_calmar_ratio()

        report.append(f"Sharpe Ratio:           {sharpe:.2f}")
        report.append(f"Sortino Ratio:          {sortino:.2f}")
        report.append(f"Calmar Ratio:           {calmar:.2f}")
        report.append(f"Max Consecutive Wins:   {self.calculate_max_consecutive_wins()}")
        report.append(f"Max Consecutive Losses: {self.calculate_max_consecutive_losses()}")
        report.append("")

        # MAE/MFE Analysis
        report.append("MAE/MFE ANALYSIS (Maximum Adverse/Favorable Excursion)")
        report.append("-" * 80)
        report.append(f"Average MAE:            ${self.trades_df['mae'].mean():.2f}")
        report.append(f"Average MFE:            ${self.trades_df['mfe'].mean():.2f}")
        report.append(f"MFE/MAE Ratio:          {self.trades_df['mfe'].mean() / self.trades_df['mae'].mean():.2f}")
        report.append("")

        # Monthly Returns
        report.append("MONTHLY RETURNS")
        report.append("-" * 80)
        monthly = self.calculate_monthly_returns()
        if len(monthly) > 0:
            report.append(f"Best Month:             {monthly.max():.2f}%")
            report.append(f"Worst Month:            {monthly.min():.2f}%")
            report.append(f"Avg Monthly Return:     {monthly.mean():.2f}%")
            report.append(f"Positive Months:        {len(monthly[monthly > 0])}/{len(monthly)}")
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate annualized Sharpe Ratio"""
        if len(self.trades_df) == 0:
            return 0

        returns = self.trades_df['pnl'] / self.results['initial_capital']
        excess_returns = returns.mean() - (risk_free_rate / 252)  # Daily risk-free rate
        std_returns = returns.std()

        if std_returns == 0:
            return 0

        # Annualize
        sharpe = (excess_returns / std_returns) * np.sqrt(252)
        return sharpe

    def calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate annualized Sortino Ratio (uses downside deviation)"""
        if len(self.trades_df) == 0:
            return 0

        returns = self.trades_df['pnl'] / self.results['initial_capital']
        excess_returns = returns.mean() - (risk_free_rate / 252)
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0:
            return 0

        downside_std = downside_returns.std()
        if downside_std == 0:
            return 0

        sortino = (excess_returns / downside_std) * np.sqrt(252)
        return sortino

    def calculate_calmar_ratio(self) -> float:
        """Calculate Calmar Ratio (CAGR / Max Drawdown)"""
        if self.results['max_drawdown'] == 0:
            return 0
        return self.results['cagr'] / self.results['max_drawdown']

    def calculate_max_consecutive_wins(self) -> int:
        """Calculate maximum consecutive winning trades"""
        wins = (self.trades_df['pnl'] > 0).astype(int)
        return self._max_consecutive(wins)

    def calculate_max_consecutive_losses(self) -> int:
        """Calculate maximum consecutive losing trades"""
        losses = (self.trades_df['pnl'] < 0).astype(int)
        return self._max_consecutive(losses)

    def _max_consecutive(self, series: pd.Series) -> int:
        """Helper to find max consecutive 1s in series"""
        max_count = 0
        current_count = 0
        for val in series:
            if val == 1:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        return max_count

    def calculate_monthly_returns(self) -> pd.Series:
        """Calculate monthly returns"""
        if len(self.trades_df) == 0:
            return pd.Series()

        monthly = self.trades_df.set_index('exit_time').resample('M')['pnl'].sum()
        monthly_pct = (monthly / self.results['initial_capital']) * 100
        return monthly_pct

    def plot_equity_curve(self, save_path: str = None):
        """Plot equity curve and drawdown"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

        # Equity curve
        ax1.plot(self.equity_df['timestamp'], self.equity_df['equity'], linewidth=2, color='#2E86AB')
        ax1.axhline(y=self.results['initial_capital'], color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
        ax1.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
        ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Drawdown
        ax2.fill_between(self.equity_df['timestamp'], 0, -self.equity_df['drawdown'],
                         color='#A23B72', alpha=0.6)
        ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax2.set_title('Drawdown', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Equity curve saved to {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_monthly_returns(self, save_path: str = None):
        """Plot monthly returns heatmap"""
        monthly = self.calculate_monthly_returns()

        if len(monthly) == 0:
            print("No monthly data to plot")
            return

        # Reshape for heatmap
        monthly_index = pd.to_datetime(monthly.index)
        df_monthly = pd.DataFrame({
            'Year': monthly_index.year,
            'Month': monthly_index.month,
            'Return': monthly.values
        })

        pivot = df_monthly.pivot(index='Month', columns='Year', values='Return')

        # Plot
        fig, ax = plt.subplots(figsize=(12, 8))
        sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                   cbar_kws={'label': 'Return (%)'}, ax=ax)
        ax.set_ylabel('Month', fontsize=12, fontweight='bold')
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_title('Monthly Returns Heatmap', fontsize=14, fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Monthly returns heatmap saved to {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_trade_analysis(self, save_path: str = None):
        """Plot trade analysis: P&L distribution, MAE/MFE scatter"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # P&L Distribution
        ax1.hist(self.trades_df['pnl'], bins=50, color='#2E86AB', alpha=0.7, edgecolor='black')
        ax1.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax1.set_xlabel('P&L ($)', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Frequency', fontsize=11, fontweight='bold')
        ax1.set_title('P&L Distribution', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # Cumulative P&L by trade
        cumulative_pnl = self.trades_df['pnl'].cumsum()
        ax2.plot(range(len(cumulative_pnl)), cumulative_pnl, linewidth=2, color='#2E86AB')
        ax2.set_xlabel('Trade Number', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Cumulative P&L ($)', fontsize=11, fontweight='bold')
        ax2.set_title('Cumulative P&L by Trade', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # MAE vs MFE Scatter (Winners vs Losers)
        winners = self.trades_df[self.trades_df['pnl'] > 0]
        losers = self.trades_df[self.trades_df['pnl'] <= 0]

        ax3.scatter(winners['mae'], winners['mfe'], alpha=0.6, color='green', label='Winners', s=50)
        ax3.scatter(losers['mae'], losers['mfe'], alpha=0.6, color='red', label='Losers', s=50)
        ax3.set_xlabel('MAE (Maximum Adverse Excursion)', fontsize=11, fontweight='bold')
        ax3.set_ylabel('MFE (Maximum Favorable Excursion)', fontsize=11, fontweight='bold')
        ax3.set_title('MAE vs MFE Analysis', fontsize=12, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Win Rate by Signal Type
        signal_types = self.trades_df['signal_type'].unique()
        win_rates = []
        for st in signal_types:
            type_trades = self.trades_df[self.trades_df['signal_type'] == st]
            wr = len(type_trades[type_trades['pnl'] > 0]) / len(type_trades) * 100
            win_rates.append(wr)

        ax4.bar(range(len(signal_types)), win_rates, color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'][:len(signal_types)])
        ax4.set_xticks(range(len(signal_types)))
        ax4.set_xticklabels(signal_types, rotation=45, ha='right')
        ax4.set_ylabel('Win Rate (%)', fontsize=11, fontweight='bold')
        ax4.set_title('Win Rate by Signal Type', fontsize=12, fontweight='bold')
        ax4.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        ax4.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Trade analysis plots saved to {save_path}")
        else:
            plt.show()

        plt.close()

    def save_results(self, output_dir: str = 'results'):
        """Save all results and plots"""
        os.makedirs(output_dir, exist_ok=True)

        # Save trade log
        trade_log_path = os.path.join(output_dir, 'trade_log.csv')
        self.trades_df.to_csv(trade_log_path, index=False)
        print(f"Trade log saved to {trade_log_path}")

        # Save equity curve
        equity_path = os.path.join(output_dir, 'equity_curve.csv')
        self.equity_df.to_csv(equity_path, index=False)
        print(f"Equity curve saved to {equity_path}")

        # Save performance report
        report_path = os.path.join(output_dir, 'performance_report.txt')
        report = self.print_performance_report()
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"Performance report saved to {report_path}")

        # Save plots
        self.plot_equity_curve(os.path.join(output_dir, 'equity_curve.png'))
        self.plot_trade_analysis(os.path.join(output_dir, 'trade_analysis.png'))
        self.plot_monthly_returns(os.path.join(output_dir, 'monthly_returns.png'))

        print(f"\nAll results saved to {output_dir}/")
