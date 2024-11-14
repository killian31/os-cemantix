# download_model.py
import os
import requests

MODEL_URL = (
    "https://embeddings.net/embeddings/frWac_no_postag_no_phrase_700_skip_cut50.bin"
)
MODEL_PATH = "models/frWac_no_postag_no_phrase_700_skip_cut50.bin"


def download_model():
    if not os.path.exists(MODEL_PATH):
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        print("Downloading the model...")
        response = requests.get(MODEL_URL, stream=True)
        with open(MODEL_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print("Model downloaded.")
    else:
        print("Model already exists.")


if __name__ == "__main__":
    download_model()
