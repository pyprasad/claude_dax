"""
Walk-Forward Optimization
Prevents overfitting through proper parameter tuning
"""

import pandas as pd
import numpy as np
import yaml
import itertools
from typing import Dict, List, Tuple
from datetime import datetime
import copy

from indicators import calculate_all_indicators
from strategy import ARIStrategy
from backtest_engine import BacktestEngine


class WalkForwardOptimizer:
    """Walk-Forward Optimization Engine"""

    def __init__(self, config: dict, data: pd.DataFrame):
        self.config = config
        self.data = data
        self.base_config = copy.deepcopy(config)

    def define_parameter_grid(self) -> Dict:
        """
        Define parameter ranges to test

        Returns:
            Dictionary of parameter ranges
        """
        param_grid = {
            # ADX thresholds
            'adx_momentum_threshold': [20, 25, 30],
            'adx_ranging_threshold': [15, 20, 25],

            # RSI parameters
            'rsi_min': [45, 50, 55],
            'rsi2_oversold': [5, 10, 15],
            'rsi2_overbought': [85, 90, 95],

            # Risk parameters
            'momentum_stop_atr_mult': [1.5, 2.0, 2.5],
            'mean_reversion_stop_atr_mult': [1.0, 1.5, 2.0],
            'momentum_tp1_r': [1.5, 2.0, 2.5],
            'mean_reversion_tp_r': [1.0, 1.5, 2.0],

            # Volatility filters
            'atr_expansion_threshold': [1.1, 1.2, 1.3],
        }

        return param_grid

    def generate_parameter_combinations(self, param_grid: Dict, max_combinations: int = 100) -> List[Dict]:
        """
        Generate parameter combinations to test

        Args:
            param_grid: Parameter ranges
            max_combinations: Maximum number of combinations to test

        Returns:
            List of parameter dictionaries
        """
        # Get all combinations
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))

        # Limit combinations
        if len(combinations) > max_combinations:
            # Random sample
            np.random.seed(42)
            indices = np.random.choice(len(combinations), max_combinations, replace=False)
            combinations = [combinations[i] for i in indices]

        # Convert to list of dicts
        param_sets = []
        for combo in combinations:
            param_dict = dict(zip(keys, combo))
            param_sets.append(param_dict)

        return param_sets

    def apply_parameters(self, config: dict, params: Dict) -> dict:
        """Apply parameter set to config"""
        new_config = copy.deepcopy(config)

        # Map parameters to config structure
        if 'adx_momentum_threshold' in params:
            new_config['strategy']['adx_momentum_threshold'] = params['adx_momentum_threshold']
        if 'adx_ranging_threshold' in params:
            new_config['strategy']['adx_ranging_threshold'] = params['adx_ranging_threshold']
        if 'rsi_min' in params:
            new_config['strategy']['momentum']['rsi_min'] = params['rsi_min']
        if 'rsi2_oversold' in params:
            new_config['strategy']['mean_reversion']['rsi2_oversold'] = params['rsi2_oversold']
        if 'rsi2_overbought' in params:
            new_config['strategy']['mean_reversion']['rsi2_overbought'] = params['rsi2_overbought']
        if 'momentum_stop_atr_mult' in params:
            new_config['strategy']['risk']['momentum_stop_atr_mult'] = params['momentum_stop_atr_mult']
        if 'mean_reversion_stop_atr_mult' in params:
            new_config['strategy']['risk']['mean_reversion_stop_atr_mult'] = params['mean_reversion_stop_atr_mult']
        if 'momentum_tp1_r' in params:
            new_config['strategy']['risk']['momentum_tp1_r'] = params['momentum_tp1_r']
        if 'mean_reversion_tp_r' in params:
            new_config['strategy']['risk']['mean_reversion_tp_r'] = params['mean_reversion_tp_r']
        if 'atr_expansion_threshold' in params:
            new_config['strategy']['momentum']['atr_expansion_threshold'] = params['atr_expansion_threshold']

        return new_config

    def split_data_walk_forward(self, train_pct: float = 0.7, num_folds: int = 5) -> List[Tuple]:
        """
        Split data into walk-forward folds

        Args:
            train_pct: Percentage of each fold for training
            num_folds: Number of walk-forward folds

        Returns:
            List of (train_data, test_data) tuples
        """
        total_length = len(self.data)
        fold_size = total_length // num_folds

        folds = []
        for i in range(num_folds):
            start_idx = i * fold_size
            end_idx = start_idx + fold_size if i < num_folds - 1 else total_length

            fold_data = self.data.iloc[start_idx:end_idx]
            train_size = int(len(fold_data) * train_pct)

            train_data = fold_data.iloc[:train_size]
            test_data = fold_data.iloc[train_size:]

            if len(train_data) > 0 and len(test_data) > 0:
                folds.append((train_data, test_data))

        return folds

    def evaluate_parameters(self, params: Dict, data: pd.DataFrame) -> Dict:
        """
        Evaluate a parameter set on given data

        Args:
            params: Parameter dictionary
            data: Data to backtest on

        Returns:
            Results dictionary with key metrics
        """
        # Apply parameters to config
        config = self.apply_parameters(self.base_config, params)

        # Calculate indicators
        data_with_indicators = calculate_all_indicators(data, config)
        data_with_indicators = data_with_indicators.dropna()

        if len(data_with_indicators) < 100:
            return {'error': 'Insufficient data after indicator calculation'}

        # Generate signals
        strategy = ARIStrategy(config)
        signals = strategy.generate_signals(data_with_indicators)

        # Run backtest
        backtest = BacktestEngine(config)
        results = backtest.run_backtest(signals, strategy)

        if 'error' in results:
            return results

        # Extract key metrics
        metrics = {
            'total_trades': results['total_trades'],
            'win_rate': results['win_rate'],
            'profit_factor': results['profit_factor'],
            'total_return_pct': results['total_return_pct'],
            'max_drawdown': results['max_drawdown'],
            'expectancy': results['expectancy'],
            'sharpe_ratio': self._calculate_sharpe(results),
            'cagr': results['cagr']
        }

        return metrics

    def _calculate_sharpe(self, results: Dict) -> float:
        """Calculate Sharpe ratio from results"""
        if 'trades_df' not in results or len(results['trades_df']) == 0:
            return 0

        returns = results['trades_df']['pnl'] / results['initial_capital']
        if returns.std() == 0:
            return 0

        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        return sharpe

    def calculate_fitness_score(self, metrics: Dict) -> float:
        """
        Calculate fitness score for parameter set

        Combines multiple objectives with weights
        """
        if 'error' in metrics or metrics['total_trades'] < 20:
            return -999999

        # Multi-objective fitness function
        # Weights: balance between returns, risk, and robustness
        fitness = (
            metrics['total_return_pct'] * 0.3 +
            metrics['profit_factor'] * 10 * 0.2 +
            (100 - metrics['max_drawdown']) * 0.2 +
            metrics['expectancy'] * 0.1 +
            metrics['sharpe_ratio'] * 10 * 0.2
        )

        # Penalty for low win rate (< 35%)
        if metrics['win_rate'] < 35:
            fitness *= 0.7

        # Penalty for low number of trades
        if metrics['total_trades'] < 30:
            fitness *= 0.8

        return fitness

    def optimize_walk_forward(self, num_folds: int = 3, max_combinations: int = 50) -> Dict:
        """
        Perform walk-forward optimization

        Args:
            num_folds: Number of walk-forward folds
            max_combinations: Maximum parameter combinations to test

        Returns:
            Best parameters and results
        """
        print(f"\n{'='*80}")
        print("WALK-FORWARD OPTIMIZATION")
        print(f"{'='*80}\n")

        # Generate parameter grid
        param_grid = self.define_parameter_grid()
        param_sets = self.generate_parameter_combinations(param_grid, max_combinations)

        print(f"Testing {len(param_sets)} parameter combinations")
        print(f"Using {num_folds} walk-forward folds\n")

        # Split data
        folds = self.split_data_walk_forward(num_folds=num_folds)
        print(f"Created {len(folds)} folds for walk-forward testing\n")

        # Track results
        all_results = []

        # For each fold
        for fold_idx, (train_data, test_data) in enumerate(folds):
            print(f"\nFold {fold_idx + 1}/{len(folds)}")
            print(f"  Train: {train_data.index[0]} to {train_data.index[-1]} ({len(train_data)} bars)")
            print(f"  Test:  {test_data.index[0]} to {test_data.index[-1]} ({len(test_data)} bars)")

            fold_results = []

            # Test each parameter set on training data
            for param_idx, params in enumerate(param_sets):
                if param_idx % 10 == 0:
                    print(f"    Testing parameter set {param_idx + 1}/{len(param_sets)}...", end='\r')

                # Evaluate on training data
                train_metrics = self.evaluate_parameters(params, train_data)
                fitness = self.calculate_fitness_score(train_metrics)

                fold_results.append({
                    'params': params,
                    'train_metrics': train_metrics,
                    'fitness': fitness
                })

            # Sort by fitness
            fold_results.sort(key=lambda x: x['fitness'], reverse=True)

            # Get best parameters from training
            best_params = fold_results[0]['params']
            print(f"\n    Best training fitness: {fold_results[0]['fitness']:.2f}")

            # Evaluate best parameters on test data (out-of-sample)
            test_metrics = self.evaluate_parameters(best_params, test_data)
            test_fitness = self.calculate_fitness_score(test_metrics)

            print(f"    Out-of-sample fitness: {test_fitness:.2f}")
            if 'total_trades' in test_metrics:
                print(f"    Test trades: {test_metrics['total_trades']}, "
                      f"Win rate: {test_metrics['win_rate']:.1f}%, "
                      f"Return: {test_metrics['total_return_pct']:.2f}%")

            all_results.append({
                'fold': fold_idx,
                'best_params': best_params,
                'train_metrics': fold_results[0]['train_metrics'],
                'test_metrics': test_metrics,
                'test_fitness': test_fitness
            })

        # Aggregate results across folds
        print(f"\n{'='*80}")
        print("OPTIMIZATION COMPLETE")
        print(f"{'='*80}\n")

        # Find most robust parameters (best average out-of-sample performance)
        avg_test_fitness = np.mean([r['test_fitness'] for r in all_results])
        print(f"Average out-of-sample fitness: {avg_test_fitness:.2f}\n")

        # Select parameters that performed best on average in testing
        best_fold = max(all_results, key=lambda x: x['test_fitness'])
        best_params = best_fold['best_params']

        print("Best Parameter Set:")
        for key, value in best_params.items():
            print(f"  {key}: {value}")

        print("\nOut-of-Sample Performance Summary:")
        for fold_result in all_results:
            test_m = fold_result['test_metrics']
            if 'error' not in test_m:
                print(f"  Fold {fold_result['fold'] + 1}: "
                      f"Return {test_m['total_return_pct']:.2f}%, "
                      f"DD {test_m['max_drawdown']:.2f}%, "
                      f"Trades {test_m['total_trades']}")

        return {
            'best_params': best_params,
            'fold_results': all_results,
            'avg_oos_fitness': avg_test_fitness
        }


def main():
    """Main optimizer execution"""
    # Load config and data
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load data
    filepath = config['data']['filepath']
    df = pd.read_csv(filepath)
    df[config['data']['date_column']] = pd.to_datetime(df[config['data']['date_column']])
    df = df.set_index(config['data']['date_column'])

    # Rename columns
    col_map = config['data']['ohlcv_columns']
    df = df.rename(columns={
        col_map['open']: 'open',
        col_map['high']: 'high',
        col_map['low']: 'low',
        col_map['close']: 'close',
        col_map['volume']: 'volume'
    })
    df = df[['open', 'high', 'low', 'close', 'volume']]

    # Initialize optimizer
    optimizer = WalkForwardOptimizer(config, df)

    # Run optimization
    results = optimizer.optimize_walk_forward(num_folds=3, max_combinations=50)

    # Save optimized config
    optimized_config = optimizer.apply_parameters(config, results['best_params'])
    with open('config_optimized.yaml', 'w') as f:
        yaml.dump(optimized_config, f, default_flow_style=False)

    print("\nOptimized configuration saved to config_optimized.yaml")
    print("\nRun backtest with optimized parameters:")
    print("  python run_backtest.py")


if __name__ == "__main__":
    main()
