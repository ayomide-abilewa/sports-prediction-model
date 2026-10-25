from __future__ import annotations

import numpy as np
from backend.probability.corners_model import CornersModel


def test_corners_model_prediction():
    model = CornersModel(dispersion=0.15)
    pred = model.predict_corners("Arsenal", "Chelsea")

    assert "expected_corners" in pred
    exp = pred["expected_corners"]
    assert exp["home"] > 0
    assert exp["away"] > 0
    assert exp["total"] == round(exp["home"] + exp["away"], 2)

    totals = pred["totals"]
    assert "over_under_9.5" in totals
    ou95 = totals["over_under_9.5"]
    assert np.isclose(ou95["over"] + ou95["under"], 1.0, atol=1e-3)
    assert 0.0 < ou95["over"] < 1.0
