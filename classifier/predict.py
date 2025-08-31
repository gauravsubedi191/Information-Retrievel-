# predict.py
import argparse
import joblib
from pathlib import Path
from typing import Tuple, List

# Define the path to the trained model.
MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "news_clf.joblib"

# Use a global variable to cache the loaded model and labels.
# This prevents the model from being reloaded from disk on every prediction call.
_model_cache = None


def load_model() -> Tuple:
    """Load the trained model pipeline and labels from disk."""
    global _model_cache
    if _model_cache is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH.resolve()}")

        # Load the pipeline and labels from the joblib file
        payload = joblib.load(MODEL_PATH)
        pipeline = payload.get("pipeline")
        labels = payload.get("labels")

        if not pipeline or not labels:
            raise ValueError("Invalid model payload. Missing 'pipeline' or 'labels' keys.")

        _model_cache = (pipeline, labels)
        print("Successfully loaded model and labels.")

    return _model_cache


def classify(text: str) -> str:
    """
    Predict the category of a single input text using the loaded model.
    """
    model, labels = load_model()
    # The model's predict method returns a list of predictions.
    # We take the first element since we're only passing one text.
    predicted_label = model.predict([text])[0]
    return predicted_label


def main():
    """
    Main function to handle command-line arguments and run the classification.
    """
    parser = argparse.ArgumentParser(description="Classify a document into Politics, Business, or Health.")
    parser.add_argument("text", type=str, nargs="+",
                        help="Text/document to classify (wrap in quotes if it contains spaces).")
    args = parser.parse_args()

    # Join the arguments to form the full input text.
    input_text = " ".join(args.text)

    try:
        category = classify(input_text)
        print(f"\nInput: {input_text}\nPredicted Category: {category}")
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Please ensure you have run 'train_classifier.py' first to create the model file.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Ensure the model file is valid and not corrupted.")


if __name__ == "__main__":
    main()
