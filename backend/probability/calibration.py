from __future__ import annotations

from typing import Literal
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
import structlog

logger = structlog.get_logger()


class ProbabilityCalibrator:
    """Calibrates raw predictive probabilities into well-calibrated posterior probabilities.
    
    Guarantees that when the model predicts 70% probability, the empirical
    frequency of that outcome occurring is as close to 70% as possible.
    """

    def __init__(self, method: Literal["isotonic", "platt"] = "isotonic"):
        self.method = method
        self.calibrator: IsotonicRegression | LogisticRegression | None = None
        self.is_fitted: bool = False

    def fit(self, raw_probs: np.ndarray, actual_outcomes: np.ndarray) -> ProbabilityCalibrator:
        """Fits calibration curve on out-of-fold predictions.
        
        Args:
            raw_probs: 1D array of uncalibrated probabilities in (0, 1)
            actual_outcomes: 1D binary array (0 or 1)
        """
        p = np.clip(np.asarray(raw_probs, dtype=float), 1e-4, 1.0 - 1e-4)
        y = np.asarray(actual_outcomes, dtype=int)

        if len(p) < 20:
            logger.warning("calibrator_small_sample", count=len(p))

        if self.method == "isotonic":
            # Non-parametric isotonic regression with out-of-bounds clipping
            self.calibrator = IsotonicRegression(y_min=0.01, y_max=0.99, out_of_bounds="clip")
            self.calibrator.fit(p, y)
        elif self.method == "platt":
            # Platt scaling via Logistic Regression on log-odds (logit)
            logits = np.log(p / (1.0 - p)).reshape(-1, 1)
            self.calibrator = LogisticRegression(solver="lbfgs")
            self.calibrator.fit(logits, y)
        else:
            raise ValueError(f"Unknown calibration method: {self.method}")

        self.is_fitted = True
        return self

    def calibrate(self, raw_probs: np.ndarray | float) -> np.ndarray | float:
        """Transforms uncalibrated probabilities into calibrated probabilities."""
        if not self.is_fitted or self.calibrator is None:
            return raw_probs

        is_scalar = isinstance(raw_probs, (int, float))
        p = np.clip(np.atleast_1d(raw_probs).astype(float), 1e-4, 1.0 - 1e-4)

        if self.method == "isotonic":
            calibrated = self.calibrator.predict(p)
        else:
            logits = np.log(p / (1.0 - p)).reshape(-1, 1)
            calibrated = self.calibrator.predict_proba(logits)[:, 1]

        result = np.clip(calibrated, 0.01, 0.99)
        return float(result[0]) if is_scalar else result

    @staticmethod
    def evaluate_calibration(
        predicted_probs: np.ndarray,
        actual_outcomes: np.ndarray,
        n_bins: int = 10,
    ) -> dict[str, float]:
        """Calculates Brier score, log-loss, and expected calibration error (ECE)."""
        p = np.clip(np.asarray(predicted_probs, dtype=float), 1e-6, 1.0 - 1e-6)
        y = np.asarray(actual_outcomes, dtype=int)

        bs = float(brier_score_loss(y, p))
        ll = float(log_loss(y, p))

        # Expected Calibration Error (ECE)
        bins = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        n_total = len(p)

        for i in range(n_bins):
            mask = (p >= bins[i]) & (p < bins[i + 1]) if i < n_bins - 1 else (p >= bins[i]) & (p <= bins[i + 1])
            if np.sum(mask) > 0:
                bin_prob = np.mean(p[mask])
                bin_actual = np.mean(y[mask])
                weight = np.sum(mask) / n_total
                ece += weight * abs(bin_prob - bin_actual)

        return {
            "brier_score": round(bs, 4),
            "log_loss": round(ll, 4),
            "ece": round(ece, 4),
            "sample_size": n_total,
        }
