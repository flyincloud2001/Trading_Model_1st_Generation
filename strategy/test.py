
import sys
import os 
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from data.loader import load_multiple
from strategy.cointegration import cadf_test
from strategy.hedge_ratio import calc_rolling_hedge_ratio
from strategy.hedge_ratio import calc_spread
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

data = load_multiple(["GLD", "GDX"])

gld = data['GLD']['Close']
gdx = data['GDX']['Close']

gld =  gld[gld.index >= gld.index.max() - pd.DateOffset(months=8)]
gdx =  gdx[gdx.index >= gdx.index.max() - pd.DateOffset(months=8)]

gld, gdx = gld.align(gdx, join='inner')

cadf_result = cadf_test(gld, gdx)




