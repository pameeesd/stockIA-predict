# Resultados oficiales

Única fuente de cifras del proyecto. Todo número citado en el preinforme, los mockups y la presentación debe salir de aquí (`reports/backtesting/`). Los resultados de etapas previas están en `reports/archive_v0.3/` y no deben citarse.

**Alcance:** pronóstico de **ventas observadas** por artículo y semana, Reino Unido, 2009-12 a 2011-11 (104 semanas completas). El dataset no contiene stock, ventas perdidas, órdenes de compra, plazos ni costos: los resultados **no** demuestran reducción de quiebres ni ahorro económico.

## Diseño de la evaluación

- Cohorte fija: 2.201 artículos con ≥20 semanas de venta positiva en las primeras 56 semanas; 1.957 tienen ventas en el período evaluado.
- 6 bloques externos disjuntos de 8 semanas (2011-01-03 a 2011-11-28), pronóstico de un paso adelante (rolling).
- En cada bloque, el candidato y su parámetro se eligen solo con las 8 semanas inmediatamente anteriores.
- 105.648 observaciones artículo-semana · 2.788.116 unidades reales.
- Métrica principal: **WAPE** = Σ|error| / Σ ventas reales. También MAE, RMSE y sesgo agregado.

## Resultado global (fuera de muestra)

| Estrategia | WAPE | MAE | RMSE | Sesgo |
|---|---:|---:|---:|---:|
| Híbrido por segmentos | 75,93 % | 20,04 | 80,09 | -13,45 % |
| **TSB (α=β elegido en validación interna)** | **77,00 %** | 20,32 | 80,29 | -6,13 % |
| Mejor método estadístico (selección interna) | 77,73 % | 20,51 | 80,06 | -7,14 % |
| Mejor método intermitente (selección interna) | 77,80 % | 20,53 | 80,33 | -6,95 % |
| HGB Hurdle Poisson (ML) | 78,41 % | 20,69 | 80,42 | -1,10 % |
| **Promedio móvil 4 semanas (baseline)** | **78,65 %** | 20,76 | 81,84 | -4,77 % |
| Híbrido calibrado por segmento | 79,28 % | 20,92 | 80,67 | -0,49 % |
| HGB Poisson (ML) | 79,42 % | 20,96 | 84,47 | -0,27 % |
| LightGBM Poisson, SKU categórico (ML) | 79,88 % | 21,08 | 81,41 | -0,25 % |
| Promedio móvil 13 semanas | 83,56 % | 22,05 | 81,37 | -0,34 % |
| SBA (selección interna) | 84,40 % | 22,27 | 84,31 | -15,96 % |
| Última semana | 90,25 % | 23,82 | 102,24 | -3,02 % |
| Croston (selección interna) | 92,14 % | 24,32 | 84,52 | +9,03 % |

TSB reduce el WAPE 1,65 puntos porcentuales frente al baseline (≈ **2,10 %** relativo).

## Estabilidad por bloque (WAPE)

| Bloque | Baseline mean4 | TSB | Híbrido | α elegido (TSB) |
|---|---:|---:|---:|---:|
| 1 (ene–feb) | 88,05 % | 88,15 % | 88,59 % | 0,50 |
| 2 (feb–abr) | 79,78 % | 80,22 % | 77,62 % | 0,50 |
| 3 (abr–jun) | 84,61 % | 81,90 % | 79,69 % | 0,30 |
| 4 (jun–ago) | 79,54 % | 77,82 % | 77,55 % | 0,20 |
| 5 (ago–oct) | 76,56 % | 74,38 % | 73,10 % | 0,30 |
| 6 (oct–nov) | 69,03 % | 65,98 % | 65,43 % | 0,20 |

TSB supera al baseline en **4 de 6** bloques (pierde por poco en los dos primeros); el híbrido, en 5 de 6.

## Por patrón de demanda (recalculado en cada origen)

| Segmento | Unidades reales | Baseline | TSB | Híbrido |
|---|---:|---:|---:|---:|
| Smooth | 455.194 | 52,80 % | 51,81 % | 49,97 % |
| Erratic | 1.526.430 | 77,93 % | 76,00 % | 74,18 % |
| Intermittent | 73.735 | 69,79 % | 69,33 % | 68,91 % |
| Lumpy | 732.757 | 97,10 % | 95,51 % | 96,40 % |

## Por producto (1.957 artículos con ventas)

| Estrategia | Mediana WAPE | Media WAPE | % productos mejor que mean4 |
|---|---:|---:|---:|
| TSB | 100,73 % | 120,61 % | 59,17 % |
| Híbrido por segmentos | 101,81 % | 165,25 % | 49,16 % |
| Baseline mean4 | 103,06 % | 109,56 % | — |
| HGB Hurdle (ML) | 111,11 % | 184,39 % | 31,99 % |

## Decisión

**TSB es el predictor principal de la solución; el promedio móvil de 4 semanas queda como baseline y respaldo.** Es una decisión ajustada:

- A favor de TSB: menor sesgo que el híbrido (-6,13 % vs -13,45 %), mejora al baseline en más productos (59 % vs 49 %), es un método único, transparente y explicable.
- A favor del híbrido: menor WAPE agregado (-1,07 pp) y mejora al baseline en 5 de 6 bloques; pero subestima más y depende de elegir entre muchos candidatos.
- Ningún modelo ML evaluado supera claramente a TSB. HGB Hurdle queda cerca del baseline (78,41 % vs 78,65 %) sin ventaja práctica.
- **TSB es un método estadístico de pronóstico para demanda intermitente, no Machine Learning supervisado.**

## Limitaciones

- WAPE absoluto alto (≈77 %): la mejora es modesta y no basta para automatizar decisiones.
- Ventas observadas ≠ demanda real; sin inventario ni ventas perdidas.
- Cohorte de artículos incumbentes (≥20 semanas activas en las primeras 56); productos nuevos quedan fuera.
- Un paso adelante, no un pronóstico fijo de varias semanas.
- La clase de cliente no está etiquetada: una factura grande no prueba que el comprador sea mayorista.
- Datos históricos del Reino Unido (2009–2011).
- Los modelos ML usan hiperparámetros fijos; la conclusión se limita a lo probado.

## Hallazgos de apoyo (diagnóstico previo, v0.3)

En el diagnóstico exploratorio se observó que la mayor parte del catálogo es irregular (65 % lumpy, 28 % erratic, 4 % intermittent, 3 % smooth) y que algunas facturas individuales concentran gran parte del volumen de un artículo (p. ej. una factura reúne 99,8 % de las unidades de un SKU en la ventana de prueba). Esos conteos y ejemplos están en `reports/archive_v0.3/` y son cualitativamente válidos, pero **sus cifras de error** fueron calculadas con un panel que contaba dos semanas por duplicado (ver `docs/METODOLOGIA.md`) y no deben citarse.
