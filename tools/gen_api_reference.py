"""
tools/gen_api_reference.py — genera la referencia de API por método.
====================================================================
Produce `docs/api_reference.md` (índice) y `docs/api_reference/*.md` (una por
capa) a partir del CÓDIGO, sin importarlo (solo AST → seguro aunque falten
dependencias como weasyprint o bcrypt).

Por cada clase y método público extrae:
  - la FIRMA exacta tomada del fuente (parámetros, anotaciones, retorno),
  - la primera línea del docstring.

Los métodos sin docstring se listan igual, marcados `⚠️ sin docstring`, y cada
archivo lleva una tabla de cobertura de docstrings. Es la estrategia de
documentación por método: la fuente de verdad es el código; los `.md` narrativos
de `docs/` explican el *por qué* y las responsabilidades.

Uso:
    python tools/gen_api_reference.py            # usa la raíz del repo
    python tools/gen_api_reference.py <repo_root>

Re-ejecutar tras cambiar firmas o docstrings (ver docs/verification.md).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# Raíz del repo = carpeta que contiene tools/. Se puede sobreescribir por argv[1].
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "api_reference"

# (título, ruta relativa, incluir_privados)
LAYERS = [
    ("Dominio · Modelos", "src/domain/models", False),
    ("Dominio · Puertos", "src/domain/ports", False),
    ("Dominio · Políticas", "src/domain/policies", True),
    ("Servicios", "src/services", False),
    ("Infraestructura", "src/infrastructure", False),
]

SKIP = {"__init__.py"}


def first_doc_line(node) -> str | None:
    doc = ast.get_docstring(node)
    if not doc:
        return None
    for line in doc.strip().splitlines():
        line = line.strip()
        if line:
            return line
    return None


def signature(node, src_lines) -> str:
    """Firma exacta tomada del fuente: de la línea `def` a la del primer stmt."""
    start = node.lineno - 1
    end = node.body[0].lineno - 1 if node.body else node.end_lineno
    raw = " ".join(l.strip() for l in src_lines[start:end])
    # Cortar en el ':' que cierra el encabezado (antes del cuerpo/docstring).
    depth = 0
    for i, ch in enumerate(raw):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ":" and depth == 0:
            raw = raw[:i]
            break
    return " ".join(raw.split())


def decorators(node) -> list[str]:
    out = []
    for d in node.decorator_list:
        try:
            out.append("@" + ast.unparse(d))
        except Exception:
            pass
    return out


def is_public(name: str) -> bool:
    return not name.startswith("_")


def render_method(node, src_lines) -> tuple[str, bool]:
    """Devuelve (línea markdown, tiene_docstring)."""
    sig = signature(node, src_lines)
    doc = first_doc_line(node)
    tag = ""
    for d in decorators(node):
        if any(k in d for k in ("abstractmethod", "property", "classmethod",
                                "staticmethod", "requiere_escritura")):
            tag += f" `{d}`"
    if doc:
        return f"- `{sig}`{tag} — {doc}", True
    return f"- `{sig}`{tag} — ⚠️ sin docstring", False


def process_file(path: Path, include_private: bool):
    src = path.read_text(encoding="utf-8")
    src_lines = src.splitlines()
    tree = ast.parse(src)
    classes, funcs = [], []
    total = con_doc = 0

    def want(name):
        return include_private or is_public(name) or name == "__init__"

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = []
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and want(m.name):
                    line, has = render_method(m, src_lines)
                    methods.append(line)
                    total += 1
                    con_doc += 1 if has else 0
            bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else ""
            classes.append((node.name, bases, first_doc_line(node), methods))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and want(node.name):
            line, has = render_method(node, src_lines)
            funcs.append(line)
            total += 1
            con_doc += 1 if has else 0

    return classes, funcs, total, con_doc


def process_layer(title, rel, include_private):
    base = ROOT / rel
    files = sorted(p for p in base.rglob("*.py")
                   if p.name not in SKIP and "__pycache__" not in p.parts)
    lines = [f"# API Reference — {title}", "",
             f"> Generado automáticamente desde `{rel}/` por "
             "`tools/gen_api_reference.py` (firmas del fuente + primera línea del "
             "docstring). Los métodos sin docstring se marcan `⚠️ sin docstring`. "
             "**No editar a mano** — re-generar con el script.", ""]
    tot_all = doc_all = 0
    cov_rows, body = [], []
    for f in files:
        classes, funcs, total, con_doc = process_file(f, include_private)
        if total == 0:
            continue
        tot_all += total
        doc_all += con_doc
        pct = (con_doc / total * 100) if total else 100
        cov_rows.append((str(f.relative_to(ROOT)).replace("\\", "/"), con_doc, total, pct))
        body.append(f"## `{f.relative_to(base).as_posix()}`")
        body.append("")
        for cname, bases, cdoc, methods in classes:
            body.append(f"### {cname}" + (f"({bases})" if bases else ""))
            if cdoc:
                body.append(f"> {cdoc}")
            body.append("")
            body += methods if methods else ["_(sin métodos públicos)_"]
            body.append("")
        if funcs:
            body.append("### Funciones de módulo")
            body.append("")
            body += funcs
            body.append("")

    pct_all = (doc_all / tot_all * 100) if tot_all else 100
    lines.append(f"**Cobertura de docstrings:** {doc_all}/{tot_all} métodos ({pct_all:.0f}%).")
    lines.append("")
    lines.append("| Archivo | Con docstring | Total | % |")
    lines.append("|---|---:|---:|---:|")
    for name, cd, tt, pct in cov_rows:
        flag = " ⚠️" if pct < 100 else ""
        lines.append(f"| `{name}` | {cd} | {tt} | {pct:.0f}%{flag} |")
    lines.append("")
    lines += body

    OUT.mkdir(parents=True, exist_ok=True)
    slug = (title.lower().replace(" · ", "_").replace(" ", "_")
            .replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u"))
    (OUT / f"{slug}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"{slug}.md", doc_all, tot_all


def main():
    print("Generando referencia de API...\n")
    index = ["# API Reference — ZECI Manager v2.0", "",
             "> Referencia por método **generada automáticamente** desde el código "
             "(`tools/gen_api_reference.py`). Cada método muestra su firma exacta y "
             "la primera línea de su docstring; los que no tienen docstring aparecen "
             "marcados `⚠️ sin docstring`. Complementa los documentos de arquitectura "
             "de `docs/` (que explican el *por qué* y las responsabilidades).", "",
             "Regenerar: `python tools/gen_api_reference.py`", "",
             "| Capa | Documento | Cobertura de docstrings |", "|---|---|---|"]
    for title, rel, incp in LAYERS:
        name, cd, tt = process_layer(title, rel, incp)
        pct = (cd / tt * 100) if tt else 100
        print(f"  {title:26} -> docs/api_reference/{name}  ({cd}/{tt}, {pct:.0f}%)")
        index.append(f"| {title} | [{name}](api_reference/{name}) | {cd}/{tt} ({pct:.0f}%) |")

    (ROOT / "docs" / "api_reference.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print("\n  Índice -> docs/api_reference.md\nListo.")


if __name__ == "__main__":
    main()
