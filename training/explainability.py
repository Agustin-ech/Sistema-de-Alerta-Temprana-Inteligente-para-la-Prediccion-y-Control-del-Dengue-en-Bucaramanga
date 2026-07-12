import shap
import matplotlib.pyplot as plt
from pathlib import Path

def generar_shap(modelo, X) -> str:
    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X)
    
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X, show=False)
    
    # Lo guarda de forma organizada
    ruta_grafica = Path(__file__).resolve().parent.parent / "scripts" / "shap_summary.png"
    plt.savefig(ruta_grafica, bbox_inches='tight')
    plt.close()
    return str(ruta_grafica)