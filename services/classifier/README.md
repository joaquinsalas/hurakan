# `whole version/services/classifier`

This directory contains the classifier service used to estimate whether a trajectory cluster represents a mature tropical cyclone.

## `.py` scripts

### `api_classifier.py`
- Exposes the classifier through a FastAPI service.
- Validates incoming feature lists, converts them to a DataFrame, runs inference, and returns predictions plus probability details.
- Includes a health endpoint that reports whether model directories are present.

### `classifier.py`
- Implements the stacked ensemble inference logic.
- Rebuilds PyTorch neural-network members on CPU, supports SVM bundles and sklearn/XGBoost pipelines, and feeds their probabilities into an AutoGluon meta-model.

### `classifier_request.py`
- Client helper for sending feature payloads to the classifier API.
- Returns the probability and predicted class from the remote service response.

### `__init__.py`
- Marks the classifier directory as a Python package.
