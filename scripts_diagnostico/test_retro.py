import pandas as pd
import numpy as np
import json
import pickle
from pathlib import Path
from types import SimpleNamespace
from sklearn.metrics import confusion_matrix

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

def cargar_artefactos_entrenamiento():
    base_dir = RAIZ_PROYECTO / "scripts"

    with open(base_dir / 'modelo_final_dengue_grave.pkl', 'rb') as f:
        modelo_final = pickle.load(f)
    with open(base_dir / 'metadata_modelo_grave.json', 'r') as f:
        meta = json.load(f)
    return modelo_final, meta['features_ordenadas'], meta['umbral_calibrado']

def construir_dataframe_local(obj_simulado, features_ordenadas):
    """
    Construye la fila de entrada al modelo directamente desde el diccionario de
    valores ya calculados (datos_vectoriales) para esta simulación de backtesting.

    No reutiliza app.api.services.reconstruir_dataframe: esa función busca la fila
    en el panel histórico de producción por nombre de UPGD + semana (con fuzzy
    matching), mientras que acá ya tenemos el vector exacto de features
    precomputado a mano en df_panel para cada simulación.
    """
    fila = {feat: obj_simulado.datos_vectoriales.get(feat, 0) for feat in features_ordenadas}
    return pd.DataFrame([fila], columns=features_ordenadas)

def precomputar_target_intervencion_global(df):
    """
    🎯 RECONSTRUCCIÓN CRONOLÓGICA CON REINDEXACIÓN
    Toma tus columnas exactas ('NOM_UPGD', 'ANO', 'SEMANA') y fuerza la línea
    de tiempo continua (1 a 53) para que las ventanas móviles futuras funcionen bien.
    """
    print("⚙️ Detectadas columnas crudas. Reindexando matriz UPGD-Tiempo...")
    
    # Asegurar nombres exactos del archivo subido en mayúsculas/minúsculas
    col_upgd = 'NOM_UPGD' if 'NOM_UPGD' in df.columns else 'nom_upgd'
    col_ano = 'ANO' if 'ANO' in df.columns else 'ano'
    col_semana = 'SEMANA' if 'SEMANA' in df.columns else 'semana'
    
    # 1. Agrupar microdatos para contar casos reales por semana por institución
    df_conteos = df.groupby([col_upgd, col_ano, col_semana]).size().reset_index(name='casos_calculados')
    
    # 2. Reindexación Estricta: Forzar semanas epidemiológicas del 1 al 53 para todas las UPGD y Años
    upgds_unicas = df_conteos[col_upgd].unique()
    anos_unicos = df_conteos[col_ano].unique()
    semanas_todas = list(range(1, 54))
    
    idx_completo = pd.MultiIndex.from_product(
        [upgds_unicas, anos_unicos, semanas_todas], 
        names=[col_upgd, col_ano, col_semana]
    ).to_frame().reset_index(drop=True)
    
    df_panel_completo = pd.merge(idx_completo, df_conteos, on=[col_upgd, col_ano, col_semana], how='left')
    df_panel_completo['casos_calculados'] = df_panel_completo['casos_calculados'].fillna(0).astype(int)
    
    # 3. Mapear alertas simuladas basadas en reglas estándar del INS (0=Sano, 1=Vigilancia, 2=Alerta Crítica)
    df_panel_completo['alerta_simulada'] = df_panel_completo['casos_calculados'].apply(lambda c: 2 if c >= 3 else (1 if c >= 1 else 0))
    
    # Ordenar cronológicamente antes de aplicar los desplazamientos temporales (.shift)
    df_panel_completo = df_panel_completo.sort_values(by=[col_upgd, col_ano, col_semana]).reset_index(drop=True)
    grupo = df_panel_completo.groupby(col_upgd)['alerta_simulada']
    
    f_1 = grupo.shift(-1).fillna(0).astype(int)
    f_2 = grupo.shift(-2).fillna(0).astype(int)
    f_3 = grupo.shift(-3).fillna(0).astype(int)
    f_4 = grupo.shift(-4).fillna(0).astype(int)
    
    # Aplicación rigurosa de las tres reglas operativas del INS a 4 semanas hacia adelante
    regla1 = (f_1 == 2) | (f_2 == 2) | (f_3 == 2) | (f_4 == 2)
    regla2 = ((f_1 >= 1).astype(int) + (f_2 >= 1).astype(int) + (f_3 >= 1).astype(int) + (f_4 >= 1).astype(int)) >= 3
    regla3 = ((f_1 >= 1) & (f_2 >= 1)) | ((f_2 >= 1) & (f_3 >= 1)) | ((f_3 >= 1) & (f_4 >= 1))
    
    df_panel_completo['target_intervencion'] = (regla1 | regla2 | regla3).astype(int)
    
    # 4. Cruzar el target robusto de vuelta a los microdatos originales
    df_final = df.merge(
        df_panel_completo[[col_upgd, col_ano, col_semana, 'target_intervencion']], 
        on=[col_upgd, col_ano, col_semana], 
        how='left'
    ).fillna({'target_intervencion': 0})
    
    return df_final

