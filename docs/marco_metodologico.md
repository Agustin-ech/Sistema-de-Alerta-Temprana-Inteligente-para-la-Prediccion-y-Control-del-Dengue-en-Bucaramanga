# Marco metodológico — CRISP-ML(Q)

Este proyecto siguió las fases de **CRISP-ML(Q)** — la extensión de CRISP-DM para
proyectos de machine learning con foco en calidad y monitoreo continuo.

## 1. Comprensión del negocio y los datos (Business & Data Understanding)

- Problema y objetivo de negocio: ver `planteamiento_problema.md`.
- Fuentes y su procedencia: ver `fuentes_datos.md`.
- Se migró de un dataset por caso individual a un panel espacio-temporal
  (UPGD × semana epidemiológica) que obligó a reescribir la ingeniería de variables
  autoregresivas y corregir los folds de `TimeSeriesSplit`.

## 2. Preparación de datos (Data Preparation)

Pipeline modular en `training/` (`data_loader.py` → `preprocessing.py` →
`endemic_channel.py` → `target.py` → `feature_engineering.py`), descrito en
`architecture.md`. Incluye:
- Reducción de memoria y limpieza estructural (`reduce_mem_usage()`,
  `preparar_dengue_base()`).
- Cálculo del canal endémico histórico por UPGD y semana del año.
- Construcción del target de intervención (`target.py`), con reglas
  inspiradas en criterios del INS (ver `data_dictionary.md`).
- Generación de 142 variables (lags, ventanas móviles, contagio espacial,
  estacionalidad cíclica).

## 3. Modelado (Modeling)

- Algoritmo: LightGBM (gradient boosting), con `optimizar_modelo()` (Optuna,
  100 trials) para búsqueda de hiperparámetros — incluyendo
  `scale_pos_weight` como hiperparámetro buscable en vez de
  `is_unbalance=True` fijo.
- Métrica de optimización: F-beta con `beta=1.5`, elegido para balancear
  precision y recall mejor que el `beta=2` inicial (que daba recall alto pero
  precision muy baja, ~3.6 falsas alarmas por alerta real).

## 4. Evaluación (Evaluation) 

Esta es la fase donde más iteración y escepticismo se aplicó activamente,
tratando cada resultado sospechoso como una hipótesis a refutar antes de
aceptarlo:

1. **Detección y corrección de leakage de identidad**:
   señales de alerta (ROC-AUC 0.97 con F2 mediocre, variables de identidad
   dominando SHAP) llevaron a una ablación que confirmó y corrigió el
   problema.
2. **Verificación de leakage temporal en `persistencia_alerta_8`**: revisión
   de código (ventanas pasado/futuro no se solapan) + ablación empírica
   (caída de solo 0.4% relativo al quitarla) para descartar que fuera un
   atajo, no solo revisar el código.
3. **Baseline ingenuo**: comparación contra 3 reglas fijas sin ML, para
   responder "¿el modelo realmente predice o solo repite inercia?" — el
   modelo supera a la mejor regla en ~42% relativo de F1.5.
4. **Validación CCF empírica**: correlación cruzada por lag entre clima y
   casos totales, para confirmar (no asumir) que los lags de 3-6 semanas
   usados en feature engineering tienen respaldo estadístico real.
5. **Análisis SHAP de falsos positivos vs. verdaderos positivos**: identificó
   el patrón de confusión del modelo (clima favorable sin momentum
   sostenido) y motivó la confirmación temporal de producción.
6. **Tres experimentos de feature engineering, probados y descartados por
   impacto negativo medido** (no por intuición): interacción explícita
   lluvia/persistencia (-4.8% F1.5), target auxiliar de stacking (-16%),
   índice bioclimático combinado (-1.5%). Los tres se revirtieron del código
   de producción tras medir el resultado.

Detalle completo de cada experimento, con números exactos, en
`BITACORA_EXPERIMENTOS.txt`. La guía para que un par externo reproduzca estos
resultados está en `validación_guide.md`.

## 5. Despliegue (Deployment)

- Backend FastAPI (`app/`) que sirve el modelo vía `/api/v1/predict/bulk`.
- Calibración de umbral operativo: no se usó el óptimo automático de F-beta
  sin más contexto, sino que se ancló a una meta operativa explícita
  (recall≈0.70, maximizar precision en ese punto).
- Post-procesamiento de "confirmación temporal" (2 semanas consecutivas sobre
  umbral antes de alertar) como capa adicional de control de falsas alarmas,
  evaluada con su propio trade-off medido antes de activarla en producción.
- Frontend con mapa Leaflet + explicabilidad SHAP en dos capas (lenguaje
  natural + detalle técnico), para servir tanto a comunidad como a
  epidemiólogos.

## 6. Monitoreo (Monitoring) — estado actual y qué falta

Este proyecto es un prototipo de concurso, no un sistema en producción real,
así que el monitoreo continuo (reentrenamiento automático, detección de
drift, alertado si el desempeño cae) **no está implementado todavía** — es la
brecha más honesta entre CRISP-ML(Q) completo y el estado actual. Lo que sí
existe como base para construirlo:
- `.github/workflows/ci.yml` corre los tests automáticos en cada cambio.
- El flag `umbral_calibrado` en `metadata_modelo_grave.json` deja explícito
  qué valor está activo y por qué.

Ver `conclusiones.md` para el detalle de esta y otras limitaciones, y qué se
necesitaría para cerrarlas.
