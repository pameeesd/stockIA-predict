# StockIA Predict · backtesting reproducible en contenedor
#
#   docker build -t stockia-predict .                         # imagen de ejecución
#   docker run --rm -v "${PWD}/reports/backtesting:/app/reports/backtesting" stockia-predict
#   docker build --target test -t stockia-predict:test .      # imagen con pruebas
#   docker run --rm stockia-predict:test
#
# Etapas: base (dependencias y código) -> test (+pytest) -> runtime (por defecto, última).

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libgomp1: runtime de OpenMP que necesitan scikit-learn, LightGBM y XGBoost en la imagen slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app

WORKDIR /app

# Las dependencias van antes que el código para aprovechar la caché de capas
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app:app scripts/ scripts/
COPY --chown=app:app data/processed/ data/processed/
RUN mkdir -p reports/backtesting && chown -R app:app /app


# ---------------------------------------------------------------- pruebas
FROM base AS test

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY --chown=app:app pytest.ini .
COPY --chown=app:app tests/ tests/
COPY --chown=app:app reports/eda/dataset_profile.json reports/eda/dataset_profile.json

USER app
CMD ["python", "-m", "pytest"]


# ---------------------------------------------------------------- ejecución (por defecto)
FROM base AS runtime

USER app
# Resultados en /app/reports/backtesting (montar un volumen para conservarlos)
CMD ["python", "scripts/05_backtesting_model_selection.py"]
