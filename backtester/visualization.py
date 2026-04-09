"""
visualization.py — Interactive charts and HTML report generation.

Uses Plotly to generate interactive HTML charts that open in a browser.
No static image files — everything is interactive and zoomable.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os
import webbrowser
from datetime import datetime


def generate_report(results: dict, output_dir: str = "output/reports") -> str:
	"""
	Generate a complete interactive HTML report for a backtest.

	Args:
		results:    Dict returned by BacktestEngine.run()
		output_dir: Directory to save the HTML report

	Returns:
		Path to the generated HTML file
	"""
	os.makedirs(output_dir, exist_ok=True)

	ticker = results["ticker"]
	benchmark = results["benchmark"]
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	filename = f"{ticker}_vs_{benchmark}_{timestamp}.html"
	filepath = os.path.join(output_dir, filename)

	# Build the figure
	fig = make_subplots(
		rows=3,
		cols=1,
		shared_xaxes=True,
		vertical_spacing=0.06,
		subplot_titles=(
			f"Portfolio Equity Curve — {ticker} Strategy vs {benchmark} Buy & Hold",
			"Drawdown",
			"Daily Returns Distribution"
		),
		row_heights=[0.5, 0.25, 0.25]
	)

	equity_curve = results["equity_curve"]
	benchmark_close = results["benchmark_close"]
	trades = results["trades"]
	m = results["metrics"]

	# --- Row 1: Equity Curve ---

	# Normalize benchmark to same starting capital
	initial_capital = results["initial_capital"]
	benchmark_aligned = benchmark_close.reindex(equity_curve.index, method="ffill")
	benchmark_normalized = (benchmark_aligned / benchmark_aligned.iloc[0]) * initial_capital

	# Strategy equity curve
	fig.add_trace(
		go.Scatter(
			x=equity_curve.index,
			y=equity_curve.values,
			name=f"{ticker} Strategy",
			line=dict(color="#00d4aa", width=2),
			hovertemplate="<b>%{x}</b><br>Portfolio: $%{y:,.2f}<extra></extra>"
		),
		row=1, col=1
	)

	# Benchmark equity curve
	fig.add_trace(
		go.Scatter(
			x=benchmark_normalized.index,
			y=benchmark_normalized.values,
			name=f"{benchmark} Buy & Hold",
			line=dict(color="#888888", width=1.5, dash="dash"),
			hovertemplate="<b>%{x}</b><br>Benchmark: $%{y:,.2f}<extra></extra>"
		),
		row=1, col=1
	)

	# Mark trade entries and exits
	buy_dates = [t["entry_date"] for t in trades]
	buy_prices = []
	for d in buy_dates:
		if d in equity_curve.index:
			buy_prices.append(equity_curve[d])
		else:
			buy_prices.append(None)

	sell_dates = [t["exit_date"] for t in trades]
	sell_prices = []
	for d in sell_dates:
		if d in equity_curve.index:
			sell_prices.append(equity_curve[d])
		else:
			sell_prices.append(None)

	# Buy markers
	fig.add_trace(
		go.Scatter(
			x=buy_dates,
			y=buy_prices,
			mode="markers",
			name="Buy",
			marker=dict(symbol="triangle-up", size=10, color="#00ff88"),
			hovertemplate="<b>BUY</b><br>%{x}<extra></extra>"
		),
		row=1, col=1
	)

	# Sell markers
	sell_colors = ["#ff4444" if t.get("exit_reason") == "stop_loss" else "#ffaa00" for t in trades]
	fig.add_trace(
		go.Scatter(
			x=sell_dates,
			y=sell_prices,
			mode="markers",
			name="Sell",
			marker=dict(symbol="triangle-down", size=10, color=sell_colors),
			hovertemplate="<b>SELL</b><br>%{x}<br>Reason: %{customdata}<extra></extra>",
			customdata=[t.get("exit_reason", "strategy") for t in trades]
		),
		row=1, col=1
	)

	# --- Row 2: Drawdown ---
	rolling_max = equity_curve.expanding().max()
	drawdown = (equity_curve - rolling_max) / rolling_max * 100

	fig.add_trace(
		go.Scatter(
			x=drawdown.index,
			y=drawdown.values,
			name="Drawdown",
			fill="tozeroy",
			line=dict(color="#ff4444", width=1),
			fillcolor="rgba(255, 68, 68, 0.3)",
			hovertemplate="<b>%{x}</b><br>Drawdown: %{y:.2f}%<extra></extra>"
		),
		row=2, col=1
	)

	# Max drawdown line
	fig.add_hline(
		y=m["max_drawdown"] * 100,
		line_dash="dash",
		line_color="red",
		annotation_text=f"Max DD: {m['max_drawdown']*100:.1f}%",
		row=2, col=1
	)

	# --- Row 3: Returns Distribution ---
	returns = equity_curve.pct_change().dropna() * 100

	fig.add_trace(
		go.Histogram(
			x=returns.values,
			name="Returns",
			nbinsx=50,
			marker_color="#00d4aa",
			opacity=0.7,
			hovertemplate="Return: %{x:.2f}%<br>Count: %{y}<extra></extra>"
		),
		row=3, col=1
	)

	# Zero line on returns distribution
	fig.add_vline(x=0, line_color="white", line_dash="dash", row=3, col=1)

	# --- Layout and Metrics Panel ---
	info = results["data_info"]

	metrics_text = (
		f"<b>PERFORMANCE SUMMARY</b><br>"
		f"Period: {info['start']} → {info['end']} ({info['years']}y)<br>"
		f"Capital: ${results['initial_capital']:,.0f} → ${results['final_capital']:,.0f}<br>"
		f"<br>"
		f"<b>RETURNS</b><br>"
		f"Total: {m['total_return']*100:.1f}% | Annual: {m['annual_return']*100:.1f}%<br>"
		f"vs {benchmark}: {m.get('outperformance', 0)*100:.1f}% alpha<br>"
		f"<br>"
		f"<b>RISK</b><br>"
		f"Sharpe: {m['sharpe_ratio']:.2f} | Sortino: {m['sortino_ratio']:.2f}<br>"
		f"Calmar: {m['calmar_ratio']:.2f} | Max DD: {m['max_drawdown']*100:.1f}%<br>"
		f"DD Duration: {m['max_drawdown_duration']} bars<br>"
		f"<br>"
		f"<b>TRADES</b><br>"
		f"Total: {m['total_trades']} | Win Rate: {m['win_rate']*100:.1f}%<br>"
		f"Profit Factor: {m['profit_factor']:.2f} | Expectancy: ${m['expectancy']:.0f}<br>"
		f"Streaks: {m['max_win_streak']}W / {m['max_loss_streak']}L<br>"
		f"Avg MAE: {m['mae']*100:.2f}%"
	)

	fig.add_annotation(
		text=metrics_text,
		xref="paper", yref="paper",
		x=1.02, y=0.98,
		showarrow=False,
		align="left",
		bgcolor="rgba(30,30,30,0.9)",
		bordercolor="#444",
		borderwidth=1,
		font=dict(size=11, color="white"),
		xanchor="left",
		yanchor="top"
	)

	fig.update_layout(
		template="plotly_dark",
		height=900,
		title=dict(
			text=f"<b>{ticker} Backtest Report</b> — {info['start']} to {info['end']}",
			font=dict(size=18)
		),
		showlegend=True,
		legend=dict(
			orientation="h",
			yanchor="bottom",
			y=1.02,
			xanchor="left",
			x=0
		),
		margin=dict(r=280),
		hovermode="x unified"
	)

	fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
	fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
	fig.update_yaxes(title_text="Frequency", row=3, col=1)
	fig.update_xaxes(title_text="Date", row=3, col=1)

	# Save and open
	fig.write_html(filepath, auto_open=False)
	print(f"Report saved: {filepath}")

	return filepath


def open_report(filepath: str) -> None:
	"""Open an HTML report in the default browser."""
	webbrowser.open(f"file://{os.path.abspath(filepath)}")
	print(f"Opening report in browser...")
