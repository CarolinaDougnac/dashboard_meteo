"""
Implementación simple del módulo `custom_color_palette`
compatible con el uso que haces en tu notebook:

- ccp.range(inicio, fin, paso)
- ccp.creates_palette([paleta_1, paleta_2, ...], extend='both')

Cada `paleta_i` es una lista de:
    [colors, valores]        (obligatorio)
    [colors, valores, ...]   (opcional: se ignoran argumentos extra)

donde:
- `colors` puede ser:
    * una lista de nombres RGB / tuplas (R,G,B)
    * un objeto Colormap de matplotlib (ej: plt.cm.Greys)

- `valores` es un array 1D (ej: ccp.range(-90, -75, 0.5))

La función crea:
- un colormap continuo que pasa por todos los segmentos
- un `BoundaryNorm` para esos límites
"""

import numpy as np
import matplotlib.colors as mcolors
from builtins import range as _py_range   # <- range ORIGINAL de Python


def range(start: float, stop: float, step: float):
    """
    Versión simple de `range` numérico.
    Devuelve un np.ndarray con puntos desde start hasta stop (incluido),
    con paso `step`.
    """
    # añadimos un pequeño epsilon para incluir el extremo superior
    n_steps = int(np.floor((stop - start) / step)) + 1
    return np.linspace(start, start + step * (n_steps - 1), n_steps)


def _colors_from_spec(color_spec, n):
    """
    Devuelve una lista de n colores (RGBA) a partir de:
    - un Colormap de matplotlib
    - una lista de nombres / tuplas RGB
    """
    if isinstance(color_spec, mcolors.Colormap):
        xs = np.linspace(0.0, 1.0, n)
        return [color_spec(x) for x in xs]

    # asumimos lista de nombres / tuplas
    names = list(color_spec)
    if len(names) == 1:
        # un solo color -> repetimos
        return [mcolors.to_rgba(names[0])] * n

    # interpolamos entre los colores dados usando range ORIGINAL de Python
    res = []
    for i in _py_range(n):
        t = i / max(n - 1, 1)
        pos = t * (len(names) - 1)
        i0 = int(np.floor(pos))
        i1 = min(int(np.ceil(pos)), len(names) - 1)
        frac = pos - i0
        c0 = np.array(mcolors.to_rgba(names[i0]))
        c1 = np.array(mcolors.to_rgba(names[i1]))
        c = (1 - frac) * c0 + frac * c1
        res.append(tuple(c))
    return res


def creates_palette(paletas, extend="both"):
    """
    paletas: lista de paleta_i

    Cada paleta_i = [colors, valores, (opcional ...)]
      - colors: lista de colores o Colormap
      - valores: array 1D (np.ndarray)
      - argumentos extra se ignoran (en tu notebook
        se usa a veces un 3er elemento para "estirar" colores)

    Devuelve:
      cmap, ticks, norm, bounds
    """
    all_vals = []
    all_cols = []

    for pal in paletas:
        if len(pal) < 2:
            continue

        color_spec = pal[0]
        vals = np.asarray(pal[1], dtype=float)

        # lista de colores para este segmento
        cols_seg = _colors_from_spec(color_spec, len(vals))
        all_vals.extend(vals.tolist())
        all_cols.extend(cols_seg)

    all_vals = np.asarray(all_vals, dtype=float)

    # ordenamos por valor
    order = np.argsort(all_vals)
    all_vals = all_vals[order]
    all_cols = [all_cols[i] for i in order]

    vmin = float(all_vals.min())
    vmax = float(all_vals.max())

    # normalizamos a 0-1 para construir el colormap
    denom = (vmax - vmin) if vmax > vmin else 1.0
    vals_norm = (all_vals - vmin) / denom

    # Nos aseguramos de que esté en [0, 1]
    vals_norm = np.clip(vals_norm, 0.0, 1.0)

    # Y garantizamos que el primero sea 0 y el último 1
    vals_norm[0] = 0.0
    vals_norm[-1] = 1.0

    color_list = list(zip(vals_norm, all_cols))

    cmap = mcolors.LinearSegmentedColormap.from_list("custom_ccp", color_list) 

    # bounds y ticks: usamos los valores únicos
    bounds = np.unique(all_vals)
    ticks = bounds.copy()

    # BoundaryNorm para que cada intervalo use un color
    norm = mcolors.BoundaryNorm(boundaries=bounds, ncolors=cmap.N, extend=extend)

    return cmap, ticks, norm, bounds


