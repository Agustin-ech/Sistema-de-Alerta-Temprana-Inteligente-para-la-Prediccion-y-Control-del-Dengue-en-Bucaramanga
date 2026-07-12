# Guía de validación para pares

Esta guía es para alguien **externo al equipo** (un jurado, un par evaluador,
un nuevo integrante) que quiera verificar por su cuenta que los resultados
documentados en `CHANGELOG.md` y `BITACORA_EXPERIMENTOS.txt` son reales y
reproducibles — no solo confiar en el texto.

## 0. Antes de empezar

Instalar el proyecto según `README.md` (sección "Instalación"). Todo lo que
sigue asume que ya puedess correr `python -m training.train` y
`uvicorn app.main:app --reload` desde la raíz del proyecto.

## 1. Verificar que el modelo entrenado corresponde a lo documentado

```bash
python -m training.train
```

Al final del entrenamiento se imprime un `classification_report` y la curva
precision-recall completa en test (últimas 52 semanas). Comparar contra:
- F1.5 documentado: 0.7081 (antes de confirmación temporal/umbral fijo).

⚠️ Nota importante: `training/calibration.py` recalcula automáticamente un
umbral óptimo OOF (valor de referencia de una corrida anterior: ~0.09;
puede variar levemente entre corridas por la aleatoriedad de Optuna), que
**no es** el umbral de producción (0.12) — ese
se fija a mano en `scripts/metadata_modelo_grave.json` porque considera
además la confirmación temporal y la meta de recall=0.70. Si vuelves a entrenar, el JSON exportado va a traer el umbral
automático, no el de producción — no es un bug, es una decisión documentada.

## 2. Verificar que no hay data leakage de identidad

```bash
python -m pytest tests/
```

Para reproducir la ablación completa (más pesado, no es parte del test suite
automático): editar la lista `EXCLUIR` en `training/train.py` para *incluir*
de vuelta las 5 variables de identidad (`nom_upgd`, `densidad_poblacional`,
`crecimiento_poblacional`, `incremento_habitantes`, `densidad_delta`),
reentrenar, y comparar el F2/F1.5 contra el modelo sin ellas. La caída
documentada al excluirlas es moderada (~11% relativo de F2) — si al incluirlas
el ROC-AUC sube mucho pero el F-beta prácticamente no mejora, es la misma
señal de alerta de leakage que originalmente detectó el equipo.

## 3. Verificar el baseline ingenuo

El código de las 3 reglas fijas comparadas contra el modelo (documentadas en
`BITACORA_EXPERIMENTOS.txt`) no vive en un archivo de
producción — fue un experimento ad-hoc. Para reproducirlo: sobre el panel de
test (últimas 52 semanas), calcular:
- Regla A: `alerta_binaria_pasada` de la semana actual == 1 → predecir 1.
- Regla B: `alerta_lag_1` == 1 → predecir 1.
- Regla C: `persistencia_alerta_4 >= 2` → predecir 1.

Y comparar el F1.5 de cada una contra `target_intervencion` real, contra los
valores documentados (0.4996, 0.4758, 0.4918 respectivamente).

## 4. Verificar los notebooks de análisis

```bash
jupyter nbconvert --to notebook --execute notebooks/03_analisis_descriptivo.ipynb
jupyter nbconvert --to notebook --execute notebooks/05_reportes_automaticos.ipynb
```

Ambos notebooks reconstruyen el panel de entrenamiento invocando los mismos
módulos de `training/` (no una copia paralela de la lógica) — si el pipeline
de producción cambia, los notebooks reflejan el cambio automáticamente en la
próxima ejecución. Deben correr sin errores y regenerar todas las figuras.

## 5. Verificar el backend en vivo

```bash
uvicorn app.main:app --reload
```

Abrir `http://127.0.0.1:8000/docs` y probar `/api/v1/predict/bulk` con una
UPGD y semana real del histórico (ver `notebooks/05_reportes_automaticos.ipynb`
para ejemplos de combinaciones UPGD/año/semana con datos disponibles). La
respuesta debe incluir tanto `alerta` (con confirmación temporal) como
`alerta_cruda` (sin ella) — comparar ambas.

## 6. Qué preguntar si algo no cuadra

- Si el F1.5 reproducido difiere bastante del documentado: revisar primero
  si `scripts/metadata_modelo_grave.json` tiene el `umbral_calibrado` fijado
  en 0.12 o si quedó el valor automático de una corrida reciente de
  `train.py` (ver punto 1).
- Si el split temporal da números raros: confirmar que el corte de test son
  las últimas 52 semanas por **(año, semana) calendario**, no por posición de
  fila — un corte por fila mezclaría UPGDs de forma incorrecta (ver el
  comentario en `training/train.py` sobre este punto exacto).
