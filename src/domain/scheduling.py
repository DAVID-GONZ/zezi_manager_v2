"""
Dominio — coloreo exacto de horarios
=====================================

Algoritmo puro (sin dependencias de infraestructura ni UI) para construir
horarios factibles mediante coloreo propio de aristas de un multigrafo
bipartito grupo<->docente.

Cada lección es una arista entre su grupo (lado A) y su docente (lado B).
Colorear las aristas con `n_colores` colores de modo que dos aristas que
comparten un extremo nunca compartan color equivale a asignar a cada lección
un slot (color) sin choques de grupo ni de docente. Si el grado máximo del
grafo es <= n_colores, el teorema de König garantiza la existencia del
coloreo, y este lo encuentra de forma exacta, determinista y polinómica.
"""
from __future__ import annotations


def colorear_aristas_bipartito(
    aristas: list[tuple[int, int]],
    n_colores: int,
) -> list[int | None]:
    """
    Coloreo propio de aristas de un multigrafo bipartito (lado A ↔ lado B).

    Cada arista es una tupla (a, b) con a en el lado A y b en el lado B.
    Devuelve una lista `color_de` paralela a `aristas`, donde `color_de[i]` es
    el color (0..n_colores-1) asignado a la arista i, tal que dos aristas que
    comparten un extremo nunca reciben el mismo color.

    Requiere que el grado máximo (sobre ambos lados) sea <= n_colores; en ese
    caso el teorema de König garantiza la existencia del coloreo. El algoritmo
    es determinista y polinómico:
      1. Regulariza el grafo a uno n_colores-regular añadiendo nodos y aristas
         ficticias (degree padding).
      2. Lo descompone en n_colores emparejamientos perfectos mediante caminos
         aumentantes (Kuhn). Las aristas reales de cada emparejamiento reciben
         el color de esa ronda.
    """
    n = len(aristas)
    color_de: list[int | None] = [None] * n
    if n == 0:
        return color_de

    nodos_a = sorted({a for a, _b in aristas})
    nodos_b = sorted({b for _a, b in aristas})
    amap = {a: i for i, a in enumerate(nodos_a)}
    bmap = {b: i for i, b in enumerate(nodos_b)}

    # Igualar el tamaño de ambos lados con nodos ficticios.
    size = max(len(nodos_a), len(nodos_b))

    # Aristas como [a_idx, b_idx, leccion_idx | None].
    edges: list[list] = [[amap[a], bmap[b], i] for i, (a, b) in enumerate(aristas)]

    grado_a = [0] * size
    grado_b = [0] * size
    for ai, bi, _ in edges:
        grado_a[ai] += 1
        grado_b[bi] += 1

    # Padding: añadir aristas ficticias hasta que todo nodo tenga grado n_colores.
    ai = 0
    bi = 0
    while ai < size and bi < size:
        if grado_a[ai] >= n_colores:
            ai += 1
            continue
        if grado_b[bi] >= n_colores:
            bi += 1
            continue
        edges.append([ai, bi, None])  # arista ficticia
        grado_a[ai] += 1
        grado_b[bi] += 1

    import sys as _sys
    limite_previo = _sys.getrecursionlimit()
    _sys.setrecursionlimit(max(limite_previo, size * 4 + 1000))
    try:
        remaining = list(range(len(edges)))
        for color in range(n_colores):
            # Adyacencia del lado A sobre las aristas restantes.
            adj: dict[int, list[int]] = {i: [] for i in range(size)}
            for ei in remaining:
                adj[edges[ei][0]].append(ei)

            match_b = [-1] * size  # nodo B -> índice de arista emparejada
            match_a = [-1] * size  # nodo A -> índice de arista emparejada

            def _kuhn(a_node: int, visitados: set[int]) -> bool:
                for ei in adj[a_node]:
                    bi2 = edges[ei][1]
                    if bi2 in visitados:
                        continue
                    visitados.add(bi2)
                    if match_b[bi2] == -1 or _kuhn(edges[match_b[bi2]][0], visitados):
                        match_b[bi2] = ei
                        match_a[a_node] = ei
                        return True
                return False

            for a_node in range(size):
                _kuhn(a_node, set())

            matched = {match_a[a] for a in range(size) if match_a[a] != -1}
            nuevos: list[int] = []
            for ei in remaining:
                if ei in matched:
                    li = edges[ei][2]
                    if li is not None:
                        color_de[li] = color
                else:
                    nuevos.append(ei)
            remaining = nuevos
    finally:
        _sys.setrecursionlimit(limite_previo)

    return color_de


__all__ = ["colorear_aristas_bipartito"]
