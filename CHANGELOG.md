# Changelog

Registro cronológico de decisiones técnicas y cambios relevantes del ENTRENAMIENTO del modelo de machine learning
proyecto SAT Dengue Grave..

## [2026-07-10]

### Added
- `training/train.py`: al final del entrenamiento ahora se imprime la curva
  Precision-Recall completa (todos los umbrales con recall ≥ 0.60), además
  del `classification_report` ya existente — facilita ver de un vistazo el
  rango completo de trade-offs disponibles antes de fijar el umbral de
  producción, sin tener que graficar aparte.

### Fixed
- `scripts_diagnostico/auditoria_target_base.py`, `diagnostico_retro.py` y
  `encontrar_semana.py` apuntaban a
  `data/epidemiological_data_bucaramanga_processed_dengue_grave1.xlsx`, que
  ya no existe en esa ruta desde la reorganización de `data/` en
  `01_raw/02_intermediate/03_primary/04_model_output` — se corrigió a
  `data/01_raw/epidemiological_data_bucaramanga_processed_dengue_grave1.xlsx`
  (y el fallback de búsqueda de `diagnostico_retro.py` ahora busca
  recursivamente en subcarpetas de `data/`, no solo en la raíz).
- Limpieza de documentación: enlace roto en `README.md` a
  `FUENTES_DE_DATOS.txt` (ya no existe, reemplazado por
  `docs/fuentes_datos.md` desde el `[2026-07-07]`) y oración incompleta en la
  sección de troubleshooting. Referencias a `CLAUDE.md` (documento interno
  que nunca se subió al repo) reemplazadas en `docs/conclusiones.md`,
  `app/api/services.py` y las notebooks 03/04 por citas a los documentos
  reales donde ese contenido sí vive (`BITACORA_EXPERIMENTOS.txt`,
  `CHANGELOG.md`, `docs/conclusiones.md`).

### Verified
- Se ejecutaron de punta a punta las 5 notebooks (`jupyter nbconvert
  --execute`), `python -m training.train` completo y `python -m pytest
  tests/` antes de subir el proyecto. El pipeline es reproducible: el
  reentrenamiento dio ROC-AUC=0.7907 (documentado: ~0.79) y umbral OOF
  automático 9.0% (documentado en `validación_guide.md`: ~0.09) — coincide
  con lo esperado. Los artefactos de producción (`scripts/*.pkl/.json`) no
  se tocaron: el reentrenamiento de verificación se hizo sobre una copia y
  se restauró el estado original después.
- **Corregido**: `training/calibration.py` — `calibrar_umbral()` lanzaba
  `ValueError` en vez de devolver un umbral por defecto cuando ningún fold
  de `TimeSeriesSplit` tenía clase positiva en train y validación a la vez
  (ej. `y` totalmente desbalanceado). Ahora devuelve `0.5` en ese caso.
  Detectado porque `pytest tests/` fallaba.
- **Corregido**: `training/feature_engineering.py` — el merge final
  (`crear_features`, paso 4) no protegía contra que `df_clima` trajera su
  propia columna `nom_upgd` (hoy no la trae porque el clima es a nivel
  ciudad, pero nada lo garantizaba en el código): de ocurrir, pandas la
  duplicaba en `nom_upgd_x`/`nom_upgd_y` en vez de fallar de forma clara.
  Ahora se descarta explícitamente antes del merge. No cambia ninguna de
  las 142 features de producción (verificado recreando el panel completo
  tras el fix).
- **Corregido**: la ficha técnica de `README.md` y el resumen de
  `BITACORA_EXPERIMENTOS.txt` mostraban `F1.5 = 0.7081` junto a
  `precision = 0.583, recall = 0.700` como si fueran del mismo punto de
  operación — son de dos puntos distintos: 0.7081 es el F1.5 **sin**
  confirmación temporal (coincide con `precision=0.513, recall=0.852`,
  ver experimento 9). El F1.5 real para `precision=0.583, recall=0.700`
  (el punto de producción final, con confirmación temporal) es **0.659**,
  ya corregido en ambos documentos.

## [2026-07-07]

### Added
- Estructura de repositorio alineada a la plantilla del concurso: `RECURSOS/`,
  `docs/`, `notebooks/`, `reports/`, `.github/workflows/ci.yml` (corre
  `pytest tests/`), `README.md` (ficha técnica + instalación, reemplaza a
  `README_RESCATE.txt`), `LICENSE` (MIT).
- `docs/` completo: `planteamiento_problema.md`, `architecture.md` (diagrama
  Mermaid del pipeline completo), `data_dictionary.md` (20 variables más
  importantes de las 142, basado en `EXPLICACION_VARIABLES_MODELO.txt`),
  `marco_metodologico.md` (CRISP-ML(Q) mapeado a las fases reales ya
  documentadas en `BITACORA_EXPERIMENTOS.txt` y este changelog),
  `fuentes_datos.md` (reemplaza al
  `FUENTES_DE_DATOS.txt` de la raíz, mismo contenido con pendiente de
  completar enlaces de datos.gov.co), `conclusiones.md` (hallazgos,
  limitaciones honestas, próximos pasos) y `validación_guide.md` (pasos
  concretos para que un par externo reproduzca los resultados).
- `notebooks/03_analisis_descriptivo.ipynb`: reconstruye el panel de
  entrenamiento con los mismos módulos de `training/`, estadísticas básicas,
  distribución del target, series de tiempo de casos y matriz de correlación
  de las variables clave.
- `notebooks/05_reportes_automaticos.ipynb`: función parametrizable
  `generar_reporte_upgd()` que produce, para cualquier UPGD/año/semana,
  probabilidad de intervención, nivel de riesgo y factores SHAP explicativos,
  guardando cada reporte generado en `reports/`.
