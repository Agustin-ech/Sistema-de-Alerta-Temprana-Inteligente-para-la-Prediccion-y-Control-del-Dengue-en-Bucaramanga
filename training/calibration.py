import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import fbeta_score

def calibrar_umbral(X_train_cv, y_train_cv, best_p_dict: dict) -> float:
    tscv = TimeSeriesSplit(n_splits=3)
    oof_probs, oof_targets = np.zeros(len(X_train_cv)), np.zeros(len(y_train_cv))
    mask_oof = np.zeros(len(X_train_cv), dtype=bool)

    for train_idx, val_idx in tscv.split(X_train_cv):
        X_tr, X_va = X_train_cv.iloc[train_idx], X_train_cv.iloc[val_idx]
        y_tr, y_va = y_train_cv.iloc[train_idx], y_train_cv.iloc[val_idx]
        if 1 not in y_tr.values or 1 not in y_va.values: continue
        
        clf_fold = lgb.LGBMClassifier(**best_p_dict)
        clf_fold.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], callbacks=[lgb.early_stopping(10, verbose=False)])
        oof_probs[val_idx] = clf_fold.predict_proba(X_va)[:, 1]
        oof_targets[val_idx] = y_va.values
        mask_oof[val_idx] = True

    oof_probs, oof_targets = oof_probs[mask_oof], oof_targets[mask_oof]
    if len(oof_targets) == 0:
        # Ningún fold tuvo clase positiva en train y validación a la vez (ej. y
        # totalmente desbalanceado o vacío): no hay con qué calibrar, se usa 0.5.
        return 0.5
    umbrales = np.arange(0.05, 0.80, 0.02)  # ⬅ CAMBIO: rango ampliado hacia abajo (antes 0.20–0.80) para confirmar si 0.20 era el óptimo real o un límite de borde
    lista_f = [fbeta_score(oof_targets, (oof_probs >= t).astype(int), beta=1.5, zero_division=0) for t in umbrales]  # ⬅ CAMBIO: beta=2 → beta=1.5
    return umbrales[np.argmax(lista_f)]