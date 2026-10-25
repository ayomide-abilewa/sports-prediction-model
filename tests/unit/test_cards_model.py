from __future__ import annotations

import numpy as np
from backend.probability.cards_model import CardsModel


def test_cards_model_standard_and_derby():
    model = CardsModel(dispersion=0.20)

    # Standard match
    std_pred = model.predict_cards("Arsenal", "Fulham", is_derby=False)
    assert std_pred["expected_cards"]["total"] > 0

    ou35 = std_pred["totals"]["over_under_3.5"]
    assert np.isclose(ou35["over"] + ou35["under"], 1.0, atol=1e-3)

    # Derby match has heightened card expectations
    derby_pred = model.predict_cards("Arsenal", "Tottenham", is_derby=True)
    assert derby_pred["expected_cards"]["total"] > std_pred["expected_cards"]["total"]
    assert derby_pred["derby_factor_applied"] is True
