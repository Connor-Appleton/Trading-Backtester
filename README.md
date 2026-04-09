# Trading Backtester

A professional backtesting framework for evaluating trading strategies across decades of market history. Built as a companion tool to the [RL Trading Agent](https://github.com/Connor-Appleton/RL-Trading-Agent).

## Overview

Test any trading strategy against historical market data with a full suite of professional performance metrics — from the dot-com crash to the 2008 collapse to the COVID recovery. Supports any valid stock ticker going back decades via Yahoo Finance.

## Features

- **Any Ticker** — backtest AAPL from 1980, MSFT from 1986, or any publicly traded stock
- **Any Benchmark** — compare against SPY, QQQ, XLF, BRK-B, or any ticker
- **Professional Metrics** — Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, Profit Factor, Expectancy, MAE, Win/Loss Streaks
- **Interactive Reports** — Plotly HTML charts with equity curve, drawdown visualization, and returns distribution
- **CSV Export** — complete trade log for further analysis
- **Strategy Interface** — plug in any strategy without modifying the framework
- **Two Modes** — daily (decades of history) or hourly (last 730 days)

## Installation

```bash
git clone https://github.com/Connor-Appleton/trading-backtester
cd trading-backtester
pip install -r requirements.txt
```

## Usage

```bash
# Basic backtest — AAPL buy and hold vs SPY
python examples/run_backtest.py --ticker AAPL --start 2020-01-01 --end 2024-01-01

# Test through the dot-com crash
python examples/run_backtest.py --ticker MSFT --start 1998-01-01 --end 2005-01-01

# Tech sector benchmark comparison
python examples/run_backtest.py --ticker AAPL --benchmark QQQ --start 2010-01-01

# Financial sector benchmark
python examples/run_backtest.py --ticker JPM --benchmark XLF --start 2005-01-01

# Compare against Berkshire Hathaway
python examples/run_backtest.py --ticker AAPL --benchmark BRK-B --start 2000-01-01

# Export trade log to CSV
python examples/run_backtest.py --ticker TSLA --start 2015-01-01 --export-csv

# Run without opening browser
python examples/run_backtest.py --ticker GOOGL --no-browser
```

## CLI Options
--ticker      Stock ticker (required) — any valid Yahoo Finance ticker
--start       Start date YYYY-MM-DD (default: 2020-01-01)
--end         End date YYYY-MM-DD (default: today)
--benchmark   Benchmark ticker (default: SPY)
--mode        daily or hourly (default: daily)
--strategy    buy_hold or random (default: buy_hold)
--capital     Starting capital in dollars (default: 10000)
--stop-loss   Stop loss as decimal e.g. 0.04 for 4% (default: none)
--no-browser  Generate report without opening browser
--export-csv  Export trade log to CSV

## Strategy Interface

Any strategy can be plugged into the framework by implementing this interface:

```python
def my_strategy(current_bar, history, position, portfolio_value, cash):
    """
    Args:
        current_bar:     dict with keys: open, high, low, close, volume, date
        history:         DataFrame of all bars up to current (no lookahead)
        position:        int — current shares held
        portfolio_value: float — total portfolio value
        cash:            float — available cash

    Returns:
        Tuple of ("buy", quantity) | ("sell", quantity) | ("hold", 0)
    """
    # Your strategy logic here
    return ("hold", 0)
```

## Metrics Reference

| Metric | Description | Good Value |
|--------|-------------|------------|
| Sharpe Ratio | Risk-adjusted return vs risk-free rate | > 1.0 |
| Sortino Ratio | Like Sharpe but only penalizes downside | > 1.0 |
| Calmar Ratio | Annual return / max drawdown | > 1.0 |
| Max Drawdown | Largest peak-to-trough decline | < 20% |
| Win Rate | % of profitable trades | > 50% |
| Profit Factor | Gross profit / gross loss | > 1.5 |
| Expectancy | Average profit per trade | Positive |
| MAE | Avg worst intra-trade drawdown | Low |

## Output Example
============================================================
BACKTEST RESULTS — AAPL vs SPY
Period:     2020-01-02 to 2023-12-29 (4.0 years)
Capital:    $10,000.00 → $26,520.68
RETURNS
Total Return:           165.21%
Annual Return:           35.09%
Benchmark Return:        14.91%
Outperformance:          20.18%
RISK METRICS
Sharpe Ratio:             0.770
Sortino Ratio:            1.095
Calmar Ratio:             1.120
Max Drawdown:           -31.33%
TRADE STATISTICS
Total Trades:                 1
Win Rate:               100.00%
Profit Factor:              inf
Expectancy:            $16520.68

## Roadmap

- [ ] PPO agent strategy wrapper — backtest the RL trading agent
- [ ] Multi-ticker portfolio backtesting
- [ ] Walk-forward optimization
- [ ] Monte Carlo simulation for robustness testing
- [ ] Parameter optimization grid search

## Part Of The RL Trading Ecosystem

This backtester is part of a larger ecosystem:

- **[RL Trading Agent](https://github.com/Connor-Appleton/RL-Trading-Agent)** — the PPO trading agent this framework evaluates
- **Trading Backtester** — this repository
- Sentiment Dashboard — coming soon
- Market Data Pipeline — coming soon

---

*Built by Connor Appleton — Fort Smith, AR*
