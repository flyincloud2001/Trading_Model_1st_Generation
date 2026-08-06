
import sys
import os 
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from data.loader import load_multiple
import matplotlib.pyplot as plt
import numpy as np

data = load_multiple(["GLD", "GDX"])

gld = data['GLD']['Close']
gdx = data['GDX']['Close']

spread = gld - gdx

fig, ax = plt.subplot(figsize=(12, 5))
ax.plot(spread)
plt.show()

