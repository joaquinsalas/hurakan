import os
import requests
from dotenv import load_dotenv

# Initialize environment variables
load_dotenv()

# Global configuration from .env
CLASSIFIER_API_URL = os.getenv("CLASSIFIER_API_URL")

if not CLASSIFIER_API_URL:
    raise ValueError("ERROR: CLASSIFIER_API_URL not found in environment variables.")

def run_ensemble_prediction(features_dict):
    """
    Performs a POST request to the Hurakan Classifier API.
    
    Args:
        features_dict (dict): Dictionary containing the following keys:
            - n_trayectorias_best_cluster: list[int]
            - dispersión_km_best_cluster: list[float]  (accent required — matches trained model)
            - horas_diff_estimadas: list[float]
            
    Returns:
        tuple: (probability [float], prediction [int])
    """
    if not features_dict: 
        return 0.0, 0
    
    try:
        # The payload is sent directly as the API Pydantic model matches these keys
        response = requests.post(CLASSIFIER_API_URL, json=features_dict, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            # Synchronized with server response: 'probability_details' and 'predictions'
            # We extract the probability for class '1' (Active/Hurricane)
            probability = float(data['probability_details'][0]['1'])
            prediction = int(data['predictions'][0])
            
            return probability, prediction
        
        # Log error details for 422 (Validation) or 500 (Server Error)
        print(f"API Error {response.status_code}: {response.text}")
        
    except requests.exceptions.ConnectionError:
        print(f"Connection Error: Is the Classifier API running at {CLASSIFIER_API_URL}?")
    except Exception as e:
        print(f"Unexpected error during prediction: {e}")
    
    return 0.0, 0

if __name__ == "__main__":
    # Local test block with the exact schema the server expects
    test_features = {
        "n_trayectorias_best_cluster": [14],
        "dispersión_km_best_cluster": [529.56],
        "horas_diff_estimadas": [276.0]
    }
    proba, pred = run_ensemble_prediction(test_features)
    print(f"Test Result -> Probability: {proba:.2%} | Prediction: {pred}")