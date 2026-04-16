# Use a stable Python version compatible with AutoGluon, FastAI, and FastCore
# Python 3.10 is the recommended production baseline for this ML stack
FROM python:3.11.11-slim

# Environment variables to improve Python behavior inside containers
# - Prevents creation of .pyc files
# - Forces stdout/stderr to be unbuffered (better logging)
# - Silences XGBoost verbose logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV XGBOOST_LOG_LEVEL=0

# Set the working directory inside the container
WORKDIR /app

# Install system-level dependencies required for:
# - Compiling Python packages
# - Running XGBoost / LightGBM
# - CPU parallelism (OpenMP)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definitions first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code and trained ML models
# This includes:
# - api_classifier.py
# - classifier.py
# - ensemble directories and model artifacts
COPY . .

# Expose the port used by the FastAPI application
EXPOSE 8082

# Start the FastAPI application using Uvicorn
# The application must listen on 0.0.0.0 to be accessible from outside the container
CMD ["uvicorn", "api_classifier:app", "--host", "0.0.0.0", "--port", "8082"]