import os
import warnings
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
import pandas as pd
from classifier import HurricaneClassifier

# Silence warnings
warnings.filterwarnings("ignore", message=".*If you are loading a serialized model.*")

app = FastAPI(
    title="Hurricane Classifier API",
    description="Inference service for hurricane cluster classification.",
    version="1.2.0"
)

# Singleton initialization
classifier = HurricaneClassifier()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENSEMBLE_DIR = os.path.join(BASE_DIR, 'ensemble_seed_2')
MODELS_DIR = os.path.join(BASE_DIR, 'modelos_ensamble')

class PredictionInput(BaseModel):
    n_trayectorias_best_cluster: list[int]
    dispersion_km_best_cluster: list[float] 
    horas_diff_estimadas: list[float]

    @field_validator('dispersion_km_best_cluster', 'horas_diff_estimadas')
    @classmethod
    def check_lengths(cls, v, info):
        # Validate lists lengths to prevent Pandas errors.
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "n_trayectorias_best_cluster": [10],
                "dispersion_km_best_cluster": [50.5],
                "horas_diff_estimadas": [-12.0]
            }
        }
    }

@app.post("/predict", tags=["Inference"])
async def predict(data: PredictionInput):
    try:
        # 1. Convert to dictionary
        input_data = data.model_dump()
        
        # 2. Validate field lengths explicitly to return a 400 error instead of 500
        lengths = [len(v) for v in input_data.values()]
        if len(set(lengths)) > 1:
            raise ValueError("All input lists must have the same length.")

        # 3. Create DataFrame and restore accent for internal model
        df = pd.DataFrame(input_data)
        df = df.rename(columns={"dispersion_km_best_cluster": "dispersión_km_best_cluster"})
        
        # Ensure exact column order expected by StandardScaler
        column_order = ["n_trayectorias_best_cluster", "dispersión_km_best_cluster", "horas_diff_estimadas"]
        df = df[column_order]

        # 4. Execute the classifier
        probabilidades, final_result = classifier.classify(df, ENSEMBLE_DIR, MODELS_DIR)
        
        # 5. Format response: return dictionaries for clarity
        res_probas = probabilidades.to_dict(orient="records")
        
        return {
            "predictions": final_result.tolist(),
            "probability_details": res_probas,
            "status": "success"
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/health", tags=["System"])
def health():
    ensemble_exists = os.path.exists(ENSEMBLE_DIR)
    models_exists = os.path.exists(MODELS_DIR)
    return {
        "status": "ok",
        "python_version": "3.11.11",
        "models_ready": ensemble_exists and models_exists
    }