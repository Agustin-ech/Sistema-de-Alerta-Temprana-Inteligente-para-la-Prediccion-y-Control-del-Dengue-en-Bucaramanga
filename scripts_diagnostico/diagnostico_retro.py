import pandas as pd
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

def diagnosticar_dataset_historico():
    print("======================================================================")
    print("🔍 AUDITORÍA DE ESTRUCTURA DATASET - VALIDACIÓN RETROSPECTIVA")
    print("======================================================================")

    # 1. Localizar el archivo de manera flexible
    ruta_dataset = RAIZ_PROYECTO / "data" / "01_raw" / "epidemiological_data_bucaramanga_processed_dengue_grave1.xlsx"
    if not ruta_dataset.exists():
        carpeta_data = RAIZ_PROYECTO / "data"
        archivos_xlsx = list(carpeta_data.glob("**/*.xlsx")) if carpeta_data.exists() else []
        archivos_csv = list(carpeta_data.glob("**/*.csv")) if carpeta_data.exists() else []
        ruta_dataset = archivos_xlsx[0] if archivos_xlsx else (archivos_csv[0] if archivos_csv else None)
        
    if not ruta_dataset:
        print("❌ ERROR: La carpeta 'data/' está vacía o no existe.")
        return

    print(f"📌 Leyendo archivo: {ruta_dataset.name}")
    df = pd.read_excel(ruta_dataset) if ruta_dataset.suffix == '.xlsx' else pd.read_csv(ruta_dataset)
    
    # 🛠️ PASO 1 Y PASO 5: Forma general y listado completo de columnas
    print(f"\n📏 Dimensiones del Dataset (Shape): {df.shape}")
    print("\n📋 Columnas disponibles (tolist):")
    print(df.columns.tolist())
    
    print("\n" + "-"*50)
    print("👀 Primeras filas (head):")
    print("-" * 50)
    print(df.head())
    
    # 🛠️ PASO 2, 3 Y 4: Mapeo inteligente de nombres epidemiológicos tradicionales
    print("\n" + "-"*50)
    print("📊 Análisis de Variables de Tiempo y Tipos de Datos:")
    print("-" * 50)
    
    # Intentar identificar la columna de Año
    col_ano = [c for c in df.columns if c.lower() in ['ano', 'ano_historico', 'año', 'año_ini_sin', 'ano_ini_sin']]
    if col_ano:
        print(f"✔️ Columna de año identificada: '{col_ano[0]}' | Tipos: {df[col_ano[0]].dtypes}")
        print(f"   Años únicos presentes: {df[col_ano[0]].unique().tolist()}")
    else:
        print("❌ No se detectó ninguna columna típica de Año.")
        
    # Intentar identificar la columna de Semana
    col_semana = [c for c in df.columns if c.lower() in ['semana', 'semana_pivote', 'semana_epi', 'semana_epi_ini_sin']]
    if col_semana:
        print(f"\n✔️ Columna de semana identificada: '{col_semana[0]}' | Tipos: {df[col_semana[0]].dtypes}")
        print(f"   Semanas únicas (ordenadas, primeras 15): {sorted(df[col_semana[0]].unique().tolist())[:15]}")
    else:
        print("❌ No se detectó ninguna columna típica de Semana.")
        
    # 💡 DETECCIÓN CRÍTICA DE PIPELINE
    print("\n" + "-"*50)
    print("🧠 Diagnóstico del Tipo de Dataset:")
    print("-" * 50)
    if 'casos_lag_1' in df.columns or 'persistencia_alerta_8' in df.columns:
        print("🚀 ¡EXCELENTE! Este es el DATASET AGREGADO (Panel Data). Tiene la ingeniería de variables calculada.")
        print("   Es apto para la validación retrospectiva directa con el modelo entrenado.")
    else:
        print("⚠️ ALERTA: Este parece ser el DATASET DE MICRODATOS (Fila por paciente).")
        print("   Si es así, necesitamos cambiar la ruta en el script hacia la matriz final consolidada por el LightGBM (.parquet, .csv o .xlsx agregada).")
    print("======================================================================\n")

if __name__ == "__main__":
    diagnosticar_dataset_historico()