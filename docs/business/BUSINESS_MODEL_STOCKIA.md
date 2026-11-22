# StockIA Predict — Modelo de negocio y propuesta de valor

> Documento de trabajo. Diferencia hechos, resultados experimentales, decisiones de diseño e hipótesis pendientes.

## Posicionamiento propuesto

StockIA es una herramienta SaaS B2B de apoyo a la planificación de demanda. Recibe históricos de ventas, valida calidad, clasifica patrones de demanda y produce pronósticos semanales por producto junto con alertas explicables de eventos inusuales. El motor seleccionado en el benchmark es TSB, un método estadístico especializado, no un modelo de Machine Learning. En su alcance inicial StockIA no sustituye un POS/ERP, no conoce existencias y no automatiza compras.

## Organización de referencia

UCI Online Retail II describe un comercio electrónico británico no presencial cuya identidad comercial no está publicada, que vende artículos de regalo y cuyos clientes incluyen mayoristas. Los datos cubren 01-12-2009 a 09-12-2011 y contienen 1.067.371 líneas. CustomerID es un identificador numérico; no debe asumirse anonimización legal. Los datos no permiten demostrar problemas de inventario. Fuente: [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii), Chen (2012), DOI 10.24432/C5CG6D.

## Cliente objetivo (hipótesis)

Comercios electrónicos pequeños y medianos con catálogo heterogéneo, patrones de venta regulares e intermitentes y pedidos ocasionales de gran volumen. La hipótesis debe validarse mediante entrevistas; no se infiere el tamaño de la empresa de referencia.

## Propuesta de valor

"Para comercios electrónicos con catálogos heterogéneos, StockIA convierte el historial de ventas en pronósticos semanales por producto y alertas de excepción explicables, ayudando al equipo a concentrar la revisión en SKU y eventos que generan mayor incertidumbre, sin reemplazar inicialmente su plataforma de comercio o ERP."

## Alcance inicial

- Ingesta por CSV/Excel y validación de calidad.
- Forecast semanal por SKU.
- Segmentación del patrón de demanda (smooth, erratic, intermittent, lumpy).
- Cola de alertas de volúmenes transaccionales inusuales.
- Explicación del pronóstico y visualización del historial.
- Exportación de resultados.

Fuera de alcance hasta obtener datos: cálculo de stock de seguridad, predicción de quiebres, cantidades de compra y automatización de purchase orders. El dataset no contiene stock, órdenes pendientes, lead times o costes.

## Competencia

| Competidor | Capacidades publicadas | Referencia de precio publicada |
|---|---|---|
| Prediko | AI demand/supply planning, forecasts, purchase orders, alerts, 150+ integrations | Desde US$49/mes para tramo de menor volumen |
| StockTrim | ML inventory forecasting, order planning, lead times variables, multi-location, API | Precio según ingresos; la página mostró US$298/mes para US$3–5M anual |
| Inventory Planner | Forecast por SKU, replenishment, POs, integraciones, stockout history | Según volumen de inventario; cotización |
| Netstock | SKU classification, safety stock, forecasting/ordering, AI order optimizer | Essentials desde US$900/mes |

Las funciones y precios son datos publicados por los proveedores; no constituyen una comparación independiente. Ninguna de las funciones generales de forecast/AI es exclusiva de StockIA. La diferenciación propuesta es una hipótesis de nicho: forecast diagnóstico y explicable para catálogos irregulares y eventos de volumen, con entrada ligera por archivo.

## Modelo de ingresos

B2B SaaS con suscripción mensual por establecimiento y tramo de SKU/volumen analizado. Servicio puntual de onboarding/mapeo de datos. No fijar tarifa hasta validar disposición a pagar y coste de servicio. Probar £19, £39 y £59 al mes como estímulos de investigación, no como precios comerciales aprobados.

## Métricas

- Técnica: WAPE, MAE, RMSE, sesgo agregado y cobertura por SKU.
- Producto: tiempo de preparación semanal, revisión de alertas, tasa de uso de pronósticos.
- Comercial: pilotos pagados y conversión a suscripción.
- Futuro: quiebres/sobrestock solo con inventario y compras históricas.

Resultado actual: TSB WAPE 77.21% frente a 78.94% del promedio móvil 4 semanas; mejora relativa aproximada 2.19%, WAPE absoluto alto y sesgo TSB -5.57%. Es una evidencia académica limitada, no prueba de beneficio económico ni readiness de producción.

## Validación comercial

1. 8–12 entrevistas con responsables de e-commerce/operaciones.
2. Test de prototipo y comprensión de pronósticos/alertas.
3. Piloto con datos recientes y autorizados de 6–24 meses.
4. Comparar con el método actual del cliente usando rolling backtest.
5. Probar disposición a pagar y solicitar al menos dos pilotos pagados antes de integraciones complejas.

Gate técnico propuesto: mejora relativa de WAPE ≥5% frente al baseline del cliente, sesgo entre -10% y +10% y cobertura ≥80% del catálogo elegible. Estos son criterios internos de decisión, no resultados conseguidos.

## Privacidad y seguridad

Minimizar campos personales, excluir customer IDs del forecast base, usar agregación/seudonimización cuando sea necesario, separación por cliente, RBAC, cifrado, retención limitada y borrado. Para operación en Reino Unido, revisar UK GDPR y guidance ICO; este archivo no es asesoría jurídica.

## Fuentes

- Chen, D. (2012). [Online Retail II, UCI](https://archive.ics.uci.edu/dataset/502/online+retail+ii).
- [Prediko pricing](https://www.prediko.io/pricing).
- [StockTrim pricing](https://www.stocktrim.com/pricing).
- [Inventory Planner pricing](https://www.inventory-planner.com/pricing/).
- [Inventory Planner forecast configuration](https://help.inventory-planner.com/en/articles/638170-configuring-the-forecast).
- [Netstock packages](https://www.netstock.com/packages/).
- [ICO — Data minimisation](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-protection-principles/a-guide-to-the-data-protection-principles/data-minimisation/).
- [ICO — Pseudonymisation](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/anonymisation/pseudonymisation/).
- [ICO — Data security](https://ico.org.uk/for-organisations/uk-GDPR-guidance-and-resources/security/a-guide-to-data-security/).
