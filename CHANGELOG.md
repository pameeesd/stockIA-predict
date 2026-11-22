# Changelog

## 2026-11-21 — First reproducible ML benchmark

- Restored 104 calendar weeks, including two weeks without UK transaction records (represented as zero recorded sales in the panel).
- Normalized `StockCode` to uppercase before aggregation.
- Selected 2,563 article codes using training-window activity only and provisional code exclusions.
- Benchmarked four baselines, HistGradientBoosting log1p, HistGradientBoosting Poisson, a two-stage HistGradientBoosting hurdle model, and XGBoost log1p.
- Added aggregate bias reporting in addition to MAE, RMSE, and WAPE.
- Documented that the test period has been inspected and later model decisions require multi-origin backtesting.

## v0.3 - Diagnóstico segmentado y facturas de alto volumen

- Se incorpora la clasificación ADI/CV² calculada solo sobre entrenamiento.
- Se agregan métricas de validación y prueba exploratoria por segmento.
- Se documentan facturas de alto volumen sin publicar IDs de factura o cliente.
- Se agrega script reproducible de segmentación y diagnóstico de facturas.
- Se incorpora Documento 05 y se incluye panel semanal derivado con atribución CC BY 4.0.

## v0.4 - Selección de modelo, diseño funcional y modelo de negocio

- Se incorpora Documento 06: backtesting con seis orígenes y selección anidada; TSB seleccionado como predictor principal y promedio móvil de 4 semanas como baseline/respaldo.
- Se incorpora Documento 07: diseño funcional, requisitos (RF-01..RF-08, RNF-01..RNF-06) y cinco mockups conceptuales (`docs/design/`).
- Se incorpora Documento 08 y `docs/business/BUSINESS_MODEL_STOCKIA.md`: modelo de negocio SaaS B2B y propuesta de valor.
- Se agrega protocolo de validación con clientes (`docs/validation/`).
- Se agregan salidas agregadas de la auditoría EDA inicial (`reports/eda/`).
- Documento 03 actualizado a la versión 1.1.

## v0.5 - Reconstrucción del backtesting multi-origen

- Se agrega `scripts/05_backtesting_model_selection.py` y salidas en `reports/backtesting/`.
- Reproduce exactamente TSB seleccionado (77,21% WAPE, -5,57% sesgo), baselines, Croston/SBA, segmentación por origen y métricas por SKU del Documento 06.
- Los modelos ML e híbridos difieren del documento por falta de especificación original; ver `BACKTESTING_RECONSTRUCTION.md`.
- Se agrega `lightgbm` a `requirements.txt`.

## v0.6 - Corrección del panel y consolidación de resultados (2026-11-22)

- **Corrección:** el panel semanal contaba dos veces las ventas del 1–9 dic 2010 (solapamiento de las hojas del Excel) y guardaba códigos como `10002.0`. Se regeneró desde el Excel original con `01_audit_dataset.py`.
- Resultado oficial actualizado: TSB 77,00 % WAPE vs 78,65 % del promedio móvil de 4 semanas (≈2,10 % relativo); TSB supera al baseline en 4 de 6 bloques.
- `reports/backtesting/` y `reports/eda/` regenerados con datos corregidos.
- Resultados v0.3 movidos a `reports/archive_v0.3/` y documentos previos a `docs/archive/`.
- `RESULTS_SUMMARY.md` y `BACKTESTING_RECONSTRUCTION.md` reemplazados por `docs/RESULTADOS.md` y `docs/METODOLOGIA.md`.
- Se agrega `docs/entrega/REQUISITOS_EVALUACION_3.md` (matriz de la pauta).
