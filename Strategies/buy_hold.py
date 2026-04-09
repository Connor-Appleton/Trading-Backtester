"""
buy_hold.py — Buy and hold baseline strategy.

Buys as many shares as possible on the first bar and holds until the end.
This is the benchmark that active strategies must beat to justify their complexity.
If your strategy can't beat buy-and-hold it's not worth the transaction costs.
"""


def buy_and_hold(current_bar: dict, history, position: int, portfolio_value: float, cash: float):
	"""
	Buy and hold strategy — buy everything on first bar, never sell.

	Args:
		current_bar:     Dict with current OHLCV data
		history:         DataFrame of historical bars (unused in this strategy)
		position:        Current shares held
		portfolio_value: Current portfolio value
		cash:            Available cash

	Returns:
		Tuple of (action, quantity)
	"""
	# If we have no position buy as many shares as possible
	if position == 0:
		price = current_bar["close"]
		quantity = int(cash // price)
		if quantity > 0:
			return ("buy", quantity)

	# Otherwise hold forever
	return ("hold", 0)
