"""
data.py — Market data fetching and management for the backtesting framework.

Supports two modes:
- daily: decades of historical data via Yahoo Finance
- hourly: up to 730 days of hourly data via Yahoo Finance

All data is returned as clean pandas DataFrames with consistent column names.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def fetch_data(ticker: str, start: str, end: str, mode: str = "daily") -> pd.DataFrame:
	"""
	Fetch historical market data for a given ticker.

	Args:
		ticker: Stock ticker symbol (e.g. 'AAPL', 'MSFT', 'SPY')
		start:  Start date as string 'YYYY-MM-DD'
		end:    End date as string 'YYYY-MM-DD'
		mode:   'daily' for daily bars, 'hourly' for hourly bars

	Returns:
		DataFrame with columns: open, high, low, close, volume
		Index is DatetimeIndex

	Raises:
		ValueError: If no data returned for the given ticker/date range
		ValueError: If mode is not 'daily' or 'hourly'
	"""
	if mode not in ("daily", "hourly"):
		raise ValueError(f"mode must be 'daily' or 'hourly', got '{mode}'")

	if mode == "hourly":
		# Yahoo Finance limits hourly data to last 730 days
		cutoff = datetime.now() - timedelta(days=730)
		start_dt = datetime.strptime(start, "%Y-%m-%d")
		if start_dt < cutoff:
			print(f"Warning: hourly mode limited to last 730 days. Adjusting start date.")
			start = cutoff.strftime("%Y-%m-%d")

	interval = "1d" if mode == "daily" else "1h"

	print(f"Fetching {ticker} {mode} data from {start} to {end}...")

	df = yf.download(
		ticker,
		start=start,
		end=end,
		interval=interval,
		auto_adjust=True,
		progress=False
	)

	if df is None or len(df) == 0:
		raise ValueError(
			f"No data returned for {ticker} between {start} and {end}. "
			f"Check that the ticker is valid and the date range is correct."
		)

	# Flatten multi-level columns if present
	if hasattr(df.columns, 'levels'):
		df.columns = df.columns.get_level_values(0)

	# Normalize column names to lowercase
	df.columns = [c.lower() for c in df.columns]

	# Ensure required columns exist
	required = ["open", "high", "low", "close", "volume"]
	missing = [c for c in required if c not in df.columns]
	if missing:
		raise ValueError(f"Missing columns in data for {ticker}: {missing}")

	# Drop rows with NaN in close price
	df = df.dropna(subset=["close"])

	print(f"Loaded {len(df)} {mode} bars for {ticker}")
	return df


def fetch_benchmark(ticker: str, start: str, end: str, mode: str = "daily") -> pd.DataFrame:
	"""
	Fetch benchmark data. Wrapper around fetch_data with clearer intent.

	Args:
		ticker: Benchmark ticker (e.g. 'SPY', 'QQQ', 'XLK')
		start:  Start date as string 'YYYY-MM-DD'
		end:    End date as string 'YYYY-MM-DD'
		mode:   'daily' or 'hourly'

	Returns:
		DataFrame with benchmark price data
	"""
	print(f"Fetching benchmark {ticker}...")
	return fetch_data(ticker, start, end, mode)


def calculate_returns(df: pd.DataFrame) -> pd.Series:
	"""
	Calculate period returns from close prices.

	Args:
		df: DataFrame with 'close' column

	Returns:
		Series of period returns (decimal, not percentage)
	"""
	return df["close"].pct_change().dropna()


def validate_date_range(start: str, end: str, mode: str) -> None:
	"""
	Validate that the date range makes sense for the given mode.

	Args:
		start: Start date string 'YYYY-MM-DD'
		end:   End date string 'YYYY-MM-DD'
		mode:  'daily' or 'hourly'

	Raises:
		ValueError: If date range is invalid
	"""
	start_dt = datetime.strptime(start, "%Y-%m-%d")
	end_dt = datetime.strptime(end, "%Y-%m-%d")

	if end_dt <= start_dt:
		raise ValueError(f"End date {end} must be after start date {start}")

	if end_dt > datetime.now():
		raise ValueError(f"End date {end} cannot be in the future")

	days = (end_dt - start_dt).days
	if days < 30:
		raise ValueError(f"Date range too short ({days} days). Minimum 30 days required.")

	if mode == "hourly" and days > 730:
		raise ValueError(
			f"Hourly mode limited to 730 days. "
			f"Your range is {days} days. Use daily mode for longer periods."
		)


def get_trading_days(df: pd.DataFrame) -> int:
	"""Return number of trading days in the dataset."""
	if hasattr(df.index, 'date'):
		return len(df.index.normalize().unique())
	return len(df)


def get_date_range_info(df: pd.DataFrame) -> dict:
	"""Return summary information about the data range."""
	return {
		"start": df.index[0].strftime("%Y-%m-%d"),
		"end": df.index[-1].strftime("%Y-%m-%d"),
		"total_bars": len(df),
		"trading_days": get_trading_days(df),
		"years": round((df.index[-1] - df.index[0]).days / 365.25, 1)
	}