def ejecutar_backtesting_acumulado(ano_evaluar=2024, semanas_rango=range(20, 48)):
    print(f"🔬 INICIANDO SIMULACIÓN DE ALERTA TEMPRANA (BACKTESTING {ano_evaluar})")
    print("=" * 80)
    
    modelo_final, features_ordenadas, umbral_calibrado = cargar_artefactos_entrenamiento()
    
    ruta_dataset = RAIZ_PROYECTO / "data" / "01_raw" / "epidemiological_data_bucaramanga_processed_dengue_grave1.xlsx"
    df_panel = pd.read_excel(ruta_dataset) if ruta_dataset.suffix == '.xlsx' else pd.read_csv(ruta_dataset)
    
    # Conservar consistencia con nombres del archivo original entrenado
    col_ano = 'ANO' if 'ANO' in df_panel.columns else ('año_ini_sin' if 'año_ini_sin' in df_panel.columns else 'ano')
    col_semana = 'SEMANA' if 'SEMANA' in df_panel.columns else ('semana_epi_ini_sin' if 'semana_epi_ini_sin' in df_panel.columns else 'semana')
    col_upgd = 'NOM_UPGD' if 'NOM_UPGD' in df_panel.columns else 'nom_upgd'
    
    df_panel = precomputar_target_intervencion_global(df_panel)
    
    print("\n📊 Distribución final balanceada del Target en el Backtesting:")
    print(df_panel['target_intervencion'].value_counts())
    print(df_panel['target_intervencion'].value_counts(normalize=True) * 100)
    print("-" * 80)

    y_true_acumulado = []
    y_pred_acumulado = []
    probabilidades_crudas = []
    bloques_priorizacion = []
    
    print(f"🏃‍♂️ Corriendo inferencias en lote para las semanas S{semanas_rango.start} a S{semanas_rango.stop-1}...")
    for sem in semanas_rango:
        datos_semana = df_panel[(df_panel[col_ano] == ano_evaluar) & (df_panel[col_semana] == sem)]
        if datos_semana.empty:
            continue
            
        for _, fila in datos_semana.iterrows():
            nombre_upgd = fila[col_upgd]
            # El excel crudo tiene columnas en mayúsculas/mixtas (ej. 'Precipitacion_Std_L1'),
            # mientras que features_ordenadas viene en minúsculas desde la metadata del modelo.
            fila_normalizada = {str(k).lower(): v for k, v in fila.items()}
            datos_vectoriales = {
                feat: fila_normalizada[feat]
                for feat in features_ordenadas
                if feat in fila_normalizada and feat != col_upgd.lower()
            }
            
            obj_simulado = SimpleNamespace(nom_upgd=nombre_upgd, semana=sem, datos_vectoriales=datos_vectoriales)
            df_fila = construir_dataframe_local(obj_simulado, features_ordenadas)
            
            prob = float(modelo_final.predict_proba(df_fila)[0, 1])
            clase_predicha = 1 if prob >= umbral_calibrado else 0
            
            target_real = int(fila['target_intervencion'])
            y_true_acumulado.append(target_real)
            y_pred_acumulado.append(clase_predicha)
            probabilidades_crudas.append(prob)
            
            bloques_priorizacion.append({
                'semana': sem,
                'upgd': nombre_upgd,
                'prob': prob,
                'real': target_real
            })

    if not y_true_acumulado:
        print("⚠️ No se acumularon registros para el rango temporal de evaluación seleccionado.")
        return
        
    prob_series = pd.Series(probabilidades_crudas)
    y_true_arr = np.array(y_true_acumulado)
    
    # ==================================================================
    # 📈 CURVA OPERATIVA MULTIUMBRAL PARA PRESENTACIÓN DEL JURADO
    # ==================================================================
    print("\n" + "═"*75)
    print("📋 TABLA DE CONFIGURACIÓN DINÁMICA DEL SISTEMA DE ALERTAS (MULTI-UMBRAL)")
    print("═"*75)
    
    umbrales_evaluar = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.49, 0.55]
    reporte_umbrales = []
    
    for u in umbrales_evaluar:
        y_pred_u = (prob_series >= u).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true_arr, y_pred_u, labels=[0, 1]).ravel()
        
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        especificidad = tn / (tn + fp) if (tn + fp) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        reporte_umbrales.append({
            "Umbral": u,
            "Sensibilidad (Recall)": f"{recall * 100:.1f}%",
            "Precisión": f"{precision * 100:.1f}%",
            "Especificidad": f"{especificidad * 100:.1f}%",
            "F1-Score": f"{f1:.3f}",
            "FP (Falsas Alarmas)": fp,
            "TP (Aciertos)": tp
        })
        
    df_umbrales = pd.DataFrame(reporte_umbrales)
    print(df_umbrales.to_string(index=False))
    print("═"*75)
    
    # ==================================================================
    # 🎯 EVALUACIÓN COMO MOTOR DE TRIAJE (Recall@Top-K)
    # ==================================================================
    print("\n🎯 CAPACIDAD DE PRIORIZACIÓN SEMANAL (Early Warning Recall@Top-K):")
    df_eval_priorizacion = pd.DataFrame(bloques_priorizacion)
    
    total_intervenciones_reales = 0
    semanas_evaluadas = 0
    
    for sem, grupo_sem in df_eval_priorizacion.groupby('semana'):
        if grupo_sem.empty:
            continue
        semanas_evaluadas += 1
        total_intervenciones_reales += grupo_sem['real'].sum()
        
    print(f" -> Semanas evaluadas dinámicamente en 2024: {semanas_evaluadas}")
    print(f" -> Total de intervenciones críticas reales en el periodo: {total_intervenciones_reales}")
    print("\n -> Resultados por cantidad de UPGD intervenidas por semana:")
    
    for k in [3, 5, 10, 15, 20, 30]:
        hits = 0
        for sem, grupo_sem in df_eval_priorizacion.groupby('semana'):
            if grupo_sem.empty:
                continue
            top_k = grupo_sem.sort_values(by='prob', ascending=False).head(k)
            hits += top_k['real'].sum()
        recall_k = (hits / total_intervenciones_reales) * 100 if total_intervenciones_reales > 0 else 0
        print(f"    • Top-{k}: captura {hits} de {total_intervenciones_reales} reales -> Recall@Top{k}: {recall_k:.1f}%")
    print("═"*75)

if __name__ == "__main__":
    ejecutar_backtesting_acumulado(ano_evaluar=2024, semanas_rango=range(20, 48))