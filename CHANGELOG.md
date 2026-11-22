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
