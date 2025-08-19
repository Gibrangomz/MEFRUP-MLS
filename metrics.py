# -*- coding: utf-8 -*-
"""Core calculation and aggregation helpers."""

import os
from datetime import date
from typing import Dict, List

from config import MACHINES, PLANNING_CSV, DIAS_ES
from csv_utils import (
    leer_csv_dict,
    leer_shipments,
    asegurar_archivos_maquina,
)


def calcular_tiempos(horas_turno, ciclo_s, paro_seg):
    turno_seg = int(max(0, horas_turno or 0) * 3600)
    operativo = max(0, turno_seg - int(max(0, paro_seg or 0)))
    ciclo = int(ciclo_s or 0)
    meta_plan = int(turno_seg // ciclo) if ciclo > 0 else 0
    meta_oper = int(operativo // ciclo) if ciclo > 0 else 0
    return turno_seg, operativo, meta_plan, meta_oper


def calcular_metricas(total, scrap, turno_seg, oper_seg, ciclo_ideal_s):
    total = int(total or 0)
    scrap = int(scrap or 0)
    buenas = max(0, total - scrap)
    A = (oper_seg / turno_seg) if turno_seg > 0 else 0.0
    A = max(0.0, min(1.0, A))
    perf_num = buenas * float(ciclo_ideal_s or 0)
    P = (perf_num / oper_seg) if oper_seg > 0 else 0.0
    P = max(0.0, min(1.0, P))
    Q = (buenas / total) if total > 0 else 0.0
    OEE = A * P * Q * 100.0
    return buenas, round(A * 100, 2), round(P * 100, 2), round(Q * 100, 2), round(OEE, 2)


def acum_por_fecha(rows, fecha_iso):
    total = scrap = 0
    meta = 0.0
    n = 0
    for r in rows:
        if r.get("fecha") != fecha_iso:
            continue
        total += parse_int_str(r.get("total_pzs", "0"))
        scrap += parse_int_str(r.get("scrap_pzs", "0"))
        meta += _safe_float(r.get("meta_oper_pzs", "0"))
        n += 1
    if total <= 0 or meta <= 0:
        return {
            "count": n,
            "total": total,
            "scrap": scrap,
            "buenas": max(0, total - scrap),
            "perf_pct": 0.0,
            "qual_pct": 0.0,
            "oee_pct": 0.0,
            "meta_pzs": meta,
        }
    buenas = max(0, total - scrap)
    P = total / meta
    Q = buenas / total
    OEE = P * Q * 100.0
    return {
        "count": n,
        "total": total,
        "scrap": scrap,
        "buenas": buenas,
        "perf_pct": round(P * 100, 2),
        "qual_pct": round(Q * 100, 2),
        "oee_pct": round(OEE, 2),
        "meta_pzs": meta,
    }


def acum_global(rows):
    total = scrap = 0
    meta = 0.0
    n = 0
    dias = set()
    for r in rows:
        total += parse_int_str(r.get("total_pzs", "0"))
        scrap += parse_int_str(r.get("scrap_pzs", "0"))
        meta += _safe_float(r.get("meta_oper_pzs", "0"))
        n += 1
        if r.get("fecha"):
            dias.add(r["fecha"])
    if total <= 0 or meta <= 0:
        return {
            "registros": n,
            "dias": len(dias),
            "total": total,
            "scrap": scrap,
            "buenas": max(0, total - scrap),
            "perf_pct": 0.0,
            "qual_pct": 0.0,
            "oee_pct": 0.0,
            "meta_pzs": meta,
        }
    buenas = max(0, total - scrap)
    P = total / meta
    Q = buenas / total
    OEE = P * Q * 100.0
    return {
        "registros": n,
        "dias": len(dias),
        "total": total,
        "scrap": scrap,
        "buenas": buenas,
        "perf_pct": round(P * 100, 2),
        "qual_pct": round(Q * 100, 2),
        "oee_pct": round(OEE, 2),
        "meta_pzs": meta,
    }


def promedio_oee_daily(path_daily):
    rows = leer_csv_dict(path_daily) if os.path.exists(path_daily) else []
    vals = [_safe_float(r.get("oee_dia_%", 0)) for r in rows]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def resumen_historico_maquina(machine):
    """Promedios históricos de OEE y sus componentes para una máquina."""
    asegurar_archivos_maquina(machine)
    rows = leer_csv_dict(machine["oee_csv"])
    if not rows:
        return dict(oee=0.0, A=0.0, P=0.0, Q=0.0)

    def _avg(key):
        vals = [_safe_float(r.get(key, 0)) for r in rows if r.get(key) not in (None, "")]
        return sum(vals) / len(vals) if vals else 0.0

    return dict(
        oee=round(_avg("oee_%"), 2),
        A=round(_avg("availability_%"), 2),
        P=round(_avg("performance_%"), 2),
        Q=round(_avg("quality_%"), 2),
    )


def dia_semana_es(f):
    try:
        y, m, d = map(int, f.split("-"))
        return DIAS_ES[date(y, m, d).weekday()]
    except Exception:
        return "Día"


def segs_to_hms_str(s):
    s = max(0, int(s))
    h = s // 3600
    m = (s % 3600) // 60
    sc = s % 60
    return f"{h:02d}:{m:02d}:{sc:02d}"


def parse_int_str(s, default=0):
    try:
        s = str(s).replace(",", ".").strip()
        return int(float(s))
    except Exception:
        return default


def producido_por_molde_global(molde_id: str, hasta_fecha: str = None) -> int:
    total_buenas = 0
    for m in MACHINES:
        rows = leer_csv_dict(m["oee_csv"])
        for r in rows:
            try:
                if str(r.get("molde", "")).strip() == str(molde_id).strip():
                    if hasta_fecha:
                        if (r.get("fecha") or "") <= hasta_fecha:
                            total_buenas += int(float(r.get("buenas_pzs", "0")))
                    else:
                        total_buenas += int(float(r.get("buenas_pzs", "0")))
            except Exception:
                pass
    return total_buenas


def enviados_por_orden(orden: str) -> int:
    return sum(
        parse_int_str(r.get("qty", "0"))
        for r in leer_shipments()
        if r.get("orden") == orden and r.get("approved", "0") == "1"
    )


def enviados_por_molde(molde_id: str) -> int:
    """Cantidad total enviada asociada a un molde (todas las órdenes)."""
    orden_a_molde = {
        r.get("orden", "").strip(): r.get("molde_id", "").strip()
        for r in leer_csv_dict(PLANNING_CSV)
    }
    total = 0
    for r in leer_shipments():
        if (
            orden_a_molde.get(r.get("orden", "").strip()) == str(molde_id).strip()
            and r.get("approved", "0") == "1"
        ):
            total += parse_int_str(r.get("qty", "0"))
    return total


def inventario_fifo():
    """Distribuye el inventario neto por molde entre sus órdenes (FIFO).

    Retorna una tupla ``(rows, totals)`` donde ``rows`` es una lista de
    diccionarios por orden con las claves:
    ``orden``, ``parte``, ``molde``, ``objetivo``, ``enviado``, ``asignado``,
    ``progreso`` y ``pendiente``. ``totals`` agrega producción total,
    enviados aprobados y stock neto restante.
    """

    orders = leer_csv_dict(PLANNING_CSV)
    by_mold = {}
    for r in orders:
        m = (r.get("molde_id", "") or "").strip()
        if not m:
            continue
        by_mold.setdefault(m, []).append(r)

    rows_out = []
    totals = dict(produccion=0, enviados=0, stock=0)

    for m, ords in by_mold.items():
        ords.sort(key=lambda r: ((r.get("inicio_ts") or ""), r.get("orden", "")))
        prod = producido_por_molde_global(m)
        shipped_by_order = {o["orden"]: enviados_por_orden(o["orden"]) for o in ords}
        shipped_total = sum(shipped_by_order.values())
        neto = max(0, prod - shipped_total)

        totals["produccion"] += prod
        totals["enviados"] += shipped_total
        totals["stock"] += neto

        restante = neto
        for o in ords:
            orden = o.get("orden", "")
            parte = o.get("parte", "")
            objetivo = parse_int_str(o.get("qty_total", "0"))
            enviado = shipped_by_order.get(orden, 0)
            necesidad = max(0, objetivo - enviado)
            asignado = min(necesidad, restante)
            restante -= asignado
            progreso = min(objetivo, enviado + asignado)
            pendiente = max(0, objetivo - progreso)
            rows_out.append(
                dict(
                    orden=orden,
                    parte=parte,
                    molde=m,
                    objetivo=objetivo,
                    enviado=enviado,
                    asignado=asignado,
                    progreso=progreso,
                    pendiente=pendiente,
                )
            )

    return rows_out, totals


# ===== resumen por máquina (hoy) con fallback robusto =====
def _safe_float(x, default=0.0):
    """Parsea un valor numérico tolerante removiendo comas y signos %."""
    try:
        if x in (None, ""):
            return default
        s = str(x).replace(",", ".").replace("%", "").strip()
        return float(s)
    except Exception:
        return default


def resumen_hoy_maquina(machine, fecha_iso):
    asegurar_archivos_maquina(machine)
    rows = [r for r in leer_csv_dict(machine["oee_csv"]) if r.get("fecha") == fecha_iso]
    if not rows:
        return dict(
            oee=0.0,
            A=0.0,
            P=0.0,
            Q=0.0,
            total=0,
            buenas=0,
            scrap=0,
            meta=0,
            ciclo_ideal=0,
            ciclo_real=0.0,
            turno_seg=0,
            oper_seg=0,
            ultimo_paro="-",
        )
    # acumulados
    total = sum(parse_int_str(r.get("total_pzs", "0")) for r in rows)
    scrap = sum(parse_int_str(r.get("scrap_pzs", "0")) for r in rows)
    buenas = max(0, total - scrap)
    # meta planeada almacenada
    meta_oper = sum(parse_int_str(r.get("meta_oper_pzs", "0")) for r in rows)
    # tiempos
    horas_sum = sum(_safe_float(r.get("horas_turno", "0")) for r in rows)
    turno_seg = int(horas_sum * 3600)
    paro_seg = int(sum(_safe_float(r.get("tiempo_paro_min", "0")) for r in rows) * 60)
    oper_seg = max(0, turno_seg - paro_seg)
    # ciclo ideal (último válido)
    ciclos = [
        parse_int_str(r.get("ciclo_s", "0"))
        for r in rows
        if parse_int_str(r.get("ciclo_s", "0")) > 0
    ]
    ciclo_ideal = ciclos[-1] if ciclos else 0

    A = (oper_seg / turno_seg) if turno_seg > 0 else None
    P = (total / meta_oper) if meta_oper > 0 else None
    Q = (buenas / total) if total > 0 else None
    if None in (A, P, Q):
        # fallback a promedios almacenados si faltan datos para calcular
        n = max(1, len(rows))
        A = sum(_safe_float(r.get("availability_%", "0")) for r in rows) / n / 100.0
        P = sum(_safe_float(r.get("performance_%", "0")) for r in rows) / n / 100.0
        Q = sum(_safe_float(r.get("quality_%", "0")) for r in rows) / n / 100.0
    oee = A * P * Q * 100.0
    A *= 100.0
    P *= 100.0
    Q *= 100.0

    # ciclo real estimado
    ciclo_real = (oper_seg / buenas) if buenas > 0 else 0.0
    # último paro
    downs = [r for r in leer_csv_dict(machine["down_csv"]) if r.get("fecha") == fecha_iso]
    if downs:
        d = downs[-1]
        try:
            mins = round(int(float(d.get("duracion_seg", "0"))) / 60.0, 1)
            ultimo = f"{d.get('inicio_ts','')} -> {d.get('fin_ts','')}   {mins:.1f} min ({d.get('motivo','')})"
        except Exception:
            ultimo = f"{d.get('inicio_ts','')} -> {d.get('fin_ts','')}   ({d.get('motivo','')})"
    else:
        ultimo = "-"
    return dict(
        oee=round(oee, 2),
        A=round(A, 2),
        P=round(P, 2),
        Q=round(Q, 2),
        total=total,
        buenas=buenas,
        scrap=scrap,
        meta=int(meta_oper),
        ciclo_ideal=ciclo_ideal,
        ciclo_real=round(ciclo_real, 2),
        turno_seg=turno_seg,
        oper_seg=oper_seg,
        ultimo_paro=ultimo,
    )


def resumen_rango_maquina(machine, desde, hasta):
    """Agrega métricas de producción en un rango de fechas."""
    asegurar_archivos_maquina(machine)
    rows = leer_csv_dict(machine["oee_csv"])
    down_rows = leer_csv_dict(machine["down_csv"])
    down_by_date = {}
    for d in down_rows:
        f = d.get("fecha")
        if not f:
            continue
        if desde and f < desde:
            continue
        if hasta and f > hasta:
            continue
        mins = _safe_float(d.get("duracion_seg", "0")) / 60.0
        down_by_date[f] = down_by_date.get(f, 0.0) + mins

    data = []
    for r in rows:
        f = r.get("fecha")
        if not f:
            continue
        if desde and f < desde:
            continue
        if hasta and f > hasta:
            continue
        total = parse_int_str(r.get("total_pzs", "0"))
        scrap = parse_int_str(r.get("scrap_pzs", "0"))
        meta = _safe_float(r.get("meta_oper_pzs", "0"))
        avail = _safe_float(r.get("availability_%", "0"))
        perf = _safe_float(r.get("performance_%", "0"))
        qual = _safe_float(r.get("quality_%", "0"))
        oee = _safe_float(r.get("oee_%", "0"))
        if total <= 0 or meta <= 0:
            continue
        buenas = max(0, total - scrap)
        paro = round(down_by_date.get(f, 0.0), 2)
        data.append(
            {
                "fecha": f,
                "paro_min": paro,
                "total": total,
                "scrap": scrap,
                "buenas": buenas,
                "availability": round(avail, 2),
                "performance": round(perf, 2),
                "quality": round(qual, 2),
                "oee": round(oee, 2),
            }
        )
    if not data:
        return {
            "rows": [],
            "totals": {
                "total": 0,
                "scrap": 0,
                "buenas": 0,
                "paro_min": 0.0,
                "availability": 0.0,
                "performance": 0.0,
                "quality": 0.0,
                "oee": 0.0,
            },
        }
    total = sum(d["total"] for d in data)
    scrap = sum(d["scrap"] for d in data)
    buenas = sum(d["buenas"] for d in data)
    paro = sum(d["paro_min"] for d in data)
    avail = sum(d["availability"] for d in data) / len(data)
    perf = sum(d["performance"] for d in data) / len(data)
    qual = sum(d["quality"] for d in data) / len(data)
    oee = sum(d["oee"] for d in data) / len(data)
    return {
        "rows": data,
        "totals": {
            "total": total,
            "scrap": scrap,
            "buenas": buenas,
            "paro_min": round(paro, 2),
            "availability": round(avail, 2),
            "performance": round(perf, 2),
            "quality": round(qual, 2),
            "oee": round(oee, 2),
        },
    }
