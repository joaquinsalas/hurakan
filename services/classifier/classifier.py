import pandas as pd
from autogluon.tabular import TabularPredictor
import os
import torch
import torch.nn as nn
import numpy as np
import pickle
import io
import warnings

# --- Environment Setup and Warning Suppression ---
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
# Force system to use CPU and ignore CUDA
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

# --- Flexible PyTorch Neural Network ---
class FlexibleNN(nn.Module):
    def __init__(self, input_dim, hidden_dims, dropout, activation_name):
        super().__init__()
        layers = []
        prev_dim = input_dim
        
        if activation_name == "relu":
            activation = nn.ReLU()
        elif activation_name == "leakyrelu":
            activation = nn.LeakyReLU()
        elif activation_name == "tanh":
            activation = nn.Tanh()
        else:
            raise ValueError(f"Unknown activation: {activation_name}")

        for h in hidden_dims:
            layers.append(nn.Linear(prev_dim, h))
            layers.append(activation)
            layers.append(nn.Dropout(dropout))
            prev_dim = h
        layers.append(nn.Linear(prev_dim, 1))  # output
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)

# --- Custom Unpickler to de-serialize GPU objects to CPU ---
class CPU_Unpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == 'torch.storage' and name == '_load_from_bytes':
            return lambda b: torch.load(io.BytesIO(b), map_location='cpu', weights_only=False)
        return super().find_class(module, name)

class HurricaneClassifier:
    NN_SEEDS = [17, 3, 11]
    XGB_SEEDS = [0, 4, 19]
    SVM_SEEDS = [4, 28, 26]
    MODEL_SEEDS = [NN_SEEDS, XGB_SEEDS, SVM_SEEDS]
    MODEL_NAMES = ['NN', 'XGB', 'SVM']

    # Exact column names as trained (INTERNAL USE ONLY - DO NOT REMOVE ACCENTS)
    MODEL_FEATURES = ["n_trayectorias_best_cluster", "dispersión_km_best_cluster", "horas_diff_estimadas"]

    def __init__(self):
        pass

    def _ensure_dataframe(self, scaler, x_test):
        """Ensures the DataFrame has the correct order and names for the scaler."""
        if not isinstance(x_test, pd.DataFrame):
            x_test = pd.DataFrame(x_test, columns=self.MODEL_FEATURES)
        else:
            x_test.columns = self.MODEL_FEATURES
        return x_test[self.MODEL_FEATURES]

    def _nn_bundle_predict_proba(self, nn_bundle, x_test):
        """Internal logic for Neural Network ensemble member prediction."""
        scaler = nn_bundle["scaler"]
        state_dict = nn_bundle["model_state"]
        params = nn_bundle["params"]

        # Force state_dict tensors to CPU
        for key in list(state_dict.keys()):
            state_dict[key] = state_dict[key].cpu()

        x_df = self._ensure_dataframe(scaler, x_test)
        xs = scaler.transform(x_df)

        input_dim = xs.shape[1]
        n_layers = params.get("n_layers", 1)
        hidden_dims = [params.get(f"n_units_layer_{i}", 64) for i in range(n_layers)]
        dropout = params.get("dropout", 0.0)
        activation_name = params.get("activation", "relu")

        model = FlexibleNN(input_dim=input_dim, hidden_dims=hidden_dims, dropout=dropout, activation_name=activation_name)
        model.load_state_dict(state_dict, strict=True)
        model.to(torch.device('cpu'))
        model.eval()

        with torch.no_grad():
            input_tensor = torch.tensor(xs, dtype=torch.float32).to(torch.device('cpu'))
            logits = model(input_tensor).squeeze(1)
            probas = torch.sigmoid(logits).cpu().numpy()
        return probas

    def _svm_bundle_predict_proba(self, svm_bundle, x_test):
        """Internal logic for SVM ensemble member prediction."""
        scaler = svm_bundle["scaler"]
        model = svm_bundle["model"]
        x_df = self._ensure_dataframe(scaler, x_test)
        xs = scaler.transform(x_df)
        probas = model.predict_proba(xs)[:, 1]
        return probas

    def predict_with_model(self, model_info, x):
        """Routes prediction to the correct model handler based on type."""
        # Neural Network Bundle
        if isinstance(model_info, dict) and "model_state" in model_info and "scaler" in model_info:
            probas = self._nn_bundle_predict_proba(model_info, x)
        # SVM Bundle
        elif isinstance(model_info, dict) and "model" in model_info and "scaler" in model_info:
            probas = self._svm_bundle_predict_proba(model_info, x)
        # XGBoost Pipeline (Sklearn)
        elif "sklearn.pipeline" in str(type(model_info)):
            x_df = self._ensure_dataframe(None, x)
            probas = model_info.predict_proba(x_df)[:, 1]
        else:
            probas = None
        return probas

    def preprocess_input(self, df, models_dir):
        """Loads all base models and collects their prediction probabilities."""
        files = []
        for model_seed_list, name in zip(self.MODEL_SEEDS, self.MODEL_NAMES):
            for seed in model_seed_list:
                file_path = os.path.join(models_dir, f"{name}_classifier_seed_{seed}.pkl")
                files.append(file_path)

        base_preds = pd.DataFrame()
        for idx, f_path in enumerate(files):
            with open(f_path, "rb") as pf:
                try:
                    # Use custom Unpickler to force CPU for PyTorch files
                    model_info = CPU_Unpickler(pf).load()
                except Exception:
                    # Fallback for non-Torch models (XGB/SVM)
                    pf.seek(0)
                    model_info = pickle.load(pf)
            
            col_name = f"model_{idx}"
            base_preds[col_name] = self.predict_with_model(model_info, df)

        return base_preds

    def classify(self, df, ensemble_dir, models_dir):
        """Main classification entry point using AutoGluon ensemble."""
        # 1. Ensure internal column names match training features
        df.columns = self.MODEL_FEATURES
        
        # 2. Get predictions from base models
        base_preds = self.preprocess_input(df, models_dir)

        # 3. Load AutoGluon predictor and run inference
        predictor = TabularPredictor.load(ensemble_dir)
        
        probabilities = predictor.predict_proba(base_preds)
        final_result = predictor.predict(base_preds)
        
        return probabilities, final_result