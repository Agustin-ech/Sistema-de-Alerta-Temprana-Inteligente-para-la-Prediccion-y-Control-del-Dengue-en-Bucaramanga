import optuna
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import fbeta_score


def optimizar_modelo(X_train_cv, y_train_cv, n_trials=100):
    
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 400),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.08, log=True),
            'num_leaves': trial.suggest_int('num_leaves', 16, 64),
            'min_child_samples': trial.suggest_int('min_child_samples', 15, 60),
            'subsample': trial.suggest_float('subsample', 0.65, 0.95),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.65, 0.95),
            'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 2.0),
            'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 2.0),
            'scale_pos_weight': trial.suggest_float('scale_pos_weight', 1.0, 15.0),  # ⬅ CAMBIO: reemplaza is_unbalance
            'objective': 'binary',
            'random_state': 42,
            'n_jobs': -1,
            'verbose': -1,
            'force_row_wise': True
        }

        tscv = TimeSeriesSplit(n_splits=5)        # ← Aumentado a 5 splits
        scores_f2 = []
        
        for train_idx, val_idx in tscv.split(X_train_cv):
            X_tr, X_va = X_train_cv.iloc[train_idx], X_train_cv.iloc[val_idx]
            y_tr, y_va = y_train_cv.iloc[train_idx], y_train_cv.iloc[val_idx]

            # Skip si fold no tiene clase positiva
            if y_tr.sum() == 0 or y_va.sum() == 0:
                continue

            clf = lgb.LGBMClassifier(**params)
            
            clf.fit(
                X_tr, y_tr,
                eval_set=[(X_va, y_va)],
                callbacks=[lgb.early_stopping(20, verbose=False)],  # ← Más patience
                eval_metric='auc'
            )
            
            probs_va = clf.predict_proba(X_va)[:, 1]
            
            # Búsqueda fina de umbral
            mejor_f2 = 0
            for th in np.arange(0.25, 0.75, 0.02):   # ← Más fina y amplio rango
                preds = (probs_va >= th).astype(int)
                score = fbeta_score(y_va, preds, beta=1.5, zero_division=0)  # ⬅ CAMBIO: beta=2 → beta=1.5
                if score > mejor_f2:
                    mejor_f2 = score
            
            scores_f2.append(mejor_f2)

        return np.mean(scores_f2) if scores_f2 else 0.0

    # Optuna con pruning (más eficiente)
    study = optuna.create_study(
        direction='maximize',
        sampler=optuna.samplers.TPESampler(seed=42),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=5)
    )
    
    study.optimize(objective, n_trials=n_trials, n_jobs=1)   # ← n_jobs=1 recomendado con LightGBM

    print(f"Mejor F1.5: {study.best_value:.5f}")  # ⬅ CAMBIO: nombre del log actualizado
    print("Mejores parámetros:", study.best_params)
    
    return study.best_params