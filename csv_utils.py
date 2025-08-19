# -*- coding: utf-8 -*-
"""Utility helpers for dealing with CSV files."""

import csv
import os
from typing import List, Dict

from config import (
    DAILY_CSV_GLOBAL,
    DAILY_CSV_INJECTOR,
    RECIPES_CSV,
    PLANNING_CSV,
    DELIV_CSV,
    SHIPMENTS_CSV,
)


def asegurar_csv(path: str, header: List[str]) -> None:
    """Ensure a CSV file exists with the provided header."""
    try:
        with open(path, "x", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)
    except FileExistsError:
        pass


def leer_csv_dict(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def leer_shipments() -> List[Dict[str, str]]:
    """Read shipments.csv guaranteeing the 'approved' column."""
    rows = leer_csv_dict(SHIPMENTS_CSV)
    for r in rows:
        if "approved" not in r or r.get("approved") == "":
            r["approved"] = "1"
    return rows


def escribir_daily(path: str, fecha_iso: str, oee_pct: float, total: int, scrap: int, meta: int) -> None:
    asegurar_csv(path, ["fecha", "oee_dia_%", "total_pzs", "scrap_pzs", "meta_pzs"])
    rows = leer_csv_dict(path)
    for r in rows:
        if r.get("fecha") == fecha_iso:
            r["oee_dia_%"] = f"{oee_pct:.2f}"; r["total_pzs"] = str(total)
            r["scrap_pzs"] = str(scrap); r["meta_pzs"] = str(meta)
            break
    else:
        rows.append({
            "fecha": fecha_iso,
            "oee_dia_%": f"{oee_pct:.2f}",
            "total_pzs": str(total),
            "scrap_pzs": str(scrap),
            "meta_pzs": str(meta),
        })
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["fecha", "oee_dia_%", "total_pzs", "scrap_pzs", "meta_pzs"])
        w.writeheader(); w.writerows(rows)


def fechas_registradas(path_daily: str):
    asegurar_csv(path_daily, ["fecha", "oee_dia_%", "total_pzs", "scrap_pzs", "meta_pzs"])
    return {r["fecha"] for r in leer_csv_dict(path_daily) if r.get("fecha")}


def asegurar_archivos_basicos() -> None:
    asegurar_csv(DAILY_CSV_GLOBAL, ["fecha", "oee_dia_%", "total_pzs", "scrap_pzs", "meta_pzs"])
    asegurar_csv(DAILY_CSV_INJECTOR, ["fecha", "oee_dia_%", "total_pzs", "scrap_pzs", "meta_pzs"])
    asegurar_csv(
        RECIPES_CSV,
        ["molde_id", "parte", "ciclo_ideal_s", "cavidades", "cavidades_habilitadas", "scrap_esperado_pct", "activo"],
    )
    if not leer_csv_dict(RECIPES_CSV):
        with open(RECIPES_CSV, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["48", "19-001-049", "45", "1", "1", "2", "1"])
            w.writerow(["84", "19-001-084", "23", "1", "1", "2", "1"])
    asegurar_csv(
        PLANNING_CSV,
        ["orden", "parte", "molde_id", "maquina_id", "qty_total", "inicio_ts", "fin_est_ts", "setup_min", "estado", "ciclo_s", "cav_on"],
    )
    asegurar_csv(DELIV_CSV, ["orden", "due_date", "qty", "cumplido"])
    asegurar_csv(SHIPMENTS_CSV, ["orden", "ship_date", "qty", "destino", "nota", "approved"])


def asegurar_archivos_maquina(machine: Dict[str, str]) -> None:
    asegurar_csv(
        machine["oee_csv"],
        [
            "timestamp",
            "fecha",
            "operador",
            "turno",
            "molde",
            "parte",
            "ciclo_s",
            "horas_turno",
            "tiempo_paro_min",
            "meta_oper_pzs",
            "total_pzs",
            "scrap_pzs",
            "buenas_pzs",
            "availability_%",
            "performance_%",
            "quality_%",
            "oee_%",
        ],
    )
    asegurar_csv(
        machine["down_csv"],
        ["fecha", "inicio_ts", "fin_ts", "duracion_seg", "motivo", "nota", "operador", "turno", "molde"],
    )
