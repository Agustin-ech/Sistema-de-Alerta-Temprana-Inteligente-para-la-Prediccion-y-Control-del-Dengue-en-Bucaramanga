import gc
from itertools import product
import pandas as pd
from sklearn.metrics import roc_auc_score, classification_report, precision_recall_curve  # ⬅ CAMBIO: import nuevo

# Importaciones de tu micro-arquitectura modular
# --- Modifica las importaciones dentro de training/train.py ---
from training.data_loader import cargar_datos
from training.preprocessing import reduce_mem_usage, preparar_dengue_base
from training.endemic_channel import calcular_canal_endemico
from training.target import crear_target
from training.feature_engineering import crear_features
from training.optimization import optimizar_modelo
from training.calibration import calibrar_umbral
from training.trainer import entrenar_modelo
from training.exporter import exportar_artefactos
from training.explainability import generar_shap
def ejecutar_pipeline_entrenamiento():
    print("📂 [1/9] Cargando set de datos...")
    # Cambia el nombre si usas la copia (1)
    df = cargar_datos("03_primary/dataset_limpio.xlsx")
    
    print("🧹 [2/9] Ejecutando limpiezas estructurales...")
    casos_upgd, df_clima, todas_upgds = preparar_dengue_base(df)
    todas_semanas = df_clima[['año_ini_sin', 'semana_epi_ini_sin']].drop_duplicates()
    
    # Crear esqueleto espacio-temporal
    esqueleto = pd.DataFrame(list(product(todas_semanas.itertuples(index=False), todas_upgds)), columns=['semana_combo', 'nom_upgd'])
    esqueleto[['año_ini_sin', 'semana_epi_ini_sin']] = pd.DataFrame(esqueleto['semana_combo'].tolist(), index=esqueleto.index)
    esqueleto = esqueleto.drop(columns=['semana_combo'])
    
    panel_maestro = esqueleto.merge(casos_upgd, on=['año_ini_sin', 'semana_epi_ini_sin', 'nom_upgd'], how='left')
    panel_maestro['casos'] = panel_maestro['casos'].fillna(0).astype(int)
    del esqueleto, casos_upgd, df
    gc.collect()

    print("📊 [3/9] Calculando canales endémicos históricos...")
    panel_maestro = calcular_canal_endemico(panel_maestro)
    
    print("🎯 [4/9] Computando target del INS (Ventanas móviles futuras)...")
    panel_maestro = crear_target(panel_maestro)
    
    print("🧬 [5/9] Extrayendo variables retrasadas (Feature Engineering)...")
    panel_maestro = crear_features(panel_maestro, df_clima)
    gc.collect()
    
    # Splitting Limpio
    panel_maestro_clean = panel_maestro.dropna(subset=['target_intervencion', 'casos_lag_52', 'media_casos_4']).reset_index(drop=True)
    panel_maestro_clean['target_intervencion'] = panel_maestro_clean['target_intervencion'].astype(int)
    panel_maestro_clean['nom_upgd'] = panel_maestro_clean['nom_upgd'].astype('category')
    
    EXCLUIR = [
        'casos', 'target_intervencion', 'año_ini_sin', 'semana_epi_ini_sin',
        'estado_sivigila_interno', 'alerta_binaria_pasada',
        # --- Experimento de ablación: variables de identidad/demografía estática ---
        'nom_upgd', 'densidad_poblacional', 'crecimiento_poblacional',
        'incremento_habitantes', 'densidad_delta'
    ]
    FEATURES = [c for c in panel_maestro_clean.columns if c not in EXCLUIR]
    
    X = panel_maestro_clean[FEATURES]
    y = panel_maestro_clean['target_intervencion']

    # Corte temporal real: las últimas 52 semanas CALENDARIO (todas las UPGDs incluidas),
    # no las últimas N filas. panel_maestro_clean está ordenado por semana desde
    # feature_engineering.py, así que el corte por (año, semana) sí separa "pasado" de
    # "futuro" en vez de separar UPGDs completas por su posición alfabética.
    semanas_unicas = (
        panel_maestro_clean[['año_ini_sin', 'semana_epi_ini_sin']]
        .drop_duplicates()
        .sort_values(['año_ini_sin', 'semana_epi_ini_sin'])
    )
    idx_test = pd.MultiIndex.from_frame(semanas_unicas.tail(52))
    idx_panel = pd.MultiIndex.from_frame(panel_maestro_clean[['año_ini_sin', 'semana_epi_ini_sin']])
    es_test = idx_panel.isin(idx_test)

    X_train_cv, X_test = X.loc[~es_test].reset_index(drop=True), X.loc[es_test].reset_index(drop=True)
    y_train_cv, y_test = y.loc[~es_test].reset_index(drop=True), y.loc[es_test].reset_index(drop=True)

    print("🏋️ [6/9] Optimizando hiperparámetros con Optuna...")
    params = optimizar_modelo(X_train_cv, y_train_cv)
    
    # ⬅ CAMBIO: is_unbalance eliminado, scale_pos_weight viene de Optuna (dentro de params)
    best_p_dict = {**params, 'objective': 'binary', 'random_state': 42, 'verbose': -1}
    
    print("🧪 [7/9] Calibrando umbral mediante Out-of-Fold (OOF)...")
    umbral_optimo = calibrar_umbral(X_train_cv, y_train_cv, best_p_dict)
    print(f"Número de variables: {len(FEATURES)}")
    print("\nVariables utilizadas por el modelo:\n")

    for i, f in enumerate(FEATURES, 1):
        print(f"{i:03d}. {f}")
    print("🚀 [8/9] Entrenando el clasificador definitivo LightGBM...")
    modelo_final = entrenar_modelo(X_train_cv, y_train_cv, best_p_dict)
    
    # Evaluación en Test
    probs_test = modelo_final.predict_proba(X_test)[:, 1]
    print(f"📈 ROC-AUC final en conjunto de Test: {roc_auc_score(y_test, probs_test):.4f}")
    print(f"🎯 Umbral sugerido OOF: {umbral_optimo * 100:.1f}%")
    # Reporte de clasificación por clase (usando el umbral OOF ya calibrado)
    y_pred = (probs_test >= umbral_optimo).astype(int)
    print("\n📋 Classification report (Test, umbral OOF):")
    print(classification_report(y_test, y_pred, digits=3))

    # ⬅ CAMBIO: curva precision-recall completa para ver el rango de trade-offs disponibles
    print("\n📐 Curva Precision-Recall (Test) — umbrales con recall >= 0.60:")
    precisions, recalls, thresholds = precision_recall_curve(y_test, probs_test)
    thresholds_ext = list(thresholds) + [1.0]
    for p, r, t in zip(precisions, recalls, thresholds_ext):
        if r >= 0.60:
            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
            print(f"  umbral={t:.2f}  precision={p:.3f}  recall={r:.3f}  f1={f1:.3f}")
    
    print("💾 [9/9] Exportando modelos y generando explicabilidad SHAP...")
    exportar_artefactos(modelo_final, FEATURES, umbral_optimo)
    generar_shap(modelo_final, X_train_cv)
    
    print("🎉 ¡Proceso finalizado con éxito! Módulos listos para producción.")

if __name__ == "__main__":
    ejecutar_pipeline_entrenamiento()