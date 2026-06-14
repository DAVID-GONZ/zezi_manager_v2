"""Revisión empírica: ciclo de vida de escenarios y su vinculación con horarios."""
import sqlite3
from src.infrastructure.db.schema import SCHEMA, INDICES, TRIGGERS
from src.infrastructure.db.seed import seed_dev, _fast_hasher

conn = sqlite3.connect(":memory:", check_same_thread=False)
for sql in SCHEMA: conn.execute(sql)
for sql in INDICES: conn.execute(sql)
for sql in TRIGGERS: conn.execute(sql)
res = seed_dev(conn, anio=2025, hasher=_fast_hasher, total_estudiantes=24, seed_random=1)
conn.commit()

from src.infrastructure.db.repositories.sqlite_infraestructura_repo import SqliteInfraestructuraRepository
from src.infrastructure.db.repositories.sqlite_asignacion_repo import SqliteAsignacionRepository
from src.infrastructure.db.repositories.sqlite_usuario_repo import SqliteUsuarioRepository
from src.services.infraestructura_service import InfraestructuraService
from src.services.horario_service import HorarioService
from src.services.usuario_service import UsuarioService
from src.services.generador_horario_service import GeneradorHorarioService

infra_repo = SqliteInfraestructuraRepository(conn=conn)
asig_repo = SqliteAsignacionRepository(conn=conn)
usu_repo = SqliteUsuarioRepository(conn=conn)
infra = InfraestructuraService(repo=infra_repo)
usu_svc = UsuarioService(repo=usu_repo)
horario = HorarioService(infra_repo=infra_repo, asignacion_repo=asig_repo, usuario_repo=usu_svc)
gen = GeneradorHorarioService(infra_repo=infra_repo, asignacion_repo=asig_repo,
                              usuario_repo=usu_svc, horario_service=horario,
                              infraestructura_service=infra)

anio_id = res.anio_id
def listar():
    return infra.listar_escenarios(anio_id)

print("=== 1. Escenarios tras seed ===")
for e in listar():
    nb = len(infra.listar_horario_escenario(e.id))
    print(f"  id={e.id} nombre={e.nombre!r} activo={e.activo} bloques={nb}")

print("\n=== 2. Generar horario (config 'Config inicial') ===")
cfg_id = conn.execute("SELECT id FROM config_generacion WHERE nombre='Config inicial'").fetchone()[0]
r = gen.generar(cfg_id, crear_escenario=True, optimizar=True)
conn.commit()
print(f"  total={r.total_requeridos} colocados={r.colocados} valido={r.valido} escenario_id={r.escenario_id}")

print("\n=== 3. Escenarios tras generar (¿aparece el generado con bloques?) ===")
gen_id = None
for e in listar():
    nb = len(infra.listar_horario_escenario(e.id))
    marca = "  <-- GENERADO" if e.nombre.startswith("Generado") else ""
    if e.nombre.startswith("Generado"): gen_id = e.id
    print(f"  id={e.id} nombre={e.nombre!r} activo={e.activo} bloques={nb}{marca}")

print("\n=== 4. datos_parrilla del escenario generado ===")
dp = horario.datos_parrilla(gen_id)
print(f"  dias={dp['dias']} franjas={len(dp['franjas'])} celdas={len(dp['celdas'])}")

print("\n=== 5. Activar el generado (exclusividad) ===")
infra.activar_escenario(gen_id); conn.commit()
acts = [(e.nombre, e.activo) for e in listar()]
print(f"  estados activo: {acts}")
n_activos = sum(1 for _, a in acts if a)
print(f"  #activos = {n_activos} (debe ser 1)")

print("\n=== 6. Duplicar el generado (¿copia los bloques?) ===")
dup = infra.duplicar_escenario(gen_id, "Copia review"); conn.commit()
nb_dup = len(infra.listar_horario_escenario(dup.id))
nb_orig = len(infra.listar_horario_escenario(gen_id))
print(f"  original bloques={nb_orig}  copia bloques={nb_dup} (deben coincidir)")

print("\n=== 7. Eliminar 'Plan alterno' (cascada) ===")
pa = next((e for e in listar() if e.nombre == "Plan alterno"), None)
if pa:
    infra.eliminar_escenario(pa.id); conn.commit()
    quedan = [e.nombre for e in listar()]
    print(f"  quedan: {quedan}")
else:
    print("  no existe Plan alterno")

print("\n=== 8. Generar OTRA vez (¿se acumulan escenarios duplicados?) ===")
r2 = gen.generar(cfg_id, crear_escenario=True, optimizar=True); conn.commit()
nombres = [e.nombre for e in listar()]
n_generados = sum(1 for n in nombres if n.startswith("Generado"))
print(f"  escenarios ahora: {nombres}")
print(f"  #'Generado ...' = {n_generados}")
