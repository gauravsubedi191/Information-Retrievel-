import joblib
from pathlib import Path

MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "news_clf.joblib"

# Ensure models folder exists (useful if you plan to save later)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

_model = None

def load_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH.resolve()}")
        payload = joblib.load(MODEL_PATH)
        _model = payload["pipeline"]
    return _model

def classify(text: str) -> str:
    """Classify a single text document into one of the trained categories."""
    model = load_model()
    return model.predict([text])[0]
