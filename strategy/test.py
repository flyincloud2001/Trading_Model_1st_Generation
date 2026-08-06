
import sys
import os 
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from data.loader import load_multiple
from strategy.hedge_ratio import calc
import matplotlib.pyplot as plt
import numpy as np

data = load_multiple(["GLD", "GDX"])

gld = data['GLD']['Close']
gdx = data['GDX']['Close']


spread = gld - gdx

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(spread)
plt.show()

