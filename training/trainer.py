import lightgbm as lgb

def entrenar_modelo(X_train_cv, y_train_cv, best_p_dict: dict) -> lgb.LGBMClassifier:
    modelo = lgb.LGBMClassifier(**best_p_dict)
    modelo.fit(X_train_cv, y_train_cv)
    return modelo