- `notebooks/04_modelo_predictivo.ipynb`: entrena un LightGBM simple (sin
  Optuna, hiperparámetros fijos, `scale_pos_weight` por heurística) sobre el
  mismo split temporal que usa producción, con validación básica
  (`classification_report`, matriz de confusión, curvas ROC y
  Precision-Recall), y lo compara al final contra el modelo optimizado de
  producción sobre el mismo test set — deja explícito que la mayor parte de
  la señal viene de la ingeniería de variables, y que la diferencia real la
  hace la calibración de umbral, no el tuning de hiperparámetros en sí.
- `scripts_diagnostico/`: se movieron ahí los scripts exploratorios sueltos
  que estaban en la raíz (`auditoria_target_base.py`, `diagnostico_retro.py`,
  `encontrar_semana.py`, `test_retro.py`), con sus rutas corregidas para
  funcionar desde la nueva ubicación. `test_retro.py` además se actualizó:
  usaba `construir_dataframe`, una función ya renombrada/reescrita en
  `services.py`, y no normalizaba a minúsculas las columnas del excel crudo
  (por lo que casi todas las features llegaban en 0) — ambos bugs quedaron
  corregidos con una reconstrucción local de la fila, sin tocar `app/`.

## [2026-07-06]

### Added
- Confirmación temporal: la alerta final solo se emite si dos semanas
  consecutivas superan el umbral (`CONFIRMACION_TEMPORAL_ACTIVA` en
  `app/api/services.py`). Precision sube de 0.513 a 0.560, recall baja de
  0.852 a 0.791.
- Reentrenamiento con 100 trials de Optuna (antes 30) y rango de búsqueda
  de umbral ampliado de `0.20-0.80` a `0.05-0.80` en `calibration.py`.
- Umbral de producción fijado en **0.12** (recall≈0.70 fijo, mejor
  precision posible en ese punto: 0.583).
- Frontend: buscador de UPGD por nombre, selector de semana
  epidemiológica, leyenda de 4 niveles de riesgo (0-25/26-50/51-75/76-100),
  ícono de alerta real (⚠) independiente del color de riesgo, indicadores
  de carga (spinner) y notificaciones tipo toast en vez de `alert()`
  nativo.
- Explicabilidad SHAP en dos capas: oración en lenguaje natural + detalle
  técnico (nombre real de variable + valor) para balancear comunidad y
  epidemiólogos.
- `FUENTES_DE_DATOS.txt`: trazabilidad de los conjuntos de datos
  integrados, para el criterio "Uso de datos abiertos" del concurso.

### Fixed
- Color del círculo en el mapa contradecía el nivel de riesgo del popup
  (ahora ambos derivan siempre de `contexto.color_hex`).
- `vecinos_alerta_prom` y otras variables aparecían sin traducir en el
  panel de explicabilidad (diccionario semántico expandido).
- `/api/v1/predict/bulk` fallaba el lote completo si una sola UPGD daba
  error; ahora los errores se recolectan por ítem sin abortar el resto.

### Removed
- Slider de "umbral de acción" ajustable por el usuario en el frontend, y
  el ícono de bandera asociado — decisión de equipo (censo) de operar
  siempre con el umbral fijo calibrado de 0.12.

### Validated (sin cambios de código, resultados documentados)
- Verificación de que `persistencia_alerta_8` no tiene leakage temporal
  (ventanas pasado/futuro no se solapan; ablación: -0.4% F1.5 relativo).
- Baseline ingenuo vs. modelo: LightGBM supera la mejor regla fija en
  ~42% relativo de F1.5, con recall 0.852 vs. ~0.43 de las reglas.
- CCF empírico confirma el diseño de lags ya usado (lluvia → 4 semanas,
  temperatura → contemporánea).
- Análisis SHAP de falsos positivos: el modelo confunde "condiciones
  climáticas favorables" con "brote ya en curso" cuando falta momentum
  epidémico sostenido.
- Tres experimentos de feature engineering probados y descartados por
  impacto negativo en F1.5: interacción explícita lluvia/persistencia
  (-4.8%), target auxiliar de stacking (-16%), índice bioclimático
  combinado (-1.5%). Ninguno se adoptó.

## [2026-07-05 y anteriores]

### Added
- Pipeline modular de entrenamiento (`training/`) orquestado por
  `train.py`: carga, preprocesamiento, canal endémico, target, feature
  engineering, optimización (Optuna + LightGBM), calibración de umbral,
  entrenamiento, exportación de artefactos, SHAP.
- Backend FastAPI (`app/`) con endpoint `/api/v1/predict/bulk`.
- Frontend con mapa Leaflet y panel de explicabilidad SHAP.
- `scale_pos_weight` como hiperparámetro buscable por Optuna (reemplazando
  `is_unbalance=True` fijo); `beta=1.5` en el F-beta score en vez de
  `beta=2`, para balancear mejor precision y recall.

### Fixed (crítico)
- **Data leakage de identidad de ubicación**: el modelo dependía de
  `nom_upgd`, `densidad_poblacional`, `crecimiento_poblacional`,
  `incremento_habitantes`, `densidad_delta`. Detectado por ROC-AUC alto
  con F2 mediocre y SHAP con valores no continuos en variables
  categóricas. Ablación confirmó que excluirlas solo cuesta ~11% de F2
  relativo (caída moderada, no catastrófica) — se excluyen de forma
  permanente.
- Migración de dataset por caso individual a panel espacio-temporal
  (UPGD × semana epidemiológica), lo que requirió reescribir feature
  engineering y corregir folds de `TimeSeriesSplit`.
- `reconstruir_dataframe()` en `services.py` lanzaba `KeyError` por
  columnas de identidad que ya no existen en el modelo entrenado.
