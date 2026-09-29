"""
export_openapi.py — Exporta la especificacion OpenAPI de AVEDRA a JSON.

Uso:
    python scripts/export_openapi.py

Genera: openapi/avedra-openapi.json
"""

from __future__ import annotations

import json
import os
import sys

# Agregar el directorio raiz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from src.api.router import api_router, docs_router

app = FastAPI(
    title="AVEDRA API",
    version="2.0.0",
    description="API REST de AVEDRA — Asistencia, Convivencia y Evaluacion",
)
app.include_router(api_router)
app.include_router(docs_router)

os.makedirs("openapi", exist_ok=True)
spec = app.openapi()
output_path = os.path.join("openapi", "avedra-openapi.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)

num_rutas = len(spec.get("paths", {}))
print(f"OpenAPI spec exportado: {num_rutas} rutas -> {output_path}")
