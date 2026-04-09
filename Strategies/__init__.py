"""
Strategies — pluggable trading strategy implementations.
"""

from strategies.buy_hold import buy_and_hold
from strategies.random_strategy import random_strategy

__all__ = [
	"buy_and_hold",
	"random_strategy"
]
