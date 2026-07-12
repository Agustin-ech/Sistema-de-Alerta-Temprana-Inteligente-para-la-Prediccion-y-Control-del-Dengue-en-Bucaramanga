import pandas as pd
import numpy as np

def evaluar_regla_ins(row):
    if np.isnan(row['est_t1']) or np.isnan(row['est_t2']) or np.isnan(row['est_t3']) or np.isnan(row['est_t4']):
        return np.nan
    ventana = [int(row['est_t1']), int(row['est_t2']), int(row['est_t3']), int(row['est_t4'])]
    alerta_bin = [1 if x >= 1 else 0 for x in ventana]
    if (2 in ventana) or (sum(alerta_bin) >= 3) or any(alerta_bin[j] == 1 and alerta_bin[j+1] == 1 for j in range(3)):
        return 1
    return 0

def crear_target(panel_maestro: pd.DataFrame) -> pd.DataFrame:
    panel_maestro = panel_maestro.sort_values(['nom_upgd', 'año_ini_sin', 'semana_epi_ini_sin']).reset_index(drop=True)
    panel_maestro['est_t1'] = panel_maestro.groupby('nom_upgd')['estado_sivigila_interno'].shift(-1)
    panel_maestro['est_t2'] = panel_maestro.groupby('nom_upgd')['estado_sivigila_interno'].shift(-2)
    panel_maestro['est_t3'] = panel_maestro.groupby('nom_upgd')['estado_sivigila_interno'].shift(-3)
    panel_maestro['est_t4'] = panel_maestro.groupby('nom_upgd')['estado_sivigila_interno'].shift(-4)
    
    panel_maestro['target_intervencion'] = panel_maestro.apply(evaluar_regla_ins, axis=1)
    panel_maestro.drop(columns=['est_t1', 'est_t2', 'est_t3', 'est_t4'], inplace=True)
    return panel_maestro