# StockIA Predict

**Pronóstico semanal de ventas por artículo y alertas de volumen inusual para comercio electrónico.**
Proyecto académico (TI2082 Aplicaciones de Inteligencia Artificial) con enfoque de portafolio.

StockIA Predict estudia cómo anticipar las unidades vendidas por artículo y semana en un comercio electrónico británico anonimizado (dataset **Online Retail II**, UCI) y propone una herramienta de apoyo a la planificación de demanda que clasifica el patrón de cada producto, pronostica con un método para demanda intermitente (TSB) y señala pedidos de volumen inusual para revisión humana.

> **Alcance:** ventas **observadas** por artículo y semana, Reino Unido. El dataset no incluye inventario, ventas perdidas, órdenes de compra ni plazos de proveedores; los resultados **no** demuestran reducción de quiebres de stock ni ahorro económico.

## Resultado principal

Evaluación con **6 bloques externos de 8 semanas** (2011-01-03 a 2011-11-28), selección de método solo con las 8 semanas previas a cada bloque, 2.201 artículos.

| Estrategia | WAPE | Sesgo |
|---|---:|---:|
| Híbrido por segmentos | 75,93 % | -13,45 % |
| **TSB (seleccionado)** | **77,00 %** | -6,13 % |
| HGB Hurdle Poisson (ML) | 78,41 % | -1,10 % |
| **Promedio móvil 4 semanas (baseline)** | **78,65 %** | -4,77 % |
| LightGBM Poisson (ML) | 79,88 % | -0,25 % |

- TSB reduce el error ≈ **2,10 %** frente al baseline, y lo supera en 4 de 6 bloques y en el 59 % de los productos.
- La mejora es **modesta** y el WAPE absoluto sigue alto: es una prueba de concepto, no un sistema listo para decidir compras.
- TSB es un método **estadístico** de pronóstico para demanda intermitente, no Machine Learning supervisado; los modelos ML evaluados no lo superan claramente.

Detalle, tablas por bloque, segmento y producto: [`docs/RESULTADOS.md`](docs/RESULTADOS.md).

## Estructura

```text
├── data/processed/uk_product_week_sales.csv   # Panel semanal derivado (CC BY 4.0)
├── docs/
│   ├── RESULTADOS.md          # Cifras oficiales (única fuente)
│   ├── METODOLOGIA.md         # Datos, protocolo, reproducibilidad, correcciones
│   ├── entrega/               # Requisitos de la Evaluación Sumativa 3
│   ├── academic/              # Documentos 01–08 (evidencia de apoyo)
│   ├── business/              # Modelo de negocio y propuesta de valor
│   ├── design/mockups/        # Mockups conceptuales
│   ├── validation/            # Protocolo de entrevistas (opcional)
│   └── archive/               # Documentos de la etapa exploratoria v0.3
├── reports/
│   ├── backtesting/           # Resultados oficiales
│   ├── eda/                   # Auditoría del dataset
│   └── archive_v0.3/          # Resultados exploratorios (no citar cifras)
├── scripts/
│   ├── 01_audit_dataset.py            # Auditoría y panel semanal desde el Excel
│   ├── 05_backtesting_model_selection.py   # Backtesting y selección de modelo
│   └── 02–04_*.py             # Diagnóstico exploratorio v0.3
├── DATASET_CITATION.md · CHANGELOG.md · requirements.txt
```

## Reproducir

```bash
python -m venv .venv
.venv/Scripts/Activate.ps1          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python scripts/05_backtesting_model_selection.py      # ~1-2 min
```

Para regenerar el panel desde los datos originales, descarga `online_retail_II.xlsx` de UCI en `data/raw/` (no se versiona) y ejecuta `scripts/01_audit_dataset.py`. Más en [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md).

## Límites de interpretación

- Una semana sin ventas se representa con cero; no equivale a disponibilidad de inventario.
- Ventas observadas no son demanda latente.
- No hay etiqueta de mayorista por cliente: una factura grande no prueba que el comprador lo sea.
- Datos históricos (2009–2011) del Reino Unido; no extrapolar sin validación con datos actuales.

## Atribución y licencia

Chen, D. (2012). *Online Retail II*. UCI Machine Learning Repository. DOI [10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D). Licencia del dataset y del panel derivado: CC BY 4.0 (ver [`DATASET_CITATION.md`](DATASET_CITATION.md)). El código no tiene licencia de reutilización independiente hasta que se elija una.
