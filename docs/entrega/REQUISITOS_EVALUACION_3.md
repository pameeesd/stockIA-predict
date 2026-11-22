# Evaluación Sumativa 3 — requisitos y estado

Asignatura TI2082 *Aplicaciones de Inteligencia Artificial* · Fecha de entrega: **25-11-2026** · Nota grupal (equipos de 2–3), cada integrante expone una parte.

## Entregables exigidos

| Entregable | Formato | Estado |
|---|---|---|
| Preinforme | **3 a 4 páginas** (sin portada), PDF o Word, nombrado con el nombre del proyecto | Pendiente de redactar (los Docs 01–08 suman decenas de páginas: pasan a ser evidencia de apoyo) |
| Mockups | **≥5 pantallas + 1 diagrama de flujo**, PDF o enlace | Parcial: ver brechas |
| Presentación | 5 min + 2 de preguntas, **1 diapositiva obligatoria de riesgos y supuestos** | Pendiente |

## Rúbrica (15 puntos) y cómo se cubre

| Criterio | Qué exige para 3 pts | Fuente en el proyecto | Brecha |
|---|---|---|---|
| Problema, usuario e impacto | Problema real, usuario identificado, evidencia de impacto (tiempo, costo o **errores**) con fuente verificable; **antes y después** del proceso | Docs 01, 03, 05; `reports/segment_diagnostics/` | Falta redactar el antes/después y fijar quién decide la adopción |
| Justificación de IA | Por qué if/else o base de datos no bastan; **comparar ≥1 alternativa sin IA**; fundamentar el tipo de IA | Doc 06 (baselines vs TSB vs ML) | Dejar explícito que el tipo es **Predicción**, TSB es estadístico adaptativo y que el ML evaluado no lo superó |
| Modelo de negocio y métrica | **Lienzo de 5 filas** completo + métrica con indicador, **línea base, meta y forma de medirla** | Doc 08, `docs/business/` | Falta formato de lienzo y una **meta** numérica clara |
| Datos, riesgos y supuestos | Origen de datos; consentimiento y resguardo si hay datos personales; **≥3 riesgos con mitigación**; diapositiva de riesgos | Docs 02, 03, 07 §6, `DATASET_CITATION.md` | Resumir en una tabla de riesgos con mitigación |
| Mockups y flujo | ≥5 pantallas **específicas**, flujo con **fallo de la IA / baja confianza**, IA ubicada, coherente con la métrica | `docs/design/mockups/` | Ver abajo |

## Pantallas mínimas exigidas vs mockups actuales

| N.º | Exigida | Mockup actual | Estado |
|---|---|---|---|
| 1 | Inicio o acceso | — | ❌ falta |
| 2 | Ingreso de datos | 02 Datos y validación | ✅ |
| 3 | Resultado de la IA con confianza o explicación | 04 Pronóstico por producto | ✅ (explicación; el modelo no calcula confianza) |
| 4 | Historial o registro (persistencia) | — | ❌ falta |
| 5 | Corrección/validación o panel de la métrica de éxito | 05 Alertas (revisión humana) | ⚠️ parcial; falta panel de métrica (WAPE vs línea base) |
| — | Diagrama de flujo con rama de error de la IA | 00 Flujo funcional (lineal) | ⚠️ falta qué ocurre si la IA falla o no tiene confianza |
| — | Anotaciones de datos de entrada/salida en pantallas con IA | — | ❌ falta |

Pantallas 01 (Resumen) y 03 (Segmentación) sobran como mínimo exigido, pero pueden quedar como apoyo.

## Puntos de honestidad que no deben perderse

- Predicción de **ventas observadas**; el dataset no tiene stock, ventas perdidas ni costos: no se afirma reducción de quiebres ni ahorro económico.
- TSB es un método estadístico, no Machine Learning supervisado; la pauta admite "Predicción" como tipo de IA.
- Mejora modesta (WAPE 77,21 % vs 78,94 %, ≈2,19 % relativa).
- Los clientes del dataset no están etiquetados como mayoristas.
