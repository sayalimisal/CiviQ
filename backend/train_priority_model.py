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
MODEL_PATH = os.path.join(
    MODEL_DIR,
    "complaint_priority_model.pkl"
)


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
            SELECT description, priority
            FROM civiq_complaints_csv
            WHERE description IS NOT NULL
              AND TRIM(description) != ''
              AND priority IS NOT NULL
              AND TRIM(priority) != ''
        """

        df = pd.read_sql(query, connection)

        df["description"] = df["description"].astype(str).str.strip()
        df["priority"] = df["priority"].astype(str).str.strip().str.upper()

        df = df[
            df["description"].ne("") &
            df["priority"].isin(
                ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            )
        ]

        return df

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def train_model():
    print("Loading priority dataset from MySQL...")

    df = load_dataset()

    if df.empty:
        print("ERROR: No usable priority data found.")
        return

    print("Total usable complaints:", len(df))

    print("\nPriority distribution:")
    print(df["priority"].value_counts())

    X = df["description"]
    y = df["priority"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

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
                class_weight="balanced",
                random_state=42,
            ),
        ),
    ])

    print("\nTraining priority model...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    print("\nPriority model training completed!")
    print(f"Test accuracy: {accuracy_score(y_test, predictions):.2%}")

    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            zero_division=0,
        )
    )

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print("\nPriority model saved successfully!")
    print("Model path:", MODEL_PATH)

    examples = [
        "An open drain is overflowing and sewage is entering nearby homes.",
        "A streetlight is not working on a quiet road.",
        "Garbage has not been collected for two days.",
        "A major road has a dangerous pothole causing accidents.",
    ]

    print("\nExample priority predictions:")

    for description in examples:
        predicted_priority = model.predict([description])[0]

        print("\nComplaint:", description)
        print("Predicted priority:", predicted_priority)


if __name__ == "__main__":
    train_model()