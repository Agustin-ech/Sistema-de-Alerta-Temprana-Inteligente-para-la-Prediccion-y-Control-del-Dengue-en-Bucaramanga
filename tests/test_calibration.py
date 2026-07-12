import pandas as pd

from training.calibration import calibrar_umbral


def test_calibrar_umbral_fallback_when_no_positive_class_in_folds():
    X = pd.DataFrame({"feature": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]})
    y = pd.Series([0, 0, 0, 0, 0, 0], name="target")

    umbral = calibrar_umbral(X, y, {"objective": "binary", "is_unbalance": True})

    assert umbral == 0.5
