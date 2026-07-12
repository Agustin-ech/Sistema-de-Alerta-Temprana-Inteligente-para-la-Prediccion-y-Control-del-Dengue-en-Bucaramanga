import json
import pickle
import re
import sys
from pathlib import Path
from itertools import product
import pandas as pd
import numpy as np
import shap
import difflib
from app.config.settings import MODEL_PATH, METADATA_PATH, BASELINE_PATH, GEO_JSON_PATH

# Asegurar que el paquete training se importe desde la raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from training.data_loader import cargar_datos
from training.preprocessing import preparar_dengue_base
from training.endemic_channel import calcular_canal_endemico
from training.target import crear_target
from training.feature_engineering import crear_features

# ==========================================
# 1. TEXTO Y TRADUCCIÓN SEMÁNTICA
# ==========================================

def normalizar_texto(texto):
    if not texto:
        return ""
    texto = str(texto).upper().strip()
    reemplazos = {"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ñ": "N"}
    for original, reemplazo in reemplazos.items():
        texto = texto.replace(original, reemplazo)
    texto = re.sub(re.compile(r'\b(S\.?A\.?S\.?|S\.?A\.?|LIMITADA|LTDA)\b'), '', texto)
    texto = re.sub(re.compile(r'[^\w\s]'), '', texto)
    return " ".join(texto.split())

# Diccionario enfocado en fenómenos epidemiológicos reales.
# Cada entrada es una oración completa en lenguaje natural (para cualquier lector),
# el detalle técnico con el valor real de la variable se agrega aparte
# (ver formatear_detalle_tecnico) para quien quiera verificar el dato concreto.
DICCIONARIO_SEMANTICO = {
    # Carga epidémica reciente y persistencia del brote
    "casos_lag_1": "Se registró un aumento de casos en la semana inmediatamente anterior.",
    "casos_lag_4": "Se observó un incremento de casos hace aproximadamente un mes, coincidiendo con el tiempo típico entre la lluvia y el contagio.",
    "casos_lag_52": "El comportamiento actual es similar al registrado en el mismo período del año anterior.",
    "media_casos_4": "El nivel general de casos en las últimas cuatro semanas ha sido alto.",
    "std_casos_4": "Se observa variabilidad en los casos recientes, típica de un brote que está comenzando o acelerando.",
    "alerta_lag_1": "La semana anterior la institución estuvo en alerta epidemiológica.",
    "alerta_lag_2": "Hace dos semanas la institución estuvo en alerta epidemiológica.",
    "persistencia_alerta_2": "La institución ha estado en alerta durante gran parte de las últimas dos semanas.",
    "persistencia_alerta_3": "La institución ha estado en alerta durante gran parte de las últimas tres semanas.",
    "persistencia_alerta_4": "La institución ha estado en alerta durante gran parte del último mes.",
    "persistencia_alerta_6": "La institución ha permanecido varias semanas consecutivas en vigilancia epidemiológica.",
    "persistencia_alerta_8": "La institución ha permanecido varias semanas consecutivas en vigilancia epidemiológica.",
    # Contagio espacial
    "vecinos_alerta_prom": "Instituciones geográficamente cercanas también están en alerta, lo que sugiere propagación regional del brote.",
    # Clima: precipitación
    "precipitacion_total": "Se acumuló una cantidad importante de lluvia recientemente.",
    "precipitacion_total_rollmean8": "Hubo lluvias persistentes durante las últimas ocho semanas.",
    "precipitacion_max10min": "Se registraron episodios de lluvia intensa en poco tiempo, favoreciendo el encharcamiento y la formación de criaderos.",
    "precipitacion_max10min_rollmean8": "Los últimos dos meses tuvieron episodios recurrentes de lluvia intensa en poco tiempo.",
    "precipitacion_frecuencia": "Ha llovido con frecuencia en las últimas semanas.",
    "precipitacion_std": "La lluvia ha sido irregular (períodos secos seguidos de aguaceros), lo que favorece más al mosquito que la lluvia constante.",
    "precipitacion_std_rollmean8": "La lluvia ha sido irregular durante las últimas ocho semanas, alternando entre secas y aguaceros.",
    # Clima: temperatura
    "temperatura_media": "Las temperaturas registradas están por encima del promedio.",
    "temperatura_min": "Las temperaturas mínimas registradas favorecen la actividad del mosquito.",
    "temperatura_max": "Hubo episodios recientes de altas temperaturas.",
    "temperatura_std": "Se registraron variaciones importantes en la temperatura.",
    "temperatura_rango": "Hubo cambios bruscos entre temperaturas mínimas y máximas.",
    "temp_rango_4sem": "Las variaciones entre temperatura mínima y máxima han sido amplias en el último mes.",
    "temp_media_6sem": "La temperatura promedio del último mes y medio favorece la actividad del mosquito.",
    "temp_max_4sem": "Las temperaturas máximas del último mes han sido elevadas.",
    "grados_dia_acum": "La acumulación de calor reciente favorece un desarrollo más rápido del mosquito y del virus dentro de él.",
    "condicion_fav_mosquito": "Se cumplen a la vez las condiciones de lluvia y temperatura ideales para la reproducción del mosquito.",
    # Estacionalidad del calendario
    "semana_sin": "La época del año actual coincide históricamente con mayor actividad del mosquito.",
    "semana_cos": "La época del año actual coincide históricamente con mayor actividad del mosquito.",
}

