# StockIA Predict

**Sistema de inteligencia predictiva para pronóstico semanal de ventas por artículo y alertas de volumen inusual**

StockIA Predict estudia cómo pronosticar las unidades vendidas por artículo y semana en un comercio electrónico británico anonimizado descrito en el dataset **Online Retail II** (UCI Machine Learning Repository), y propone una herramienta SaaS B2B de apoyo a la planificación de demanda.

> **Alcance probado:** ventas positivas registradas por artículo y semana para Reino Unido. El dataset no incluye inventario disponible, ventas perdidas, órdenes de compra ni plazos de proveedores. Los resultados **no** demuestran reducción de quiebres de stock ni optimización real de compras.

## Estado del proyecto

| Etapa | Documento | Estado |
|---|---|---|
| Caso y problemática | 01 | ✅ |
| Caracterización del dataset | 02 | ✅ |
| Auditoría y EDA | 03 (v1.1) | ✅ |
| Diseño experimental y primer benchmark ML | 04 | ✅ |
| Diagnóstico segmentado y pedidos de alto volumen | 05 | ✅ |
| Comparación final y selección de modelo (backtesting multi-origen) | 06 | ✅ |
| Diseño funcional y mockups | 07 | ✅ |
| Modelo de negocio y propuesta de valor | 08 | ✅ |
| Validación con clientes (entrevistas) | protocolo | ⏳ pendiente de ejecutar |
| MVP / implementación | — | ⏳ por desarrollar |

## Pregunta de investigación

¿Puede una estrategia especializada para demanda intermitente, un modelo de Machine Learning o un híbrido por segmentos pronosticar las unidades semanales registradas por producto con menor error y sesgo que un baseline sencillo?

## Resultado principal (Documento 06)

Evaluación con **seis bloques externos disjuntos de 8 semanas** (2011-01-03 a 2011-11-28) y selección anidada de parámetros en ventanas internas, sobre 2.201 artículos.

| Estrategia | WAPE | Sesgo |
|---|---:|---:|
| **TSB (seleccionado en validación interna)** | **77,21%** | -5,57% |
| Híbrido por segmentos | 77,34% | -10,59% |
| Promedio móvil 4 semanas (baseline) | 78,94% | -4,14% |
| HGB Hurdle Poisson (ML) | 83,52% | +9,75% |
| LightGBM Poisson (ML) | 106,03% | +20,12% |

- **Predictor principal: TSB** (Teunter-Syntetos-Babai). Mejora al baseline en 5 de 6 ventanas y en el 60,40% de los productos.
- **Baseline y respaldo:** promedio móvil de 4 semanas.
- La mejora es modesta (≈2,19% relativa) y el WAPE absoluto sigue alto.
- TSB es un **método estadístico** para demanda intermitente, no Machine Learning supervisado. Los modelos ML evaluados (HGB, LightGBM) no superaron a los métodos estadísticos bajo este protocolo.

Detalle completo en [`RESULTS_SUMMARY.md`](RESULTS_SUMMARY.md) y [`SEGMENT_AND_VOLUME_DIAGNOSTICS.md`](SEGMENT_AND_VOLUME_DIAGNOSTICS.md).

## Producto propuesto

Herramienta SaaS B2B que recibe historiales de venta (CSV/XLSX), valida calidad, clasifica patrones de demanda (smooth, erratic, intermittent, lumpy con ADI/CV²), genera pronósticos semanales por SKU con TSB y muestra alertas explicables de facturas de volumen inusual. **No** sustituye un POS/ERP, no conoce existencias y no automatiza compras.

- Diseño funcional y requisitos: [`docs/academic/Documento_07_Diseno_Funcional_y_Mockups_StockIA.docx`](docs/academic/)
- Mockups conceptuales: [`docs/design/`](docs/design/)
- Modelo de negocio: [`docs/business/BUSINESS_MODEL_STOCKIA.md`](docs/business/BUSINESS_MODEL_STOCKIA.md)
- Protocolo de validación con clientes: [`docs/validation/INTERVIEW_PROTOCOL.md`](docs/validation/INTERVIEW_PROTOCOL.md)

