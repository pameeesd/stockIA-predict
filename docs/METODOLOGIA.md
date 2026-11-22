# Metodología, reproducibilidad y correcciones

## Datos

Chen, D. (2012). *Online Retail II*, UCI Machine Learning Repository, DOI 10.24432/C5CG6D (CC BY 4.0). Ver `DATASET_CITATION.md`.

Auditoría del Excel original (`scripts/01_audit_dataset.py`, salidas en `reports/eda/`):

| Dato | Valor |
|---|---:|
| Registros originales | 1.067.371 |
| Duplicados exactos eliminados (copia analítica) | 34.335 (3,22 %) |
| Facturas únicas / clientes con ID / países | 53.628 / 5.942 / 43 |
| Sin Customer ID | 235.151 (22,76 %) |
| Cancelaciones (prefijo C) / cantidades negativas | 19.104 / 22.496 filas |
| Líneas de venta positivas (todos los países) | 1.010.539 |
| Líneas de venta positivas, Reino Unido | 928.637 (91,90 %) · 9.437.249 unidades |
| Semanas completas para modelar | 104 (2009-12-07 a 2011-11-28); 2 sin ventas (2009-12-28 y 2010-12-27) |
| Códigos de artículo activos (UK) | 4.775 · 3.112 con ≥20 semanas activas · 1.634 con ≥50 · 735 con ≥80 |

Preparación: se eliminan duplicados exactos, cancelaciones y cantidades no positivas; se filtra Reino Unido; `StockCode` se normaliza a mayúsculas; se excluyen provisionalmente `DOT`, `M`, `C2`, `POST`, `BANK CHARGES`, `GIFT_0001_30`; se agregan unidades positivas por artículo y semana y las semanas sin venta se representan con cero. `CustomerID` no se usa en el modelo ni en las salidas publicadas.

## Corrección del panel semanal (2026-11-22)

El panel `data/processed/uk_product_week_sales.csv` incluido hasta la v0.4 **contaba dos veces** las ventas del 1 al 9 de diciembre de 2010, porque las dos hojas del Excel se solapan en esas fechas y ese panel no eliminaba los duplicados (+80.621 unidades en la semana 2010-11-29 y +82.299 en la 2010-12-06, 1,8 % del total). Además guardaba códigos numéricos como `10002.0`.

El panel actual se regeneró con `01_audit_dataset.py` desde el Excel original (deduplicado, códigos sin sufijo). Efecto sobre el resultado principal:

| | Panel con duplicados | Panel corregido |
|---|---:|---:|
| TSB, WAPE / sesgo | 77,21 % / -5,57 % | **77,00 % / -6,13 %** |
| Promedio móvil 4 sem., WAPE | 78,94 % | **78,65 %** |
| Mejora relativa | 2,19 % | **≈2,1 %** |
| Bloques donde TSB supera al baseline | 5 de 6 | **4 de 6** |

La conclusión cualitativa no cambia. Los Documentos Word 03–06 y los resultados de `reports/archive_v0.3/` se calcularon con el panel anterior y quedaron archivados (`docs/archive/`); en los Documentos 07 y 08 se actualizaron las cifras. Las cifras vigentes son las de `docs/RESULTADOS.md`.

## Backtesting multi-origen (`scripts/05_backtesting_model_selection.py`)

El código original del Documento 06 no estaba disponible; este script lo reconstruye. Con el panel anterior reproducía **exactamente** el TSB seleccionado, los baselines, Croston/SBA, los segmentos y las métricas por producto del Documento 06; los modelos ML y los híbridos diferían porque el documento no especificaba sus variables ni hiperparámetros.

- Orígenes 56, 64, 72, 80, 88 y 96; bloque externo de 8 semanas; selección con las 8 semanas internas previas.
- TSB con α = β ∈ {0,05; 0,10; 0,20; 0,30; 0,40; 0,50}, inicializado en la primera venta positiva (p = 1, z = y). Croston y SBA con el mismo α.
- Segmentación ADI/CV² (umbrales 1,32 y 0,49; Syntetos, Boylan y Croston, 2005) recalculada en cada origen con historial previo.
- ML reentrenado en cada origen con hiperparámetros fijos: HGB Poisson, HGB Hurdle Poisson (clasificador × regresor) y LightGBM Poisson con SKU categórico, con las variables de `scripts/02_train_forecasting_models.py`.
- Híbrido por segmento: en cada ventana interna elige el candidato de menor WAPE por segmento; el calibrado añade un factor de escala por segmento aprendido solo en la ventana interna.

## Cómo reproducir

```bash
python -m venv .venv && .venv/Scripts/Activate.ps1   # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt

python -m pytest                                                    # pruebas, incluida la reproducción del resultado
# Resultado oficial con el panel incluido (~1-2 min)
python scripts/05_backtesting_model_selection.py
python scripts/05_backtesting_model_selection.py --skip-ml          # solo estadísticos

# En contenedor (ver Dockerfile): docker build -t stockia-predict . && docker run --rm stockia-predict

# Desde el Excel original (data/raw/online_retail_II.xlsx, no versionado)
python scripts/01_audit_dataset.py --input data/raw/online_retail_II.xlsx --output reports/generated
```

Los scripts `02`–`04` pertenecen al diagnóstico exploratorio v0.3 (benchmark inicial con una sola ventana de prueba y análisis de facturas de alto volumen); se conservan por trazabilidad y sus resultados están en `reports/archive_v0.3/`. Esa ventana de prueba ya fue inspeccionada y no debe reutilizarse para elegir modelos.

## Referencias

- Teunter, R. H., Syntetos, A. A., & Babai, M. Z. (2011). Intermittent demand: Linking forecasting to inventory obsolescence. *European Journal of Operational Research, 214*(3), 606–615. https://doi.org/10.1016/j.ejor.2011.05.018
- Syntetos, A. A., & Boylan, J. E. (2005). The accuracy of intermittent demand estimates. *International Journal of Forecasting, 21*(2), 303–314. https://doi.org/10.1016/j.ijforecast.2004.10.001
