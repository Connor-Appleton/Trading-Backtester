"""
metrics.py — Performance metric calculations for the backtesting framework.

All metrics follow standard financial industry definitions.
Returns are assumed to be period returns (decimal, not percentage).
"""

import numpy as np
import pandas as pd
from typing import List, Tuple


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.043, periods_per_year: int = 252) -> float:
	"""
	Sharpe Ratio — risk-adjusted return relative to a risk-free rate.

	Formula: (Mean Return - Risk Free Rate) / Std Dev of Returns
	Annualized by multiplying by sqrt(periods_per_year)

	Args:
		returns:          Series of period returns
		risk_free_rate:   Annual risk-free rate (default 4.3% — current T-bill rate)
		periods_per_year: 252 for daily, 8760 for hourly

	Returns:
		Annualized Sharpe ratio. Above 1.0 is good, above 2.0 is excellent.
	"""
	if len(returns) == 0 or returns.std() == 0:
		return 0.0

	period_rf = risk_free_rate / periods_per_year
	excess_returns = returns - period_rf
	return float(np.sqrt(periods_per_year) * excess_returns.mean() / excess_returns.std())


def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.043, periods_per_year: int = 252) -> float:
	"""
	Sortino Ratio — like Sharpe but only penalizes downside volatility.

	Better than Sharpe for strategies with asymmetric returns because it
	doesn't penalize upside volatility — only losses count against you.

	Formula: (Mean Return - Risk Free Rate) / Downside Std Dev
	"""
	if len(returns) == 0:
		return 0.0

	period_rf = risk_free_rate / periods_per_year
	excess_returns = returns - period_rf
	downside_returns = excess_returns[excess_returns < 0]

	if len(downside_returns) == 0 or downside_returns.std() == 0:
		return float('inf')

	downside_std = np.sqrt(periods_per_year) * downside_returns.std()
	annualized_excess = periods_per_year * excess_returns.mean()
	return float(annualized_excess / downside_std)


def max_drawdown(equity_curve: pd.Series) -> Tuple[float, int]:
	"""
	Maximum Drawdown — largest peak-to-trough decline in portfolio value.

	This is the single most important risk metric. A strategy that returns
	50% annually but has an 80% max drawdown is unacceptable for most investors
	because most people would panic and sell before recovery.

	Args:
		equity_curve: Series of portfolio values over time

	Returns:
		Tuple of (max_drawdown_pct, max_drawdown_duration_days)
		max_drawdown_pct is negative (e.g. -0.25 means 25% drawdown)
	"""
	if len(equity_curve) == 0:
		return 0.0, 0

	rolling_max = equity_curve.expanding().max()
	drawdown = (equity_curve - rolling_max) / rolling_max

	max_dd = float(drawdown.min())

	# Calculate drawdown duration
	in_drawdown = drawdown < 0
	max_duration = 0
	current_duration = 0

	for is_down in in_drawdown:
		if is_down:
			current_duration += 1
			max_duration = max(max_duration, current_duration)
		else:
			current_duration = 0

	return max_dd, max_duration


def calmar_ratio(returns: pd.Series, equity_curve: pd.Series, periods_per_year: int = 252) -> float:
	"""
	Calmar Ratio — annualized return divided by maximum drawdown.

	Measures how much return you get per unit of drawdown risk.
	Above 1.0 is good — means your annual return exceeds your worst drawdown.

	Formula: Annualized Return / |Max Drawdown|
	"""
	if len(returns) == 0:
		return 0.0

	annual_return = (1 + returns.mean()) ** periods_per_year - 1
	max_dd, _ = max_drawdown(equity_curve)

	if max_dd == 0:
		return float('inf')

	return float(annual_return / abs(max_dd))


def win_rate(trades: List[dict]) -> float:
	"""
	Win Rate — percentage of trades that were profitable.

	Args:
		trades: List of trade dicts with 'pnl' key

	Returns:
		Win rate as decimal (0.55 = 55% win rate)
	"""
	if not trades:
		return 0.0

	winners = sum(1 for t in trades if t.get("pnl", 0) > 0)
	return float(winners / len(trades))


def profit_factor(trades: List[dict]) -> float:
	"""
	Profit Factor — gross profit divided by gross loss.

	Above 1.0 means strategy is profitable.
	Above 1.5 is good. Above 2.0 is excellent.

	Formula: Sum of winning trades / |Sum of losing trades|
	"""
	if not trades:
		return 0.0

	gross_profit = sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0)
	gross_loss = abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0))

	if gross_loss == 0:
		return float('inf')

	return float(gross_profit / gross_loss)


def expectancy(trades: List[dict]) -> float:
	"""
	Expectancy — average profit per trade in dollars.

	This is the most practical metric for real money decisions.
	A positive expectancy means on average every trade makes money.

	Formula: (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
	"""
	if not trades:
		return 0.0

	winners = [t["pnl"] for t in trades if t.get("pnl", 0) > 0]
	losers = [t["pnl"] for t in trades if t.get("pnl", 0) < 0]

	win_rate_val = len(winners) / len(trades)
	loss_rate_val = len(losers) / len(trades)

	avg_win = np.mean(winners) if winners else 0.0
	avg_loss = abs(np.mean(losers)) if losers else 0.0

	return float((win_rate_val * avg_win) - (loss_rate_val * avg_loss))


