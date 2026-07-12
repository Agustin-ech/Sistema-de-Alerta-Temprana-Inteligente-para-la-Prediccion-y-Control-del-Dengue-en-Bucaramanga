import pandas as pd
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

# 1. Cargar el dataset que detectó el script
ruta_dataset = RAIZ_PROYECTO / "data" / "01_raw" / "epidemiological_data_bucaramanga_processed_dengue_grave1.xlsx"
df = pd.read_excel(ruta_dataset) if ruta_dataset.suffix == '.xlsx' else pd.read_csv(ruta_dataset)
df.columns = df.columns.str.lower()

print("="*70)
print("🔍 INFORME DE AUDITORÍA: estado_sivigila_interno")
print("="*70)

# Buscar variantes de nombre por si las minúsculas o el pipeline lo cambiaron
cols_estado = [c for c in df.columns if 'estado' in c or 'sivigila' in c or 'alerta' in c]
print(f"📋 Columnas candidatas encontradas: {cols_estado}\n")

col_evaluar = 'estado_sivigila_interno' if 'estado_sivigila_interno' in df.columns else (cols_estado[0] if cols_estado else None)

if col_evaluar:
    print(f"📊 1. Describe de '{col_evaluar}':")
    print(df[col_evaluar].describe())
    print("\n📊 2. Value Counts (con dropna=False):")
    print(df[col_evaluar].value_counts(dropna=False))
    
    # Identificar nombres de tiempo dinámicos
    col_ano = [c for c in df.columns if c in ['ano', 'año', 'año_ini_sin', 'ano_ini_sin']][0]
    col_sem = [c for c in df.columns if c in ['semana', 'semana_epi_ini_sin']][0]
    col_upgd = [c for c in df.columns if c in ['nom_upgd', 'upgd']][0]
    
    print(f"\n👀 3. Muestra de las primeras 30 filas:")
    print(df[[col_upgd, col_ano, col_sem, col_evaluar]].head(30).to_string(index=False))
else:
    print("❌ ERROR GRAVE: No se encontró la columna 'estado_sivigila_interno' ni ninguna variante similar.")
    print("Columnas disponibles totales:", df.columns.tolist()[:20], "... [primeras 20]")

print("="*70)