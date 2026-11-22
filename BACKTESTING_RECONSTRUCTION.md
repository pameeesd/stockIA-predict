# Reconstrucción del backtesting multi-origen (Documento 06)

El código original del experimento del Documento 06 no estaba disponible. `scripts/05_backtesting_model_selection.py` lo reconstruye a partir del protocolo descrito en el documento y del panel semanal incluido en `data/processed/`. Las salidas están en `reports/backtesting/`.

```bash
python scripts/05_backtesting_model_selection.py            # completo (~1-2 min)
python scripts/05_backtesting_model_selection.py --skip-ml  # solo métodos estadísticos
```

## Protocolo implementado

- Cohorte fija: 2.201 artículos con ≥20 semanas positivas en las primeras 56 semanas (excluye `DOT`, `M`, `C2`, `POST`, `BANK CHARGES`, `GIFT_0001_30`).
- Seis orígenes (índices 56, 64, 72, 80, 88, 96): bloque externo de 8 semanas; selección de candidato/parámetro solo con las 8 semanas internas previas.
- Un paso adelante en modo rolling.
- TSB con α = β ∈ {0,05; 0,10; 0,20; 0,30; 0,40; 0,50}, inicializado en la primera venta positiva (p = 1, z = y).
- Croston y SBA (factor 1 − α/2) con el mismo α para tamaño e intervalo; intervalo inicial = semanas hasta la primera venta.
- Segmentación ADI/CV² (1,32 / 0,49) recalculada en cada origen con el historial anterior.
- ML reentrenado en cada origen con hiperparámetros fijos: HGB Poisson, HGB Hurdle Poisson (clasificador × regresor Poisson) y LightGBM Poisson con SKU categórico, usando las variables de `scripts/02_train_forecasting_models.py`.

## Verificación contra el Documento 06

| Resultado | Documento 06 | Reconstrucción | ¿Coincide? |
|---|---:|---:|:-:|
| Artículos en cohorte / con ventas externas | 2.201 / 1.957 | 2.201 / 1.957 | ✅ |
| Unidades reales evaluadas | 2.788.116 | 2.788.116 | ✅ |
| TSB seleccionado: WAPE / sesgo | 77,21% / -5,57% | 77,21% / -5,57% | ✅ |
| α elegidos por fold (TSB) | 0,5 · 0,5 · 0,3 · 0,3 · 0,3 · 0,2 | igual | ✅ |
| TSB por fold | 89,63 · 80,29 · 82,00 · 77,64 · 74,38 · 65,99 | igual | ✅ |
| Promedio móvil 4: WAPE / sesgo | 78,94% / -4,14% | 78,94% / -4,14% | ✅ |
| Mejor intermitente seleccionado | 78,15% / -6,20% | 78,15% / -6,20% | ✅ |
| Mejor estadístico seleccionado | 78,50% / -5,84% | 78,50% / -5,84% | ✅ |
| Unidades por segmento (smooth/erratic/intermittent/lumpy) | 436.270 / 1.545.354 / 63.792 / 742.700 | igual | ✅ |
| WAPE TSB y mean4 por segmento | ver Doc 06 §7 | igual | ✅ |
| TSB mediana / media WAPE por SKU; % mejor que mean4 | 100,84% / 121,82% / 60,40% | igual | ✅ |
| HGB Poisson (ML) | 83,62% / +8,91% | 79,35% / +1,18% | ❌ |
| HGB Hurdle Poisson (ML) | 83,52% / +9,75% | 80,31% / +3,38% | ❌ |
| LightGBM Poisson SKU (ML) | 106,03% / +20,12% | 82,37% / +6,96% | ❌ |
| Híbrido por segmentos | 77,34% / -10,59% | 76,38% / -13,40% | ❌ |
| Híbrido calibrado | 79,79% / +0,82% | 80,32% / +1,02% | ❌ |

**Todo el componente estadístico, incluido el modelo seleccionado (TSB), se reproduce exactamente.** Los modelos ML no coinciden porque el Documento 06 no especifica sus variables ni hiperparámetros; la reconstrucción usa las variables del benchmark inicial y parámetros fijos razonables. Como los híbridos pueden elegir candidatos ML, también difieren. Se probaron variantes del pool del híbrido solo con candidatos estadísticos (75,6–76,5% WAPE) y ninguna reproduce el 77,34%.

## Implicaciones para la decisión

La decisión del Documento 06 se mantiene con la reconstrucción:

- Los ML reconstruidos rinden mejor que los del documento, pero **siguen sin superar a TSB ni al promedio móvil de 4 semanas** (79,35% el mejor).
- El híbrido reconstruido obtiene menor WAPE agregado (76,38%), pero con **mayor subestimación (-13,40%)** y mejora al baseline solo en el **49,36% de los productos** (TSB: 60,40%). Por los criterios del documento (sesgo, rendimiento por SKU y estabilidad), TSB sigue siendo el candidato principal.
- Las cifras ML e híbridas de esta reconstrucción no deben sustituir a las del Documento 06 sin una nota metodológica; si se actualiza el documento, conviene citar este script como fuente reproducible.
