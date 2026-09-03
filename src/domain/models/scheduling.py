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

    def _kuhn(
        a_node: int,
        visitados: set[int],
        adj: dict[int, list[int]],
        match_b: list[int],
        match_a: list[int],
    ) -> bool:
        for ei in adj[a_node]:
            bi2 = edges[ei][1]
            if bi2 in visitados:
                continue
            visitados.add(bi2)
            if match_b[bi2] == -1 or _kuhn(edges[match_b[bi2]][0], visitados, adj, match_b, match_a):
                match_b[bi2] = ei
                match_a[a_node] = ei
                return True
        return False

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

            for a_node in range(size):
                _kuhn(a_node, set(), adj, match_b, match_a)

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


def reparar_coloreo(
    aristas: list[tuple[int, int]],
    color_de: list[int],
    n_colores: int,
    dia_de_color: list[int],
    *,
    vetos_duros: frozenset[tuple[int, int]] = frozenset(),
    vetos_blandos: frozenset[tuple[int, int]] = frozenset(),
    max_por_dia: dict[int, int] | None = None,
    min_por_dia: dict[int, int] | None = None,
    max_intentos: int = 200_000,
    limite_segundos: float = 5.0,
    semilla: int = 0,
) -> tuple[list[int], dict[str, int]]:
    """
    Repara un coloreo propio para satisfacer restricciones laterales.

    `colorear_aristas_bipartito` produce un horario sin choques de grupo ni de
    docente, pero es ciego a todo lo demás: vetos de disponibilidad, franjas de
    reunión y topes de horas por día. Esta función parte de ese coloreo y lo
    corrige mediante **intercambios dentro de la fila de un grupo**: permutar
    los colores de dos lecciones del mismo grupo, o mover una a un color que el
    grupo tenga libre. Ese movimiento nunca rompe la propiedad del coloreo,
    porque solo se aplica si el docente destino está libre en el color destino.

    El intercambio es el movimiento correcto —y a menudo el único posible—
    cuando la demanda de un grupo iguala al número de slots: en ese caso el
    grupo está lleno y no existe ningún hueco al que mover una lección.

    Parámetros
    ----------
    aristas       lista de (grupo, docente), paralela a `color_de`.
    color_de      coloreo propio inicial (sin None).
    n_colores     número de colores/slots.
    dia_de_color  color -> índice de día, para los topes diarios.
    vetos_duros   {(docente, color)} prohibidos (indisponibilidad declarada).
    vetos_blandos {(docente, color)} desaconsejados (franja de reunión).
    max_por_dia   {docente: tope de horas al día}.
    min_por_dia   {docente: piso de horas en un día ya ocupado}.

    Devuelve `(color_de_reparado, violaciones)`, con las claves
    `indisponibilidad`, `reunion`, `exceso_max_dia` y `deficit_min_dia`.
    Devuelve siempre el mejor estado alcanzado: nunca empeora la entrada.
    """
    import random
    import time

    n = len(aristas)
    if n == 0 or n_colores <= 0:
        return list(color_de), {
            "indisponibilidad": 0,
            "reunion": 0,
            "exceso_max_dia": 0,
            "deficit_min_dia": 0,
        }

    gid = [a[0] for a in aristas]
    tid = [a[1] for a in aristas]
    max_por_dia = max_por_dia or {}
    min_por_dia = min_por_dia or {}
    n_dias = (max(dia_de_color) + 1) if dia_de_color else 1

    col = list(color_de)
    at_g: dict[int, dict[int, int]] = {}
    at_t: dict[int, dict[int, int]] = {}
    horas: dict[int, list[int]] = {}
    for i, k in enumerate(col):
        at_g.setdefault(gid[i], {})[k] = i
        at_t.setdefault(tid[i], {})[k] = i
        horas.setdefault(tid[i], [0] * n_dias)[dia_de_color[k]] += 1

    # Pesos: la indisponibilidad domina; el piso diario es la única blanda.
    p_duro, p_blando, p_max, p_min = 1000, 100, 100, 1

    def _pen_dia(t: int, d: int) -> tuple[int, int]:
        x = horas[t][d]
        tope = max_por_dia.get(t)
        piso = min_por_dia.get(t)
        mx = (x - tope) if (tope is not None and x > tope) else 0
        mn = (piso - x) if (piso and 0 < x < piso) else 0
        return mx, mn

    def _veto(i: int) -> tuple[int, int]:
        clave = (tid[i], col[i])
        return (1 if clave in vetos_duros else 0, 1 if clave in vetos_blandos else 0)

    pen_d = sum(1 for i in range(n) if (tid[i], col[i]) in vetos_duros)
    pen_b = sum(1 for i in range(n) if (tid[i], col[i]) in vetos_blandos)
    pen_mx = pen_mn = 0
    for t in horas:
        for d in range(n_dias):
            a, b = _pen_dia(t, d)
            pen_mx += a
            pen_mn += b

    def _aplicar(i: int, j: int | None, k1: int, k2: int) -> None:
        """Mueve i de k1 a k2; si j no es None, lo mueve de k2 a k1."""
        g = gid[i]
        col[i] = k2
        at_g[g][k2] = i
        del at_t[tid[i]][k1]
        at_t[tid[i]][k2] = i
        if j is None:
            del at_g[g][k1]
        else:
            col[j] = k1
            at_g[g][k1] = j
            del at_t[tid[j]][k2]
            at_t[tid[j]][k1] = j
        d1, d2 = dia_de_color[k1], dia_de_color[k2]
        if d1 != d2:
            horas[tid[i]][d1] -= 1
            horas[tid[i]][d2] += 1
            if j is not None:
                horas[tid[j]][d2] -= 1
                horas[tid[j]][d1] += 1

    actual = pen_d * p_duro + pen_b * p_blando + pen_mx * p_max + pen_mn * p_min
    mejor = actual
    mejor_col = list(col)
    mejor_pen = (pen_d, pen_b, pen_mx, pen_mn)

    rnd = random.Random(semilla)
    t_fin = time.monotonic() + limite_segundos
    conflictivas: list[int] = []
    intentos = 0

    while intentos < max_intentos and actual > 0:
        intentos += 1
        if intentos % 256 == 0 and time.monotonic() > t_fin:
            break

        # Sesgo hacia lecciones que participan en alguna violación: con 360
        # lecciones y un puñado de conflictos, el muestreo uniforme desperdicia
        # casi todos los intentos.
        if not conflictivas:
            for idx in range(n):
                k = col[idx]
                if (tid[idx], k) in vetos_duros or (tid[idx], k) in vetos_blandos:
                    conflictivas.append(idx)
                    continue
                a, b = _pen_dia(tid[idx], dia_de_color[k])
                if a or b:
                    conflictivas.append(idx)
        sesgar = bool(conflictivas) and rnd.random() < 0.9
        i = rnd.choice(conflictivas) if sesgar else rnd.randrange(n)
        if intentos % 512 == 0:
            conflictivas.clear()

        k1 = col[i]
        k2 = rnd.randrange(n_colores)
        if k1 == k2:
            continue
        j = at_g[gid[i]].get(k2)
        # Permutar dos lecciones del mismo grupo Y del mismo docente no cambia
        # nada (el coste solo mira docente y día) y ademas corrompe el indice,
        # porque las dos escrituras sobre at_t[t] se pisan entre si.
        if j is not None and tid[i] == tid[j]:
            continue
        # El docente de i debe quedar libre en k2 (salvo que lo ocupe el propio j).
        if at_t[tid[i]].get(k2) not in (None, j):
            continue
        if j is not None and at_t[tid[j]].get(k1) not in (None, i):
            continue

        d1, d2 = dia_de_color[k1], dia_de_color[k2]
        afectados = {(tid[i], d1), (tid[i], d2)}
        if j is not None:
            afectados |= {(tid[j], d1), (tid[j], d2)}

        ant_mx = ant_mn = 0
        for t, d in afectados:
            a, b = _pen_dia(t, d)
            ant_mx += a
            ant_mn += b
        vd, vb = _veto(i)
        if j is not None:
            vd2, vb2 = _veto(j)
            vd += vd2
            vb += vb2

        _aplicar(i, j, k1, k2)

        nue_mx = nue_mn = 0
        for t, d in afectados:
            a, b = _pen_dia(t, d)
            nue_mx += a
            nue_mn += b
        nvd, nvb = _veto(i)
        if j is not None:
            nvd2, nvb2 = _veto(j)
            nvd += nvd2
            nvb += nvb2

        cand = actual + (nvd - vd) * p_duro + (nvb - vb) * p_blando
        cand += (nue_mx - ant_mx) * p_max + (nue_mn - ant_mn) * p_min

        if cand <= actual:
            # Se aceptan los movimientos laterales: son los que permiten
            # recorrer la meseta hasta encontrar la permutación que resuelve.
            actual = cand
            pen_d += nvd - vd
            pen_b += nvb - vb
            pen_mx += nue_mx - ant_mx
            pen_mn += nue_mn - ant_mn
            conflictivas.clear()
            if cand < mejor:
                mejor = cand
                mejor_col = list(col)
                mejor_pen = (pen_d, pen_b, pen_mx, pen_mn)
        elif j is None:
            _aplicar(i, None, k2, k1)
        else:
            _aplicar(j, i, k1, k2)

    d, b, mx, mn = mejor_pen
    return mejor_col, {
        "indisponibilidad": d,
        "reunion": b,
        "exceso_max_dia": mx,
        "deficit_min_dia": mn,
    }


__all__ = ["colorear_aristas_bipartito", "reparar_coloreo"]