def traducir_variable_inteligente(variable):
    """
    Busca coincidencia exacta; si no existe debido a transformaciones complejas
    (ej: rollmean8_lag_12), extrae el fenómeno base del string.
    """
    var_lower = variable.lower()
    if var_lower in DICCIONARIO_SEMANTICO:
        return DICCIONARIO_SEMANTICO[var_lower]

    if "persistencia_alerta" in var_lower:
        return "La institución ha permanecido varias semanas consecutivas en vigilancia epidemiológica."
    if "alerta" in var_lower and "lag" in var_lower:
        return "La institución estuvo en alerta epidemiológica en semanas recientes."
    if "vecinos" in var_lower:
        return "Instituciones geográficamente cercanas también están en alerta, lo que sugiere propagación regional del brote."
    if "temperatura" in var_lower or "temp_" in var_lower:
        return "Las condiciones de temperatura registradas favorecen la actividad del mosquito transmisor."
    if "precipitacion" in var_lower or "precip" in var_lower or "lluvia" in var_lower:
        return "Las condiciones de lluvia recientes favorecen la reproducción del mosquito transmisor."
    if "casos" in var_lower:
        return "El comportamiento reciente de casos reportados contribuye a esta estimación."
    if "alerta" in var_lower:
        return "La persistencia de alertas epidemiológicas en semanas anteriores contribuye a esta estimación."

    return variable.replace('_', ' ').capitalize() + "."


def formatear_detalle_tecnico(nombre_variable, valor):
    """
    Detalle técnico breve (nombre real de la variable + su valor en esta predicción),
    pensado para que un epidemiólogo pueda verificar el dato concreto detrás de la
    frase en lenguaje natural, sin tener que confiar en la redacción a ciegas.
    """
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return f"{nombre_variable}: {valor}"

    if v == int(v):
        valor_fmt = str(int(v))
    else:
        valor_fmt = f"{v:.2f}".rstrip('0').rstrip('.')

    return f"{nombre_variable} = {valor_fmt}"

# ==========================================
# 2. CARGADORES GLOBALES E INSTANCIAS
# ==========================================

