# Dataset: Online Retail II — atribución y cambios

## Atribución requerida

Chen, D. (2012). *Online Retail II*. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D

Registro oficial: https://archive.ics.uci.edu/dataset/502/online+retail+ii

Licencia del dataset: Creative Commons Attribution 4.0 International (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/

## Organización descrita

El registro de UCI describe un comercio minorista británico no basado en tiendas físicas cuya identidad se mantiene anonimizada. Este proyecto no inventa ni atribuye un nombre comercial a esa organización.

## Modificaciones realizadas para el análisis

1. Se leen y combinan las dos hojas del libro de Excel.
2. Se eliminan duplicados exactos en la copia analítica, sin modificar el archivo original (incluye el solapamiento del 1 al 9 de diciembre de 2010 entre las dos hojas del libro).
3. Se excluyen del objetivo de ventas las facturas identificadas como cancelaciones (prefijo `C`) y las cantidades no positivas.
4. Se filtran registros de `Country = United Kingdom`.
5. Se normaliza `StockCode` a mayúsculas antes de agrupar, fusionando variantes que solo difieren por uso de mayúsculas/minúsculas.
6. Se excluyen los bordes temporales parciales y se reconstruyen 104 semanas calendario completas entre 2009-12-07 y 2011-11-28.
7. Se agregan cantidades positivas por código de artículo y semana.
8. En el panel de modelado, una combinación producto-semana sin una venta registrada se representa como cero. Esto no prueba que hubiera inventario disponible.
9. Se excluyen provisionalmente seis códigos de cargos/servicios/vales: `DOT`, `M`, `C2`, `POST`, `BANK CHARGES` y `GIFT_0001_30`. La revisión completa del catálogo continúa pendiente.

## Limitaciones de uso e interpretación

- Los datos son históricos (2009–2011) y no describen por sí solos el mercado actual.
- La base no contiene existencias, disponibilidad, ventas perdidas, roturas de stock, órdenes de compra, proveedores, plazos de entrega, costos de adquisición ni márgenes.
- Las cantidades registradas representan ventas observadas, no demanda latente.
- `CustomerID` no se utiliza en el modelo ni en las predicciones publicadas.

## Alcance de la licencia

CC BY 4.0 permite compartir y adaptar el material con atribución, enlace a la licencia e indicación de cambios. Esta atribución se mantiene junto con los datos derivados distribuidos en este repositorio. La licencia del dataset no determina la licencia del código fuente del proyecto.
