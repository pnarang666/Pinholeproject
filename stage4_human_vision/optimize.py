"""Simple Pareto-front utilities for Stage 4."""


def pareto_front(rows, maximize=None, minimize=None):
    maximize = maximize or []
    minimize = minimize or []
    survivors = []
    for i, row_i in enumerate(rows):
        dominated = False
        for j, row_j in enumerate(rows):
            if i == j:
                continue
            ge_all = all(row_j[k] >= row_i[k] for k in maximize) and all(row_j[k] <= row_i[k] for k in minimize)
            strict = any(row_j[k] > row_i[k] for k in maximize) or any(row_j[k] < row_i[k] for k in minimize)
            if ge_all and strict:
                dominated = True
                break
        if not dominated:
            survivors.append(row_i)
    return survivors
