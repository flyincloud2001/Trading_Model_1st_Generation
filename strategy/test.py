
import sys
import os 
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from data.loader import load_multiple
from strategy.cointegration import cadf_test
from strategy.hedge_ratio import calc_rolling_hedge_ratio
from strategy.hedge_ratio import calc_spread
import matplotlib.pyplot as plt
import numpy as np

data = load_multiple(["GLD", "GDX"])

gld = data['GLD']['Close']
gdx = data['GDX']['Close']

hedge_ratios=  calc_rolling_hedge_ratio(gld, gdx, )
hedge_ratio = result['hedge_ratio']

spread = gld - hedge_ratio* gdx

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(spread)
plt.show()

