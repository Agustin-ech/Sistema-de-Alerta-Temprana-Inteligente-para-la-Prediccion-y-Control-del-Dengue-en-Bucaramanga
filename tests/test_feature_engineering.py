import pandas as pd

from training.feature_engineering import crear_features


def test_crear_features_no_agrega_columnas_texto_por_merge():
    panel_maestro = pd.DataFrame(
        {
            'año_ini_sin': [2020, 2020, 2021],
            'semana_epi_ini_sin': [1, 2, 1],
            'nom_upgd': ['BUCARAMANGA_CENTRAL', 'BUCARAMANGA_CENTRAL', 'BUCARAMANGA_CENTRAL'],
            'casos': [1, 0, 2],
            'target_intervencion': [0, 1, 0],
            'estado_sivigila_interno': [0, 1, 0],
        }
    )
    df_clima = pd.DataFrame(
        {
            'año_ini_sin': [2020, 2020, 2021],
            'semana_epi_ini_sin': [1, 2, 1],
            'nom_upgd': ['BUCARAMANGA_CENTRAL', 'BUCARAMANGA_CENTRAL', 'BUCARAMANGA_CENTRAL'],
            'temperatura_media': [25.0, 26.0, 24.0],
            'precipitacion_total': [5.0, 0.0, 12.0],
        }
    )

    resultado = crear_features(panel_maestro, df_clima)

    assert 'nom_upgd_x' not in resultado.columns
    assert 'nom_upgd_y' not in resultado.columns
    assert resultado['temperatura_media'].tolist() == [25.0, 26.0, 24.0]
