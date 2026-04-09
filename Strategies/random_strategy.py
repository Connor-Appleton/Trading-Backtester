"""
random_strategy.py — Random baseline strategy.

Makes completely random buy/sell/hold decisions.
Any strategy that can't beat random is worthless.
This gives you the floor — the absolute minimum acceptable performance.
"""

import random


def random_strategy(current_bar: dict, history, position: int, portfolio_value: float, cash: float):
	"""
	Random strategy — purely random decisions for baseline comparison.

	Args:
		current_bar:     Dict with current OHLCV data
		history:         DataFrame of historical bars
		position:        Current shares held
		portfolio_value: Current portfolio value
		cash:            Available cash

	Returns:
		Tuple of (action, quantity)
	"""
	price = current_bar["close"]
	roll = random.random()

	if position == 0:
		# No position — randomly buy or hold
		if roll > 0.7:  # 30% chance to buy
			quantity = int(cash // price)
			if quantity > 0:
				return ("buy", quantity)
	else:
		# In position — randomly sell or hold
		if roll > 0.7:  # 30% chance to sell
			return ("sell", position)

	return ("hold", 0)