## Dataset y atribución

- Chen, D. (2012). *Online Retail II*. UCI Machine Learning Repository. DOI: <https://doi.org/10.24432/C5CG6D>
- Ficha: <https://archive.ics.uci.edu/dataset/502/online+retail+ii> · Licencia CC BY 4.0 · Período 2009-12 a 2011-12.

La empresa descrita por UCI es un comercio británico sin tiendas físicas y permanece anonimizada. Lee [`DATASET_CITATION.md`](DATASET_CITATION.md) antes de redistribuir o adaptar los datos. El Excel original no se versiona; se incluye un panel semanal derivado (4,3 MB) en `data/processed/` con atribución.

## Estructura

```text
stockIA-predict/
├── data/
│   ├── raw/                          # Excel UCI (local, no versionado)
│   └── processed/uk_product_week_sales.csv   # Panel semanal derivado (CC BY 4.0)
├── docs/
│   ├── academic/                     # Documentos 01–08
│   ├── business/                     # Modelo de negocio y propuesta de valor
│   ├── design/mockups/               # Mockups conceptuales v1
│   ├── validation/                   # Protocolo y guía de entrevistas
│   └── REPRODUCIBILITY_CHECK.md
├── reports/
│   ├── eda/                          # Salidas agregadas de la auditoría inicial
│   ├── benchmark/                    # Primer benchmark (Documento 04)
│   └── segment_diagnostics/          # Segmentación y facturas (Documento 05)
├── scripts/
│   ├── 01_audit_dataset.py
│   ├── 02_train_forecasting_models.py
│   ├── 03_segment_model_experiment.py
│   └── 04_invoice_spike_diagnostics.py
├── EXPERIMENT_PROTOCOL.md
├── RESULTS_SUMMARY.md
├── SEGMENT_AND_VOLUME_DIAGNOSTICS.md
├── DATASET_CITATION.md
└── CHANGELOG.md
```

> El script del backtesting multi-origen del Documento 06 (Croston/SBA/TSB, híbridos, LightGBM) aún no está incluido en `scripts/`.

## Reproducibilidad

Requiere Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Con el panel semanal incluido:

```bash
python scripts/03_segment_model_experiment.py
python scripts/03_segment_model_experiment.py --write-predictions   # predicciones detalladas (archivo grande)
```

Desde el Excel original (descárgalo de UCI y colócalo en `data/raw/online_retail_II.xlsx`; no lo subas a GitHub):

```bash
python scripts/01_audit_dataset.py --input data/raw/online_retail_II.xlsx --output reports/generated
python scripts/02_train_forecasting_models.py --input reports/generated/uk_product_week_sales.csv --output reports/ml_experiment
python scripts/04_invoice_spike_diagnostics.py --workbook data/raw/online_retail_II.xlsx
```

Los scripts exportan estadísticas agregadas y no escriben números de factura ni identificadores de clientes.

## Límites de interpretación

- Una semana sin ventas registradas se representa con cero; no equivale necesariamente a inventario disponible.
- Las ventas observadas no son demanda latente ni ventas perdidas.
- Los picos pueden reflejar pedidos de alto volumen, pero el dataset no etiqueta a los clientes como mayoristas.
- ADI/CV² es una clasificación descriptiva; no garantiza que un modelo especializado mejore.
- Las métricas por artículo-semana y la calibración del volumen agregado son criterios distintos.
- Los datos son históricos (2009–2011) y del Reino Unido; no deben extrapolarse sin validación con datos actuales.

## Foco académico y portafolio

La evaluación académica se centra en la justificación de IA, diseño del experimento, comparación con baselines, interpretación de resultados y límites de la solución. AWS, Terraform, Docker, GitHub Actions, seguridad y resiliencia se documentarán como evidencia complementaria de ingeniería.

## Licencia del código

La atribución CC BY 4.0 corresponde al dataset y al panel derivado. El código del repositorio permanece sin una licencia de reutilización independiente hasta que se elija expresamente una.
