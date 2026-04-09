"""
Backtester — Professional backtesting framework for trading strategies.
"""

from backtester.engine import BacktestEngine
from backtester.metrics import calculate_all_metrics
from backtester.data import fetch_data, fetch_benchmark
from backtester.visualization import generate_report, open_report

__all__ = [
	"BacktestEngine",
	"calculate_all_metrics",
	"fetch_data",
	"fetch_benchmark",
	"generate_report",
	"open_report"
]
