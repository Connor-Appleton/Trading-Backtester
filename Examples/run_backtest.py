"""
run_backtest.py — Command line interface for the backtesting framework.

Usage:
	python examples/run_backtest.py --ticker AAPL --start 2020-01-01 --end 2024-01-01
	python examples/run_backtest.py --ticker MSFT --benchmark QQQ --mode daily
	python examples/run_backtest.py --ticker TSLA --start 2018-01-01 --strategy random

Run with --help for full options.
"""

import argparse
import sys
import os
import csv

# Add parent directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtester.engine import BacktestEngine
from backtester.visualization import generate_report, open_report
from strategies.buy_hold import buy_and_hold
from strategies.random_strategy import random_strategy


def parse_args():
	parser = argparse.ArgumentParser(
		description="RL Trading Agent Backtester — test any strategy across decades of market history",
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  python examples/run_backtest.py --ticker AAPL --start 2000-01-01 --end 2010-01-01
  python examples/run_backtest.py --ticker MSFT --benchmark QQQ --start 1990-01-01
  python examples/run_backtest.py --ticker TSLA --strategy random --start 2015-01-01
  python examples/run_backtest.py --ticker JPM --benchmark XLF --start 2005-01-01
		"""
	)

	parser.add_argument(
		"--ticker",
		type=str,
		required=True,
		help="Stock ticker to backtest (e.g. AAPL, MSFT, GOOGL, BRK-B)"
	)
	parser.add_argument(
		"--start",
		type=str,
		default="2020-01-01",
		help="Start date YYYY-MM-DD (default: 2020-01-01)"
	)
	parser.add_argument(
		"--end",
		type=str,
		default=None,
		help="End date YYYY-MM-DD (default: today)"
	)
	parser.add_argument(
		"--benchmark",
		type=str,
		default="SPY",
		help="Benchmark ticker (default: SPY). Any valid ticker works: QQQ, XLF, BRK-B etc."
	)
	parser.add_argument(
		"--mode",
		type=str,
		default="daily",
		choices=["daily", "hourly"],
		help="Data frequency (default: daily). hourly limited to last 730 days."
	)
	parser.add_argument(
		"--strategy",
		type=str,
		default="buy_hold",
		choices=["buy_hold", "random"],
		help="Strategy to test (default: buy_hold)"
	)
	parser.add_argument(
		"--capital",
		type=float,
		default=10000.0,
		help="Starting capital in dollars (default: 10000)"
	)
	parser.add_argument(
		"--stop-loss",
		type=float,
		default=None,
		help="Stop loss percentage as decimal (e.g. 0.04 for 4%%). Default: no stop loss"
	)
	parser.add_argument(
		"--no-browser",
		action="store_true",
		help="Generate report but don't open browser automatically"
	)
	parser.add_argument(
		"--export-csv",
		action="store_true",
		help="Export trade log to CSV"
	)

	return parser.parse_args()


def select_strategy(name: str):
	"""Return the strategy function for a given name."""
	strategies = {
		"buy_hold": buy_and_hold,
		"random": random_strategy,
	}
	if name not in strategies:
		print(f"Unknown strategy '{name}'. Available: {list(strategies.keys())}")
		sys.exit(1)
	return strategies[name]


def export_trades_csv(results: dict, output_dir: str = "output/reports") -> str:
	"""Export trade log to CSV file."""
	os.makedirs(output_dir, exist_ok=True)
	from datetime import datetime
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	filename = f"{results['ticker']}_trades_{timestamp}.csv"
	filepath = os.path.join(output_dir, filename)

	trades = results["trades"]
	if not trades:
		print("No trades to export.")
		return None

	fieldnames = [
		"entry_date", "exit_date", "entry_price", "exit_price",
		"shares", "pnl", "pnl_pct", "exit_reason", "mae"
	]

	with open(filepath, "w", newline="") as f:
		writer = csv.DictWriter(f, fieldnames=fieldnames)
		writer.writeheader()
		for trade in trades:
			row = {k: trade.get(k, "") for k in fieldnames}
			if "pnl_pct" in row:
				row["pnl_pct"] = f"{row['pnl_pct']*100:.2f}%"
			if "mae" in row:
				row["mae"] = f"{row['mae']*100:.2f}%"
			writer.writerow(row)

	print(f"Trade log exported: {filepath}")
	return filepath


def main():
	args = parse_args()

	# Default end date to today
	if args.end is None:
		from datetime import date
		args.end = date.today().strftime("%Y-%m-%d")

	print(f"\nRL Trading Agent Backtester")
	print(f"{'='*40}")
	print(f"Ticker:    {args.ticker}")
	print(f"Period:    {args.start} to {args.end}")
	print(f"Benchmark: {args.benchmark}")
	print(f"Mode:      {args.mode}")
	print(f"Strategy:  {args.strategy}")
	print(f"Capital:   ${args.capital:,.2f}")
	if args.stop_loss:
		print(f"Stop Loss: {args.stop_loss*100:.1f}%")
	print(f"{'='*40}\n")

	# Run backtest
	engine = BacktestEngine(
		ticker=args.ticker.upper(),
		start=args.start,
		end=args.end,
		initial_capital=args.capital,
		mode=args.mode,
		benchmark_ticker=args.benchmark.upper(),
		stop_loss_pct=args.stop_loss
	)

	strategy = select_strategy(args.strategy)
	results = engine.run(strategy)

	# Generate and open report
	report_path = generate_report(results)

	if not args.no_browser:
		open_report(report_path)

	# Export CSV if requested
	if args.export_csv:
		export_trades_csv(results)

	print(f"\nDone! Report: {report_path}")


if __name__ == "__main__":
	main()
