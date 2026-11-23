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
- Resultado oficial actualizado: TSB 77,00 % WAPE vs 78,65 % del promedio móvil de 4 semanas (≈2,1 % relativo); TSB supera al baseline en 4 de 6 bloques.
- `reports/backtesting/` y `reports/eda/` regenerados con datos corregidos.
- Resultados v0.3 movidos a `reports/archive_v0.3/` y documentos previos a `docs/archive/`.
- `RESULTS_SUMMARY.md` y `BACKTESTING_RECONSTRUCTION.md` reemplazados por `docs/RESULTADOS.md` y `docs/METODOLOGIA.md`.
- Se agrega `docs/entrega/REQUISITOS_EVALUACION_3.md` (matriz de la pauta).

## v0.7 - Entrega de la Evaluación Sumativa 3 (2026-11-22)

- `docs/entrega/`: preinforme (portada + 3 páginas), mockups (6 pantallas + flujo con rama de error y anotaciones de IA) y presentación (5 diapositivas), con fuentes HTML y guion de exposición.
- Documentos 07 y 08 actualizados con las cifras corregidas; Documentos 03–06 archivados en `docs/archive/word_v1/`; mockups v1 reemplazados.
- Preinforme ampliado: introducción y caso de estudio (negocio anonimizado con sus datos reales), solución elegida frente a alternativas y resultados esperados; ahora portada + 4 páginas. Presentación y guion alineados.

## v0.8 - Pruebas, contenedor e integración continua (2026-11-22)

- `tests/`: 25 pruebas (métodos de pronóstico, ausencia de fuga de información, segmentación, integridad del panel con regresión del solapamiento duplicado, reproducción del resultado oficial). `pytest.ini`, `requirements-dev.txt`.
- `Dockerfile` multietapa (base, test, runtime; usuario no root) y `.dockerignore`. Probado localmente: pruebas dentro del contenedor y ejecución del backtesting con volumen.
- `.github/workflows/ci.yml`: pruebas con pytest y construcción/prueba de humo de la imagen en cada push y pull request.

## v0.9 - Cobertura de stock informativa en el alcance del MVP (2026-11-22)

- Panel opcional de cobertura de stock (pantalla 3 y flujo): con stock y plazo de entrega ingresados por el usuario calcula semanas de cobertura y una cantidad referencial a pedir (pronóstico × (plazo + semanas de seguridad) − stock). Es aritmética sobre el pronóstico, informativa y no validada; no hay órdenes de compra automáticas ni predicción de quiebres.
- Preinforme, presentación, guion, requisitos, modelo de negocio y Documento 07 alineados con el nuevo alcance.

## v1.0 - Aplicación web (Streamlit) y paquete `stockia` (2026-11-22)

- `stockia/`: pronóstico (TSB, Croston/SBA, medias móviles, segmentación ADI/CV²), ingesta con validación de calidad, motor de la semana siguiente, backtesting rodante, alertas de volumen inusual, cobertura de stock informativa, SQLite y evaluación de pronósticos guardados contra la venta real. Los métodos se movieron de `scripts/05_backtesting_model_selection.py` al paquete.
- `app/`: aplicación Streamlit con las 6 pantallas de los mockups. Con los datos de demostración reproduce las cifras oficiales; subir el Excel original reproduce exactamente el panel de demostración.
- `scripts/06_build_demo_assets.py` y `data/demo/` (descripciones de productos, 496 alertas en el período, informe de calidad), sin números de factura ni identificadores de clientes.
- 66 pruebas (lógica, interfaz con `streamlit.testing` y reproducción del resultado oficial). Etapa `app` en el Dockerfile y comprobación de salud de la imagen en CI. Corrección: la conexión SQLite se reutiliza entre los hilos de Streamlit.
- La mejora relativa se expresa como ≈2,1 % (exacto: 2,09 %) en todos los documentos.

## v1.1 - README de portafolio (2026-11-22)

- README reescrito para portafolio: problema, solución, resultados con su aclaración del WAPE, qué demuestra el proyecto, arquitectura (Mermaid), cómo ejecutarlo y límites.
- `docs/img/` con capturas de la app y `scripts/07_capture_screenshots.py` para regenerarlas (Playwright con Edge/Chrome instalado).
- Filtros de la app con textos en español y tabla por patrón con formato numérico.

## v1.2 - Infraestructura como código (Terraform) (2026-11-22)

- `infra/terraform/`: VPC, balanceador, ECR y servicio ECS Fargate para publicar la imagen `app`. Escrito y validado (`terraform fmt` y `validate`); **no se ejecutó `plan` ni `apply`** y no hay recursos creados en AWS.
- `allowed_cidrs` obligatorio (la app no tiene autenticación real), una sola tarea por usar SQLite local, HTTPS opcional con ACM.
