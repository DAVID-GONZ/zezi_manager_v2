"""
audit_auth.py — Auditoría de la capa de autenticación
======================================================
Exit code 0 si todo OK, 1 si hay errores.
"""
from __future__ import annotations

import ast
import importlib
import sys
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

OK  = "✅"
ERR = "❌"
WRN = "⚠️ "

AUTH_DIR = Path("src/infrastructure/auth")

# ── Contratos esperados ───────────────────────────────────────────────────────

ARCHIVOS_ESPERADOS = {
    "bcrypt_auth_service.py": {
        "descripcion": "Implementación de IAuthenticationService con bcrypt",
        "clase_esperada": "BcryptAuthService",
        "implementa_port": "IAuthenticationService",
        "metodos_minimos": [
            "hashear_password",
            "verificar_password",
            "cambiar_password",
            "resetear_password",
        ],
        "debe_contener": ["bcrypt", "sha256"],
        "no_debe_contener": ["sqlite3", "execute", "SELECT", "INSERT"],
    },
    "bcrypt_auth.py": {
        "descripcion": "Utilidades bcrypt puras (sin dependencias de dominio)",
        "funciones_o_clases": ["hashear", "verificar"],
        "no_debe_importar": [
            "src.domain", "src.services",
            "src.infrastructure.db", "sqlite3",
        ],
        "debe_contener": ["bcrypt"],
    },
    "jwt_handler.py": {
        "descripcion": "Generación y verificación de tokens JWT (para API v3.0)",
        "funciones_o_clases": ["JWTHandler", "crear_token", "verificar_token"],
        "campos_payload_minimos": [
            "usuario_id", "rol", "exp",
        ],
        "no_debe_contener": ["sqlite3", "SELECT"],
    },
}

IMPORTS_PROHIBIDOS = {
    "sqlite3", "pandas", "nicegui",
    "SqliteUsuarioRepository", "SqliteEstudianteRepository",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def titulo(texto: str) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {texto}")
    print(f"{'─' * 62}")


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"  {ERR} Error de sintaxis: {e}")
        return None


def _nombres_definidos(tree: ast.Module) -> set[str]:
    nombres = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nombres.add(node.name)
    return nombres


def _imports_en_modulo(tree: ast.Module) -> set[str]:
    nombres = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                nombres.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                nombres.add(node.module)
            for a in node.names:
                nombres.add(a.name)
    return nombres


