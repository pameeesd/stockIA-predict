# Protocolo del primer experimento de predicción

## Unidad y objetivo

- Mercado: Reino Unido.
- Unidad: `StockCode` normalizado × semana calendario.
- Objetivo: suma de unidades positivas vendidas en la semana siguiente.
- Horizonte: un paso adelante (una semana).
- Frecuencia: 104 semanas completas entre 2009-12-07 y 2011-11-28.

## Selección temporal de artículos

Se seleccionan artículos con al menos 20 semanas de ventas positivas dentro de las primeras 72 semanas. La selección no utiliza las semanas de validación ni prueba. Se excluyen provisionalmente seis códigos de cargos/servicios/vales que deben verificarse contra el catálogo.

## Particiones

| Partición | Índices de semana objetivo | Fechas |
|---|---|---|
| Entrenamiento | 13–71 | 2010-03-08 a 2011-04-18 |
| Validación | 72–87 | 2011-04-25 a 2011-08-08 |
| Prueba exploratoria | 88–103 | 2011-08-15 a 2011-11-28 |

El contexto inicial de 13 semanas se utiliza para crear características. El protocolo es de origen móvil un paso adelante: antes de pronosticar cada semana se consideran disponibles las ventas reales de semanas previas.

## Características

Rezagos 1, 2, 3, 4, 8, 13 y 52; medias móviles de 4, 8, 13, 26 y 52 semanas; desviación estándar de cuatro semanas; número de semanas activas en trece semanas; máximo de trece semanas; diferencia entre medias; nivel histórico; tasa de actividad; media de valores positivos; coeficiente de variación histórico; y codificación seno/coseno de semana ISO.

Todas las características se calculan usando semanas anteriores al objetivo.

## Modelos

- Baselines: última semana, promedio móvil de 4 semanas, promedio móvil de 13 semanas y naive estacional de 52 semanas.
- HistGradientBoosting sobre `log1p(y)`.
- HistGradientBoosting con pérdida Poisson sobre la escala original no negativa.
- Modelo hurdle: clasificador de ocurrencia de venta y regresor de cantidad condicionada a venta.
- XGBoost sobre `log1p(y)`, con parada temprana en validación.

## Métricas

- MAE: error absoluto medio por combinación producto-semana.
- RMSE: raíz del error cuadrático medio, sensible a errores grandes.
- WAPE: suma de errores absolutos / suma de valores reales × 100.
- Sesgo agregado: (suma predicha − suma real) / suma real × 100.

## Advertencias

El período de prueba no se utilizó para ajustar parámetros, pero ya fue inspeccionado al comparar variantes exploratorias. No es un holdout completamente ciego para futuras iteraciones. La selección definitiva requiere backtesting temporal con múltiples orígenes y, de ser posible, un conjunto independiente adicional.
