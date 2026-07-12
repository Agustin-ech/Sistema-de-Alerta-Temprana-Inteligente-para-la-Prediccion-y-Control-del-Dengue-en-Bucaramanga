import os
import pickle
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from app.api.schemas import UpgdInput, ExplainRequest
from app.api.services import predict_upgd, explicar_prediccion, metadata, modelo

app = FastAPI(title="SAT Modular con Soporte SHAP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/predict/bulk")
def prediccion_masiva(payload: List[UpgdInput]):
    if not modelo:
        raise HTTPException(status_code=500, detail="El modelo no se encuentra disponible.")

    features = metadata.get('features_ordenadas', [])
    umbral = metadata.get('umbral_calibrado', 0.5)

    # Si una UPGD puntual no tiene datos para la semana pedida (ej. borde del
    # histórico), no debe tumbar la carga completa de las demás — se omite esa
    # UPGD y se informan los errores aparte para que el frontend pueda avisar.
    resultados = []
    errores = []
    for item in payload:
        try:
            resultados.append(predict_upgd(item, features))
        except (ValueError, RuntimeError) as e:
            errores.append({"upgd": item.nom_upgd, "semana": item.semana, "detalle": str(e)})

    return {"status": "success", "umbral_sugerido_oof": umbral, "data": resultados, "errores": errores}

@app.post("/api/v1/explain")
def obtener_explicabilidad(payload: ExplainRequest):
    if not modelo:
        raise HTTPException(status_code=500, detail="El explicador SHAP no se encuentra disponible.")
    
    features = metadata.get('features_ordenadas', [])
    return explicar_prediccion(payload, features)