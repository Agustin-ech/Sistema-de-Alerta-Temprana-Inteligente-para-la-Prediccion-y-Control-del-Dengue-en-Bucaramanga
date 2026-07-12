import pandas as pd
import numpy as np

def calcular_canal_endemico(panel_maestro: pd.DataFrame) -> pd.DataFrame:
    dict_mediana, dict_q3 = {}, {}
    for (upgd, sem), sub_df in panel_maestro.groupby(['nom_upgd', 'semana_epi_ini_sin']):
        anios = sub_df['año_ini_sin'].unique()
        for anio in anios:
            historico = sub_df[sub_df['año_ini_sin'] < anio]['casos'].values
            clave = (upgd, anio, sem)
            if len(historico) >= 3:
                dict_mediana[clave] = np.percentile(historico, 50)
                dict_q3[clave] = np.percentile(historico, 75)
            else:
                dict_mediana[clave], dict_q3[clave] = np.nan, np.nan

    idx_temp = panel_maestro.set_index(['nom_upgd', 'año_ini_sin', 'semana_epi_ini_sin']).index
    panel_maestro['mediana_hist'] = idx_temp.map(dict_mediana)
    panel_maestro['q3_hist'] = idx_temp.map(dict_q3)

    condiciones = [
        panel_maestro['mediana_hist'].isna(),
        panel_maestro['casos'] > panel_maestro['q3_hist'],
        panel_maestro['casos'] > panel_maestro['mediana_hist']
    ]
    panel_maestro['estado_sivigila_interno'] = np.select(condiciones, [0, 2, 1], default=0)
    panel_maestro.drop(columns=['mediana_hist', 'q3_hist'], inplace=True)
    return panel_maestro