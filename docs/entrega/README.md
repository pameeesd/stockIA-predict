# Entrega · Evaluación Sumativa 3

| Archivo | Entregable de la pauta |
|---|---|
| `StockIA_Predict_Preinforme.pdf` | Preinforme: portada + 3 páginas |
| `StockIA_Predict_Mockups.pdf` | Mockups: 6 pantallas + diagrama de flujo |
| `StockIA_Predict_Presentacion.pdf` | Presentación de 5 minutos (diapositiva de riesgos incluida) |
| `GUION_PRESENTACION.md` | Reparto entre integrantes, tiempos y preguntas probables |
| `REQUISITOS_EVALUACION_3.md` | Rúbrica y estado de cumplimiento |
| `mockups/` | Las pantallas como imágenes |
| `src/` | Fuentes HTML editables de los tres PDF |

Regenerar un PDF (Edge instalado en Windows):

```powershell
$e = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
& $e --headless=new --no-pdf-header-footer --virtual-time-budget=3000 --print-to-pdf="$PWD\StockIA_Predict_Mockups.pdf" "file:///$($PWD -replace '\','/')/src/mockups.html"
```

Cambiar `mockups` por `preinforme` o `presentacion` para los otros dos. Todas las cifras salen de `docs/RESULTADOS.md`.
