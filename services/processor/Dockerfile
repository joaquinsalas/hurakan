FROM python:3.11.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libnetcdf-c++4 \
    libnetcdf-dev \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY services/processor/requirements.txt ./requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project context so the processor can access 
# services.utils and other shared packages
COPY . .

# Run the monitor service
CMD ["python3", "-m", "services.processor.monitor_service"]
