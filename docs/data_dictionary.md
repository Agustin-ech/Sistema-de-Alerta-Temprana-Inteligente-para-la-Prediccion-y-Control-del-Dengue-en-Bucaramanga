# Diccionario de datos

El modelo final usa **142 variables** de entrada (ver
`scripts/metadata_modelo_grave.json` → `features_ordenadas` para la lista
completa). Este documento cubre, en detalle, las **20 más importantes según
SHAP** — el mínimo pedido por la rúbrica del concurso es de 10 a 20 variables,
así que esta tabla ya cumple ese criterio por sí sola, y el modelo lo supera
ampliamente en variables totales. La versión completa y con más contexto
narrativo está en `EXPLICACION_VARIABLES_MODELO.txt` (raíz del proyecto).

## Convenciones usadas en todo el panel

- **Unidad de análisis**: una fila = una UPGD en una semana epidemiológica.
- **"Ventana de N semanas"**: agregación (promedio, suma o desviación
  estándar) sobre las **N semanas anteriores** a la evaluada — nunca incluye
  la semana actual ni el futuro, para evitar leakage temporal.
- **Canal endémico**: cada semana se clasifica comparando sus casos contra la
  mediana y el percentil 75 históricos de *esa misma semana epidemiológica* en
  años previos de la misma UPGD:
  - Nivel 0 (verde): casos ≤ mediana histórica.
  - Nivel 1 (amarillo / alerta): mediana < casos ≤ percentil 75.
  - Nivel 2 (rojo / brote): casos > percentil 75.

## Variable objetivo

| Variable | Tipo | Descripción |
|---|---|---|
| `target_intervencion` | binaria (0/1) | 1 si en alguna de las próximas 4 semanas se cumple: (A) se alcanza nivel 2/brote, o (B) ≥3 de 4 semanas siguientes en nivel 1 o 2, o (C) 2 semanas consecutivas en nivel 1 o 2. Ver detalle completo en `EXPLICACION_VARIABLES_MODELO.txt`. |

## Grupo 1 — Carga epidémica reciente y persistencia del brote

Las variables más influyentes del modelo: reflejan que un brote tiene inercia
y se sostiene varias semanas, no aparece de golpe.

| Variable | Tipo | Descripción |
|---|---|---|
| `media_casos_4` | continua | Promedio de casos en las 4 semanas anteriores. |
| `casos_lag_52` | entera | Casos hace exactamente 52 semanas (mismo periodo, año anterior) — memoria estacional/interanual. |
| `persistencia_alerta_8` | entera (0-8) | De las últimas 8 semanas, cuántas estuvieron en nivel de alerta (≥ mediana histórica). |
| `std_casos_4` | continua | Variabilidad de casos en las últimas 4 semanas — un brote iniciando suele ser más inestable que un periodo endémico estable. |
| `persistencia_alerta_6` | entera (0-6) | Igual que la anterior, ventana de 6 semanas. |
| `casos_lag_4` | entera | Casos hace 4 semanas — coincide con la ventana causal lluvia→caso notificado (3-6 semanas, ver `planteamiento_problema.md`). |
| `casos_lag_1` | entera | Casos de la semana inmediatamente anterior. |
| `persistencia_alerta_4` | entera (0-4) | Igual patrón, ventana de 4 semanas. |
| `persistencia_alerta_3` | entera (0-3) | Igual patrón, ventana de 3 semanas. |

## Grupo 2 — Contagio espacial

| Variable | Tipo | Descripción |
|---|---|---|
| `vecinos_alerta_prom` | continua (0-1) | Promedio de cuántas de las 3 UPGD geográficamente más cercanas (distancia real en km) estuvieron en alerta la semana anterior. Puesto 6 de 142 en importancia — confirma que la dimensión espacial aporta señal real más allá de lo temporal. |

## Grupo 3 — Clima: precipitación

| Variable | Tipo | Descripción |
|---|---|---|
| `precipitacion_max10min_rollmean8` | continua | Promedio, últimas 8 semanas, de la lluvia máxima en un lapso de 10 minutos — captura aguaceros intensos, más relevantes para criaderos por encharcamiento que la lluvia acumulada suave. |
| `precipitacion_std_rollmean8` | continua | Variabilidad de la lluvia en las últimas 8 semanas — lluvia irregular (secas y luego aguaceros) favorece más al vector que la lluvia constante. |

## Grupo 4 — Clima: temperatura

| Variable | Tipo | Descripción |
|---|---|---|
| `temp_rango_4sem` | continua | Amplitud térmica (máx-mín) promedio, últimas 4 semanas — afecta desarrollo larvario y supervivencia del mosquito adulto. |
| `grados_dia_acum` | continua | "Grados-día" acumulados sobre 16°C (umbral biológico de referencia) — proxy entomológico estándar de velocidad de desarrollo del mosquito y del periodo de incubación extrínseco del virus. |
| `temp_media_6sem` | continua | Temperatura media, últimas 6 semanas. |
| `temp_max_4sem` | continua | Temperatura máxima promedio, últimas 4 semanas. |
| `temperatura_std_rollmean8` | continua | Variabilidad de temperatura, últimas 8 semanas (cambios bruscos de clima). |
| `temperatura_std_rollmean4` | continua | Igual, ventana de 4 semanas. |

## Grupo 5 — Estacionalidad del calendario

| Variable | Tipo | Descripción |
|---|---|---|
| `semana_sin`, `semana_cos` | continua | Codificación cíclica de la semana del año (par seno/coseno) para que la semana 52 y la semana 1 queden matemáticamente cerca, en vez de lejos como números crudos. Permite aprender estacionalidad general (lluvias, vacaciones, movilidad) independiente del clima puntual del año. |

## Variables excluidas deliberadamente (data leakage)

Estas 5 variables se identificaron con **data leakage de identidad de
ubicación** (el modelo memorizaba qué UPGD era cuál en vez de aprender
dinámica epidemiológica real) y quedan excluidas de forma permanente.

| Variable | Por qué se excluyó |
|---|---|
| `nom_upgd` | Identidad directa de la institución. |
| `densidad_poblacional` | Aparecía con SHAP hasta +7.5 — desproporcionado frente a cualquier variable dinámica. |
| `crecimiento_poblacional` | Estática por UPGD, actúa como proxy de identidad. |
| `incremento_habitantes` | Lo mismo. |
| `densidad_delta` | Lo mismo. |

## Dónde ver las 142 variables completas

`scripts/metadata_modelo_grave.json` → clave `features_ordenadas` tiene la
lista completa en el orden exacto que espera el modelo. La mayoría son
variantes sistemáticas de las de arriba (lags `_L1` a `_L8`, `RollMean2/4/8`,
`RollSum2/4/8`, `Std`) aplicadas a cada variable cruda de precipitación y
temperatura — ver `feature_engineering.py` para la lógica de generación.
