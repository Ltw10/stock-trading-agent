# Use Python 3.11 slim for smaller image and faster pulls
FROM python:3.11-slim

WORKDIR /app

# Install CPU-only PyTorch first (much smaller/faster than full torch from PyPI).
# This keeps the build under Railway's timeout and satisfies transformers/FinBERT.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Then install the rest of dependencies (pip will skip torch as already satisfied).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the worker (Procfile style)
CMD ["python", "main.py"]
