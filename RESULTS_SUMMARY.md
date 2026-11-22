# Resumen de resultados: benchmark exploratorio

## Resultado de prueba (2009–2011 historical data; final dates 2011-08-15 to 2011-11-28)

| Modelo | MAE | RMSE | WAPE | Unidades predichas | Sesgo total |
|---|---:|---:|---:|---:|---:|
| HGB hurdle | 20.09 | 102.74 | 63.70% | 835,037 | -35.4% |
| HGB log1p | 20.36 | 103.94 | 64.56% | 765,339 | -40.8% |
| XGBoost log1p | 20.51 | 104.96 | 65.05% | 738,683 | -42.9% |
| Promedio móvil 13 | 22.46 | 102.33 | 71.22% | 1,050,054 | -18.8% |
| HGB Poisson | 23.09 | 110.06 | 73.23% | 1,269,422 | -1.8% |
| Promedio móvil 4 | 22.71 | 103.40 | 72.01% | 1,189,930 | -8.0% |
| Última semana | 26.02 | 131.82 | 82.52% | 1,248,271 | -3.5% |
| Naive estacional 52 | 39.11 | 175.92 | 124.02% | 1,806,145 | +39.7% |

## Interpretación

El modelo hurdle logra el menor WAPE y MAE de esta comparación y reduce ambas métricas aproximadamente 10,56% respecto del promedio móvil de 13 semanas. Aun así, subestima las unidades agregadas en aproximadamente 35,4% y su RMSE es ligeramente peor que el del promedio móvil de 13 semanas.

La variante HGB Poisson se aproxima al total agregado (sesgo de -1,8%), pero presenta WAPE y MAE peores que el baseline de 13 semanas. Esto muestra que la calibración global y el error por artículo-semana son dimensiones diferentes.

## Conclusión

Ningún modelo se declara listo para uso comercial. Los resultados respaldan continuar la investigación de predicción de ventas registradas, no una afirmación de reducción de roturas de stock ni de optimización real de compras. Se necesita backtesting multi-origen, validación de catálogo, análisis por segmentos y datos de inventario/abastecimiento para estudiar reposición.

La ventana de prueba ya fue inspeccionada como parte del benchmark exploratorio; no debe reutilizarse como un holdout ciego para elegir iteraciones futuras.


## Diagnóstico segmentado y de facturas de alto volumen (v0.3)

| Patrón | Artículos | Participación | Mejor candidato en validación | WAPE |
|---|---:|---:|---|---:|
| Lumpy | 1.668 | 65,1% | XGBoost log1p | 82,89% |
| Erratic | 716 | 27,9% | HGB Hurdle | 66,52% |
| Intermittent | 98 | 3,8% | HGB log1p | 63,53% |
| Smooth | 81 | 3,2% | HGB Hurdle | 48,66% |

En la prueba exploratoria, lumpy y erratic reúnen 83,8% de las unidades y el XGBoost global subestima estos segmentos en 49,2% y 34,2%. Se identificaron ejemplos de facturas individuales que concentran 99,8%, 45,2%, 31,8% o 29,0% del volumen de determinados artículos. Sin embargo, los 50 artículos con mayor subestimación acumulan 29,5% del faltante, de modo que el problema es más amplio que unos pocos picos. UCI informa que muchos clientes son mayoristas, pero el dataset no etiqueta formalmente a cada cliente. Consultar `SEGMENT_AND_VOLUME_DIAGNOSTICS.md`.


## Comparación final con backtesting multi-origen (Documento 06)

Seis bloques externos disjuntos de 8 semanas (2011-01-03 a 2011-11-28), selección anidada de parámetros en las 8 semanas internas previas a cada origen. Cohorte fija: 2.201 artículos con ≥20 semanas positivas en las primeras 56 semanas; 105.648 observaciones artículo-semana; 2.788.116 unidades.

| Estrategia | WAPE | MAE | RMSE | Sesgo |
|---|---:|---:|---:|---:|
| **TSB (α=β seleccionado en validación interna)** | **77,21%** | 20,38 | 80,47 | -5,57% |
| Híbrido por segmentos | 77,34% | 20,41 | 80,19 | -10,59% |
| Mejor intermitente (selección interna) | 78,15% | 20,62 | 80,54 | -6,20% |
| Mejor estadístico (selección interna) | 78,50% | 20,72 | 80,40 | -5,84% |
| Promedio móvil 4 semanas (baseline) | 78,94% | 20,83 | 82,04 | -4,14% |
| Híbrido calibrado por segmento | 79,79% | 21,06 | 80,57 | +0,82% |
| HGB Hurdle Poisson (ML) | 83,52% | 22,04 | 80,86 | +9,75% |
| HGB Poisson (ML) | 83,62% | 22,07 | 81,13 | +8,91% |
| LightGBM Poisson, SKU categórico (ML) | 106,03% | 27,98 | 81,99 | +20,12% |

**Decisión:** TSB es el predictor principal (mejora al baseline en 5/6 ventanas; mediana WAPE por SKU 100,84% vs 103,34%; menor error absoluto que el baseline en 60,40% de los productos). El promedio móvil de 4 semanas queda como baseline y respaldo. La mejora es modesta (≈2,19% relativa) y el WAPE absoluto sigue alto. TSB es un método estadístico para demanda intermitente, **no** Machine Learning supervisado; los candidatos ML evaluados no superaron a los métodos estadísticos bajo este protocolo.
