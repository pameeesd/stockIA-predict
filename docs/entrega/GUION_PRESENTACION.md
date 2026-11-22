# Guion de la presentación (5 min + 2 de preguntas)

Archivos: `StockIA_Predict_Presentacion.pdf` (5 diapositivas) y `StockIA_Predict_Mockups.pdf` (se muestra directamente, sin rehacerlo en diapositivas).

| Tiempo | Quién | Qué muestra | Idea clave |
|---|---|---|---|
| 0:00–0:10 | Pamela | Diapositiva 1 | Quiénes somos y cuál es nuestro caso: el comercio electrónico británico anonimizado del dataset público de UCI, con sus datos reales. |
| 0:10–1:10 | Pamela | Diapositiva 2 · Caso, problema e impacto | Qué es el negocio y por qué lo elegimos (datos reales y abiertos, catálogo heterogéneo, típico de una pyme). La demanda es irregular: 62 % de semanas sin venta, 81 % de las unidades en artículos irregulares, 78,65 % de error del método actual. Ejemplo del artículo 84826. Antes/después. |
| 1:10–1:40 | Pamela | Diapositiva 3 · ¿Por qué IA? | Reglas y SQL no bastan; TSB reduce el error ≈2,1 %; es predicción estadística adaptativa, no ML; el ML no lo superó. |
| 1:40–3:40 | Pablo | **PDF de mockups** (pantallas 1–6 y flujo) | Recorrido: acceso → carga y validación → resultado de la IA (fiabilidad) → historial → revisión y corrección → métricas. Mostrar dónde interviene la IA (cuadros verdes), el panel opcional de cobertura de stock (pantalla 3) y el flujo cuando la IA falla o no tiene confianza. |
| 3:40–4:25 | Pamela | Diapositiva 4 · Modelo de negocio y métrica | Lienzo en una frase por bloque; WAPE 78,65 % → 77,00 %; meta de piloto ≥5 % por validar. |
| 4:25–5:00 | Pablo | Diapositiva 5 · Riesgos y supuestos | Cinco riesgos con mitigación; recalcar que la mejora es modesta y que no se afirma ahorro ni reducción de quiebres. |

## Preguntas probables y respuestas

- **¿Por qué TSB no es Machine Learning si la asignatura es de IA?** Porque la pauta admite *Predicción* como tipo de IA. TSB es un método predictivo adaptativo; además evaluamos ML supervisado (HGB, LightGBM) y no mejoró, y preferimos no presentar como ML lo que no lo es.
- **¿Un 77 % de error significa que falla más de lo que acierta?** No. El WAPE son las unidades de error divididas por las unidades vendidas; no es el porcentaje de predicciones erradas ni una probabilidad de acierto. Indica que, por producto y por semana, el pronóstico es aproximado porque la demanda es muy irregular (62 % de las semanas sin venta). En el total acumulado el sesgo es de solo −6,13 %. Por eso mostramos fiabilidad y referencia, y la decisión es de la persona.
- **¿La mejora de 2,1 % es relevante?** Es modesta y lo decimos. El valor está en clasificar el patrón de cada producto, mostrar fiabilidad y detectar pedidos extraordinarios; la meta de 5 % se valida en un piloto con datos reales.
- **¿Cuánto dinero ahorra?** No lo sabemos: el dataset no tiene stock, ventas perdidas ni costos. La evidencia de impacto es el error de pronóstico.
- **¿Qué pasa si la IA no tiene confianza?** Se marca «Fiabilidad baja» (menos de 20 semanas de historia o patrón lumpy), se muestra la referencia junto al pronóstico y se pide revisión manual.
- **¿Recomienda cuánto comprar?** Ofrece una cobertura de stock informativa: con el stock y el plazo que ingresa el usuario, calcula cuántas semanas le alcanza y una cantidad referencial (pronóstico × (plazo + seguridad) − stock). No es una orden de compra ni está validada, porque el dataset no tiene inventario ni plazos; es aritmética sobre el pronóstico, no un modelo de IA. Validarla es fase futura.
- **¿Los clientes grandes son mayoristas?** No lo podemos afirmar: el dataset no etiqueta clientes.
- **¿Dónde están los datos y el código?** Dataset público de UCI (CC BY 4.0); código y resultados en github.com/pameeesd/stockIA-predict.
- **¿Hablaron con la empresa del caso?** No. La empresa está anonimizada en el dataset; usamos sus transacciones reales como caso de estudio y nos ubicamos como equipo que le propone la solución. Las conclusiones valen para ese negocio y período (Reino Unido, 2009–2011).
- **¿Usaron datos personales?** El Customer ID viene seudonimizado en el dataset, no se usa en el modelo ni se muestra.

Cada integrante debe poder explicar su parte y responder al menos una pregunta.
