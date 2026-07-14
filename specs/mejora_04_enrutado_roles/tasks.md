# Tasks: Coherencia de roles en el enrutado (mejora_04_enrutado_roles)

- [x] T1: En `main.py`, cambiar el alias `/informes` a `roles=_AULA` (espeja su
      destino) y añadir un comentario junto a `redirigir_a` con la convención
      "un alias hereda los roles de su destino".
  Verifica: `python -m pytest tests/unit/interface/auth/ -q`
  Produce: `/informes` con `roles=_AULA`; tests de autorización verdes

- [x] T2: Añadir un test guardarraíl en `tests/unit/interface/auth/` que verifique,
      sobre `rutas_registradas()`, que cada ruta-alias de redirección apunta a una
      ruta registrada y con los mismos roles que su destino (R1/R4).
  Verifica: `python -m pytest tests/unit/interface/auth/ -q`
  Produce: `tests/unit/interface/auth/test_alias_roles.py` verde

- [x] T3: Verificar entorno completo.
  Verifica: `python init.py`
  Produce: todos los checks verdes
