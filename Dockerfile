FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Dependencies first so this layer is cached when only code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY data/raw/ ./data/raw/
COPY sql/ ./sql/
COPY pytest.ini .

RUN mkdir -p data/processed

# Default: run the whole pipeline on the bundled synthetic data.
# Add --write-db (and pass -e DB_URI=...) to upsert into iris_staging.
# Run the tests with: docker run --rm task-cre-72 pytest -q
CMD ["python", "scripts/run_pipeline.py"]
