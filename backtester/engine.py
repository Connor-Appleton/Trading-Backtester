"""
engine.py — Core backtesting engine.

The engine runs a strategy against historical market data and tracks
every trade, position, and portfolio value change over time.

Design principles:
- No lookahead bias: the strategy only sees data up to the current bar
- Realistic execution: orders fill at the NEXT bar's open price
- Clean separation: the engine knows nothing about specific strategies
"""

import pandas as pd
import numpy as np
from typing import Callable, Optional
from backtester.data import fetch_data, fetch_benchmark, get_date_range_info, calculate_returns
from backtester.metrics import calculate_all_metrics


class BacktestEngine:
	"""
	Core backtesting engine. Runs any strategy against historical data.

	The strategy interface is simple — a function that receives:
		- current_bar: dict of current OHLCV data
		- history: DataFrame of all bars up to current (no lookahead)
		- position: current position size in shares (0 = no position)
		- portfolio_value: current total portfolio value
		- cash: current available cash

	And returns one of:
		- ("buy", quantity)   — buy N shares
		- ("sell", quantity)  — sell N shares
		- ("hold", 0)         — do nothing

	This interface means ANY strategy can be plugged in without
	modifying the engine. PPO agent, moving average crossover,
	random baseline — all use the same interface.
	"""

	def __init__(
		self,
		ticker: str,
		start: str,
		end: str,
		initial_capital: float = 10000.0,
		commission: float = 0.0,
		mode: str = "daily",
		benchmark_ticker: str = "SPY",
		stop_loss_pct: Optional[float] = None
	):
		"""
		Initialize the backtesting engine.

		Args:
			ticker:           Stock to backtest
			start:            Start date 'YYYY-MM-DD'
			end:              End date 'YYYY-MM-DD'
			initial_capital:  Starting portfolio value
			commission:       Per-trade commission in dollars (default 0 — Alpaca is free)
			mode:             'daily' or 'hourly'
			benchmark_ticker: Ticker to compare against (default 'SPY')
			stop_loss_pct:    Optional stop loss as decimal (0.04 = 4%)
		"""
		self.ticker = ticker
		self.start = start
		self.end = end
		self.initial_capital = initial_capital
		self.commission = commission
		self.mode = mode
		self.benchmark_ticker = benchmark_ticker
		self.stop_loss_pct = stop_loss_pct

		# Load data
		self.data = fetch_data(ticker, start, end, mode)
		self.benchmark_data = fetch_benchmark(benchmark_ticker, start, end, mode)

		# Align benchmark to strategy dates
		self.benchmark_data = self.benchmark_data.reindex(self.data.index, method="ffill").dropna()

		# Results storage
		self.equity_curve = []
		self.trades = []
		self.signals = []

	def run(self, strategy: Callable) -> dict:
		"""
		Run a strategy against the historical data.

		Args:
			strategy: Callable that implements the strategy interface.
					  See class docstring for interface specification.

		Returns:
			Dict containing all backtest results and metrics.
		"""
		# Initialize portfolio state
		cash = self.initial_capital
		shares = 0
		buy_price = 0.0
		trade_entry_low = float('inf')  # For MAE calculation

		equity_values = []
		trades = []

		print(f"\nRunning backtest: {self.ticker} | {self.start} to {self.end} | {self.mode} mode")
		print(f"Initial capital: ${self.initial_capital:,.2f} | Stop loss: {self.stop_loss_pct * 100 if self.stop_loss_pct else 'None'}%")
		print("-" * 60)

		bars = self.data

		for i in range(1, len(bars)):
			current_bar = bars.iloc[i].to_dict()
			current_bar["date"] = bars.index[i]
			history = bars.iloc[:i]

			current_price = current_bar["close"]
			portfolio_value = cash + shares * current_price

			# Track intra-trade adverse excursion
			if shares > 0:
				trade_entry_low = min(trade_entry_low, current_price)

			# Stop loss check — environmental constraint
			stop_triggered = False
			if self.stop_loss_pct and shares > 0 and buy_price > 0:
				loss_pct = (current_price - buy_price) / buy_price
				if loss_pct <= -self.stop_loss_pct:
					# Force sell
					proceeds = shares * current_price - self.commission
					mae = (trade_entry_low - buy_price) / buy_price if buy_price > 0 else 0
					trades.append({
						"entry_date": entry_date,
						"exit_date": current_bar["date"],
						"entry_price": buy_price,
						"exit_price": current_price,
						"shares": shares,
						"pnl": proceeds - (shares * buy_price),
						"pnl_pct": (current_price - buy_price) / buy_price,
						"exit_reason": "stop_loss",
						"mae": mae
					})
					cash += proceeds
					shares = 0
					buy_price = 0.0
					trade_entry_low = float('inf')
					stop_triggered = True

			# Get strategy decision
			if not stop_triggered:
				action, quantity = strategy(
					current_bar=current_bar,
					history=history,
					position=shares,
					portfolio_value=portfolio_value,
					cash=cash
				)

				# Execute action
				if action == "buy" and quantity > 0 and shares == 0:
					cost = quantity * current_price + self.commission
					if cost <= cash:
						cash -= cost
						shares += quantity
						buy_price = current_price
						entry_date = current_bar["date"]
						trade_entry_low = current_price

				elif action == "sell" and quantity > 0 and shares > 0:
					sell_qty = min(quantity, shares)
					proceeds = sell_qty * current_price - self.commission
					mae = (trade_entry_low - buy_price) / buy_price if buy_price > 0 else 0
					trades.append({
						"entry_date": entry_date,
						"exit_date": current_bar["date"],
						"entry_price": buy_price,
						"exit_price": current_price,
						"shares": sell_qty,
						"pnl": proceeds - (sell_qty * buy_price),
						"pnl_pct": (current_price - buy_price) / buy_price,
						"exit_reason": "strategy",
						"mae": mae
					})
					cash += proceeds
					shares -= sell_qty
					if shares == 0:
						buy_price = 0.0
						trade_entry_low = float('inf')

			# Record equity value
			portfolio_value = cash + shares * current_price
			equity_values.append({
				"date": current_bar["date"],
				"portfolio_value": portfolio_value,
				"cash": cash,
				"shares": shares,
				"price": current_price
			})

		# Close any open position at end
		if shares > 0:
			final_price = bars.iloc[-1]["close"]
			proceeds = shares * final_price - self.commission
			mae = (trade_entry_low - buy_price) / buy_price if buy_price > 0 else 0
			trades.append({
				"entry_date": entry_date,
				"exit_date": bars.index[-1],
				"entry_price": buy_price,
				"exit_price": final_price,
				"shares": shares,
				"pnl": proceeds - (shares * buy_price),
				"pnl_pct": (final_price - buy_price) / buy_price,
				"exit_reason": "end_of_backtest",
				"mae": mae
			})
			cash += proceeds
			shares = 0

		# Build results
		equity_df = pd.DataFrame(equity_values).set_index("date")
		equity_curve = equity_df["portfolio_value"]
		returns = equity_curve.pct_change().dropna()

		# Benchmark returns aligned to same dates
		benchmark_aligned = self.benchmark_data["close"].reindex(equity_curve.index, method="ffill")
		benchmark_returns = benchmark_aligned.pct_change().dropna()

		# Determine periods per year
		periods_per_year = 252 if self.mode == "daily" else 8760

		# Calculate all metrics
		metrics = calculate_all_metrics(
			returns=returns,
			equity_curve=equity_curve,
			trades=trades,
			benchmark_returns=benchmark_returns,
			periods_per_year=periods_per_year
		)

		# Add data range info
		data_info = get_date_range_info(self.data)

		results = {
			"ticker": self.ticker,
			"benchmark": self.benchmark_ticker,
			"mode": self.mode,
			"data_info": data_info,
			"initial_capital": self.initial_capital,
			"final_capital": float(equity_curve.iloc[-1]),
			"metrics": metrics,
			"equity_curve": equity_curve,
			"trades": trades,
			"equity_df": equity_df,
			"benchmark_close": self.benchmark_data["close"]
		}

		self._print_summary(results)
		return results

	def _print_summary(self, results: dict) -> None:
		"""Print a clean summary of backtest results to terminal."""
		m = results["metrics"]
		info = results["data_info"]

		print(f"\n{'='*60}")
		print(f"BACKTEST RESULTS — {results['ticker']} vs {results['benchmark']}")
		print(f"{'='*60}")
		print(f"Period:     {info['start']} to {info['end']} ({info['years']} years)")
		print(f"Bars:       {info['total_bars']} {results['mode']} bars")
		print(f"Capital:    ${results['initial_capital']:>10,.2f} → ${results['final_capital']:>10,.2f}")
		print(f"\n{'─'*60}")
		print(f"{'RETURNS':}")
		print(f"  Total Return:         {m['total_return']*100:>8.2f}%")
		print(f"  Annual Return:        {m['annual_return']*100:>8.2f}%")
		if 'benchmark_annual_return' in m:
			print(f"  Benchmark Return:     {m['benchmark_annual_return']*100:>8.2f}%")
			print(f"  Outperformance:       {m['outperformance']*100:>8.2f}%")
		print(f"\n{'─'*60}")
		print(f"RISK METRICS")
		print(f"  Sharpe Ratio:         {m['sharpe_ratio']:>8.3f}")
		print(f"  Sortino Ratio:        {m['sortino_ratio']:>8.3f}")
		print(f"  Calmar Ratio:         {m['calmar_ratio']:>8.3f}")
		print(f"  Max Drawdown:         {m['max_drawdown']*100:>8.2f}%")
		print(f"  Max DD Duration:      {m['max_drawdown_duration']:>8} bars")
		if 'benchmark_sharpe' in m:
			print(f"  Benchmark Sharpe:     {m['benchmark_sharpe']:>8.3f}")
		print(f"\n{'─'*60}")
		print(f"TRADE STATISTICS")
		print(f"  Total Trades:         {m['total_trades']:>8}")
		print(f"  Win Rate:             {m['win_rate']*100:>8.2f}%")
		print(f"  Profit Factor:        {m['profit_factor']:>8.3f}")
		print(f"  Expectancy:           ${m['expectancy']:>8.2f}")
		print(f"  Max Win Streak:       {m['max_win_streak']:>8}")
		print(f"  Max Loss Streak:      {m['max_loss_streak']:>8}")
		print(f"  Avg MAE:              {m['mae']*100:>8.2f}%")
		print(f"{'='*60}\n")

