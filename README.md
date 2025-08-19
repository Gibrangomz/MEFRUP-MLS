# MEFRUP-MLS

Aplicación de monitoreo y reportes de producción.

## Dependencias

Instalar las librerías necesarias:

```bash
pip install customtkinter pillow tkcalendar matplotlib plotly kaleido pandas fpdf openpyxl
```

La vista de reportes permite exportar los datos a PDF o Excel, incluyendo tiempos de paro y métricas diarias.

### Módulo de reportes

`mefrupALS.py` expone funciones de visualización con Plotly:

- `plot_turnos(df)`: barras A/P/Q y línea OEE por turno o día.
- `panel_kpis(df)`: resumen horizontal de KPIs del periodo.
- `kpi_card(df)`: tarjeta con métricas agregadas y estadísticas.
- `heatmap_oee(df)`: mapa de calor OEE día vs turno.

Las funciones aceptan un `DataFrame` filtrado por máquina y fechas. Las
columnas de porcentaje pueden venir en escala 0‑1 o 0‑100; el módulo las
normaliza automáticamente y devuelve `plotly.graph_objects.Figure` listo para
integrar en otras vistas.
