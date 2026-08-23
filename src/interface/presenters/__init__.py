"""Presenters puros de la capa de interfaz.

Un *presenter* contiene el estado y la lógica de decisión de una página (lo que
antes vivía en closures entrelazados con los `refreshables` de NiceGUI), pero
**sin importar `nicegui`**: recibe datos y devuelve datos/estado. Así la lógica
de la UI se testea de verdad (llamando al presenter) en vez de reimplementarla
en el test. La página queda como adaptador fino: llama a las transiciones del
presenter y dispara los `.refresh()`.

Regla dura (verificada por `tests/unit/interface/presenters/test_presenters_puros.py`):
ningún módulo de este paquete puede importar `nicegui`.
"""
