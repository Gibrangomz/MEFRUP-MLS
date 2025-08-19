"""Módulo de reportes diarios con agregación por máquina y visualizaciones.

Funciones expuestas:
    load_data(desde=None, hasta=None)
    aggregate_daily(df, machine=None)
    plot_stacked_turns(df)
    plot_daily_oee(df)
    plot_kpis(df)

Los datos de entrada son los CSVs por turno generados por la app de
inyección (campos: fecha, turno, horas_turno, tiempo_paro_min, ciclo_s,
total_pzs, scrap_pzs, buenas_pzs).  Las funciones agregan por día y, de
forma opcional, por máquina, utilizando sumas de numeradores y
nominadores para evitar promedios erróneos cuando existen múltiples
turnos.

Las gráficas utilizan seaborn con un estilo claro y etiquetas legibles.
Las leyendas y textos se muestran en español y los porcentajes se
formatean como "88%".
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Iterable, List, Optional

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Se asume que mefrupALS.py define la lista MACHINES con la ruta de los CSV
try:
    from mefrupALS import MACHINES  # type: ignore
except Exception:  # pragma: no cover - fallback vacío
    MACHINES: List[dict] = []


# ---------------------------------------------------------------------------
# Utilidades de carga de datos
# ---------------------------------------------------------------------------

NUMERIC_COLS = [
    "horas_turno",
    "tiempo_paro_min",
    "ciclo_s",
    "total_pzs",
    "scrap_pzs",
    "buenas_pzs",
]


def _read_machine_csv(machine: dict) -> pd.DataFrame:
    """Lee el CSV de OEE de una máquina y normaliza las columnas básicas."""
    path = machine["oee_csv"]
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, usecols=[
        "fecha",
        "turno",
        "horas_turno",
        "tiempo_paro_min",
        "ciclo_s",
        "total_pzs",
        "scrap_pzs",
        "buenas_pzs",
    ])
    df["maquina"] = machine.get("id", "")
    return df


def load_data(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    machines: Optional[Iterable[dict]] = None,
) -> pd.DataFrame:
    """Carga los CSV de producción por turno y regresa un DataFrame.

    Los parámetros ``desde`` y ``hasta`` son cadenas 'YYYY-MM-DD'.
    """

    machines = list(machines or MACHINES)
    frames = [_read_machine_csv(m) for m in machines]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)

    # Conversión de tipos numéricos y limpieza de outliers/NaN
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").clip(lower=0)
    df.dropna(subset=["horas_turno", "tiempo_paro_min", "total_pzs", "scrap_pzs", "buenas_pzs"], inplace=True)

    # Parseo de fechas
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
    df.dropna(subset=["fecha"], inplace=True)

    # Rango de fechas
    if desde:
        desde_dt = datetime.strptime(desde, "%Y-%m-%d").date()
        df = df[df["fecha"] >= desde_dt]
    if hasta:
        hasta_dt = datetime.strptime(hasta, "%Y-%m-%d").date()
        df = df[df["fecha"] <= hasta_dt]

    # Tiempos derivados
    df["paro_seg"] = df["tiempo_paro_min"] * 60.0
    df["turno_seg"] = df["horas_turno"] * 3600.0
    df["oper_seg"] = (df["turno_seg"] - df["paro_seg"]).clip(lower=0)
    df["perf_num"] = df["buenas_pzs"] * df["ciclo_s"]

    # Métricas por turno
    df["A"] = df["oper_seg"] / df["turno_seg"].replace({0: pd.NA})
    df["P"] = df["perf_num"] / df["oper_seg"].where(df["ciclo_s"].notna())
    df["Q"] = df["buenas_pzs"] / df["total_pzs"].replace({0: pd.NA})
    df["OEE"] = df["A"] * df["P"] * df["Q"] * 100.0

    # Elimina filas con métricas no definidas
    df.dropna(subset=["A", "P", "Q"], inplace=True)

    # Agregado "Todas" para facilitar facetas
    agg_all = (
        df.groupby(["fecha", "turno"])[
            ["turno_seg", "oper_seg", "perf_num", "total_pzs", "buenas_pzs"]
        ]
        .sum()
        .reset_index()
    )
    agg_all["A"] = agg_all["oper_seg"] / agg_all["turno_seg"].replace({0: pd.NA})
    agg_all["P"] = agg_all["perf_num"] / agg_all["oper_seg"].replace({0: pd.NA})
    agg_all["Q"] = agg_all["buenas_pzs"] / agg_all["total_pzs"].replace({0: pd.NA})
    agg_all["OEE"] = agg_all["A"] * agg_all["P"] * agg_all["Q"] * 100.0
    agg_all["maquina"] = "Todas"
    df_all = pd.concat([df, agg_all], ignore_index=True, sort=False)

    return df_all


# ---------------------------------------------------------------------------
# Agregación diaria
# ---------------------------------------------------------------------------

def aggregate_daily(df: pd.DataFrame, machine: Optional[str] = None) -> pd.DataFrame:
    """Agrega el DataFrame por día (y opcionalmente por máquina).

    ``machine`` puede ser un ``id`` de máquina o "Todas". Si es ``None``
    se regresa el agregado para todas las máquinas y el total combinado.
    """

    if machine:
        df = df[df["maquina"] == machine]

    group_cols = ["maquina", "fecha"]
    results = []
    for (maq, fecha), g in df.groupby(group_cols):
        turno_seg = g["turno_seg"].sum()
        oper_seg = g["oper_seg"].sum()

        g_perf = g[g["ciclo_s"].notna()]
        perf_num = g_perf["perf_num"].sum()
        oper_perf = g_perf["oper_seg"].sum()

        total = g["total_pzs"].sum()
        buenas = g["buenas_pzs"].sum()

        A = oper_seg / turno_seg if turno_seg > 0 else pd.NA
        P = perf_num / oper_perf if oper_perf > 0 else pd.NA
        Q = buenas / total if total > 0 else pd.NA
        OEE = A * P * Q * 100.0 if pd.notna(A) and pd.notna(P) and pd.notna(Q) else pd.NA

        results.append(
            {
                "maquina": maq,
                "fecha": fecha,
                "turnos": g["turno"].nunique(),
                "A": A,
                "P": P,
                "Q": Q,
                "OEE": OEE,
                "total_pzs": total,
                "buenas_pzs": buenas,
            }
        )

    daily = pd.DataFrame(results)
    daily.sort_values(["maquina", "fecha"], inplace=True)
    return daily


# ---------------------------------------------------------------------------
# Gráficas
# ---------------------------------------------------------------------------

sns.set_theme(style="whitegrid")


def _format_percent(ax: plt.Axes) -> None:
    """Aplica formato de porcentaje en el eje Y."""
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(lambda y, _: f"{y:.0f}%")


def plot_stacked_turns(df: pd.DataFrame, output_path: str = "stacked_turns.png") -> None:
    """Barras apiladas por día y turno para A, P, Q con línea de OEE diario."""

    machines = df["maquina"].unique()
    machines.sort()
    ncols = len(machines)
    fig, axes = plt.subplots(1, ncols, figsize=(6 * ncols, 5), sharey=True)
    if ncols == 1:
        axes = [axes]

    for ax, maq in zip(axes, machines):
        d = df[df["maquina"] == maq].copy()
        daily = aggregate_daily(df, machine=maq)
        dates = sorted(d["fecha"].unique())
        turns = sorted(d["turno"].unique())
        width = 0.8 / max(1, len(turns))
        colors = {"A": "#4c78a8", "P": "#f58518", "Q": "#54a24b"}

        for i, fecha in enumerate(dates):
            for j, turno in enumerate(turns):
                row = d[(d["fecha"] == fecha) & (d["turno"] == turno)]
                if row.empty:
                    continue
                bottom = 0
                x = i + j * width
                for metric in ["A", "P", "Q"]:
                    val = float(row.iloc[0][metric]) * 100.0
                    ax.bar(x, val, width, bottom=bottom, color=colors[metric])
                    bottom += val

        # Línea OEE por día
        ax.plot(
            [i + 0.4 for i in range(len(dates))],
            daily["OEE"].values,
            color="black",
            linewidth=1.5,
            marker="o",
            label="OEE día",
        )
        ax.set_xticks([i + 0.4 for i in range(len(dates))])
        ax.set_xticklabels([str(d) for d in dates], rotation=45, ha="right")
        _format_percent(ax)
        ax.set_xlabel("Fecha")
        ax.set_title(maq or "")

    axes[0].legend(["Availability", "Performance", "Quality"], loc="upper left")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_daily_oee(daily: pd.DataFrame, output_path: str = "oee_diario.png") -> None:
    """Serie temporal diaria: línea OEE_día con barras secundarias de buenas piezas."""

    machines = daily["maquina"].unique()
    machines.sort()
    ncols = len(machines)
    fig, axes = plt.subplots(1, ncols, figsize=(6 * ncols, 5), sharey=True)
    if ncols == 1:
        axes = [axes]

    for ax, maq in zip(axes, machines):
        d = daily[daily["maquina"] == maq]
        ax2 = ax.twinx()
        ax2.bar(d["fecha"].astype(str), d["buenas_pzs"], color="#9ecae1", label="Buenas")
        ax.plot(d["fecha"].astype(str), d["OEE"], color="black", marker="o", label="OEE")
        _format_percent(ax)
        ax.set_xlabel("Fecha")
        ax.set_title(maq or "")
        ax2.set_ylabel("Buenas")
        ax.legend(loc="upper left")
        ax2.legend(loc="upper right")
        ax.set_xticklabels(d["fecha"].astype(str), rotation=45, ha="right")

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_kpis(daily: pd.DataFrame, output_path: str = "kpis.png") -> None:
    """Gráfica horizontal de KPIs diarios con anotación del número de turnos."""

    machines = daily["maquina"].unique()
    machines.sort()
    ncols = len(machines)
    fig, axes = plt.subplots(4, ncols, figsize=(6 * ncols, 10), sharex="col")
    metrics = ["A", "P", "Q", "OEE"]
    colors = {"A": "#4c78a8", "P": "#f58518", "Q": "#54a24b", "OEE": "#333"}

    for c, maq in enumerate(machines):
        d = daily[daily["maquina"] == maq]
        for r, metric in enumerate(metrics):
            ax = axes[r, c] if ncols > 1 else axes[r]
            sns.barplot(x=d[metric] * 100.0, y=d["fecha"].astype(str), ax=ax, color=colors[metric])
            ax.set_title(f"{maq} – {metric}")
            _format_percent(ax)
            for idx, (val, turns) in enumerate(zip(d[metric], d["turnos"])):
                ax.text(
                    float(val) * 100.0 + 1,
                    idx,
                    f"turnos={turns}",
                    va="center",
                    fontsize=8,
                )
            if r < len(metrics) - 1:
                ax.set_xlabel("")

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Exportación de resumen diario
# ---------------------------------------------------------------------------

def export_daily_csv(daily: pd.DataFrame, path: str = "resumen_diario.csv") -> None:
    """Exporta el DataFrame diario a CSV."""
    daily.to_csv(path, index=False)


__all__ = [
    "load_data",
    "aggregate_daily",
    "plot_stacked_turns",
    "plot_daily_oee",
    "plot_kpis",
    "export_daily_csv",
]