def cargar_json(ruta, normalize_keys: bool = False):
    if ruta.exists():
        with open(ruta, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            if normalize_keys:
                return {normalizar_texto(k): v for k, v in datos.items()}
            return datos
    return {}


def cargar_modelo():
    if MODEL_PATH.exists():
        with open(MODEL_PATH, 'rb') as f:
            return pickle.load(f)
    return None


def inicializar_panel_historico():
    df = cargar_datos("03_primary/dataset_limpio.xlsx")
    casos_upgd, df_clima, todas_upgds = preparar_dengue_base(df)
    todas_semanas = df_clima[['año_ini_sin', 'semana_epi_ini_sin']].drop_duplicates()

    esqueleto = pd.DataFrame(list(product(todas_semanas.itertuples(index=False), todas_upgds)), columns=['semana_combo', 'nom_upgd'])
    esqueleto[['año_ini_sin', 'semana_epi_ini_sin']] = pd.DataFrame(esqueleto['semana_combo'].tolist(), index=esqueleto.index)
    esqueleto = esqueleto.drop(columns=['semana_combo'])

    panel_maestro = esqueleto.merge(casos_upgd, on=['año_ini_sin', 'semana_epi_ini_sin', 'nom_upgd'], how='left')
    panel_maestro['casos'] = panel_maestro['casos'].fillna(0).astype(int)
    panel_maestro = calcular_canal_endemico(panel_maestro)
    panel_maestro = crear_target(panel_maestro)
    panel_maestro = crear_features(panel_maestro, df_clima)
    panel_maestro['nom_upgd'] = panel_maestro['nom_upgd'].astype(str).str.upper().str.strip()
    panel_maestro['nom_upgd_normalizado'] = panel_maestro['nom_upgd'].apply(normalizar_texto)
    
    # ✅ Validación: Asegurar que todas las columnas del metadata existen
    features_requeridas = metadata.get('features_ordenadas', [])
    columnas_faltantes = [f for f in features_requeridas if f not in panel_maestro.columns]
    if columnas_faltantes:
        print(f"⚠️  Columnas faltantes en panel_historico: {columnas_faltantes[:10]}...")  # Mostrar primeras 10
        for col_faltante in columnas_faltantes:
            panel_maestro[col_faltante] = 0.0  # Rellenar con 0 como valor por defecto
        print(f"✅ Se agregaron {len(columnas_faltantes)} columnas faltantes")
    
    return panel_maestro

print("1. Cargando modelo...")
modelo = cargar_modelo()
print("✓ Modelo cargado")

print("2. Cargando metadata...")
metadata = cargar_json(METADATA_PATH)
print("✓ Metadata cargada")

print("3. Cargando coordenadas y baseline...")
baseline = cargar_json(BASELINE_PATH)
coordenadas_upgd = cargar_json(GEO_JSON_PATH, normalize_keys=True)
print("✓ Coordenadas listas")

print("4. Inicializando SHAP...")
explainer = shap.TreeExplainer(modelo)
print("✓ SHAP listo")

print("5. Inicializando panel histórico...")
panel_historico = inicializar_panel_historico()
print("✓ Panel histórico listo")

try:
    panel_historico = inicializar_panel_historico()
except Exception as e:
    panel_historico = None
    print(f"⚠️ No se pudo inicializar el panel histórico: {e}")

# ==========================================
# 3. LÓGICA CENTRAL DE DATAFRAMES Y CONTEXTO
# ==========================================

def reconstruir_dataframe(item, features_ordenadas):
    """
    Reconstruye automáticamente la fila de características a partir del histórico.
    Usa similitud de textos (Fuzzy Matching) para encontrar la UPGD correcta.
    """
    if panel_historico is None:
        raise RuntimeError("El panel histórico no está disponible. Comprueba el dataset.")

    nombre_enviado = normalizar_texto(item.nom_upgd)
    semana = item.semana
    
    # Obtener todos los nombres únicos que REALMENTE existen en el modelo
    nombres_validos = panel_historico['nom_upgd_normalizado'].unique().tolist()
    
    # 1. Búsqueda inteligente: Encontrar el nombre más parecido al que envió el frontend
    # cutoff=0.5 significa que requiere al menos un 50% de similitud.
    coincidencias = difflib.get_close_matches(nombre_enviado, nombres_validos, n=1, cutoff=0.5)
    
    if coincidencias:
        nombre_real_modelo = coincidencias[0]
        print(f"🔄 Auto-corrigiendo nombre: '{nombre_enviado}' -> '{nombre_real_modelo}'")
    else:
        # Si no hay nada similar (cutoff < 0.5), intentamos ver si una palabra clave está contenida
        # Ejemplo: Si envían "ISABU" y en la base está "HOSPITAL ISABU"
        palabras = [p for p in nombre_enviado.split() if len(p) > 3]
        posibles = [n for n in nombres_validos if any(p in n for p in palabras)]
        
        if posibles:
            nombre_real_modelo = posibles[0]
            print(f"🔄 Auto-corrigiendo por palabra clave: '{nombre_enviado}' -> '{nombre_real_modelo}'")
        else:
            raise ValueError(f"No existe ninguna UPGD parecida a '{item.nom_upgd}' en el modelo.")

    # 2. Filtrar el dataframe con el nombre real encontrado y la semana
    candidatos = panel_historico[
        (panel_historico['nom_upgd_normalizado'] == nombre_real_modelo) &
        (panel_historico['semana_epi_ini_sin'] == semana)
    ]

    # Manejo de error si la UPGD existe pero no tiene datos para esa semana
    if candidatos.empty:
        upgd_existe = panel_historico[panel_historico['nom_upgd_normalizado'] == nombre_real_modelo]
        disponibles = sorted(upgd_existe["semana_epi_ini_sin"].unique())
        raise ValueError(
            f"La UPGD se reconoció como '{nombre_real_modelo}', pero NO hay datos para la semana {semana}. "
            f"Semanas disponibles: {disponibles}"
        )

    # 3. Seleccionar la fila más reciente si hay duplicados por año y clonar features
    fila = candidatos.sort_values('año_ini_sin', ascending=False).iloc[[0]]
    df = fila[features_ordenadas].copy().reset_index(drop=True)

    # 4. Restaurar el tipo de dato categórico si es necesario
    if 'nom_upgd' in df.columns:
        if pd.api.types.is_categorical_dtype(panel_historico['nom_upgd']):
            categorias = panel_historico['nom_upgd'].cat.categories
        else:
            categorias = [x for x in panel_historico['nom_upgd'].unique() if isinstance(x, str)]
        df['nom_upgd'] = pd.Categorical(df['nom_upgd'], categories=categorias)

    return df

def obtener_metadatos_riesgo(prob, semana_actual):
    # Cortes de riesgo revisados con criterio epidemiológico (2026-07-06):
    # 0-25% Bajo, 26-50% Medio, 51-75% Alto, 76-100% Crítico.
    pct = prob * 100
    if pct <= 25:
        estado, ins_nivel, color = "Riesgo Bajo", "Normal", "#28a745"
    elif pct <= 50:
        estado, ins_nivel, color = "Riesgo Medio", "Vigilancia", "#ffc107"
    elif pct <= 75:
        estado, ins_nivel, color = "Riesgo Alto", "Alerta", "#fd7e14"
    else:
        estado, ins_nivel, color = "Riesgo Crítico", "Posible intervención", "#dc3545"

    semanas_horizonte = []
    for i in range(1, 5):
        sem = semana_actual + i
        if sem > 52:
            sem = sem - 52
        semanas_horizonte.append(sem)
    return {
        "estado": estado,
        "ins_nivel": ins_nivel,
        "color_hex": color,
        "horizonte": f"Semanas {semanas_horizonte[0]}–{semanas_horizonte[-1]}"
    }

# ==========================================
# 4. ENDPOINTS CORE UNIFICADOS
# ==========================================

# Ver CHANGELOG.md [2026-07-06]: con esta confirmación activa, F1.5 test 0.7081->0.7018 (~igual),
# precision 0.513->0.560 (menos falsas alarmas), recall 0.852->0.791 (~6pp menos casos detectados),
# -14.8% de volumen de alertas. Cambiar a False para volver a la versión de mayor recall (cruda).
CONFIRMACION_TEMPORAL_ACTIVA = True

def predict_upgd(item, features_ordenadas):
    df_fila = reconstruir_dataframe(item, features_ordenadas)
    prob = float(modelo.predict_proba(df_fila)[0,1])

    umbral = metadata["umbral_calibrado"]

    alerta_cruda = prob >= umbral
    alerta = alerta_cruda

    if CONFIRMACION_TEMPORAL_ACTIVA:
        try:
            semana_anterior = item.semana - 1 if item.semana > 1 else 52
            item_anterior = item.model_copy(update={'semana': semana_anterior})
            df_fila_anterior = reconstruir_dataframe(item_anterior, features_ordenadas)
            prob_anterior = float(modelo.predict_proba(df_fila_anterior)[0, 1])
            alerta = alerta_cruda and (prob_anterior >= umbral)
        except (ValueError, RuntimeError):
            # No hay dato de la semana anterior (ej. UPGD nueva o borde del histórico):
            # no se puede confirmar, se mantiene la alerta cruda.
            alerta = alerta_cruda

    nombre_busqueda = normalizar_texto(item.nom_upgd)
    coord = coordenadas_upgd.get(nombre_busqueda, {"lat": 7.1193, "lng": -73.1227})
    meta_riesgo = obtener_metadatos_riesgo(prob, item.semana)

    return {
        "upgd": item.nom_upgd,
        "semana_evaluada": item.semana,  # ✅ Agregar semana para que el frontend la tenga
        "probabilidad_brote": prob,
        "umbral": umbral,
        "alerta": alerta,
        "alerta_cruda": alerta_cruda,
        "coordenadas": coord,
        "contexto": meta_riesgo
    }

def explicar_prediccion(item, features_ordenadas):
    df_fila = reconstruir_dataframe(item, features_ordenadas)
    prob = float(modelo.predict_proba(df_fila)[0, 1])
    pct = prob * 100
    
    if explainer is None:
        raise RuntimeError("El explicador SHAP no está disponible.")
        
    shap_values = explainer.shap_values(df_fila)
    if isinstance(shap_values, list):
        valores_impacto = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
    elif len(shap_values.shape) == 3:
        valores_impacto = shap_values[0, :, 1]
    else:
        valores_impacto = shap_values[0]
    
    factores = []
    for var, impacto in zip(features_ordenadas, valores_impacto):
        if abs(impacto) > 0.005:
            factores.append({"variable": var, "impacto": float(impacto)})
            
    factores = sorted(factores, key=lambda x: abs(x['impacto']), reverse=True)
    top_factores = factores[:3]

    factores_positivos = [f for f in top_factores if f['impacto'] > 0]
    factores_negativos = [f for f in top_factores if f['impacto'] <= 0]
    
    meta_riesgo = obtener_metadatos_riesgo(prob, item.semana)
    
    # Narrativa alineada a los mismos 4 cortes de obtener_metadatos_riesgo (0-25 Bajo,
    # 26-50 Medio, 51-75 Alto, 76-100 Crítico), revisados con criterio epidemiológico (2026-07-06).
    if pct <= 25:
        narrativa = f"El riesgo estimado de intervención para las próximas cuatro semanas es bajo ({pct:.1f}%). Aunque se identifican algunos factores aislados en la zona, su efecto es compensado por condiciones ambientales e históricas favorables, manteniendo la probabilidad dentro de los niveles basales esperados."
    elif pct <= 50:
        narrativa = f"El riesgo estimado de intervención se encuentra en un nivel medio ({pct:.1f}%). Se evidencia una actividad regular del vector combinada con variaciones climáticas locales que requieren un monitoreo preventivo continuo en la institución."
    elif pct <= 75:
        narrativa = f"El riesgo estimado de intervención es alto ({pct:.1f}%). Se evidencia una combinación sostenida de condiciones ambientales y comportamiento de contagios que amerita reforzar la vigilancia y evaluar medidas preventivas en la zona."
    else:
        narrativa = f"Se detecta un escenario epidemiológico crítico con un riesgo estimado del {pct:.1f}%. Los principales determinantes ambientales y el comportamiento de la curva de contagios exigen una evaluación inmediata de medidas de intervención en la zona."

    # Explicación en dos capas: una oración en lenguaje natural (para cualquier
    # lector) + un detalle técnico con el nombre y valor reales de la variable
    # (para que un epidemiólogo pueda verificar el dato concreto).
    factores_legibles = []
    for f in top_factores:
        texto_formal = traducir_variable_inteligente(f['variable'])
        valor_real = df_fila[f['variable']].iloc[0]
        detalle_tecnico = formatear_detalle_tecnico(f['variable'], valor_real)

        v_abs = abs(f['impacto'])
        if v_abs > 0.15:
            peso_str, barras = "Alta", "███"
        elif v_abs > 0.05:
            peso_str, barras = "Media", "██"
        else:
            peso_str, barras = "Baja", "█"

        factores_legibles.append({
            "variable": texto_formal,
            "detalle_tecnico": detalle_tecnico,
            "es_aumento": f['impacto'] > 0,
            "peso_cualitativo": peso_str,
            "barras": barras
        })

    return {
        "riesgo": prob,
        "factores": factores_legibles,
        "explicacion_natural": narrativa,
        "contexto": meta_riesgo
    }