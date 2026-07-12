import pandas as pd
import numpy as np

def reduce_mem_usage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reduce el uso de memoria de un DataFrame convirtiendo columnas numéricas
    a tipos de datos más pequeños.
    """
    if not isinstance(df, pd.DataFrame):
        print(f"DEBUG: Se recibió un {type(df)} en lugar de un DataFrame.")
        return df

    # 1. Hacemos una copia inicial
    df = df.copy()
    
    # 2. 🛡️ LA CURA: Eliminar columnas con nombres duplicados
    # Esto asegura que df[col] siempre sea una Serie (una sola columna)
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    for col in df.columns:
        # Obtenemos el tipo de la columna
        col_type = df[col].dtype
        
        # Saltamos si no es numérico
        if not pd.api.types.is_numeric_dtype(col_type):
            continue
            
        # Saltamos si es tipo 'category'
        if col_type.name == 'category':
            continue

        c_min = df[col].min()
        c_max = df[col].max()
        
        # Lógica de reducción para enteros
        if str(col_type).startswith('int'):
            if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                df[col] = df[col].astype(np.int8)
            elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                df[col] = df[col].astype(np.int16)
            elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                df[col] = df[col].astype(np.int32)
            else:
                df[col] = df[col].astype(np.int64)
        # Lógica de reducción para floats
        else:
            df[col] = df[col].astype(np.float32)
            
    return df

def preparar_dengue_base(df: pd.DataFrame) -> tuple:
    # 1. Filtro del evento (Aseguramos resiliencia en nombres de columna)
    col_evento = 'nombre_evento' if 'nombre_evento' in df.columns else 'NOMBRE_EVENTO'
    df_dengue = df[df[col_evento].str.contains('dengue', case=False, na=False)].copy()
    
    col_upgd = 'nom_upgd' if 'nom_upgd' in df_dengue.columns else 'NOM_UPGD'
    df_dengue[col_upgd] = df_dengue[col_upgd].astype(str).str.upper().str.strip()
    
    # 2. Conteo puro de casos
    casos_upgd = df_dengue.groupby(['año_ini_sin', 'semana_epi_ini_sin', col_upgd]).size().reset_index(name='casos')
    casos_upgd = casos_upgd.rename(columns={col_upgd: 'nom_upgd'})
    
    # =====================================================================
    # 3. RESCATE DEMOGRÁFICO (El salvavidas para tus nuevas variables)
    # =====================================================================
    # Detectamos de forma dinámica si existen estas columnas en el Excel
    vars_posibles = ['poblacion', 'densidad_poblacional', 'crecimiento_poblacional', 'incremento_habitantes', 'densidad_delta']
    cols_demo_presentes = [c for c in df.columns if c.lower() in vars_posibles]
    
    if cols_demo_presentes:
        # Extraemos las características únicas de cada UPGD
        # (Tomamos el último valor disponible, asumiendo que los datos de población no cambian por semana)
        df_demo = df_dengue[[col_upgd] + cols_demo_presentes].drop_duplicates(subset=[col_upgd], keep='last')
        df_demo = df_demo.rename(columns={col_upgd: 'nom_upgd'})
        
        # Le pegamos estas variables a la tabla de casos
        casos_upgd = casos_upgd.merge(df_demo, on='nom_upgd', how='left')

    # =====================================================================
    # 4. EXTRACCIÓN DE CLIMA (Serie temporal continua)
    # =====================================================================
    cols_clima = [c for c in df.columns if 'precipitacion' in c.lower() or 'temperatura' in c.lower() or 'total' in c.lower()]
    df_clima = df[['año_ini_sin', 'semana_epi_ini_sin'] + cols_clima].drop_duplicates().sort_values(['año_ini_sin', 'semana_epi_ini_sin']).reset_index(drop=True)
    
    # Interpolación para rellenar huecos en los sensores
    for col in df_clima.select_dtypes(include=np.number).columns:
        if col not in ['año_ini_sin', 'semana_epi_ini_sin']:
            df_clima[col] = df_clima[col].interpolate(method='linear', limit_direction='both').bfill().ffill()
            
    return casos_upgd, df_clima, df_dengue[col_upgd].unique()