# Diagnóstico segmentado y análisis de pedidos de alto volumen

## Qué se encontró

La subestimación del pronóstico no se distribuye por igual entre los artículos. El catálogo experimental está dominado por patrones de demanda irregulares:

| Patrón | Artículos | Participación |
|---|---:|---:|
| Lumpy | 1.668 | 65,1% |
| Erratic | 716 | 27,9% |
| Intermittent | 98 | 3,8% |
| Smooth | 81 | 3,2% |

La clasificación ADI/CV² se calculó únicamente sobre las primeras 72 semanas de entrenamiento, usando los umbrales 1,32 y 0,49 descritos por Syntetos, Boylan y Croston (2005).

## Rendimiento en validación

| Segmento | Mejor candidato | WAPE | Promedio móvil 13 semanas |
|---|---|---:|---:|
| Smooth | HGB Hurdle | 48,66% | 52,94% |
| Erratic | HGB Hurdle | 66,52% | 77,25% |
| Intermittent | HGB log1p | 63,53% | 69,29% |
| Lumpy | XGBoost log1p | 82,89% | 106,81% |

El modelo global XGBoost seleccionado por WAPE en validación obtuvo WAPE 63,86% en la ventana de prueba exploratoria, pero subestimó el volumen total en 36,9%. En el período de prueba, lumpy y erratic reúnen 83,8% de las unidades observadas y XGBoost las subestima en 49,2% y 34,2%, respectivamente.

## Qué aportó el análisis de facturas

Para los 25 artículos con mayor subestimación individual se agregaron líneas por artículo y factura dentro de la ventana de prueba. La salida publicada contiene estadísticas agregadas; no se exportan números de factura ni identificadores de cliente.

- SKU 84826: una factura reúne 12.540 de 12.560 unidades observadas para el artículo (99,84%); en la ventana aparecen seis facturas y seis identificadores de cliente distintos.
- SKU 16014: las dos facturas de mayor volumen son de 3.000 y 2.000 unidades. Ambas están asociadas al mismo identificador anonimizado de cliente y juntas equivalen al 75,4% de las 6.632 unidades observadas.
- SKU 84077: la factura individual mayor representa 29,0% de las 16.550 unidades del artículo.
- SKU 21787: la factura individual mayor representa 31,8% de las 5.629 unidades.
- SKU 22197: la factura mayor representa solo 8,2% de las 24.209 unidades, por lo que la subestimación también aparece en productos con actividad más distribuida (539 facturas).

UCI señala que muchos clientes de la empresa son mayoristas, pero el dataset no identifica formalmente cuáles lo son. Por tanto, las operaciones se describen como pedidos de alto volumen o patrones compatibles con compra mayorista, no como mayoristas confirmados.

Además, el error no depende de unas pocas facturas extremas: los 10, 25 y 50 artículos con mayor subestimación acumulan aproximadamente 11,9%, 20,7% y 29,5% de las unidades subestimadas.

## Interpretación

La evidencia apunta a dos dificultades relacionadas pero distintas:

1. **Demanda intermitente o variable:** los artículos lumpy y erratic concentran casi todo el catálogo y gran parte del volumen. Un modelo basado en rezagos y promedios tiende a suavizar picos que no tienen regularidad suficiente en el historial.
2. **Pedidos excepcionales de alto volumen:** algunas facturas individuales explican una parte muy grande de las ventas de un artículo en la ventana. Si ocurren con poca frecuencia, las características históricas no anticipan el salto.

No sería correcto eliminar automáticamente las facturas grandes: podrían ser ventas legítimas. Tampoco bastaría con un factor multiplicador para todos los pronósticos, porque los 50 artículos con mayor subestimación explican menos de un tercio del faltante estimado.

## Decisiones de diseño para StockIA

- Mantener un pronóstico base de unidades vendidas por artículo y semana.
- Evaluar métodos especializados de demanda intermitente (Croston, SBA y TSB) y modelos segmentados.
- Incorporar un detector separado de eventos o pedidos excepcionales, utilizando magnitud de factura, frecuencia y recurrencia.
- Mostrar la explicación, la incertidumbre y la evidencia histórica al usuario.
- Solicitar validación humana antes de convertir un evento extraordinario en una recomendación de compra.
- No automatizar reposición ni prometer reducción de quiebres hasta contar con inventario disponible, ventas no satisfechas, órdenes de compra, plazos y costos.

## Limitaciones experimentales

La ventana final de prueba fue inspeccionada durante este análisis. No debe reutilizarse como holdout ciego para seleccionar nuevas variantes. El siguiente ciclo debe usar backtesting de origen móvil con varios cortes temporales y, si es posible, reservar un período nuevo no consultado.
