# Evaluación Sumativa 3 — requisitos y estado

Asignatura TI2082 *Aplicaciones de Inteligencia Artificial* · Fecha de entrega: **25-11-2026** · Nota grupal (equipos de 2–3), cada integrante expone una parte.

## Entregables exigidos

| Entregable | Formato | Estado |
|---|---|---|
| Preinforme | **3 a 4 páginas** (sin portada), PDF o Word, nombrado con el nombre del proyecto | ✅ `StockIA_Predict_Preinforme.pdf`: portada + 3 páginas |
| Mockups | **≥5 pantallas + 1 diagrama de flujo**, PDF o enlace | ✅ `StockIA_Predict_Mockups.pdf`: 6 pantallas + flujo |
| Presentación | 5 min + 2 de preguntas, **1 diapositiva obligatoria de riesgos y supuestos** | ✅ `StockIA_Predict_Presentacion.pdf` (5 diapositivas) y `GUION_PRESENTACION.md` |

## Rúbrica (15 puntos) y cómo se cubre

| Criterio | Qué exige para 3 pts | Fuente en el proyecto | Brecha |
|---|---|---|---|
| Problema, usuario e impacto | Problema real, usuario identificado, evidencia de impacto (tiempo, costo o **errores**) con fuente verificable; **antes y después** del proceso | Doc 01; `reports/eda/`, `docs/RESULTADOS.md` | Cubierto en preinforme §1, §2, §3 y §6 |
| Justificación de IA | Por qué if/else o base de datos no bastan; **comparar ≥1 alternativa sin IA**; fundamentar el tipo de IA | `docs/RESULTADOS.md` (baselines vs TSB vs ML) | Cubierto en preinforme §4 y §5 |
| Modelo de negocio y métrica | **Lienzo de 5 filas** completo + métrica con indicador, **línea base, meta y forma de medirla** | Doc 08, `docs/business/` | Cubierto en preinforme §7 y §8 |
| Datos, riesgos y supuestos | Origen de datos; consentimiento y resguardo si hay datos personales; **≥3 riesgos con mitigación**; diapositiva de riesgos | Doc 02, Doc 07 §6, `DATASET_CITATION.md`, `docs/METODOLOGIA.md` | Cubierto en preinforme §9 y §10 y diapositiva 5 |
| Mockups y flujo | ≥5 pantallas **específicas**, flujo con **fallo de la IA / baja confianza**, IA ubicada, coherente con la métrica | `docs/entrega/mockups/` | Cubierto: ver tabla siguiente |

## Pantallas mínimas exigidas y dónde se cubren

| N.º | Exigida | Pantalla entregada |
|---|---|---|
| 1 | Inicio o acceso | 1 · Inicio / acceso |
| 2 | Ingreso de datos | 2 · Ingreso de datos (mapeo y validación) |
| 3 | Resultado de la IA con confianza o explicación | 3 · Resultado de la IA (explicación y fiabilidad histórica) |
| 4 | Historial o registro | 4 · Historial de ejecuciones |
| 5 | Corrección o métricas | 5 · Revisión y corrección · 6 · Métricas de éxito |
| — | Diagrama de flujo con fallo de la IA | 7 · Flujo (datos inválidos, baja fiabilidad, corrección del usuario) |
| — | Anotaciones de datos de entrada/salida | Cuadro «IA · datos de entrada y salida» en las pantallas 2, 3, 4, 5 y 6 |

## Puntos de honestidad que no deben perderse

- Predicción de **ventas observadas**; el dataset no tiene stock, ventas perdidas ni costos: no se afirma reducción de quiebres ni ahorro económico.
- TSB es un método estadístico, no Machine Learning supervisado; la pauta admite "Predicción" como tipo de IA.
- Mejora modesta (WAPE 77,00 % vs 78,65 %, ≈2,1 % relativa); TSB supera a la línea base en 4 de 6 bloques.
- La cobertura de stock (pantalla 3) es informativa: usa stock y plazo ingresados por el usuario, supone demanda constante y no está validada; no hay órdenes de compra automáticas ni predicción de quiebres.
- Los clientes del dataset no están etiquetados como mayoristas.
