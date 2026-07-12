import os
from pathlib import Path

# Raíz del proyecto entero (sube 2 niveles desde config/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Directorios de artefactos y mapas
SCRIPTS_DIR = BASE_DIR / "scripts"
GEO_DIR = BASE_DIR / "app" / "geo"

# Rutas definitivas a archivos
MODEL_PATH = SCRIPTS_DIR / "modelo_final_dengue_grave.pkl"
METADATA_PATH = SCRIPTS_DIR / "metadata_modelo_grave.json"
BASELINE_PATH = SCRIPTS_DIR / "baseline_features.json"
GEO_JSON_PATH = GEO_DIR / "upgd_coordenadas.json"