def win_loss_streaks(trades: List[dict]) -> Tuple[int, int]:
	"""
	Win/Loss Streaks — longest consecutive winning and losing trades.

	High loss streaks are psychologically damaging and can cause
	emotional decision making. Important for real money deployment.

	Returns:
		Tuple of (max_win_streak, max_loss_streak)
	"""
	if not trades:
		return 0, 0

	max_win_streak = 0
	max_loss_streak = 0
	current_win = 0
	current_loss = 0

	for trade in trades:
		pnl = trade.get("pnl", 0)
		if pnl > 0:
			current_win += 1
			current_loss = 0
			max_win_streak = max(max_win_streak, current_win)
		elif pnl < 0:
			current_loss += 1
			current_win = 0
			max_loss_streak = max(max_loss_streak, current_loss)
		else:
			current_win = 0
			current_loss = 0

	return max_win_streak, max_loss_streak


def maximum_adverse_excursion(trades: List[dict]) -> float:
	"""
	Maximum Adverse Excursion (MAE) — average worst intra-trade drawdown.

	Measures how far against you a trade went before closing.
	High MAE means your stop loss is saving you from catastrophic losses.
	Low MAE means trades rarely go significantly against you before winning.

	Returns:
		Average MAE as decimal (e.g. -0.03 means trades went 3% against you on average)
	"""
	if not trades:
		return 0.0

	maes = [t.get("mae", 0) for t in trades if "mae" in t]
	if not maes:
		return 0.0

	return float(np.mean(maes))


def annual_return(returns: pd.Series, periods_per_year: int = 252) -> float:
	"""
	Annualized Return — compound annual growth rate of the strategy.

	Formula: (1 + mean_period_return) ^ periods_per_year - 1
	"""
	if len(returns) == 0:
		return 0.0

	return float((1 + returns.mean()) ** periods_per_year - 1)


def benchmark_comparison(strategy_returns: pd.Series, benchmark_returns: pd.Series, periods_per_year: int = 252) -> dict:
	"""
	Compare strategy performance against a benchmark.

	Args:
		strategy_returns:  Series of strategy period returns
		benchmark_returns: Series of benchmark period returns
		periods_per_year:  252 for daily, 8760 for hourly

	Returns:
		Dict with strategy vs benchmark metrics
	"""
	strat_annual = annual_return(strategy_returns, periods_per_year)
	bench_annual = annual_return(benchmark_returns, periods_per_year)

	return {
		"strategy_annual_return": strat_annual,
		"benchmark_annual_return": bench_annual,
		"outperformance": strat_annual - bench_annual,
		"strategy_sharpe": sharpe_ratio(strategy_returns, periods_per_year=periods_per_year),
		"benchmark_sharpe": sharpe_ratio(benchmark_returns, periods_per_year=periods_per_year),
	}


def calculate_all_metrics(
	returns: pd.Series,
	equity_curve: pd.Series,
	trades: List[dict],
	benchmark_returns: pd.Series = None,
	periods_per_year: int = 252
) -> dict:
	"""
	Calculate the complete suite of performance metrics.

	This is the main entry point for metric calculation.
	Call this with your backtest results to get everything at once.

	Args:
		returns:           Series of period returns
		equity_curve:      Series of portfolio values
		trades:            List of completed trade dicts
		benchmark_returns: Optional benchmark returns for comparison
		periods_per_year:  252 for daily, 8760 for hourly

	Returns:
		Dict containing all metrics
	"""
	max_dd, max_dd_duration = max_drawdown(equity_curve)
	max_win_streak, max_loss_streak = win_loss_streaks(trades)

	metrics = {
		"annual_return":        annual_return(returns, periods_per_year),
		"sharpe_ratio":         sharpe_ratio(returns, periods_per_year=periods_per_year),
		"sortino_ratio":        sortino_ratio(returns, periods_per_year=periods_per_year),
		"calmar_ratio":         calmar_ratio(returns, equity_curve, periods_per_year),
		"max_drawdown":         max_dd,
		"max_drawdown_duration": max_dd_duration,
		"win_rate":             win_rate(trades),
		"profit_factor":        profit_factor(trades),
		"expectancy":           expectancy(trades),
		"max_win_streak":       max_win_streak,
		"max_loss_streak":      max_loss_streak,
		"mae":                  maximum_adverse_excursion(trades),
		"total_trades":         len(trades),
		"total_return":         float((equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1) if len(equity_curve) > 0 else 0.0,
	}

	if benchmark_returns is not None:
		bench_metrics = benchmark_comparison(returns, benchmark_returns, periods_per_year)
		metrics.update(bench_metrics)

	return metrics
