## Conjuntos de datos integrados (`data/dataset.xlsx` / `data/dataset_limpio.xlsx`)

El panel espacio-temporal (UPGD × semana epidemiológica) que alimenta el
modelo se construyó cruzando varios dominios de datos distintos:

| # | Dominio | Qué aporta | Fuente |
|---|---|---|---|
| 1 | Vigilancia epidemiológica (SIVIGILA) | Casos de dengue reportados por UPGD y semana epidemiológica en Bucaramanga | https://portalsivigila.ins.gov.co/Paginas/Buscador.aspx# |
| 2 | Clima — precipitación | Series semanales de precipitación (total, máxima en 10 min, frecuencia) para Bucaramanga | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Precipitaciones/ksew-j3zj |
| 3 | Clima — temperatura | Series semanales de temperatura (media, mínima, máxima, rango) para Bucaramanga | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Temperatura-Ambiente-del-Aire/sbwg-7ju4/about_data |
| 4 | Demografía / población | Población, densidad y crecimiento poblacional por UPGD — usadas solo para el análisis de ablación de leakage, **excluidas del modelo final** (ver `data_dictionary.md`) | https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion |
| 5 | Geolocalización de instituciones | Coordenadas (lat/lng) de las 17 UPGD, usadas para el mapa y para calcular el contagio espacial (`vecinos_alerta_prom`) | app/geo/upgd_coordenadas.json |

## Artefactos intermedios (no son fuentes nuevas)

`datos_extraidos/` y `consolidado_enfermedades_bucaramanga.xlsx` (raíz del
proyecto) **no son fuentes de datos adicionales**: son la extracción cruda
del ZIP `data/datos_al_ecosistema.zip` (SIVIGILA, dominio #1 de la tabla) y
su consolidado, generados y regenerables por
`notebooks/02_limpieza_transformacion.ipynb`. Se conservan en el repo como
checkpoint intermedio, no como insumo independiente del pipeline.