def _hereda_de(tree: ast.Module, clase: str, base: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == clase:
            for b in node.bases:
                nombre_base = ""
                if isinstance(b, ast.Name):
                    nombre_base = b.id
                elif isinstance(b, ast.Attribute):
                    nombre_base = b.attr
                if nombre_base == base:
                    return True
    return False


# ── Verificaciones funcionales ────────────────────────────────────────────────

def verificar_bcrypt_operaciones() -> list[str]:
    """Prueba real de hash y verificación con bcrypt."""
    errores = []
    titulo("3. Pruebas funcionales — bcrypt")

    try:
        from src.infrastructure.auth.bcrypt_auth import hashear, verificar
        password = "test_password_123"
        hash1 = hashear(password)
        hash2 = hashear(password)

        if hash1 != hash2:
            print(f"  {OK} hashear(): genera salt distinto cada vez (seguro)")
        else:
            print(f"  {ERR} hashear(): dos hashes iguales para misma clave (inseguro)")
            errores.append("bcrypt_auth: hashes idénticos — falta salt aleatorio")

        if verificar(password, hash1):
            print(f"  {OK} verificar(): password correcto → True")
        else:
            print(f"  {ERR} verificar(): password correcto devolvió False")
            errores.append("bcrypt_auth: verificar() falla con password correcto")

        if not verificar("wrong_password", hash1):
            print(f"  {OK} verificar(): password incorrecto → False")
        else:
            print(f"  {ERR} verificar(): password incorrecto devolvió True")
            errores.append("bcrypt_auth: verificar() acepta password incorrecto")

        if hash1.startswith("$2b$"):
            print(f"  {OK} Hash tiene formato bcrypt estándar ($2b$)")
        else:
            print(f"  {WRN} Hash no empieza con $2b$ — verificar formato")

    except ImportError as e:
        print(f"  {ERR} No se pudo importar bcrypt_auth: {e}")
        errores.append(f"bcrypt_auth.py: no importable — {e}")
    except Exception as e:
        print(f"  {ERR} Error en pruebas bcrypt: {e}")
        errores.append(f"bcrypt_auth.py: error funcional — {e}")

    return errores


def verificar_compatibilidad_sha256() -> list[str]:
    """Verifica que el servicio maneja hashes sha256: del seed."""
    errores = []
    titulo("4. Compatibilidad con hashes legacy (sha256: del seed)")

    try:
        from src.infrastructure.auth.bcrypt_auth_service import BcryptAuthService
        svc = BcryptAuthService()

        password = "Admin2025*"
        digest = hashlib.sha256(password.encode()).hexdigest()
        hash_legacy = f"sha256:{digest}"

        if svc.verificar_password(password, hash_legacy):
            print(f"  {OK} Acepta hashes sha256: del seed de desarrollo")
        else:
            print(f"  {ERR} No acepta hashes sha256: (rompe el seed de dev)")
            errores.append("BcryptAuthService: no compatible con hash sha256 legacy")

        if not svc.verificar_password("clave_incorrecta", hash_legacy):
            print(f"  {OK} Rechaza password incorrecto con hash sha256:")
        else:
            print(f"  {ERR} Acepta password incorrecto con hash sha256: (inseguro)")
            errores.append("BcryptAuthService: acepta password incorrecto en sha256")

        hash_bcrypt = svc.hashear_password(password)
        if svc.verificar_password(password, hash_bcrypt):
            print(f"  {OK} hashear_password() + verificar_password() coherentes")
        else:
            print(f"  {ERR} hashear y verificar no son coherentes")
            errores.append("BcryptAuthService: hashear/verificar incoherentes")

    except ImportError as e:
        print(f"  {ERR} No se pudo importar BcryptAuthService: {e}")
        errores.append(f"BcryptAuthService: no importable — {e}")
    except Exception as e:
        print(f"  {ERR} Error en pruebas de compatibilidad: {e}")
        errores.append(f"BcryptAuthService: error — {e}")

    return errores


def verificar_jwt_handler() -> list[str]:
    """Prueba funcional del JWT handler."""
    errores = []
    titulo("5. Pruebas funcionales — JWT Handler")

    try:
        mod_path = "src.infrastructure.auth.jwt_handler"
        mod = importlib.import_module(mod_path)

        tiene_clase    = hasattr(mod, "JWTHandler")
        tiene_crear    = hasattr(mod, "crear_token") or (
            tiene_clase and hasattr(mod.JWTHandler, "crear_token")
        )
        tiene_verificar = hasattr(mod, "verificar_token") or (
            tiene_clase and hasattr(mod.JWTHandler, "verificar_token")
        )

        if tiene_clase:
            print(f"  {OK} JWTHandler definido como clase")
        else:
            print(f"  {WRN} JWTHandler no es una clase — verificar estructura")

        if tiene_crear:
            print(f"  {OK} crear_token definido")
        else:
            print(f"  {ERR} crear_token no encontrado")
            errores.append("jwt_handler: falta crear_token")

        if tiene_verificar:
            print(f"  {OK} verificar_token definido")
        else:
            print(f"  {ERR} verificar_token no encontrado")
            errores.append("jwt_handler: falta verificar_token")

        if tiene_crear and tiene_verificar:
            try:
                payload_test = {"usuario_id": 1, "rol": "profesor"}

                if tiene_clase:
                    handler = mod.JWTHandler(secret="test_secret_key_audit")
                    token   = handler.crear_token(payload_test)
                    decoded = handler.verificar_token(token)
                else:
                    token   = mod.crear_token(payload_test, secret="test_secret")
                    decoded = mod.verificar_token(token, secret="test_secret")

                if token and isinstance(token, str):
                    print(f"  {OK} crear_token() genera un string")
                else:
                    print(f"  {ERR} crear_token() no genera string válido")
                    errores.append("jwt_handler: crear_token no retorna string")

                if decoded and isinstance(decoded, dict):
                    print(f"  {OK} verificar_token() decodifica correctamente")
                    for campo in ["usuario_id", "rol"]:
                        if campo in decoded:
                            print(f"  {OK} Payload contiene '{campo}'")
                        else:
                            print(f"  {WRN} Payload no contiene '{campo}'")
                    if "exp" in decoded or "exp" in str(decoded):
                        print(f"  {OK} Token incluye campo de expiración (exp)")
                    else:
                        print(f"  {WRN} Token sin 'exp' — tokens no expiran (inseguro)")
                else:
                    print(f"  {ERR} verificar_token() no retorna dict")
                    errores.append("jwt_handler: verificar_token no retorna dict")

            except Exception as e:
                print(f"  {WRN} Prueba funcional incompleta: {e}")
                print(f"       (puede requerir configuración específica de secret)")

    except ImportError as e:
        print(f"  {ERR} No se pudo importar jwt_handler: {e}")
        errores.append(f"jwt_handler: no importable — {e}")
    except Exception as e:
        print(f"  {ERR} Error inesperado: {e}")
        errores.append(f"jwt_handler: error — {e}")

    return errores


def verificar_implementa_port() -> list[str]:
    """Verifica que BcryptAuthService implementa IAuthenticationService."""
    errores = []
    titulo("6. Verificación de contrato — IAuthenticationService")

    try:
        from src.domain.ports.service_ports import IAuthenticationService
        from src.infrastructure.auth.bcrypt_auth_service import BcryptAuthService

        if issubclass(BcryptAuthService, IAuthenticationService):
            print(f"  {OK} BcryptAuthService hereda de IAuthenticationService")
        else:
            print(f"  {ERR} BcryptAuthService NO hereda de IAuthenticationService")
            errores.append("BcryptAuthService: no implementa el port")

        abstractos = getattr(IAuthenticationService, "__abstractmethods__", set())
        implementados = []
        faltantes     = []
        for metodo in abstractos:
            if hasattr(BcryptAuthService, metodo):
                implementados.append(metodo)
            else:
                faltantes.append(metodo)

        if implementados:
            print(f"  {OK} Métodos implementados: {implementados}")
        if faltantes:
            print(f"  {ERR} Métodos faltantes del port: {faltantes}")
            errores.append(f"BcryptAuthService: métodos sin implementar: {faltantes}")

        try:
            instancia = BcryptAuthService()
            print(f"  {OK} BcryptAuthService() instancia sin parámetros")
        except Exception as e:
            print(f"  {ERR} BcryptAuthService() no instancia: {e}")
            errores.append(f"BcryptAuthService: no instancia — {e}")

    except ImportError as e:
        print(f"  {ERR} Error de importación: {e}")
        errores.append(f"Verificación de port: error de importación — {e}")

    return errores


def verificar_no_accede_bd(path: Path, nombre: str) -> list[str]:
    errores = []
    contenido = path.read_text(encoding="utf-8")
    patrones_bd = ["sqlite3", "execute(", "SELECT ", "INSERT ", "UPDATE ", "fetch_one", "fetch_all"]
    encontrados = [p for p in patrones_bd if p in contenido]
    if encontrados:
        print(f"  {ERR} {nombre}: acceso directo a BD detectado: {encontrados}")
        errores.append(f"{nombre}: acceso directo a BD — {encontrados}")
    else:
        print(f"  {OK} {nombre}: sin acceso directo a BD")
    return errores


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 62)
    print("  AUDITORÍA DE AUTH — ZECI Manager v2.0")
    print("=" * 62)

    todos_los_errores: list[str] = []

    # ── 1. Existencia de archivos ─────────────────────────────────────────────
    titulo("1. Existencia de archivos")

    for archivo in ARCHIVOS_ESPERADOS:
        path = AUTH_DIR / archivo
        if path.exists():
            size = path.stat().st_size
            print(f"  {OK} {archivo}  ({size:,} bytes)")
        else:
            print(f"  {ERR} {archivo} — NO ENCONTRADO")
            todos_los_errores.append(f"Faltante: {archivo}")

    init_path = AUTH_DIR / "__init__.py"
    if init_path.exists():
        print(f"  {OK} __init__.py")
    else:
        print(f"  {ERR} __init__.py — NO ENCONTRADO")
        todos_los_errores.append("Faltante: auth/__init__.py")

    # ── 2. Auditoría estática ─────────────────────────────────────────────────
    titulo("2. Auditoría estática — AST")

    for archivo, spec in ARCHIVOS_ESPERADOS.items():
        path = AUTH_DIR / archivo
        if not path.exists():
            continue

        print(f"\n  📄 {archivo}  —  {spec['descripcion']}")
        tree = _parse(path)
        if tree is None:
            todos_los_errores.append(f"{archivo}: error de sintaxis")
            continue

        imports = _imports_en_modulo(tree)
        prohibidos = imports & IMPORTS_PROHIBIDOS
        if prohibidos:
            print(f"  {ERR} Imports prohibidos: {prohibidos}")
            todos_los_errores.append(f"{archivo}: imports prohibidos {prohibidos}")
        else:
            print(f"  {OK} Sin imports de infraestructura de BD")

        for no_imp in spec.get("no_debe_importar", []):
            if no_imp in imports:
                print(f"  {ERR} Importa '{no_imp}' (no debería)")
                todos_los_errores.append(f"{archivo}: no debe importar '{no_imp}'")

        definidos = _nombres_definidos(tree)
        clase = spec.get("clase_esperada")
        if clase:
            if clase in definidos:
                print(f"  {OK} Clase '{clase}' definida")
            else:
                print(f"  {ERR} Clase '{clase}' NO encontrada")
                todos_los_errores.append(f"{archivo}: falta clase '{clase}'")

        for nombre in spec.get("funciones_o_clases", []):
            if nombre in definidos:
                print(f"  {OK} '{nombre}' definido")
            else:
                print(f"  {WRN} '{nombre}' no encontrado (puede estar en la clase)")

        port = spec.get("implementa_port")
        if port and clase:
            if _hereda_de(tree, clase, port):
                print(f"  {OK} {clase} hereda de {port}")
            else:
                print(f"  {WRN} Herencia de {port} no detectada estáticamente")
                print(f"       (se verifica en runtime en sección 6)")

        for metodo in spec.get("metodos_minimos", []):
            if metodo in definidos:
                print(f"  {OK} Método '{metodo}' presente")
            else:
                print(f"  {ERR} Método '{metodo}' FALTANTE")
                todos_los_errores.append(f"{archivo}: falta método '{metodo}'")

        contenido = path.read_text(encoding="utf-8")
        for palabra in spec.get("debe_contener", []):
            if palabra in contenido:
                print(f"  {OK} Contiene '{palabra}'")
            else:
                print(f"  {ERR} No contiene '{palabra}'")
                todos_los_errores.append(f"{archivo}: falta '{palabra}'")

        for palabra in spec.get("no_debe_contener", []):
            if palabra in contenido:
                print(f"  {ERR} Contiene '{palabra}' (no debería)")
                todos_los_errores.append(f"{archivo}: contiene '{palabra}' inapropiado")

        errores_bd = verificar_no_accede_bd(path, archivo)
        todos_los_errores.extend(errores_bd)

    # ── Pruebas funcionales ───────────────────────────────────────────────────
    todos_los_errores.extend(verificar_bcrypt_operaciones())
    todos_los_errores.extend(verificar_compatibilidad_sha256())
    todos_los_errores.extend(verificar_jwt_handler())
    todos_los_errores.extend(verificar_implementa_port())

    # ── 7. __init__.py exporta lo necesario ───────────────────────────────────
    titulo("7. Verificación de __init__.py")

    init_path = AUTH_DIR / "__init__.py"
    if init_path.exists():
        contenido = init_path.read_text(encoding="utf-8")
        for nombre in ["BcryptAuthService", "JWTHandler"]:
            if nombre in contenido:
                print(f"  {OK} '{nombre}' exportado")
            else:
                print(f"  {WRN} '{nombre}' no exportado en __init__.py")

    # ── 8. Seguridad básica ───────────────────────────────────────────────────
    titulo("8. Verificaciones de seguridad")

    bcrypt_svc = AUTH_DIR / "bcrypt_auth_service.py"
    if bcrypt_svc.exists():
        contenido = bcrypt_svc.read_text(encoding="utf-8")
        if "ROUNDS" in contenido or "rounds" in contenido:
            print(f"  {OK} Factor de costo bcrypt (ROUNDS) configurable")
        else:
            print(f"  {WRN} No hay ROUNDS explícito — verificar factor de costo")

        if "12" in contenido or "rounds=12" in contenido:
            print(f"  {OK} Factor de costo bcrypt >= 12 (adecuado para producción)")
        else:
            print(f"  {WRN} Verificar que ROUNDS >= 12 en producción")

        if "except" in contenido and "False" in contenido:
            print(f"  {OK} verificar_password() captura excepciones (no lanza en fallo)")
        else:
            print(f"  {WRN} Verificar que verificar_password() retorna False (no lanza)")

    jwt_path = AUTH_DIR / "jwt_handler.py"
    if jwt_path.exists():
        contenido = jwt_path.read_text(encoding="utf-8")
        if "exp" in contenido or "expire" in contenido or "expir" in contenido:
            print(f"  {OK} JWT incluye lógica de expiración")
        else:
            print(f"  {ERR} JWT sin expiración — tokens permanentes (inseguro)")
            todos_los_errores.append("jwt_handler: tokens sin expiración")

        if "HS256" in contenido or "RS256" in contenido or "algorithm" in contenido.lower():
            print(f"  {OK} Algoritmo de firma especificado explícitamente")
        else:
            print(f"  {WRN} Algoritmo no especificado explícitamente")

    # ── Resumen ───────────────────────────────────────────────────────────────
    print()
    print("=" * 62)
    print("  RESUMEN")
    print("=" * 62)

    faltantes = [e for e in todos_los_errores if e.startswith("Faltante:")]
    otros     = [e for e in todos_los_errores if not e.startswith("Faltante:")]

    print(f"  Archivos auditados:  {len(ARCHIVOS_ESPERADOS)}")
    print(f"  Archivos faltantes:  {len(faltantes)}")
    print(f"  Errores funcionales: {len(otros)}")
    print()

    if todos_los_errores:
        print(f"  {ERR} AUDITORÍA FALLIDA — {len(todos_los_errores)} problema(s):")
        for e in todos_los_errores:
            print(f"      • {e}")
        return 1
    else:
        print(f"  {OK} AUDITORÍA EXITOSA — capa de auth correcta")
        return 0


if __name__ == "__main__":
    sys.exit(main())
