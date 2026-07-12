# Planteamiento del problema

## Contexto

El dengue es endémico en Bucaramanga y sus picos de casos saturan de forma
impredecible la capacidad de respuesta de las instituciones de salud (UPGD —
Unidad Primaria Generadora de Datos). Hoy la vigilancia epidemiológica es
**reactiva**: el sistema SIVIGILA reporta casos ya ocurridos, y la decisión de
intervenir (refuerzo de fumigación, campañas de prevención, alistamiento de
camas) se toma después de que el brote ya es evidente en las cifras.

## El problema concreto

No existe una señal temprana, específica por institución, que anticipe **con
semanas de antelación** qué UPGD va a necesitar intervención — obligando a
que la respuesta de salud pública sea uniforme y reactiva en vez de focalizada
y preventiva.

## Pregunta que responde el proyecto

> Para cada UPGD de Bucaramanga y cada semana epidemiológica, ¿se activará en
> las próximas 1 a 4 semanas una condición de intervención (brote, alerta
> sostenida, o alerta repetida) según criterios inspirados en el INS?

Es deliberadamente **una pregunta binaria de intervención, no una predicción
del número de casos** — un conteo exacto es menos accionable operativamente
que una alerta clara de sí/no sobre la que un equipo de salud pública puede
actuar. Las tres reglas exactas de intervención (brote directo, alerta
sostenida ≥3 de 4 semanas, dos semanas consecutivas en alerta) están detalladas
en `data_dictionary.md` y en `EXPLICACION_VARIABLES_MODELO.txt`.

## Por qué es un problema de IA y no de reglas fijas

Ya se comparó explícitamente al modelo contra 3 reglas fijas sin aprendizaje
("estuvo en alerta esta semana", "estuvo en alerta la semana pasada", "≥2 de
las últimas 4 semanas en alerta") sobre el mismo split temporal. El modelo
LightGBM las supera en ~42% relativo de F1.5, y sobre todo en recall (0.852
vs. ~0.43 de la mejor regla) — evidencia de que hay señal real combinando
clima, estacionalidad y contagio espacial que una regla fija no captura (ver
`BITACORA_EXPERIMENTOS.txt`, experimento de baseline ingenuo).

## Alcance

- **Unidad de análisis**: UPGD × semana epidemiológica (panel espacio-temporal,
  no caso individual).
- **Cobertura geográfica**: 17 UPGD de Bucaramanga con vigilancia continua.
- **Horizonte de predicción**: 1 a 4 semanas hacia adelante.
- **Fuera de alcance explícitamente**: predicción de número exacto de casos,
  predicción a nivel de paciente individual, y expansión a otros municipios
  (el canal endémico y el contagio espacial están calibrados sobre las 17 UPGD
  de Bucaramanga específicamente — ver `architecture.md` para qué se necesitaría
  para escalar a otra ciudad).

## Objetivo de desempeño y por qué se fijó ahí

Tras varias rondas de calibración de umbral, se fijó como meta operativa **recall ≈ 0.70**
(detectar el 70% de las intervenciones reales) maximizando la precision en ese
punto exacto, en vez de perseguir el óptimo automático de F-beta sin más
contexto. La razón: un sistema de alerta con recall bajo es inútil para salud
pública (deja pasar brotes reales), pero un recall de 1.0 sin control de
precisión generaría tantas falsas alarmas que el equipo dejaría de confiar en
el sistema. El punto de operación actual (umbral=0.12, con confirmación
temporal de 2 semanas) da **precision=0.583, recall=0.700** — el mejor balance
encontrado en ese punto de la curva.

## Usuarios y decisión que habilita

- **Equipos de salud pública municipal**: priorizar visitas de control
  vectorial y campañas de prevención hacia las UPGD con alerta activa, en vez
  de repartir recursos de forma pareja.
- **Las propias UPGD**: anticipar necesidad de camas/insumos con 1 a 4 semanas
  de margen en vez de reaccionar cuando el pico ya está ocurriendo.

Ver `conclusiones.md` para limitaciones actuales y qué se necesitaría para
llevar esto de prototipo a herramienta operativa.
