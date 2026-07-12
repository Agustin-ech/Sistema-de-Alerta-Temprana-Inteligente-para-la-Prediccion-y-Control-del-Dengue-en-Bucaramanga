import pandas as pd
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

# Cargar el archivo detectado
ruta = RAIZ_PROYECTO / "data" / "01_raw" / "epidemiological_data_bucaramanga_processed_dengue_grave1.xlsx"
df = pd.read_excel(ruta)
df.columns = df.columns.str.lower()

# Identificar columnas de tiempo
col_ano = [c for c in df.columns if c in ['ano', 'año', 'año_ini_sin']][0]
col_semana = [c for c in df.columns if c in ['semana', 'semana_epi_ini_sin']][0]

# Agrupar para ver cuáles son las semanas "más calientes" (con más brotes/casos)
top_semanas = df.groupby([col_ano, col_semana]).size().reset_index(name='total_casos')
top_semanas = top_semanas.sort_values(by='total_casos', ascending=False)

print("====================================================")
print("🎯 TOP 5 SEMANAS CON MÁS REGISTROS HISTÓRICOS")
print("====================================================")
print(top_semanas.head(5).to_string(index=False))
print("====================================================")