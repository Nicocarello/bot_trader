"""
Backtest Metrics Calculator.
Computes quantitative performance analysis like Sharpe Ratio, Max Drawdown, and Win Rate.
"""
import numpy as np
from typing import List

class BacktestMetrics:
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        returns_array = np.array(returns)
        mean_return = np.mean(returns_array) - risk_free_rate
        std_dev = np.std(returns_array)
        if std_dev == 0:
            return 0.0
        # Annualized assuming daily returns (sqrt(252))
        return float((mean_return / std_dev) * np.sqrt(252))

    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> float:
        if not equity_curve:
            return 0.0
        peak = equity_curve[0]
        max_dd = 0.0
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        return float(max_dd)
