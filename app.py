import os
import random

from flask import Flask, redirect, render_template, request, session, url_for
from gensim.models import KeyedVectors

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Model and cleaned_key_map will be loaded when the application starts
MODEL_PATH = "models/frWac_no_postag_no_phrase_700_skip_cut50.bin"

# Initialize model and cleaned_key_map as None
model = None
cleaned_key_map = None


def load_model(path):
    return KeyedVectors.load_word2vec_format(path, binary=True, unicode_errors="ignore")


def query(word, target_word):
    original_key = cleaned_key_map.get(word)
    if original_key is None:
        return None
    original_target_key = cleaned_key_map.get(target_word)
    return model.similarity(original_key, original_target_key)


def create_cleaned_key_map():
    cleaned_key_map = {
        key.split("_")[0].split("-")[0]: key for key in model.key_to_index
    }
    cleaned_key_map = {
        key: value for key, value in cleaned_key_map.items() if key.isalnum()
    }
    cleaned_key_map = {
        key: value for key, value in cleaned_key_map.items() if "'" not in key
    }
    return cleaned_key_map


def get_interest_words(difficulty="d"):
    try:
        with open(f"data/interest_words_{difficulty}.txt", "r") as f:
            interest_words = [line.strip() for line in f.readlines()]
        return interest_words
    except FileNotFoundError:
        print(f"Data file for difficulty '{difficulty}' not found.")
        return []
    except Exception as e:
        print(f"Error reading interest words file: {e}")
        return []


def get_target_word(mode):
    interest_words = get_interest_words(mode)
    target_word = random.choice(interest_words)
    while target_word not in cleaned_key_map:
        target_word = random.choice(interest_words)
    return target_word


def get_most_similar(target_word):
    most_similar = model.most_similar(cleaned_key_map[target_word], topn=1000)
    most_similar = [
        (key.split("_")[0].split("-")[0], value)
        for key, value in most_similar
        if key != cleaned_key_map[target_word]
    ]
    cleaned_most_similar = {}
    for key, value in most_similar:
        if key not in cleaned_most_similar:
            cleaned_most_similar[key] = value
        elif value > cleaned_most_similar[key]:
            cleaned_most_similar[key] = value
    cleaned_most_similar = sorted(
        cleaned_most_similar.items(), key=lambda x: x[1], reverse=True
    )
    return cleaned_most_similar


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        mode = request.form.get("mode")
        if mode not in ["f", "d"]:
            return render_template("index.html", error="Invalid mode selected.")
        try:
            session["mode"] = mode
            session["target_word"] = get_target_word(mode)
            session["jokers"] = 100
            session["results"] = {}

            # Calculer le max_similarity
            most_similar = get_most_similar(session["target_word"])
            max_similarity = most_similar[0][1]  # Score du mot le plus similaire
            session["max_similarity"] = float(max_similarity)

            return redirect(url_for("game"))
        except Exception as e:
            print(f"Exception in index route: {e}")
            return render_template("index.html", error=str(e))
    return render_template("index.html")


@app.route("/game", methods=["GET", "POST"])
def game():
    if "target_word" not in session:
        return redirect(url_for("index"))

    target_word = session["target_word"]
    jokers = session.get("jokers", 100)
    results = session.get("results", {})
    max_similarity = session.get("max_similarity", 1.0)  # Valeur par défaut à 1.0

    message = ""
    alert_class = ""
    progress_percent = None  # Initialiser à None
    sorted_results = []
    if request.method == "POST":
        word = request.form.get("word").strip()
        if word == "0000":
            return redirect(url_for("result", status="quit"))
        elif word == "5555":
            if jokers == 0:
                message = "Vous n'avez plus de jokers :("
                alert_class = "alert-warning"
            else:
                most_similar = get_most_similar(target_word)
                joker_index = jokers - 1
                if joker_index < len(most_similar):
                    hint_word = most_similar[joker_index][0]
                    similarity = most_similar[joker_index][1]
                    jokers -= 1
                    session["jokers"] = jokers
                    results[hint_word] = float(similarity)
                    session["results"] = results
                    message = f"{hint_word}: {similarity*100:.2f}"
                    # Définir la classe d'alerte en fonction du score
                    if similarity >= 0.25:
                        alert_class = "alert-success"
                    else:
                        alert_class = "alert-secondary"
                else:
                    message = "Plus de mots similaires disponibles."
                    alert_class = "alert-warning"
        elif word == "9999":
            return redirect(url_for("result", status="reveal"))
        else:
            similarity = query(word, target_word)
            if similarity is None:
                message = f"Je ne connais pas le mot {word}."
                alert_class = "alert-danger"
            else:
                if word == target_word:
                    return redirect(url_for("result", status="win"))
                results[word] = float(similarity)
                session["results"] = results

                if similarity >= 0.25:
                    # Calculer le pourcentage de progression
                    min_similarity = 0.25
                    normalized_similarity = (similarity - min_similarity) / (
                        max_similarity - min_similarity
                    )
                    progress_percent = (
                        normalized_similarity * 99.8 + 0.1
                    )  # Entre 0.1% et 99.9%
                    progress_percent = max(
                        0.1, min(progress_percent, 99.9)
                    )  # S'assurer que c'est entre 0.1 et 99.9

                    progress_percent = round(
                        progress_percent, 2
                    )  # Arrondir à 2 décimales

                    message = f"{word}: {similarity*100:.2f}%"
                    alert_class = "alert-secondary"  # Classe par défaut
                else:
                    # Similarité inférieure à 25%, pas d'animation
                    message = f"{word}: {similarity*100:.2f}%"
                    alert_class = "alert-secondary"
                    progress_percent = None  # Pas d'animation
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    else:
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
        alert_class = ""

    return render_template(
        "game.html",
        jokers=jokers,
        message=message,
        alert_class=alert_class,
        progress_percent=progress_percent,
        results=sorted_results,
    )


@app.route("/result/<status>")
def result(status):
    target_word = session.get("target_word", "")
    # Regenerate most_similar
    most_similar = get_most_similar(target_word)[:100]
    return render_template(
        "result.html", status=status, target_word=target_word, most_similar=most_similar
    )


if __name__ == "__main__":
    # Load resources when the application starts
    MODEL_PATH = "models/frWac_no_postag_no_phrase_700_skip_cut50.bin"
    if not os.path.isfile(MODEL_PATH):
        os.makedirs("models", exist_ok=True)
        os.system(
            f"wget https://embeddings.net/embeddings/frWac_no_postag_no_phrase_700_skip_cut50.bin -P models/ --quiet"
        )
    print("Loading the model...")
    model = load_model(MODEL_PATH)
    print("Creating cleaned key map...")
    cleaned_key_map = create_cleaned_key_map()
    print("Resources loaded successfully.")
    app.run(debug=True)
