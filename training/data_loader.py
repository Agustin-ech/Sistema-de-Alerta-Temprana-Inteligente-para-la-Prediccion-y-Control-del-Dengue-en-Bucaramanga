import pandas as pd
from pathlib import Path

def cargar_datos(nombre_archivo: str) -> pd.DataFrame:
    # Subir un nivel desde 'training/' y entrar a 'data/'
    ruta = Path(__file__).resolve().parent.parent / "data" / nombre_archivo
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo de datos en: {ruta}")
    df = pd.read_excel(ruta)
    df.columns = df.columns.str.lower().str.strip()
    return df