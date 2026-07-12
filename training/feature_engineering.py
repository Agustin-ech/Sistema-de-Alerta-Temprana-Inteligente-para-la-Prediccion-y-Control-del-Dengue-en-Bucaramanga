import json
from pathlib import Path
import pandas as pd
import numpy as np
from training.preprocessing import reduce_mem_usage

GEO_JSON_PATH = Path(__file__).resolve().parent.parent / "app" / "geo" / "upgd_coordenadas.json"


def _haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def _calcular_vecinos(nom_upgds, k=3, coords_path=GEO_JSON_PATH):
    """Para cada UPGD, las k más cercanas geográficamente (según app/geo/upgd_coordenadas.json)."""
    with open(coords_path, encoding='utf-8') as f:
        coords = json.load(f)
    upgds_validas = [u for u in nom_upgds if u in coords]
    vecinos = {}
    for u in upgds_validas:
        distancias = sorted(
            ((v, _haversine_km(coords[u]['lat'], coords[u]['lng'], coords[v]['lat'], coords[v]['lng']))
             for v in upgds_validas if v != u),
            key=lambda x: x[1]
        )
        vecinos[u] = [v for v, _ in distancias[:k]]
    return vecinos


def agregar_contagio_espacial(panel_maestro: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    """
    vecinos_alerta_prom: promedio de alerta_binaria_pasada de las k UPGDs geográficamente más
    cercanas, desplazado 1 semana (mismo patrón que persistencia_alerta_N) para no usar
    información contemporánea de los vecinos como si ya se conociera.
    """
    vecinos = _calcular_vecinos(panel_maestro['nom_upgd'].unique().tolist(), k=k)

    pivot_lag = panel_maestro.pivot_table(
        index=['año_ini_sin', 'semana_epi_ini_sin'],
        columns='nom_upgd',
        values='alerta_binaria_pasada'
    ).sort_index().shift(1)

    contagio = {
        upgd: pivot_lag[[v for v in vecinos_upgd if v in pivot_lag.columns]].mean(axis=1)
        for upgd, vecinos_upgd in vecinos.items()
        if any(v in pivot_lag.columns for v in vecinos_upgd)
    }

    contagio_long = pd.DataFrame(contagio, index=pivot_lag.index).reset_index().melt(
        id_vars=['año_ini_sin', 'semana_epi_ini_sin'],
        var_name='nom_upgd',
        value_name='vecinos_alerta_prom'
    )

    panel_maestro = panel_maestro.merge(
        contagio_long, on=['año_ini_sin', 'semana_epi_ini_sin', 'nom_upgd'], how='left'
    )
    panel_maestro['vecinos_alerta_prom'] = panel_maestro['vecinos_alerta_prom'].fillna(0)
    return panel_maestro


def agregar_rezagos_biologicos(df: pd.DataFrame, p_tot: str, t_med: str, t_min: str, t_max: str) -> pd.DataFrame:
    """Agrega features biológicas sin generar fragmentación"""
    new_features = {}
    
    # ====================== PRECIPITACIÓN ======================
    new_features['precip_acum_4sem'] = df[p_tot].rolling(window=4, min_periods=1).sum()
    new_features['precip_acum_6sem'] = df[p_tot].rolling(window=6, min_periods=1).sum()
    new_features['precip_acum_8sem'] = df[p_tot].rolling(window=8, min_periods=1).sum()
    new_features['semanas_humedas_4'] = (df[p_tot] > 10).rolling(window=4, min_periods=1).sum()
    new_features['semanas_humedas_6'] = (df[p_tot] > 10).rolling(window=6, min_periods=1).sum()
    new_features['precip_max_4sem'] = df[p_tot].rolling(window=4, min_periods=1).max()

    # ====================== TEMPERATURA ======================
    new_features['temp_media_3sem'] = df[t_med].rolling(window=3, min_periods=1).mean()
    new_features['temp_media_6sem'] = df[t_med].rolling(window=6, min_periods=1).mean()
    new_features['temp_min_4sem'] = df[t_min].rolling(window=4, min_periods=1).mean()
    new_features['temp_max_4sem'] = df[t_max].rolling(window=4, min_periods=1).mean()
    new_features['temp_rango_4sem'] = new_features['temp_max_4sem'] - new_features['temp_min_4sem']
    new_features['grados_dia_acum'] = np.maximum(df[t_med] - 16, 0).rolling(window=7, min_periods=1).sum()

    # ====================== INTERACCIONES ======================
    new_features['condicion_fav_mosquito'] = (
        (new_features['precip_acum_6sem'] > 50) &
        (new_features['temp_media_6sem'].between(22, 30))
    ).astype(int)

    # Concatenar todo de una vez
    df = pd.concat([df, pd.DataFrame(new_features, index=df.index)], axis=1)
    return df.copy()


def crear_features(panel_maestro: pd.DataFrame, df_clima: pd.DataFrame) -> pd.DataFrame:
    # =====================================================================
    # 1. CÁLCULO DE DIMENSIONES CLIMÁTICAS
    # =====================================================================
    df_clima = df_clima.sort_values(['año_ini_sin', 'semana_epi_ini_sin']).reset_index(drop=True)

    # Detección dinámica de columnas
    col_temp_media = [c for c in df_clima.columns if 'temperatura' in c.lower() and ('media' in c.lower() or 'promedio' in c.lower())]
    col_temp_max = [c for c in df_clima.columns if 'temperatura' in c.lower() and 'max' in c.lower()]
    col_temp_min = [c for c in df_clima.columns if 'temperatura' in c.lower() and 'min' in c.lower()]
    col_precip_total = [c for c in df_clima.columns if 'precipitacion' in c.lower() and ('total' in c.lower() or 'acum' in c.lower())]
    col_precip_max = [c for c in df_clima.columns if 'precipitacion' in c.lower() and 'max' in c.lower()]

    t_med = col_temp_media[0] if col_temp_media else df_clima.filter(like='temperatura').columns[0]
    p_tot = col_precip_total[0] if col_precip_total else df_clima.filter(like='precip').columns[0]
    t_max = col_temp_max[0] if col_temp_max else t_med
    t_min = col_temp_min[0] if col_temp_min else t_med

    # Diccionario para recolectar todas las features climáticas
    climate_features = {}

    climate_features['temperatura_media_rollmean4'] = df_clima[t_med].rolling(4, min_periods=1).mean()
    climate_features['temperatura_std_rollmean8'] = df_clima[t_med].rolling(8, min_periods=1).std().fillna(0)
    
    if col_temp_max and col_temp_min:
        climate_features['temperatura_rango'] = df_clima[col_temp_max[0]] - df_clima[col_temp_min[0]]
    else:
        climate_features['temperatura_rango'] = df_clima[t_med].rolling(4).max() - df_clima[t_med].rolling(4).min()

    climate_features['precipitacion_total_rollmean8'] = df_clima[p_tot].rolling(8, min_periods=1).sum()
    
    if col_precip_max:
        climate_features['precipitacion_max10min_rollmean8'] = df_clima[col_precip_max[0]].rolling(8, min_periods=1).max()
    else:
        climate_features['precipitacion_max10min_rollmean8'] = df_clima[p_tot].rolling(4, min_periods=1).max()

    climate_features['precipitacion_frecuencia'] = df_clima[p_tot].rolling(4, min_periods=1).apply(
        lambda x: 1 if sum(x > 2) > 0 else 0, raw=True
    )

    # Estacionalidad
    climate_features['semana_sin'] = np.sin(2 * np.pi * df_clima['semana_epi_ini_sin'] / 52)
    climate_features['semana_cos'] = np.cos(2 * np.pi * df_clima['semana_epi_ini_sin'] / 52)

    # Concatenar todas las features climáticas de una vez
    df_clima = pd.concat([df_clima, pd.DataFrame(climate_features)], axis=1)

    # ====================== REZAGOS BIOLÓGICOS ======================
    df_clima = agregar_rezagos_biologicos(df_clima, p_tot, t_med, t_min, t_max)

    # Optimización de memoria
    df_clima = reduce_mem_usage(df_clima)

    # =====================================================================
    # 2. COMPONENTES EPIDEMIOLÓGICOS
    # =====================================================================
    # Orden temporal primero (no por UPGD): así los cortes train/test y los folds
    # de TimeSeriesSplit corresponden a semanas calendario reales, no a bloques de UPGD.
    # groupby(...).shift()/rolling() más abajo siguen siendo correctos porque pandas
    # preserva, dentro de cada grupo, el orden de aparición de las filas en el frame.
    panel_maestro = panel_maestro.sort_values(['año_ini_sin', 'semana_epi_ini_sin', 'nom_upgd']).reset_index(drop=True)

    if 'estado_sivigila_interno' not in panel_maestro.columns:
        panel_maestro['estado_sivigila_interno'] = (panel_maestro['casos'] > 0).astype(int)

    panel_maestro['alerta_binaria_pasada'] = (panel_maestro['estado_sivigila_interno'] >= 1).astype(int)

    for s in [2, 3, 4, 6, 8]:
        panel_maestro[f'persistencia_alerta_{s}'] = (
            panel_maestro.groupby('nom_upgd')['alerta_binaria_pasada']
            .transform(lambda x: x.shift(1).rolling(s, min_periods=1).sum())
            .fillna(0)
        )

    panel_maestro['alerta_lag_1'] = panel_maestro.groupby('nom_upgd')['alerta_binaria_pasada'].shift(1).fillna(0)
    panel_maestro['alerta_lag_2'] = panel_maestro.groupby('nom_upgd')['alerta_binaria_pasada'].shift(2).fillna(0)
    panel_maestro['casos_lag_1'] = panel_maestro.groupby('nom_upgd')['casos'].shift(1).fillna(0)
    panel_maestro['casos_lag_4'] = panel_maestro.groupby('nom_upgd')['casos'].shift(4).fillna(0)
    panel_maestro['casos_lag_52'] = panel_maestro.groupby('nom_upgd')['casos'].shift(52).fillna(0)

    panel_maestro['media_casos_4'] = panel_maestro.groupby('nom_upgd')['casos'].transform(
        lambda x: x.shift(1).rolling(4, min_periods=1).mean()
    ).fillna(0)

    panel_maestro['std_casos_4'] = panel_maestro.groupby('nom_upgd')['casos'].transform(
        lambda x: x.shift(1).rolling(4, min_periods=1).std()
    ).fillna(0)

    panel_maestro = agregar_contagio_espacial(panel_maestro)

    # =====================================================================
    # 3. VARIABLES DEMOGRÁFICAS
    # =====================================================================
    vars_demograficas = ['Poblacion', 'densidad_poblacional', 'crecimiento_poblacional',
                         'incremento_habitantes', 'densidad_delta']
    
    for var in vars_demograficas:
        if var in panel_maestro.columns:
            panel_maestro[var] = panel_maestro.groupby('nom_upgd')[var].transform(lambda x: x.ffill().bfill())
            panel_maestro[var] = panel_maestro[var].astype(np.float32)

    # =====================================================================
    # 4. MERGE FINAL
    # =====================================================================
    # df_clima es a nivel ciudad (no por UPGD), así que no debería traer su
    # propia columna 'nom_upgd' — si la trajera, el merge (que no usa
    # 'nom_upgd' como llave) la duplicaría en nom_upgd_x/nom_upgd_y en vez
    # de fallar de forma clara.
    df_clima = df_clima.drop(columns=['nom_upgd'], errors='ignore')
    panel_maestro = panel_maestro.merge(df_clima, on=['año_ini_sin', 'semana_epi_ini_sin'], how='left')

    # Reducción final de memoria
    panel_maestro = reduce_mem_usage(panel_maestro)
    return panel_maestro.copy()