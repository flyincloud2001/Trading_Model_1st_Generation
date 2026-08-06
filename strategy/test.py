import sys
import os 
os.path.append(os.path.join(os.path.dirname(__file__), ".."))
from data.loader import load_multiple
import matplotlib.pyplot as plt
import numpy as np

gld, gdx = load_multiple(["GLD", "GDX"])
print(gld)

