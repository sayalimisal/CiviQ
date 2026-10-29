from fastapi import FastAPI, HTTPException
from database import get_db_connection
from pydantic import BaseModel, Field
from typing import Optional
import joblib
import os

app = FastAPI(title="CiviQueue API")
# AI Category to Department Mapping
CATEGORY_DEPARTMENT_MAP = {
    "Streetlight": "Streetlight",
    "Street Light": "Streetlight",
    "Road Damage": "Roads",
    "Garbage": "Garbage",
    "Water Leakage": "Water",
    "Water Supply": "Water",
    "Drainage": "Drainage & Sewage",
    "Noise Pollution": "Public Health",
    "Traffic": "Traffic & Road Safety",
    "Public Toilet": "Public Facilities & Accessibility",
    "Tree Hazard": "Parks & Public Spaces",
}


def get_department_for_category(category: str) -> str:
    normalized_category = category.strip().lower()

    for mapped_category, department in CATEGORY_DEPARTMENT_MAP.items():
        if mapped_category.lower() == normalized_category:
            return department

    return "Public Health"

MODEL_PATH = "models/complaint_category_model.pkl"

category_model = joblib.load(MODEL_PATH)

category_model = joblib.load(MODEL_PATH)
PRIORITY_MODEL_PATH = "models/complaint_priority_model.pkl"

priority_model = joblib.load(PRIORITY_MODEL_PATH)
class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    citizen_id: int = Field(..., gt=0)

    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    address: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=100)

    priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")

@app.get("/")
def home():
    return {
        "message": "CiviQueue Backend is running!",
        "project": "AI-powered civic intelligence system"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
class ComplaintPrediction(BaseModel):
    description: str = Field(..., min_length=10)


@app.post("/predict-category")
def predict_category(data: ComplaintPrediction):
    try:
        predicted_category = category_model.predict(
            [data.description]
        )[0]

        return {
            "description": data.description,
            "predicted_category": str(predicted_category),
            "model": "TF-IDF + Logistic Regression"
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(error)}"
        )
@app.post("/predict-priority")
def predict_priority(data: ComplaintPrediction):
    try:
        predicted_priority = priority_model.predict(
            [data.description]
        )[0]

        return {
            "description": data.description,
            "predicted_priority": str(predicted_priority),
            "model": "TF-IDF + Logistic Regression"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Priority prediction failed: {str(e)}"
        )

@app.get("/db-health")
def db_health():
    connection = get_db_connection()

    if connection is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        result = cursor.fetchone()
        cursor.close()

        return {
            "status": "success",
            "database": result[0]
        }

    finally:
        connection.close()


@app.get("/complaints")
def get_complaints(limit: int = 20):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100"
        )

    connection = get_db_connection()

    if connection is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM civiq_complaints_csv LIMIT %s",
            (limit,)
        )

        complaints = cursor.fetchall()

        return {
            "count": len(complaints),
            "complaints": complaints
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not fetch complaints from database"
        )

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
@app.post("/complaints")
def create_complaint(complaint: ComplaintCreate):
    connection = get_db_connection()

    if connection is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )

    cursor = None

    try:
        cursor = connection.cursor()

        # 1. Predict complaint category using AI
        predicted_category = str(
            category_model.predict([complaint.description])[0]
        )

        # 2. Predict complaint priority using AI
        predicted_priority = str(
            priority_model.predict([complaint.description])[0]
        ).upper()

        # 3. Assign department based on predicted category
        assigned_department = get_department_for_category(
            predicted_category
        )

        # 4. Find department ID from database
        cursor.execute(
            """
            SELECT id
            FROM departments
            WHERE LOWER(name) = LOWER(%s)
            LIMIT 1
            """,
            (assigned_department,)
        )

        department_row = cursor.fetchone()

        department_id = (
            department_row[0]
            if department_row is not None
            else None
        )

        # 5. Save complaint and AI results
        query = """
            INSERT INTO complaints (
                title,
                description,
                citizen_id,
                latitude,
                longitude,
                address,
                category,
                priority,
                department_id,
                ai_category,
                ai_department
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            complaint.title,
            complaint.description,
            complaint.citizen_id,
            complaint.latitude,
            complaint.longitude,
            complaint.address,
            predicted_category,
            predicted_priority,
            department_id,
            predicted_category,
            assigned_department
        )

        cursor.execute(query, values)
        connection.commit()

        new_complaint_id = cursor.lastrowid

        return {
            "message": "Complaint submitted successfully",
            "complaint_id": new_complaint_id,
            "title": complaint.title,
            "predicted_category": predicted_category,
            "predicted_priority": predicted_priority,
            "assigned_department": assigned_department,
            "department_id": department_id,
            "status": "PENDING"
        }

    except Exception as error:
        connection.rollback()
        print("Complaint submission error:", error)

        raise HTTPException(
            status_code=500,
            detail="Could not submit complaint. Check the server terminal."
        )

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()
@app.get("/citizens/{citizen_id}/complaints")
def get_citizen_complaints(citizen_id: int):
    connection = get_db_connection()

    if connection is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                title,
                description,
                category,
                priority,
                status,
                address,
                latitude,
                longitude,
                created_at
            FROM complaints
            WHERE citizen_id = %s
            ORDER BY created_at DESC
            """,
            (citizen_id,)
        )

        complaints = cursor.fetchall()

        return {
            "citizen_id": citizen_id,
            "count": len(complaints),
            "complaints": complaints
        }

    except Exception as error:
        print("Fetch citizen complaints error:", error)

        raise HTTPException(
            status_code=500,
            detail="Could not fetch citizen complaints"
        )

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


class ComplaintStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern="^(PENDING|ASSIGNED|IN_PROGRESS|RESOLVED|CONFIRMED|REOPENED|CLOSED)$"
    )


@app.patch("/complaints/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    update: ComplaintStatusUpdate
):
    connection = get_db_connection()

    if connection is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )

    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM complaints WHERE id = %s",
            (complaint_id,)
        )

        existing_complaint = cursor.fetchone()

        if existing_complaint is None:
            raise HTTPException(
                status_code=404,
                detail="Complaint not found"
            )

        cursor.execute(
            """
            UPDATE complaints
            SET status = %s
            WHERE id = %s
            """,
            (update.status, complaint_id)
        )

        connection.commit()

        return {
            "message": "Complaint status updated successfully",
            "complaint_id": complaint_id,
            "status": update.status
        }

    except HTTPException:
        raise

    except Exception as error:
        connection.rollback()
        print("Complaint status update error:", error)

        raise HTTPException(
            status_code=500,
            detail="Could not update complaint status"
        )

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()

class ComplaintPrediction(BaseModel):
    description: str = Field(..., min_length=10)


@app.post("/predict-category")
def predict_category(data: ComplaintPrediction):
    try:
        predicted_category = category_model.predict(
            [data.description]
        )[0]

        return {
            "description": data.description,
            "predicted_category": str(predicted_category),
            "model": "TF-IDF + Logistic Regression"
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(error)}"
        )