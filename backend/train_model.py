import os
import pandas as pd
import mysql.connector
import joblib

from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

load_dotenv()

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "complaint_category_model.pkl")


def load_dataset():
    connection = None

    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "civiq"),
        )

        query = """
            SELECT description, category
            FROM civiq_complaints_csv
            WHERE description IS NOT NULL
              AND TRIM(description) != ''
              AND category IS NOT NULL
              AND TRIM(category) != ''
        """

        df = pd.read_sql(query, connection)

        df["description"] = df["description"].astype(str).str.strip()
        df["category"] = df["category"].astype(str).str.strip()

        df = df[
            (df["description"] != "") &
            (df["category"] != "")
        ]

        return df

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def train_model():
    print("Loading dataset from MySQL...")

    df = load_dataset()

    if df is None or df.empty:
        print("ERROR: No usable data found.")
        return

    print("Total usable complaints:", len(df))
    print("Total categories:", df["category"].nunique())

    print("\nCategory distribution:")
    print(df["category"].value_counts())

    X = df["description"]
    y = df["category"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    print("\nTraining complaints:", len(X_train))
    print("Testing complaints:", len(X_test))

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                max_features=10000,
            ),
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                random_state=42,
            ),
        ),
    ])

    print("\nTraining AI model...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)

    print("\nModel training completed!")
    print(f"Test accuracy: {accuracy:.2%}")

    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print("\nModel saved successfully!")
    print("Model path:", MODEL_PATH)

    print("\nExample predictions:")

    examples = [
        "Garbage has not been collected for three days.",
        "Water is leaking from a broken pipeline.",
        "The road has a large pothole.",
        "The streetlight is not working at night.",
    ]

    for description in examples:
        predicted_category = model.predict([description])[0]

        print("\nComplaint:", description)
        print("Predicted category:", predicted_category)


if __name__ == "__main__":
    train_model()