"""Validated, file-backed configuration for the operational pipeline."""
from dataclasses import dataclass, field
from pathlib import Path
import math
import tomllib

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = dict(coverage=.30, stockout=.20, demand=.15, unmet=.15, supplier=.10, priority=.10)

@dataclass(frozen=True)
class Settings:
    budget: float = 300000.0
    sample_size: int = 1000
    random_seed: int = 42
    model_threads: int = 4
    future_holiday_flag: int = 0
    commercial_policy: str = "carry_forward"
    artifact_dir: str = "outputs/production"
    weights: dict = field(default_factory=lambda: WEIGHTS.copy())

    def __post_init__(self):
        if not math.isfinite(self.budget) or self.budget < 0:
            raise ValueError("budget must be finite and nonnegative")
        for name in ("sample_size", "model_threads"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.random_seed) is not int or self.random_seed < 0:
            raise ValueError("random_seed must be a nonnegative integer")
        if self.future_holiday_flag not in (0, 1):
            raise ValueError("future_holiday_flag must be 0 or 1")
        if self.commercial_policy != "carry_forward":
            raise ValueError("Only explicit carry_forward commercial inputs are supported")
        if set(self.weights) != set(WEIGHTS) or any(not math.isfinite(v) or v < 0 for v in self.weights.values()):
            raise ValueError("All six nonnegative finite priority weights are required")
        if not math.isclose(sum(self.weights.values()), 1.0, abs_tol=1e-9):
            raise ValueError("Priority weights must sum to one")
        path = (ROOT / self.artifact_dir).resolve()
        if not path.is_relative_to(ROOT) or path == ROOT:
            raise ValueError("artifact_dir must be a subdirectory of the project")

def load_settings(path=None):
    path = Path(path) if path else ROOT / "config/pipeline.toml"
    with path.open("rb") as stream:
        return Settings(**tomllib.load(stream))
