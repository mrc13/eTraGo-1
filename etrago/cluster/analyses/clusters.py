# -*- coding: utf-8 -*-
"""
plots to anaylse the cluster structure (based on the distance martrix)
"""
from config import clustered_path

from os import path

import matplotlib
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd

# TODO: replace clustered path by root path, once the results
# structure is changend
Z = pd.read_csv(path.join(clustered_path, 'Z.csv')).values

last = Z[-200:, 2]
last_rev = last[::-1]
idxs = np.arange(1, len(last) + 1)
plt.plot(idxs, last_rev)
plt.show()

acceleration = np.diff(last, 2)  # 2nd derivative of the distances
acceleration_rev = acceleration[::-1]
plt.plot(idxs[:-2] + 1, acceleration_rev)
plt.show()
# k = acceleration_rev.argmax() + 2  # if idx 0 is the max of this we want 2 clusters
# print("clusters:", k)
# dendrogram(Z, color_threshold=25)
#
#
#
