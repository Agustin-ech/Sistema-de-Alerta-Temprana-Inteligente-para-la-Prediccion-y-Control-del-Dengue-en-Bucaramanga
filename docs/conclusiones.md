# Conclusiones

## Hallazgos principales

1. **El modelo predice, no solo repite inercia.** Comparado contra 3 reglas
   fijas sin ML sobre el mismo split temporal, LightGBM da F1.5=0.7081 frente
   a un máximo de 0.4996 de la mejor regla — y sobre todo el recall salta de
   ~0.43 a 0.852, evidencia de que el modelo anticipa casos que la sola
   inercia de "ya estaba en alerta" no detecta (ver `BITACORA_EXPERIMENTOS.txt`).
2. **La mayoría de la señal es real, no memorización de identidad.** El
   experimento de ablación que excluyó las 5 variables de identidad/demografía
   mostró una caída moderada (~11% relativo de F2), no un desplome — confirma
   que el modelo aprende dinámica clima-epidemiológica genuina.
3. **El momentum epidémico pesa más que el clima crudo.** Las variables de
   `persistencia_alerta_*` dominan la importancia SHAP muy por encima de
   cualquier variable climática individual — coherente con la epidemiología
   del dengue (un brote tiene inercia) y validado empíricamente, no asumido.
4. **El diseño de lags climáticos (3-6 semanas) ya estaba bien calibrado.**
   El análisis CCF confirmó exactamente el lag=4 semanas ya usado para lluvia,
   sin encontrar ningún error de diseño que corregir.
5. **El sistema sabe distinguir "condiciones para un brote" de "el brote ya
   está pasando".** El análisis de falsos positivos vía SHAP mostró que el
   modelo genera falsas alarmas principalmente cuando hay clima favorable sin
   momentum epidémico sostenido — un patrón biológicamente sensato, que
   motivó la confirmación temporal de 2 semanas en producción.

## Limitaciones actuales (honestas, no minimizadas)

1. **Techo de precision en el punto de operación actual.** Con recall fijo en
   ~0.70, la mejor precision alcanzable con este dataset es ~0.58 — tres
   intentos distintos de mejorar esto vía feature engineering (interacción
   climática, target auxiliar de stacking, índice bioclimático) fallaron
   empíricamente. La conclusión documentada es que subir la precision por
   encima de ese techo requiere **datos nuevos**, no más ingeniería sobre el
   mismo dataset (~8800 filas) — ver "Próximos pasos" más abajo.
2. **No hay monitoreo continuo en producción.** Este es un prototipo de
   concurso: no existe reentrenamiento automático, detección de drift, ni
   alertado si el desempeño real cae respecto al validado offline. Ver
   `marco_metodologico.md` sección 6.
3. **El umbral de producción (0.12) está fijado a mano.** Si se vuelve a
   correr `training/train.py`, `calibrar_umbral()` recalcula automáticamente
   un valor distinto (~0.09, el óptimo OOF puro) que no considera la
   confirmación temporal ni la meta de recall=0.70 — hay que volver a fijarlo
   manualmente en `metadata_modelo_grave.json` tras cada reentrenamiento (o
   resolver esto de fondo ajustando `calibrar_umbral()`, pendiente).
4. **Escala geográfica limitada.** El canal endémico y el contagio espacial
   están calibrados sobre las 17 UPGD de Bucaramanga específicamente (ver
   `architecture.md` para qué se necesitaría para escalar).
5. **Trade-off de la confirmación temporal sin validar con el usuario final.**
   Activar la confirmación de 2 semanas mejora precision a costa de recall
   (menos casos reales detectados) — la decisión se tomó priorizando menos
   volumen operativo, pero está pendiente de confirmar con un equipo de salud
   pública real si ese es el trade-off correcto — ver `CHANGELOG.md`
   [2026-07-06] para las cifras exactas del trade-off medido.

## Próximos pasos (en orden de impacto esperado)

1. **Conseguir datos adicionales** — es la única vía identificada con
   evidencia de que movería la precision por encima del techo actual (~0.58).
   Candidatos: más años de histórico SIVIGILA, datos de fumigación/control
   vectorial ya ejecutado (para no confundir "riesgo" con "riesgo ya mitigado"),
   o cobertura de más UPGD.
2. **Cerrar el monitoreo continuo** — automatizar el chequeo de que el
   desempeño en producción no se degrade respecto al validado, y que
   `calibrar_umbral()` considere la confirmación temporal y la meta de
   recall=0.70 en su propia búsqueda (en vez del ajuste manual actual).
3. **Validar el trade-off de confirmación temporal con un equipo de salud
   pública real** — la decisión actual (5b) es una hipótesis razonable, no
   una validación externa.
