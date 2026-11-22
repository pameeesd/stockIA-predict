# StockIA Predict · backtesting reproducible en contenedor
#
#   docker build -t stockia-predict .                         # imagen de ejecución
#   docker run --rm -v "${PWD}/reports/backtesting:/app/reports/backtesting" stockia-predict
#   docker build --target test -t stockia-predict:test .      # imagen con pruebas
#   docker run --rm stockia-predict:test
#   docker build --target app -t stockia-app .                # aplicación web
#   docker run --rm -p 8501:8501 -v stockia-data:/app/data/app stockia-app   # http://localhost:8501
#
# Etapas: base (dependencias y código) -> test (+pytest) -> app (Streamlit) -> runtime (por defecto, última).

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

COPY --chown=app:app stockia/ stockia/
COPY --chown=app:app scripts/ scripts/
COPY --chown=app:app app/ app/
COPY --chown=app:app .streamlit/ .streamlit/
COPY --chown=app:app data/processed/ data/processed/
COPY --chown=app:app data/demo/ data/demo/
RUN mkdir -p reports/backtesting data/app && chown -R app:app /app


# ---------------------------------------------------------------- pruebas
FROM base AS test

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY --chown=app:app pytest.ini .
COPY --chown=app:app tests/ tests/
COPY --chown=app:app reports/eda/dataset_profile.json reports/eda/dataset_profile.json

USER app
CMD ["python", "-m", "pytest"]


# ---------------------------------------------------------------- aplicación web
FROM base AS app

EXPOSE 8501
VOLUME ["/app/data/app"]
USER app
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s   CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]


# ---------------------------------------------------------------- ejecución (por defecto)
FROM base AS runtime

USER app
# Resultados en /app/reports/backtesting (montar un volumen para conservarlos)
CMD ["python", "scripts/05_backtesting_model_selection.py"]
