import json
import pickle
from pathlib import Path

def exportar_artefactos(modelo, features: list, umbral: float):
    # Forzar escritura en la carpeta scripts/ un nivel arriba
    base_dir = Path(__file__).resolve().parent.parent / "scripts"
    base_dir.mkdir(exist_ok=True)
    
    with open(base_dir / 'modelo_final_dengue_grave.pkl', 'wb') as f:
        pickle.dump(modelo, f)
        
    with open(base_dir / 'metadata_modelo_grave.json', 'w') as f:
        json.dump({
            'features_ordenadas': features,
            'umbral_calibrado': float(umbral)
        }, f, indent=4)