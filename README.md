#  Sistema de Alerta Temprana Inteligente para la Predicción y Control del Dengue en Bucaramanga

Sistema de Alerta Temprana (SAT) de brotes de dengue grave para Bucaramanga,Colombia. Predice, por UPGD (institución de salud) y semana epidemiológica,
la probabilidad de que se requiera intervención en las próximas 4 semanas,
combinando vigilancia epidemiológica (SIVIGILA), clima (precipitación y
temperatura) y contagio espacial entre UPGDs vecinas.

## Ficha técnica

| | |
|---|---|
| Problema | Predicción temprana de brotes de dengue grave a nivel de UPGD |
| Técnica de IA | LightGBM (gradient boosting), tuning con Optuna, explicabilidad con SHAP |
| Datos integrados | SIVIGILA (casos), precipitación, temperatura, demografía, geolocalización de 17 UPGD |
| Variables de entrada | 142 features (autoregresivas, climáticas, de contagio espacial, estacionales) |
| Validación | TimeSeriesSplit, ablación de leakage, baseline ingenuo, CCF empírico |
| Resultado (test, últimas 52 semanas) | F1.5 = 0.659, precision = 0.583, recall = 0.700 (umbral = 0.12, con confirmación temporal de 2 semanas) — F1.5 = 0.7081 es la cifra *sin* confirmación temporal (ver `BITACORA_EXPERIMENTOS.txt`) |
| Backend | FastAPI (`app/`) — `/api/v1/predict/bulk` y `/api/v1/explain` |
| Frontend | Mapa Leaflet con explicabilidad SHAP (`frontend/`) |

Ver [BITACORA_EXPERIMENTOS.txt](BITACORA_EXPERIMENTOS.txt) para el detalle de
cada experimento y decisión de diseño, y [docs/fuentes_datos.md](docs/fuentes_datos.md)
para la trazabilidad de los conjuntos de datos usados.

## Instalación (Windows)

Requisito: Python 3.13 (probado y funcionando con esta versión exacta;
versiones más nuevas pueden dar problemas de compatibilidad con algunas
librerías). Descargalo de https://www.python.org/downloads/release/python-31313/
("Windows installer (64-bit)") si no lo tenés. Al instalar, marcá la
casilla "Add python.exe to PATH".

Verificar versión instalada (en PowerShell o CMD, desde cualquier lado):

```
py -3.13 --version
```

1. Crear el entorno virtual (desde la carpeta raíz del proyecto, la que
   tiene este archivo adentro):

   ```
   py -3.13 -m venv venv
   ```

2. Activar el entorno:

   - PowerShell: `venv\Scripts\Activate.ps1`
   - CMD: `venv\Scripts\activate.bat`

   Si PowerShell da error de "ejecución de scripts deshabilitada", correr
   una sola vez como administrador:

   ```
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```

   Vas a ver `(venv)` al inicio de la línea de comandos si funcionó.

3. Instalar las librerías (con el venv ya activado):

   ```
   pip install -r requirements.txt
   ```

4. Ejecutar SIEMPRE desde la raíz del proyecto (no entrar a la carpeta
   `app/`), porque los imports internos son absolutos:

   ```
   # Entrenar el modelo (opcional, ya viene uno entrenado en scripts/)
   python -m training.train

   # Levantar el backend
   uvicorn app.main:app --reload
   ```

   El backend queda en http://127.0.0.1:8000 y la documentación
   interactiva de la API en http://127.0.0.1:8000/docs.

5. Frontend: abrir `frontend/index.html` directamente en el navegador
   (con el backend corriendo en paralelo en otra terminal).

### Nota para Linux/Mac

```
python3 -m venv venv
source venv/bin/activate   # o venv/bin/activate.fish si usas fish
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Si algo no arranca, mira [BITACORA_EXPERIMENTOS.txt](BITACORA_EXPERIMENTOS.txt)
para el historial completo de decisiones técnicas del proyecto, y
[CHANGELOG.md](CHANGELOG.md) para el resumen cronológico de qué se probó y
qué quedó en producción.

## Datos

Las carpetas `data/` y `datos_extraidos/`, y el archivo
`consolidado_enfermedades_bucaramanga.xlsx`, **no están en este repositorio**
porque suman ~1.5 GB (GitHub bloquea archivos de más de 100 MB y no es buena
práctica versionar datasets pesados junto al código).

Para conseguirlos:

1. Descarga el .zip desde este enlace de Google Drive:
   **https://drive.google.com/file/d/1v5vAxgcQS33plxfy4hNa3ri5h-Dt2SFh/view?usp=sharing**
2. Descomprimelo en la raíz del proyecto (la misma carpeta donde está este
   README), de forma que quede:

   ```
   IA_PREDICTIVA/
   ├── data/
   ├── datos_extraidos/
   └── consolidado_enfermedades_bucaramanga.xlsx
   ```

3. Listo, el resto del proyecto (entrenamiento, backend) los va a encontrar
   automáticamente en esas rutas.

## Estructura del repositorio

```
app/                Backend FastAPI (endpoints, servicios de inferencia, geolocalización)
app/config/         Configuración centralizada (rutas de modelo, metadata, geo)
training/           Pipeline de entrenamiento modular, orquestado por training/train.py
frontend/           Mapa Leaflet + panel de explicabilidad SHAP
data/               Datasets fuente e intermedios (no está en el repo, ver "Datos" más abajo)
scripts/            Artefactos del modelo entrenado (pkl, metadata, gráfico SHAP)
scripts_diagnostico/ Scripts sueltos de auditoría/diagnóstico del target y del pipeline
tests/              Pruebas unitarias (calibración, feature engineering)
docs/               Documentación técnica ampliada
notebooks/          Notebooks de exploración y análisis
reports/            Figuras y reportes generados
RECURSOS/           Material de presentación (pptx, pdf, imágenes)
.github/workflows/  CI (corre pytest tests/ en cada cambio)
```
