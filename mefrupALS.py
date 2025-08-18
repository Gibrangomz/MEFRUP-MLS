# -*- coding: utf-8 -*-
# Requisitos:
#   pip install customtkinter pillow tkcalendar

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image
from tkcalendar import Calendar
import csv, os, logging, traceback
from datetime import datetime, date, timedelta

# ---------- rutas / const ----------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))

# CSVs por máquina
MACHINES = [
    {
        "id": "arburg",
        "name": "ARBURG 320C GOLDEN EDITION",
        "oee_csv":  os.path.join(BASE_DIR, "oee_arburg.csv"),
        "down_csv": os.path.join(BASE_DIR, "down_arburg.csv")
    },
    {
        "id": "yizumi",
        "name": "YIZUMI UN90 A5",
        "oee_csv":  os.path.join(BASE_DIR, "oee_yizumi.csv"),
        "down_csv": os.path.join(BASE_DIR, "down_yizumi.csv")
    }
]

# diarios (compat) + combinado
DAILY_CSV_GLOBAL   = os.path.join(BASE_DIR, "oee_daily.csv")
DAILY_CSV_INJECTOR = os.path.join(BASE_DIR, "oee_inyeccion_daily.csv")

RECIPES_CSV = os.path.join(BASE_DIR, "recipes.csv")
LOGO_PATH   = os.path.join(BASE_DIR, "10b41fef-97af-4e79-90c4-b496e0dd3197.png")

# planificación y milestones
PLANNING_CSV = os.path.join(BASE_DIR, "planning.csv")   # orden, parte, molde_id, maquina_id, qty_total, inicio_ts, fin_est_ts, setup_min, estado, ciclo_s, cav_on
DELIV_CSV    = os.path.join(BASE_DIR, "deliveries.csv") # orden, due_date, qty, cumplido(0/1)

# NUEVO: salidas / embarques
SHIPMENTS_CSV = os.path.join(BASE_DIR, "shipments.csv") # orden, ship_date, qty, destino, nota

OPERADORES   = ["OPERADOR 1", "OPERADOR 2", "OPERADOR 3"]
TURNOS_HORAS = {1: 8, 2: 8, 3: 8}
DIAS_ES      = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

TICK_MS     = 1000
DEBOUNCE_MS = 160
DASH_REFRESH_MS = 5000

MOTIVOS_PARO = [
    "Cambio de molde",
    "Pieza Atorada",
    "Sin operador",
    "Calidad",
    "Mantenimiento",
    "Energía (Se fue la luz)"
]

# ---------- CSV utils ----------
def asegurar_csv(path, header):
    try:
        with open(path, "x", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)
    except FileExistsError:
        pass

def leer_csv_dict(path):
    if not os.path.exists(path): return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def escribir_daily(path, fecha_iso, oee_pct, total, scrap, meta):
    asegurar_csv(path, ["fecha","oee_dia_%","total_pzs","scrap_pzs","meta_pzs"])
    rows = leer_csv_dict(path)
    for r in rows:
        if r.get("fecha")==fecha_iso:
            r["oee_dia_%"]=f"{oee_pct:.2f}"; r["total_pzs"]=str(total)
            r["scrap_pzs"]=str(scrap); r["meta_pzs"]=str(meta); break
    else:
        rows.append({"fecha":fecha_iso,"oee_dia_%":f"{oee_pct:.2f}",
                     "total_pzs":str(total),"scrap_pzs":str(scrap),"meta_pzs":str(meta)})
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["fecha","oee_dia_%","total_pzs","scrap_pzs","meta_pzs"])
        w.writeheader(); w.writerows(rows)

def fechas_registradas(path_daily):
    asegurar_csv(path_daily, ["fecha","oee_dia_%","total_pzs","scrap_pzs","meta_pzs"])
    return {r["fecha"] for r in leer_csv_dict(path_daily) if r.get("fecha")}

def asegurar_archivos_basicos():
    asegurar_csv(DAILY_CSV_GLOBAL, ["fecha","oee_dia_%","total_pzs","scrap_pzs","meta_pzs"])
    asegurar_csv(DAILY_CSV_INJECTOR, ["fecha","oee_dia_%","total_pzs","scrap_pzs","meta_pzs"])
    asegurar_csv(RECIPES_CSV, [
        "molde_id","parte","ciclo_ideal_s","cavidades","cavidades_habilitadas","scrap_esperado_pct","activo"
    ])
    if not leer_csv_dict(RECIPES_CSV):
        with open(RECIPES_CSV,"a",newline="",encoding="utf-8") as f:
            w=csv.writer(f)
            w.writerow(["48","19-001-049","45","1","1","2","1"])
            w.writerow(["84","19-001-084","23","1","1","2","1"])
    asegurar_csv(PLANNING_CSV, ["orden","parte","molde_id","maquina_id","qty_total","inicio_ts","fin_est_ts","setup_min","estado","ciclo_s","cav_on"])
    asegurar_csv(DELIV_CSV,    ["orden","due_date","qty","cumplido"])
    asegurar_csv(SHIPMENTS_CSV,["orden","ship_date","qty","destino","nota"])

def asegurar_archivos_maquina(machine):
    asegurar_csv(machine["oee_csv"], [
        "timestamp","fecha","operador","turno","molde","parte","ciclo_s","horas_turno",
        "tiempo_paro_min","meta_oper_pzs","total_pzs","scrap_pzs","buenas_pzs",
        "availability_%","performance_%","quality_%","oee_%"
    ])
    asegurar_csv(machine["down_csv"], [
        "fecha","inicio_ts","fin_ts","duracion_seg","motivo","nota","operador","turno","molde"
    ])

# ---------- cálculos ----------
def calcular_tiempos(horas_turno, ciclo_s, paro_seg):
    turno_seg = int(max(0, horas_turno or 0) * 3600)
    operativo = max(0, turno_seg - int(max(0, paro_seg or 0)))
    ciclo     = int(ciclo_s or 0)
    meta_plan = int(turno_seg // ciclo) if ciclo>0 else 0
    meta_oper = int(operativo // ciclo) if ciclo>0 else 0
    return turno_seg, operativo, meta_plan, meta_oper

def calcular_metricas(total, scrap, turno_seg, oper_seg, ciclo_ideal_s):
    total   = int(total or 0)
    scrap   = int(scrap or 0)
    buenas  = max(0, total - scrap)
    A = (oper_seg/turno_seg) if turno_seg>0 else 0.0
    A = max(0.0, min(1.0, A))
    perf_num = buenas * float(ciclo_ideal_s or 0)
    P = (perf_num/oper_seg) if oper_seg>0 else 0.0
    P = max(0.0, min(1.0, P))
    Q = (buenas/total) if total>0 else 0.0
    OEE = A * P * Q * 100.0
    return buenas, round(A*100,2), round(P*100,2), round(Q*100,2), round(OEE,2)

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
    if total<=0 or meta<=0:
        return {"count":n,"total":total,"scrap":scrap,"buenas":max(0,total-scrap),
                "perf_pct":0.0,"qual_pct":0.0,"oee_pct":0.0,"meta_pzs":meta}
    buenas=max(0,total-scrap); P=total/meta; Q=buenas/total; OEE=P*Q*100.0
    return {"count":n,"total":total,"scrap":scrap,"buenas":buenas,
            "perf_pct":round(P*100,2),"qual_pct":round(Q*100,2),
            "oee_pct":round(OEE,2),"meta_pzs":meta}

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
    if total<=0 or meta<=0:
        return {"registros":n,"dias":len(dias),"total":total,"scrap":scrap,
                "buenas":max(0,total-scrap),"perf_pct":0.0,"qual_pct":0.0,"oee_pct":0.0,"meta_pzs":meta}
    buenas=max(0,total-scrap); P=total/meta; Q=buenas/total; OEE=P*Q*100.0
    return {"registros":n,"dias":len(dias),"total":total,"scrap":scrap,"buenas":buenas,
            "perf_pct":round(P*100,2),"qual_pct":round(Q*100,2),"oee_pct":round(OEE,2),"meta_pzs":meta}

def acum_por_fecha(rows, fecha_iso):
    total=scrap=0; meta=0.0; n=0
    for r in rows:
        if r.get("fecha")!=fecha_iso: continue
        try:
            total+=int(float(r.get("total_pzs","0")))
            scrap+=int(float(r.get("scrap_pzs","0")))
            meta +=float(r.get("meta_oper_pzs","0"))
            n+=1
        except: pass
    if total<=0 or meta<=0:
        return {"count":n,"total":total,"scrap":scrap,"buenas":max(0,total-scrap),
                "perf_pct":0.0,"qual_pct":0.0,"oee_pct":0.0,"meta_pzs":meta}
    buenas=max(0,total-scrap); P=total/meta; Q=buenas/total; OEE=P*Q*100.0
    return {"count":n,"total":total,"scrap":scrap,"buenas":buenas,
            "perf_pct":round(P*100,2),"qual_pct":round(Q*100,2),
            "oee_pct":round(OEE,2),"meta_pzs":meta}

def acum_global(rows):
    total=scrap=0; meta=0.0; n=0; dias=set()
    for r in rows:
        try:
            total+=int(float(r.get("total_pzs","0")))
            scrap+=int(float(r.get("scrap_pzs","0")))
            meta +=float(r.get("meta_oper_pzs","0"))
            n+=1
            if r.get("fecha"): dias.add(r["fecha"])
        except: pass
    if total<=0 or meta<=0:
        return {"registros":n,"dias":len(dias),"total":total,"scrap":scrap,
                "buenas":max(0,total-scrap),"perf_pct":0.0,"qual_pct":0.0,"oee_pct":0.0,"meta_pzs":meta}
    buenas=max(0,total-scrap); P=total/meta; Q=buenas/total; OEE=P*Q*100.0
    return {"registros":n,"dias":len(dias),"total":total,"scrap":scrap,"buenas":buenas,
            "perf_pct":round(P*100,2),"qual_pct":round(Q*100,2),"oee_pct":round(OEE,2),"meta_pzs":meta}


def promedio_oee_daily(path_daily):
    rows = leer_csv_dict(path_daily) if os.path.exists(path_daily) else []
    vals = [_safe_float(r.get("oee_dia_%", 0)) for r in rows]
    return round(sum(vals)/len(vals),2) if vals else 0.0

def dia_semana_es(f):
    try: y,m,d=map(int,f.split("-")); return DIAS_ES[date(y,m,d).weekday()]
    except: return "Día"

def segs_to_hms_str(s):
    s=max(0,int(s)); h=s//3600; m=(s%3600)//60; sc=s%60; return f"{h:02d}:{m:02d}:{sc:02d}"

def parse_int_str(s, default=0):
    try:
        s = str(s).replace(",",".").strip()
        return int(float(s))
    except:
        return default

# ===== producidas por molde (para milestones/órdenes) =====
def producido_por_molde_global(molde_id: str, hasta_fecha: str = None) -> int:
    total_buenas = 0
    for m in MACHINES:
        rows = leer_csv_dict(m["oee_csv"])
        for r in rows:
            try:
                if str(r.get("molde","")).strip() == str(molde_id).strip():
                    if hasta_fecha:
                        if (r.get("fecha") or "") <= hasta_fecha:
                            total_buenas += int(float(r.get("buenas_pzs","0")))
                    else:
                        total_buenas += int(float(r.get("buenas_pzs","0")))
            except: pass
    return total_buenas

def enviados_por_orden(orden: str) -> int:
    return sum(parse_int_str(r.get("qty","0")) for r in leer_csv_dict(SHIPMENTS_CSV) if r.get("orden")==orden)

# ===== resumen por máquina (hoy) con fallback robusto =====
def _safe_float(x, default=0.0):
    try: return float(str(x).replace(",",".")) if x not in (None,"") else default
    except: return default

def resumen_hoy_maquina(machine, fecha_iso):
    asegurar_archivos_maquina(machine)
    rows = [r for r in leer_csv_dict(machine["oee_csv"]) if r.get("fecha")==fecha_iso]
    if not rows:
        return dict(oee=0.0,A=0.0,P=0.0,Q=0.0,total=0,buenas=0,scrap=0,
                    meta=0, ciclo_ideal=0, ciclo_real=0.0,
                    turno_seg=0, oper_seg=0, ultimo_paro="-")
    # acumulados
    total = sum(parse_int_str(r.get("total_pzs","0")) for r in rows)
    scrap = sum(parse_int_str(r.get("scrap_pzs","0")) for r in rows)
    buenas= max(0,total-scrap)
    # tiempos
    horas_sum = sum(_safe_float(r.get("horas_turno","0")) for r in rows)
    turno_seg = int(horas_sum * 3600)
    paro_seg  = int(sum(_safe_float(r.get("tiempo_paro_min","0")) for r in rows) * 60)
    oper_seg  = max(0, turno_seg - paro_seg)
    # ciclo ideal promedio (último válido o promedio)
    ciclos = [parse_int_str(r.get("ciclo_s","0")) for r in rows if parse_int_str(r.get("ciclo_s","0"))>0]
    ciclo_ideal = ciclos[-1] if ciclos else 0

    # métricas con fallback
    if turno_seg>0 and ciclo_ideal>0:
        A = (oper_seg/turno_seg)
        P = ((buenas*ciclo_ideal)/oper_seg) if oper_seg>0 else 0.0
        Q = (buenas/total) if total>0 else 0.0
        oee = A*P*Q*100.0
        A*=100.0; P*=100.0; Q*=100.0
    else:
        # fallback a promedio de columnas A/P/Q/OEE si existen
        A = sum(_safe_float(r.get("availability_%","0")) for r in rows) / max(1,len(rows))
        P = sum(_safe_float(r.get("performance_%","0")) for r in rows) / max(1,len(rows))
        Q = sum(_safe_float(r.get("quality_%","0")) for r in rows) / max(1,len(rows))
        oee = sum(_safe_float(r.get("oee_%","0")) for r in rows) / max(1,len(rows))

    # meta operativa
    meta_oper = int((oper_seg // ciclo_ideal) if ciclo_ideal>0 else 0)
    # ciclo real estimado
    ciclo_real = (oper_seg/buenas) if buenas>0 else 0.0
    # último paro
    downs = [r for r in leer_csv_dict(machine["down_csv"]) if r.get("fecha")==fecha_iso]
    if downs:
        d = downs[-1]
        try:
            mins = round(int(float(d.get("duracion_seg","0")))/60.0,1)
            ultimo = f"{d.get('inicio_ts','')} -> {d.get('fin_ts','')}   {mins:.1f} min ({d.get('motivo','')})"
        except:
            ultimo = f"{d.get('inicio_ts','')} -> {d.get('fin_ts','')}   ({d.get('motivo','')})"
    else:
        ultimo="-"
    return dict(oee=round(oee,2),A=round(A,2),P=round(P,2),Q=round(Q,2),
                total=total,buenas=buenas,scrap=scrap, meta=meta_oper,
                ciclo_ideal=ciclo_ideal, ciclo_real=round(ciclo_real,2),
                turno_seg=turno_seg, oper_seg=oper_seg, ultimo_paro=ultimo)

def resumen_rango_maquina(machine, desde, hasta):
    """Agrega métricas de producción en un rango de fechas."""
    asegurar_archivos_maquina(machine)
    rows = leer_csv_dict(machine["oee_csv"])
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
        if total <= 0 or meta <= 0:
            continue
        buenas = max(0, total - scrap)
        P = total / meta if meta > 0 else 0.0
        Q = buenas / total if total > 0 else 0.0
        oee = P * Q * 100.0
        data.append({
            "fecha": f,
            "total": total,
            "scrap": scrap,
            "buenas": buenas,
            "oee": round(oee, 2)
        })
    if not data:
        return {"total":0, "scrap":0, "buenas":0, "oee_prom":0.0}, []
    total = sum(d["total"] for d in data)
    scrap = sum(d["scrap"] for d in data)
    buenas = sum(d["buenas"] for d in data)
    oee_prom = sum(d["oee"] for d in data) / len(data)
    stats = {
        "total": total,
        "scrap": scrap,
        "buenas": buenas,
        "oee_prom": round(oee_prom, 2)
    }
    return stats, data

# ---------- Vistas ----------
class RecipesView(ctk.CTkFrame):
    """Gestor de Recetas (molde/parte/ciclo...)"""
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app=app
        self._build()

    def _build(self):
        header=ctk.CTkFrame(self, corner_radius=0, fg_color=("white","#111111"))
        header.pack(fill="x", side="top")
        left=ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", command=self.app.go_menu, width=100, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text="Recetas — Moldes/Partes", font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")

        body=ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=16, pady=16)
        table_card=ctk.CTkFrame(body, corner_radius=18)
        table_card.pack(side="left", fill="both", expand=True, padx=(0,10))
        ctk.CTkLabel(table_card, text="Recetas", font=ctk.CTkFont("Helvetica",13,"bold")).pack(anchor="w", padx=8, pady=(8,0))
        ctk.CTkFrame(table_card, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=8, pady=(6,8))

        cols=("molde_id","parte","ciclo_ideal_s","cavidades","cavidades_habilitadas","scrap_esperado_pct","activo")
        self.tree=ttk.Treeview(table_card, columns=cols, show="headings", height=12)
        heads=[("molde_id","Molde",90),("parte","# Parte",140),("ciclo_ideal_s","Ciclo (s)",90),
               ("cavidades","Cav.",70),("cavidades_habilitadas","Cav. ON",80),
               ("scrap_esperado_pct","Scrap %",80),("activo","Activo",70)]
        for key,txt,w in heads:
            self.tree.heading(key, text=txt); self.tree.column(key, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        btnbar=ctk.CTkFrame(table_card, fg_color="transparent"); btnbar.pack(fill="x", padx=8, pady=(0,10))
        ctk.CTkButton(btnbar, text="Nuevo", command=self._new).pack(side="left", padx=(0,8))
        ctk.CTkButton(btnbar, text="Guardar", command=self._save).pack(side="left", padx=8)
        ctk.CTkButton(btnbar, text="Eliminar", fg_color="#ef4444", hover_color="#dc2626", command=self._delete).pack(side="left", padx=8)
        ctk.CTkButton(btnbar, text="↻ Recargar", fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB", command=self._load).pack(side="left", padx=8)
        ctk.CTkButton(btnbar, text="Ir a OEE", command=self.app.go_oee_select_machine).pack(side="right")

        # Formulario
        form=ctk.CTkFrame(body, corner_radius=18)
        form.pack(side="left", fill="both", expand=False, padx=(10,0))
        ctk.CTkLabel(form, text="Editar receta", font=ctk.CTkFont("Helvetica",13,"bold")).pack(anchor="w", padx=8, pady=(8,0))
        ctk.CTkFrame(form, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=8, pady=(6,8))

        def frow(lbl, var, width=160, typ="entry"):
            r=ctk.CTkFrame(form, fg_color="transparent"); r.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(r, text=lbl).pack(side="left")
            if typ=="entry":
                e=ctk.CTkEntry(r, width=width, textvariable=var, justify="center")
                e.pack(side="right"); return e
            else:
                om=ctk.CTkOptionMenu(r, values=["0","1"], variable=var); om.pack(side="right"); return om

        self.var_molde = tk.StringVar()
        self.var_parte = tk.StringVar()
        self.var_ciclo = tk.StringVar()
        self.var_cavs  = tk.StringVar()
        self.var_cavs_on = tk.StringVar()
        self.var_scrap = tk.StringVar()
        self.var_activo= tk.StringVar(value="1")

        frow("Molde ID", self.var_molde)
        frow("# Parte", self.var_parte)
        frow("Ciclo ideal (s)", self.var_ciclo)
        frow("Cavidades", self.var_cavs)
        frow("Cavidades habilitadas", self.var_cavs_on)
        frow("Scrap esperado (%)", self.var_scrap)
        frow("Activo (1/0)", self.var_activo, typ="om")

        self._load()

    def _load(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in leer_csv_dict(RECIPES_CSV):
            self.tree.insert("", "end", values=(r["molde_id"], r["parte"], r["ciclo_ideal_s"],
                                                r["cavidades"], r["cavidades_habilitadas"],
                                                r["scrap_esperado_pct"], r["activo"]))
        # refresca catálogo de moldes en App
        self.app._refresh_moldes_from_recipes()

    def _on_select(self, *_):
        sel=self.tree.selection()
        if not sel: return
        vals=self.tree.item(sel[0],"values")
        (self.var_molde.set(vals[0]), self.var_parte.set(vals[1]), self.var_ciclo.set(vals[2]),
         self.var_cavs.set(vals[3]), self.var_cavs_on.set(vals[4]), self.var_scrap.set(vals[5]),
         self.var_activo.set(vals[6]))

    def _new(self):
        self.var_molde.set(""); self.var_parte.set(""); self.var_ciclo.set("")
        self.var_cavs.set(""); self.var_cavs_on.set(""); self.var_scrap.set(""); self.var_activo.set("1")

    def _save(self):
        m=self.var_molde.get().strip()
        if not (m and self.var_ciclo.get().strip()):
            messagebox.showwarning("Faltan datos","Molde y ciclo ideal son obligatorios."); return
        rows=leer_csv_dict(RECIPES_CSV); found=False
        for r in rows:
            if r["molde_id"]==m:
                r.update({
                    "parte": self.var_parte.get().strip(),
                    "ciclo_ideal_s": self.var_ciclo.get().strip(),
                    "cavidades": self.var_cavs.get().strip(),
                    "cavidades_habilitadas": self.var_cavs_on.get().strip(),
                    "scrap_esperado_pct": self.var_scrap.get().strip(),
                    "activo": self.var_activo.get().strip() or "1"
                })
                found=True; break
        if not found:
            rows.append({
                "molde_id": m,
                "parte": self.var_parte.get().strip(),
                "ciclo_ideal_s": self.var_ciclo.get().strip(),
                "cavidades": self.var_cavs.get().strip(),
                "cavidades_habilitadas": self.var_cavs_on.get().strip(),
                "scrap_esperado_pct": self.var_scrap.get().strip(),
                "activo": self.var_activo.get().strip() or "1"
            })
        with open(RECIPES_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["molde_id","parte","ciclo_ideal_s",
                                            "cavidades","cavidades_habilitadas","scrap_esperado_pct","activo"])
            w.writeheader(); w.writerows(rows)
        self._load()
        messagebox.showinfo("Recetas","Receta guardada.")
        self.app._refresh_moldes_from_recipes()
        try:
            self.app._on_molde_change(); self.app._update_now()
        except: pass

    def _delete(self):
        sel=self.tree.selection()
        if not sel: return
        molde = self.tree.item(sel[0],"values")[0]
        if not messagebox.askyesno("Eliminar","¿Eliminar la receta del molde "+str(molde)+"?"): return
        rows=[r for r in leer_csv_dict(RECIPES_CSV) if r["molde_id"]!=molde]
        with open(RECIPES_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["molde_id","parte","ciclo_ideal_s",
                                            "cavidades","cavidades_habilitadas","scrap_esperado_pct","activo"])
            w.writeheader(); w.writerows(rows)
        self._load()
        self.app._refresh_moldes_from_recipes()
        try:
            self.app._on_molde_change(); self.app._update_now()
        except: pass

class MachineChooser(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app=app
        box=ctk.CTkFrame(self, corner_radius=20); box.pack(expand=True, fill="both", padx=40, pady=40)
        ctk.CTkLabel(box, text="Selecciona máquina", font=ctk.CTkFont("Helvetica",26,"bold")).pack(pady=(18,8))
        grid=ctk.CTkFrame(box, fg_color="transparent"); grid.pack(pady=10)
        for i, m in enumerate(MACHINES):
            ctk.CTkButton(grid, text=m["name"], height=56, corner_radius=16,
                          command=lambda mm=m: self.app.go_oee(mm)).grid(row=i, column=0, pady=8, padx=8, sticky="ew")
        ctk.CTkButton(box, text="← Volver al menú", height=44, corner_radius=12,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                      command=self.app.go_menu).pack(pady=(18,0))

class OEEView(ctk.CTkFrame):
    def __init__(self, master, app, machine):
        super().__init__(master, fg_color="transparent")
        self.app=app
        self.machine=machine
        self._build_header()
        self._build_body()

    def _build_header(self):
        header=ctk.CTkFrame(self, corner_radius=0, fg_color=("white","#111111"))
        header.pack(fill="x", side="top")
        left=ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Elegir máquina", command=self.app.go_oee_select_machine, width=140, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text=f"OEE — Registro de Producción ({self.machine['name']})",
                     font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")

        right=ctk.CTkFrame(header, fg_color="transparent"); right.pack(side="right", padx=16, pady=10)
        self.clock_lbl = ctk.CTkLabel(right, text="", font=ctk.CTkFont("Helvetica",13))
        self.clock_lbl.pack(side="right", padx=(8,0))
        theme = ctk.CTkSegmentedButton(right, values=["Claro","Oscuro"],
                                       command=lambda v: ctk.set_appearance_mode("dark" if v=="Oscuro" else "light"))
        theme.set("Claro"); theme.pack(side="right", padx=10)
        try:
            img=Image.open(LOGO_PATH); logo=ctk.CTkImage(light_image=img, dark_image=img, size=(120,48))
            ctk.CTkLabel(right, image=logo, text="").pack(side="right", padx=10); self.logo=logo
        except: pass

    def _build_body(self):
        body=ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=16, pady=16)
        body.grid_rowconfigure(0, weight=1); body.grid_columnconfigure(0, weight=1); body.grid_columnconfigure(1, weight=1)

        # izquierda
        left=ctk.CTkScrollableFrame(body, corner_radius=18); left.grid(row=0, column=0, sticky="nsew", padx=(0,10))

        # Fecha
        sec=self._sec(left,"Fecha"); sec.pack(fill="x", padx=14, pady=(14,8))
        row=ctk.CTkFrame(sec, fg_color="transparent"); row.pack(fill="x")
        ctk.CTkLabel(row, text="YYYY-MM-DD").pack(side="left")
        ctk.CTkEntry(row, width=140, textvariable=self.app.fecha_sel, justify="center").pack(side="left", padx=8)
        ctk.CTkButton(row, text="Usar", command=self.app._on_fecha_change).pack(side="left", padx=8)
        ctk.CTkButton(row, text="📅", width=40, command=self.app._open_calendar).pack(side="left", padx=6)
        self.lbl_dia=ctk.CTkLabel(sec, text="", font=ctk.CTkFont("Helvetica", 12, "bold")); self.lbl_dia.pack(anchor="w", pady=(6,0))
        self.app.lbl_dia=self.lbl_dia

        # Operador
        sec=self._sec(left,"Operador"); sec.pack(fill="x", padx=14, pady=8)
        op=ctk.CTkOptionMenu(sec, values=["Selecciona"]+[o.capitalize() for o in OPERADORES],
                             command=lambda v: self.app._set_operador(v.lower()) if v!="Selecciona" else None)
        op.set("Selecciona"); op.pack(fill="x", padx=4, pady=4)

        # Turno
        sec=self._sec(left,"Turno"); sec.pack(fill="x", padx=14, pady=8)
        tu=ctk.CTkOptionMenu(sec, values=["Selecciona","1","2","3"],
                             command=lambda v: self.app._set_turno(v) if v.isdigit() else None)
        tu.set("Selecciona"); tu.pack(fill="x", padx=4, pady=4)

        # Molde / Receta
        sec=self._sec(left,"Molde / Receta"); sec.pack(fill="x", padx=14, pady=8)
        valores_moldes = ["Selecciona"] + sorted([k for k in self.app.recipe_map.keys()])
        self.molde_menu = ctk.CTkOptionMenu(sec, values=valores_moldes)
        self.molde_menu.pack(fill="x", padx=4, pady=4)
        self.molde_menu.configure(command=lambda v: self.app._set_molde(v) if v.isdigit() else None)

        info = ctk.CTkFrame(sec, fg_color="transparent"); info.pack(fill="x", pady=(6,0))
        ctk.CTkLabel(info, text="Ciclo ideal (s):").grid(row=0, column=0, sticky="w", padx=(0,6))
        ctk.CTkLabel(info, textvariable=self.app.ciclo_s, font=ctk.CTkFont("Helvetica",12,"bold")).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(info, text="# Parte:").grid(row=1, column=0, sticky="w", padx=(0,6), pady=(4,0))
        self.lbl_parte = ctk.CTkLabel(info, text="", font=ctk.CTkFont("Helvetica",12,"bold"))
        self.lbl_parte.grid(row=1, column=1, sticky="w", pady=(4,0))
        ctk.CTkLabel(info, text="Cavidades (ON/Tot):").grid(row=2, column=0, sticky="w", padx=(0,6), pady=(4,0))
        self.lbl_cavs = ctk.CTkLabel(info, text="", font=ctk.CTkFont("Helvetica",12,"bold"))
        self.lbl_cavs.grid(row=2, column=1, sticky="w", pady=(4,0))
        self.app.lbl_parte = self.lbl_parte
        self.app.lbl_cavs  = self.lbl_cavs

        # Producción
        sec=self._sec(left,"Producción (turno)"); sec.pack(fill="x", padx=14, pady=8)
        self._counter(sec,"Total",self.app.total)
        self._counter(sec,"Scrap",self.app.scrap)
        actions=ctk.CTkFrame(sec, fg_color="transparent"); actions.pack(fill="x", pady=(10,0))
        self.btn_guardar=ctk.CTkButton(actions, text="Guardar (Ctrl+Enter)", corner_radius=12, command=self.app._guardar)
        self.btn_guardar.pack(side="left", expand=True, fill="x", padx=(0,6))
        ctk.CTkButton(actions, text="Reset contadores", corner_radius=12, fg_color="#E5E7EB",
                      text_color="#111", hover_color="#D1D5DB", command=self.app._reset_contadores)\
            .pack(side="left", expand=True, fill="x", padx=(6,0))
        self.app.btn_guardar=self.btn_guardar

        # Paros
        sec=self._sec(left,"Paros (cronómetro)"); sec.pack(fill="x", padx=14, pady=8)
        picker=ctk.CTkFrame(sec, fg_color="transparent"); picker.pack(fill="x", pady=(0,8))
        ctk.CTkLabel(picker, text="Motivo").pack(side="left")
        self.motivo_menu = ctk.CTkOptionMenu(picker, values=MOTIVOS_PARO); self.motivo_menu.pack(side="left", padx=8)
        ctk.CTkLabel(picker, text="Nota").pack(side="left", padx=(12,0))
        self.nota_entry=ctk.CTkEntry(picker, width=220, placeholder_text="opcional"); self.nota_entry.pack(side="left", padx=8)

        r1=ctk.CTkFrame(sec, fg_color="transparent"); r1.pack(fill="x", pady=(2,2))
        ctk.CTkLabel(r1, text="Paro actual").pack(side="left")
        self.lbl_paro_actual=ctk.CTkLabel(r1, text="00:00:00", font=ctk.CTkFont("Helvetica",16,"bold")); self.lbl_paro_actual.pack(side="right")

        r2=ctk.CTkFrame(sec, fg_color="transparent"); r2.pack(fill="x", pady=(2,8))
        ctk.CTkLabel(r2, text="Paro acumulado (turno)").pack(side="left")
        self.lbl_paro_acum=ctk.CTkLabel(r2, text="00:00:00", font=ctk.CTkFont("Helvetica",16,"bold")); self.lbl_paro_acum.pack(side="right")

        rbtn=ctk.CTkFrame(sec, fg_color="transparent"); rbtn.pack(fill="x", pady=(0,8))
        self.btn_toggle_paro=ctk.CTkButton(rbtn, text="Iniciar paro", height=44, corner_radius=14,
                                           command=self.app.toggle_paro, fg_color="#ef4444", hover_color="#dc2626")
        self.btn_toggle_paro.pack(side="left", expand=True, fill="x", padx=(0,8))
        ctk.CTkButton(rbtn, text="Reset paros", height=44, corner_radius=14, fg_color="#E5E7EB",
                      text_color="#111", hover_color="#D1D5DB", command=self.app.reset_paros)\
            .pack(side="left", expand=True, fill="x", padx=(8,0))

        # bitácora
        table_card=ctk.CTkFrame(sec, corner_radius=10); table_card.pack(fill="both", expand=True, pady=(10,0))
        cols=("inicio","fin","motivo","nota","dur_min")
        self.tree=ttk.Treeview(table_card, columns=cols, show="headings", height=6)
        for c, txt, w, anchor in [("inicio","Inicio",135,"center"),("fin","Fin",135,"center"),
                                  ("motivo","Motivo",160,"w"),("nota","Nota",220,"w"),("dur_min","Dur (min)",80,"e")]:
            self.tree.heading(c, text=txt); self.tree.column(c, width=w, anchor=anchor)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        style=ttk.Style(); style.configure("Treeview", rowheight=24, font=("Helvetica",10))
        style.configure("Treeview.Heading", font=("Helvetica",10,"bold"))

        # derecha
        right=ctk.CTkFrame(body, corner_radius=18); right.grid(row=0, column=1, sticky="nsew", padx=(10,0))
        sec=self._sec(right,"Metas"); sec.pack(fill="x", padx=14, pady=(14,8))
        r=ctk.CTkFrame(sec, fg_color="transparent"); r.pack(fill="x")
        ctk.CTkLabel(r, text="Meta planificada (pzs)").pack(side="left")
        self.meta_plan_val=ctk.CTkLabel(r, text="0", font=ctk.CTkFont("Helvetica",16,"bold")); self.meta_plan_val.pack(side="left", padx=6)
        r=ctk.CTkFrame(sec, fg_color="transparent"); r.pack(fill="x", pady=(6,0))
        ctk.CTkLabel(r, text="Meta operativa (pzs)").pack(side="left")
        self.meta_oper_val=ctk.CTkLabel(r, text="0", font=ctk.CTkFont("Helvetica",16,"bold")); self.meta_oper_val.pack(side="left", padx=6)

        bars=ctk.CTkFrame(right, fg_color="transparent"); bars.pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(bars, text="Disponibilidad").pack(anchor="w")
        self.pb_avail=ctk.CTkProgressBar(bars); self.pb_avail.set(0.0); self.pb_avail.pack(fill="x", pady=(2,8))
        ctk.CTkLabel(bars, text="Avance a meta (operativa)").pack(anchor="w")
        self.pb_meta=ctk.CTkProgressBar(bars); self.pb_meta.set(0.0); self.pb_meta.pack(fill="x", pady=(2,8))
        ctk.CTkLabel(bars, text="Calidad (Buenas / Total)").pack(anchor="w")
        self.pb_quality=ctk.CTkProgressBar(bars); self.pb_quality.set(0.0); self.pb_quality.pack(fill="x", pady=(2,8))

        sec=self._sec(right,"Tiempo real (turno)"); sec.pack(fill="x", padx=14, pady=8)
        self._metric(sec,"Availability (RT)",self.app.avail_rt)
        self._metric(sec,"Performance (RT)",self.app.perf_rt)
        self._metric(sec,"Quality (RT)",self.app.qual_rt)
        self._metric(sec,"OEE (RT)",self.app.oee_rt)

        sec=self._sec(right,"Día seleccionado (acumulado)"); sec.pack(fill="x", padx=14, pady=8)
        self._metric(sec,"Total día",self.app.tot_day)
        self._metric(sec,"Scrap día",self.app.scr_day)
        self._metric(sec,"Buenas día",self.app.buen_day)
        self._metric(sec,"Performance día",self.app.perf_day)
        self._metric(sec,"Quality día",self.app.qual_day)
        self._metric(sec,"OEE día",self.app.oee_day)
        ctk.CTkLabel(sec, textvariable=self.app.day_info, text_color=("#6b7280","#9CA3AF")).pack(anchor="w", pady=(6,0))

        sec=self._sec(right,"Histórico (promedio OEE día)"); sec.pack(fill="x", padx=14, pady=8)
        self._metric(sec,"OEE histórico",self.app.oee_hist)

        sec=self._sec(right,"Global (todos los registros)"); sec.pack(fill="x", padx=14, pady=(8,14))
        self._metric(sec,"Total global",self.app.glob_total)
        self._metric(sec,"Scrap global",self.app.glob_scrap)
        self._metric(sec,"Buenas global",self.app.glob_buenas)
        self._metric(sec,"Performance global",self.app.glob_perf)
        self._metric(sec,"Quality global",self.app.glob_qual)
        self._metric(sec,"OEE global",self.app.glob_oee)
        ctk.CTkLabel(sec, textvariable=self.app.glob_info, text_color=("#6b7280","#9CA3AF")).pack(anchor="w", pady=(6,0))

        # refs
        self.app.meta_plan_val=self.meta_plan_val; self.app.meta_oper_val=self.meta_oper_val
        self.app.pb_avail=self.pb_avail; self.app.pb_meta=self.pb_meta; self.app.pb_quality=self.pb_quality
        self.app.lbl_paro_actual=self.lbl_paro_actual; self.app.lbl_paro_acum=self.lbl_paro_acum
        self.app.btn_toggle_paro=self.btn_toggle_paro
        self.app.motivo_menu=self.motivo_menu; self.app.nota_entry=self.nota_entry; self.app.tree=self.tree
        self.app.molde_menu=self.molde_menu
        self.app._clock_label = self.clock_lbl

    # helpers UI
    def _sec(self, parent, title):
        card=ctk.CTkFrame(parent, corner_radius=16)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont("Helvetica",13,"bold")).pack(anchor="w", padx=8, pady=(8,0))
        ctk.CTkFrame(card, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=8, pady=(6,8))
        return card
    def _counter(self, parent, label, var):
        r=ctk.CTkFrame(parent, fg_color="transparent"); r.pack(fill="x", pady=6)
        ctk.CTkLabel(r, text=label).pack(side="left")
        e=ctk.CTkEntry(r, width=140, textvariable=var, justify="center"); e.pack(side="left", padx=8)
        ctk.CTkButton(r, text="-", width=44, height=40, command=lambda: self.app._nudge(var,-1), corner_radius=14).pack(side="left", padx=4)
        ctk.CTkButton(r, text="+", width=44, height=40, command=lambda: self.app._nudge(var,+1), corner_radius=14).pack(side="left", padx=4)
        e.bind("<FocusOut>", lambda ev: self.app._sanitize(var)); e.bind("<Return>", lambda ev: self.app._sanitize(var))
    def _metric(self, parent, label, var):
        r=ctk.CTkFrame(parent, fg_color="transparent"); r.pack(fill="x", pady=4)
        ctk.CTkLabel(r, text=label).pack(side="left")
        ctk.CTkLabel(r, textvariable=var, font=ctk.CTkFont("Helvetica",16,"bold")).pack(side="right")

# ===== TABLERO EN VIVO (mejorado) =====
class LiveDashboard(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._timer = None
        self._build()

    def _tone(self, oee):
        if oee >= 85: return ("#DCFCE7", "#065F46")
        if oee >= 60: return ("#FEF9C3", "#92400E")
        return ("#FEE2E2", "#991B1B")

    def _build(self):
        header=ctk.CTkFrame(self, corner_radius=0, fg_color=("white","#111111"))
        header.pack(fill="x", side="top")
        left=ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", command=self.app.go_menu, width=110, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text="Tablero en vivo — Área de Inyección",
                     font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")

        right=ctk.CTkFrame(header, fg_color="transparent"); right.pack(side="right", padx=16, pady=10)
        self.clock_lbl = ctk.CTkLabel(right, text="", font=ctk.CTkFont("Helvetica",13))
        self.clock_lbl.pack(side="right", padx=(8,0))
        ctk.CTkButton(right, text="Actualizar", command=self._refresh_now, width=110).pack(side="right", padx=(0,8))
        try:
            img=Image.open(LOGO_PATH); logo=ctk.CTkImage(light_image=img, dark_image=img, size=(120,48))
            ctk.CTkLabel(right, image=logo, text="").pack(side="right", padx=10); self.logo=logo
        except: pass

        body=ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=16, pady=16)
        body.grid_columnconfigure(0, weight=1); body.grid_columnconfigure(1, weight=1); body.grid_rowconfigure(1, weight=1)

        # Top: combinado
        self.card_area = ctk.CTkFrame(body, corner_radius=18)
        self.card_area.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(0,12))
        ctk.CTkLabel(self.card_area, text="OEE Área (hoy)", font=ctk.CTkFont("Helvetica", 16, "bold")).pack(anchor="w", padx=12, pady=(10,0))
        self.lbl_area = ctk.CTkLabel(self.card_area, text="0.00 %", font=ctk.CTkFont("Helvetica", 28, "bold"))
        self.lbl_area.pack(anchor="w", padx=12, pady=(4,12))

        # Cards por máquina
        self.cards = {}
        for i, m in enumerate(MACHINES):
            card = ctk.CTkFrame(body, corner_radius=18)
            card.grid(row=1, column=i, sticky="nsew", padx=6, pady=6)
            ctk.CTkLabel(card, text=m["name"], font=ctk.CTkFont("Helvetica", 15, "bold")).pack(anchor="w", padx=12, pady=(10,6))
            row1 = ctk.CTkFrame(card, fg_color="transparent"); row1.pack(fill="x", padx=12)
            self.cards[m["id"]] = {
                "wrap": card,
                "oee": ctk.CTkLabel(row1, text="OEE 0.00%", font=ctk.CTkFont("Helvetica",16,"bold")),
                "A":   ctk.CTkLabel(row1, text="A 0.00%",   font=ctk.CTkFont("Helvetica",13)),
                "P":   ctk.CTkLabel(row1, text="P 0.00%",   font=ctk.CTkFont("Helvetica",13)),
                "Q":   ctk.CTkLabel(row1, text="Q 0.00%",   font=ctk.CTkFont("Helvetica",13))
            }
            self.cards[m["id"]]["oee"].pack(side="left")
            self.cards[m["id"]]["A"].pack(side="left", padx=(12,0))
            self.cards[m["id"]]["P"].pack(side="left", padx=(12,0))
            self.cards[m["id"]]["Q"].pack(side="left", padx=(12,0))
            self.cards[m["id"]]["paro"]= ctk.CTkLabel(card, text="Último paro: -", wraplength=520, justify="left")
            self.cards[m["id"]]["paro"].pack(anchor="w", padx=12, pady=(8,10))

        self._refresh_now()

    def _refresh_now(self):
        # reloj
        self.clock_lbl.configure(text=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        hoy = date.today().isoformat()

        # por máquina y promedio de área
        oees = []
        for m in MACHINES:
            r = resumen_hoy_maquina(m, hoy)
            oees.append(r["oee"])
            card = self.cards[m["id"]]
            card["oee"].configure(text=f"OEE {r['oee']:.2f}%")
            card["A"].configure(text=f"A {r['A']:.2f}%")
            card["P"].configure(text=f"P {r['P']:.2f}%")
            card["Q"].configure(text=f"Q {r['Q']:.2f}%")
            card["paro"].configure(text=f"Último paro: {r['ultimo_paro']}")
            bg, fg = self._tone(r["oee"])
            try:
                card["wrap"].configure(fg_color=bg)
            except:
                pass
        if oees:
            area_oee = sum(oees) / len(oees)
            self.lbl_area.configure(text=f"{area_oee:.2f} %")
        else:
            self.lbl_area.configure(text="0.00 %")

        if self._timer: self.after_cancel(self._timer)
        self._timer = self.after(DASH_REFRESH_MS, self._refresh_now)

# ---------- Reportes ----------
class ReportsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#111111"))
        header.pack(fill="x", side="top")
        ctk.CTkButton(header, text="← Menú", command=self.app.go_menu, width=110, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(16,10), pady=10)
        ctk.CTkLabel(header, text="Reportes de Producción", font=ctk.CTkFont("Helvetica", 20, "bold"))\
            .pack(side="left", pady=10)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=40, pady=40)
        body.grid_columnconfigure(1, weight=1)

        opciones = [m["id"] for m in MACHINES]
        self.machine_var = tk.StringVar(value=opciones[0])
        ctk.CTkLabel(body, text="Máquina:").grid(row=0, column=0, sticky="w", pady=6)
        ctk.CTkOptionMenu(body, values=opciones, variable=self.machine_var).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(body, text="Desde (AAAA-MM-DD):").grid(row=1, column=0, sticky="w", pady=6)
        self.desde_entry = ctk.CTkEntry(body)
        self.desde_entry.grid(row=1, column=1, sticky="w")

        ctk.CTkLabel(body, text="Hasta (AAAA-MM-DD):").grid(row=2, column=0, sticky="w", pady=6)
        self.hasta_entry = ctk.CTkEntry(body)
        self.hasta_entry.grid(row=2, column=1, sticky="w")

        ctk.CTkButton(body, text="Generar", command=self._generar).grid(row=3, column=0, columnspan=2, pady=(20,0))

    def _generar(self):
        mid = self.machine_var.get()
        machine = next((m for m in MACHINES if m["id"] == mid), None)
        if not machine:
            messagebox.showerror("Error", "Máquina inválida")
            return
        desde = self.desde_entry.get().strip()
        hasta = self.hasta_entry.get().strip()
        stats, data = resumen_rango_maquina(machine, desde, hasta)
        messagebox.showinfo(
            "Reporte",
            f"Total: {stats['total']}\nBuenas: {stats['buenas']}\nScrap: {stats['scrap']}\nOEE Promedio: {stats['oee_prom']:.2f}%"
        )
        try:
            import seaborn as sns
            import matplotlib.pyplot as plt
            fechas = [d["fecha"] for d in data]
            oees = [d["oee"] for d in data]
            plt.figure(figsize=(8,4))
            sns.lineplot(x=fechas, y=oees)
            plt.xticks(rotation=45)
            plt.ylabel("OEE %")
            plt.tight_layout()
            plt.show()
        except Exception as e:
            messagebox.showerror("Error graficando", str(e))

# ---------- Menú ----------
class MainMenu(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        box=ctk.CTkFrame(self, corner_radius=20); box.pack(expand=True, fill="both", padx=40, pady=40)
        try:
            img=Image.open(LOGO_PATH); logo=ctk.CTkImage(light_image=img, dark_image=img, size=(240,96))
            ctk.CTkLabel(box, image=logo, text="").pack(pady=(30,10)); self.logo=logo
        except:
            ctk.CTkLabel(box, text="MEFRUP", font=ctk.CTkFont("Helvetica",36,"bold")).pack(pady=(50,10))
        ctk.CTkLabel(box, text="Mefrup MLS", font=ctk.CTkFont("Helvetica",28,"bold")).pack(pady=(0,6))
        ctk.CTkLabel(box, text="Sistema de Monitoreo y Producción", font=ctk.CTkFont("Helvetica",14)).pack(pady=(0,20))
        ctk.CTkButton(box, text="Tablero en vivo (Área Inyección)", height=48, corner_radius=14,
                      command=app.go_dashboard).pack(pady=(0,12), ipadx=20)
        ctk.CTkButton(box, text="OEE y Registro de Producción", height=48, corner_radius=14,
                      command=app.go_oee_select_machine).pack(pady=(0,12), ipadx=20)
        ctk.CTkButton(box, text="Recetas (Moldes/Partes)", height=44, corner_radius=14,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                      command=app.go_recipes).pack(pady=(0,8), ipadx=20)
        ctk.CTkButton(box, text="Planificación + Milestones", height=44, corner_radius=14,
                      command=app.go_planning).pack(pady=(0,8), ipadx=20)
        ctk.CTkButton(box, text="Tablero de Órdenes (Progreso)", height=44, corner_radius=14,
                      command=app.go_orders_board).pack(pady=(0,8), ipadx=20)
        ctk.CTkButton(box, text="Reportes de Producción", height=44, corner_radius=14,
                      command=app.go_reports).pack(pady=(0,8), ipadx=20)
        # NUEVO
        ctk.CTkButton(box, text="Salida de Piezas (Embarques)", height=44, corner_radius=14,
                      command=app.go_shipments).pack(pady=(0,8), ipadx=20)

# ---------- App ----------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light"); ctk.set_default_color_theme("blue")
        self.title("Mefrup — ALS")
        try: self.state("zoomed")
        except: self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}")

        self._error_showing=False
        self._update_job=None
        self._last_tick_value=None
        self._clock_label=None

        # estado OEE
        self.operador=tk.StringVar(value=""); self.turno=tk.IntVar(value=0)
        self.molde=tk.IntVar(value=0); self.parte=tk.StringVar(value="")
        self.ciclo_s=tk.IntVar(value=0)
        self.total=tk.StringVar(value="0"); self.scrap=tk.StringVar(value="0")
        self.fecha_sel=tk.StringVar(value=date.today().isoformat())

        # cronómetro paros
        self.paro_running=False; self.paro_accum_secs=0; self.paro_start_ts=None
        self.paro_motivo=""; self.paro_nota=""

        # métricas / labels
        self.avail_rt=tk.StringVar(value="0.00%"); self.perf_rt=tk.StringVar(value="0.00%")
        self.qual_rt=tk.StringVar(value="0.00%"); self.oee_rt=tk.StringVar(value="0.00%")
        self.tot_day=tk.StringVar(value="0"); self.scr_day=tk.StringVar(value="0"); self.buen_day=tk.StringVar(value="0")
        self.perf_day=tk.StringVar(value="0.00%"); self.qual_day=tk.StringVar(value="0.00%"); self.oee_day=tk.StringVar(value="0.00%")
        self.day_info=tk.StringVar(value="Sin registros para la fecha."); self.oee_hist=tk.StringVar(value="0.00%")
        self.glob_total=tk.StringVar(value="0"); self.glob_scrap=tk.StringVar(value="0"); self.glob_buenas=tk.StringVar(value="0")
        self.glob_perf=tk.StringVar(value="0.00%"); self.glob_qual=tk.StringVar(value="0.00%"); self.glob_oee=tk.StringVar(value="0.00%")
        self.glob_info=tk.StringVar(value="Registros: 0 | Días: 0")

        # recetas catalog
        asegurar_archivos_basicos()
        self.recipes = leer_csv_dict(RECIPES_CSV)
        self.recipe_map = {}

        # vistas / contexto
        self.active_machine = None
        self.oee_page = None
        self.choose_page = None
        self.oee_pages = {}  # id->OEEView
        self.machine_context = {}
        self.dashboard_page = None

        # planificación
        self.planning_page = None
        self.orders_board_page = None
        self.reports_page = None
        self.shipments_page = None
        self._shipments_preselect_order = None

        # recalculo en tiempo real
        self.turno.trace_add("write", lambda *a: self._schedule_update())
        self.molde.trace_add("write", lambda *a: self._on_molde_change())
        self.total.trace_add("write", lambda *a: self._soft_sanitize(self.total, schedule=True))
        self.scrap.trace_add("write", lambda *a: self._soft_sanitize(self.scrap, schedule=True))

        # contenedor & vistas
        self.container=ctk.CTkFrame(self, corner_radius=0, fg_color="transparent"); self.container.pack(fill="both", expand=True)
        self.menu_page=MainMenu(self.container, self)
        self.recipes_page=RecipesView(self.container, self)
        self.choose_page=MachineChooser(self.container, self)
        self.dashboard_page=LiveDashboard(self.container, self)
        self.reports_page=ReportsView(self.container, self)

        self._refresh_moldes_from_recipes()
        self.go_menu()

        self.after(TICK_MS, self._tick)
        self.after(200, self._apply_initial_scale)

    # helpers
    def _set_text_if_changed(self, widget, text: str):
        if getattr(widget, "_last_text", None) != text:
            widget.configure(text=text)
            widget._last_text = text
    def _set_pb_if_changed(self, pb, frac: float, eps: float = 1e-3):
        frac = max(0.0, min(1.0, float(frac)))
        if abs(getattr(pb, "_last_val", -1.0) - frac) > eps:
            pb.set(frac); pb._last_val = frac

    # navegación
    def _pack_only(self, view):
        for w in self.container.winfo_children(): w.pack_forget()
        view.pack(fill="both", expand=True)

    def go_menu(self):
        self._unbind_shortcuts_oee()
        self._pack_only(self.menu_page)

    def go_dashboard(self):
        self._unbind_shortcuts_oee()
        self._pack_only(self.dashboard_page)

    def go_oee_select_machine(self):
        self._unbind_shortcuts_oee()
        self._pack_only(self.choose_page)

    def go_oee(self, machine):
        self.active_machine = machine
        asegurar_archivos_maquina(machine)
        self.machine_context[machine["id"]] = {
            "oee_csv": machine["oee_csv"],
            "down_csv": machine["down_csv"]
        }
        if machine["id"] not in self.oee_pages:
            self.oee_pages[machine["id"]] = OEEView(self.container, self, machine)
        self.oee_page = self.oee_pages[machine["id"]]
        self._refresh_moldes_from_recipes(force_update_menu=True)
        self._pack_only(self.oee_page)
        self._bind_shortcuts_oee()
        self._update_now(); self._refrescar_dia(); self._refrescar_hist(); self._refrescar_global()
        self._update_save_state(); self._refresh_paro_labels(); self._reload_downtime_table()

    def go_recipes(self):
        self._unbind_shortcuts_oee()
        self._pack_only(self.recipes_page)

    def go_planning(self):
        if not self.planning_page:
            self.planning_page = PlanningMilestonesView(self.container, self)
        self._pack_only(self.planning_page)

    def go_orders_board(self):
        if not self.orders_board_page:
            self.orders_board_page = OrdersBoardView(self.container, self)
        self._pack_only(self.orders_board_page)

    def go_reports(self):
        if not self.reports_page:
            self.reports_page = ReportsView(self.container, self)
        self._pack_only(self.reports_page)

    def go_shipments(self, preselect_order: str|None=None):
        self._shipments_preselect_order = preselect_order
        if not self.shipments_page:
            self.shipments_page = ShipmentsView(self.container, self)
        self._pack_only(self.shipments_page)
        if preselect_order: self.shipments_page.set_order(preselect_order)

    # recetas / moldes
    def _refresh_moldes_from_recipes(self, force_update_menu=False):
        self.recipes = leer_csv_dict(RECIPES_CSV)
        self.recipe_map = {}
        opciones = ["Selecciona"]
        for r in self.recipes:
            if r.get("activo", "1") == "1":
                mid = (r.get("molde_id") or "").strip()
                if mid:
                    self.recipe_map[mid] = r
                    opciones.append(mid)
        if hasattr(self, "molde_menu"):
            try:
                self.molde_menu.configure(values=opciones)
                cur = str(self.molde.get() or "")
                if cur not in opciones:
                    self.molde.set(0); self.ciclo_s.set(0); self.parte.set("")
                if force_update_menu and cur in opciones:
                    self.molde_menu.set(cur if cur else "Selecciona")
            except: pass
        if force_update_menu and self.oee_page:
            try: self._on_molde_change()
            except: pass

    # BINDS OEE
    def _bind_shortcuts_oee(self):
        self.unbind("<Control-Return>"); self.bind("<Control-Return>", lambda e: self._guardar())
        self.unbind("<Control-g>"); self.bind("<Control-g>", lambda e: self._nudge(self.total,+1))
        self.unbind("<Control-h>"); self.bind("<Control-h>", lambda e: self._nudge(self.total,-1))
        self.unbind("<Control-s>"); self.bind("<Control-s>", lambda e: self._nudge(self.scrap,+1))
        self.unbind("<Control-d>"); self.bind("<Control-d>", lambda e: self._nudge(self.scrap,-1))
    def _unbind_shortcuts_oee(self):
        self.unbind("<Control-Return>"); self.unbind("<Control-g>"); self.unbind("<Control-h>")
        self.unbind("<Control-s>"); self.unbind("<Control-d>")

    # ERRORES
    def report_callback_exception(self, exc, val, tb):
        try:
            logging.basicConfig(filename=os.path.join(BASE_DIR,"ui_errors.log"),
                                level=logging.ERROR,filemode="a")
            logging.error("".join(traceback.format_exception(exc,val,tb)))
        except: pass
        if getattr(self,"_error_showing",False): return
        self._error_showing=True
        try: messagebox.showerror("Error en la UI", f"{val}\n(Detalle en ui_errors.log)")
        finally: self.after(200, lambda: setattr(self,"_error_showing",False))

    # llamados por OptionMenu
    def _set_operador(self, nombre:str):
        self.operador.set(nombre or ""); self._update_save_state()
    def _set_turno(self, turno_val):
        try: self.turno.set(int(turno_val))
        except: self.turno.set(0)
        self._update_now(); self._update_save_state()
    def _set_molde(self, molde_val):
        try: self.molde.set(int(molde_val))
        except: self.molde.set(0)
        try:
            if hasattr(self, "molde_menu"):
                vals = self.molde_menu.cget("values")
                if str(molde_val) in vals:
                    self.molde_menu.set(str(molde_val))
        except: pass
        self._update_save_state()

    # recetas / moldes
    def _on_molde_change(self, *_):
        mid = str(self.molde.get() or "")
        rec = self.recipe_map.get(mid)
        if rec:
            self.parte.set((rec.get("parte") or "").strip())
            raw = (rec.get("ciclo_ideal_s") or "").replace(",", ".").strip()
            try: self.ciclo_s.set(int(float(raw)))
            except: self.ciclo_s.set(0)
            self.rec_cavs    = (rec.get("cavidades") or "").strip()
            self.rec_cavs_on = (rec.get("cavidades_habilitadas") or "").strip()
            self.rec_scrap   = (rec.get("scrap_esperado_pct") or "").strip()
        else:
            self.parte.set(""); self.ciclo_s.set(0)
            self.rec_cavs = self.rec_cavs_on = self.rec_scrap = ""
        if hasattr(self, "lbl_parte"):
            try: self.lbl_parte.configure(text=self.parte.get() or "-")
            except: pass
        if hasattr(self, "lbl_cavs"):
            try:
                cavs_on = getattr(self, "rec_cavs_on", "") or "-"
                cavs = getattr(self, "rec_cavs", "") or "-"
                self.lbl_cavs.configure(text=f"{cavs_on}/{cavs}")
            except: pass
        self._schedule_update()

    # ENTRADA
    def _get_int(self, v:tk.StringVar):
        s=(v.get() or "").strip()
        if s.startswith("-"): s=s[1:]
        return int(s) if s.isdigit() else 0
    def _set_int(self, v:tk.StringVar, n:int): v.set(str(max(0,int(n))))
    def _sanitize(self, v:tk.StringVar): self._set_int(v, self._get_int(v)); self._update_now()
    def _nudge(self, v:tk.StringVar, d:int): self._set_int(v, self._get_int(v)+d); self._update_now()

    def _soft_sanitize(self, var: tk.StringVar, schedule=False):
        s=(var.get() or "")
        ns="".join(ch for ch in s if ch.isdigit())
        if ns!=s: var.set(ns)
        if var is self.scrap:
            try:
                t=int(self.total.get() or 0); sc=int(self.scrap.get() or 0)
                if sc>t: self.scrap.set(str(t))
            except: pass
        if schedule: self._schedule_update()

    # DEBOUNCE
    def _schedule_update(self):
        if self._update_job: self.after_cancel(self._update_job)
        self._update_job = self.after(DEBOUNCE_MS, self._update_now)
    def _update_now(self):
        self._update_job=None
        self._update_calculos()

    # FECHA
    def _on_fecha_change(self):
        f=self.fecha_sel.get().strip()
        try: y,m,d=map(int,f.split("-")); _=date(y,m,d)
        except: messagebox.showwarning("Fecha inválida","Usa YYYY-MM-DD."); return
        if self.oee_page and hasattr(self.oee_page, "lbl_dia"):
            self.oee_page.lbl_dia.configure(text=f"{dia_semana_es(f)} — {f}")
        self._refrescar_dia(); self._update_save_state(); self._reload_downtime_table()

    def _open_calendar(self):
        # (no bloqueamos por daily global para mantener independencia)
        try:
            y,m,d=map(int,(self.fecha_sel.get() or date.today().isoformat()).split("-"))
            init=date(y,m,d)
        except: init=date.today()
        top=tk.Toplevel(self); top.title("Selecciona fecha"); top.transient(self); top.grab_set(); top.resizable(False,False)
        self.update_idletasks()
        top.geometry(f"+{self.winfo_rootx()+self.winfo_width()//2-180}+{self.winfo_rooty()+self.winfo_height()//2-170}")
        cal=Calendar(top, selectmode="day", year=init.year, month=init.month, day=init.day, date_pattern="yyyy-mm-dd",
                     firstweekday="monday", showweeknumbers=False)
        cal.pack(padx=14, pady=14)
        b=tk.Frame(top); b.pack(fill="x", padx=14, pady=(0,14))
        def choose():
            ch=cal.get_date()
            self.fecha_sel.set(ch); self._on_fecha_change(); top.destroy()
        tk.Button(b, text="Seleccionar", command=choose).pack(side="left", padx=(0,6))
        tk.Button(b, text="Cerrar", command=top.destroy).pack(side="left")

    # CRONÓMETRO (OEE)
    def toggle_paro(self):
        if not self.active_machine:
            messagebox.showwarning("Máquina","Primero elige una máquina."); return
        if not self.paro_running:
            motivo = getattr(self, "motivo_menu", None).get() if hasattr(self, "motivo_menu") else MOTIVOS_PARO[0]
            nota   = getattr(self, "nota_entry", None).get() if hasattr(self, "nota_entry") else ""
            self.paro_motivo=motivo; self.paro_nota=nota
            self.paro_running=True; self.paro_start_ts=datetime.now()
            self.btn_toggle_paro.configure(text="Reanudar", fg_color="#10b981", hover_color="#059669")
        else:
            self._finalizar_evento_paro()
            self.paro_running=False; self.paro_start_ts=None
            self.paro_motivo=""; self.paro_nota=""
            self.btn_toggle_paro.configure(text="Iniciar paro", fg_color="#ef4444", hover_color="#dc2626")
        self._refresh_paro_labels(); self._schedule_update(); self._update_save_state()

    def _finalizar_evento_paro(self):
        if not (self.paro_start_ts and self.active_machine): return
        dur=int((datetime.now()-self.paro_start_ts).total_seconds())
        self.paro_accum_secs += max(0,dur)
        row=[self.fecha_sel.get().strip(),
             self.paro_start_ts.strftime("%Y-%m-%d %H:%M:%S"),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             str(dur), self.paro_motivo, self.paro_nota,
             self.operador.get(), str(self.turno.get() or ""), str(self.molde.get() or "")]
        try:
            with open(self.active_machine["down_csv"],"a",newline="",encoding="utf-8") as f: csv.writer(f).writerow(row)
        except PermissionError:
            messagebox.showerror("Archivo en uso","Cierra el CSV de paros.")
        self._reload_downtime_table()

    def reset_paros(self):
        if self.paro_running:
            messagebox.showwarning("Paro activo","Detén el paro antes de reiniciar."); return
        if messagebox.askyesno("Reset de paros","¿Reiniciar a 00:00:00 el paro acumulado del turno?"):
            self.paro_accum_secs=0; self._refresh_paro_labels(); self._schedule_update()

    def _current_paro_secs(self):
        return int((datetime.now()-self.paro_start_ts).total_seconds()) if (self.paro_running and self.paro_start_ts) else 0
    def _total_paro_secs(self): return self.paro_accum_secs + self._current_paro_secs()
    def _refresh_paro_labels(self):
        if hasattr(self,"lbl_paro_actual"): self.lbl_paro_actual.configure(text=segs_to_hms_str(self._current_paro_secs()))
        if hasattr(self,"lbl_paro_acum"):   self.lbl_paro_acum.configure(text=segs_to_hms_str(self._total_paro_secs()))
    def _tick(self):
        if self._clock_label:
            self._clock_label.configure(text=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        now_val = self._current_paro_secs() if self.paro_running else None
        if now_val is not None and now_val != self._last_tick_value:
            self._last_tick_value = now_val
            self._refresh_paro_labels()
            self._schedule_update()
        self.after(TICK_MS, self._tick)

    def _reload_downtime_table(self):
        if not (hasattr(self, "tree") and self.active_machine): return
        for i in self.tree.get_children(): self.tree.delete(i)
        f=self.fecha_sel.get().strip()
        for r in leer_csv_dict(self.active_machine["down_csv"]):
            if r.get("fecha")!=f: continue
            try: dmin = round(int(float(r.get("duracion_seg","0")))/60.0,1)
            except: dmin=0.0
            self.tree.insert("", "end", values=(r.get("inicio_ts",""), r.get("fin_ts",""),
                                                r.get("motivo",""), r.get("nota",""), f"{dmin:.1f}"))

    # ============ cálculos + guardar OEE ============
    def _update_calculos(self):
        horas = TURNOS_HORAS.get(int(self.turno.get() or 0), 0)
        ciclo = int(self.ciclo_s.get() or 0)
        turno_seg, oper_seg, meta_plan, meta_oper = calcular_tiempos(horas, ciclo, self._total_paro_secs())
        if hasattr(self,"meta_plan_val"): self._set_text_if_changed(self.meta_plan_val, str(meta_plan))
        if hasattr(self,"meta_oper_val"): self._set_text_if_changed(self.meta_oper_val, str(meta_oper))

        total=self._get_int(self.total); scrap=min(self._get_int(self.scrap), total)
        buenas, A, P, Q, OEE = calcular_metricas(total, scrap, turno_seg, oper_seg, ciclo)
        self.avail_rt.set(f"{A:.2f}%"); self.perf_rt.set(f"{P:.2f}%")
        self.qual_rt.set(f"{Q:.2f}%");  self.oee_rt.set(f"{OEE:.2f}%")
        if hasattr(self,"pb_avail"):   self._set_pb_if_changed(self.pb_avail, A/100.0)
        if hasattr(self,"pb_meta"):    self._set_pb_if_changed(self.pb_meta,  (total/meta_oper) if meta_oper>0 else 0.0)
        if hasattr(self,"pb_quality"): self._set_pb_if_changed(self.pb_quality, (buenas/total) if total>0 else 0.0)

    # helper: turno ya registrado para ESTA máquina
    def _turno_bloqueado_maquina(self, machine, fecha_iso, turno:int) -> bool:
        rows = leer_csv_dict(machine["oee_csv"])
        for r in rows:
            try:
                if r.get("fecha")==fecha_iso and int(float(r.get("turno","0")))==int(turno):
                    return True
            except: pass
        return False

    def _guardar(self):
        if not self.active_machine:
            messagebox.showwarning("Máquina","Primero elige una máquina."); return
        f=self.fecha_sel.get().strip()
        if self.paro_running: messagebox.showwarning("Paro activo","Detén el paro antes de guardar."); return
        if not (self.operador.get() and self.turno.get() and self.molde.get()):
            messagebox.showwarning("Faltan datos","Selecciona operador, turno y molde."); return
        try: y,m,d=map(int,f.split("-")); _=date(y,m,d)
        except: messagebox.showwarning("Fecha inválida","Usa YYYY-MM-DD."); return
        # Independencia por máquina + por turno
        if self._turno_bloqueado_maquina(self.active_machine, f, int(self.turno.get())):
            messagebox.showwarning("Turno ya registrado", f"{f} — turno {self.turno.get()} ya fue registrado en {self.active_machine['name']}."); return

        total=self._get_int(self.total); scrap=min(self._get_int(self.scrap), total)
        paro_seg=self._total_paro_secs()
        horas=TURNOS_HORAS.get(int(self.turno.get() or 0),0); ciclo=int(self.ciclo_s.get() or 0)
        turno_seg, oper_seg, _, meta_oper = calcular_tiempos(horas, ciclo, paro_seg)
        buenas, A, P, Q, OEE = calcular_metricas(total, scrap, turno_seg, oper_seg, ciclo)

        ts=f"{f}T{datetime.now().strftime('%H:%M:%S')}"
        row=[ts,f,self.operador.get(),self.turno.get(),self.molde.get(),self.parte.get(),ciclo,horas,
             int(round(paro_seg/60.0)), meta_oper,total,scrap,buenas,A,P,Q,OEE]
        try:
            with open(self.active_machine["oee_csv"],"a",newline="",encoding="utf-8") as fi: csv.writer(fi).writerow(row)
        except PermissionError:
            messagebox.showerror("Archivo en uso","Cierra el CSV de la máquina y vuelve a intentar."); return

        rows_maquina = leer_csv_dict(self.active_machine["oee_csv"])
        a=acum_por_fecha(rows_maquina, f)
        escribir_daily(DAILY_CSV_GLOBAL, f, a["oee_pct"], a["total"], a["scrap"], a["meta_pzs"])

        # combinado área
        total_area = meta_area = scrap_area = 0
        for m in MACHINES:
            r = acum_por_fecha(leer_csv_dict(m["oee_csv"]), f)
            total_area += r["total"]; scrap_area += r["scrap"]; meta_area += r["meta_pzs"]
        if total_area>0 and meta_area>0:
            buenas_area = max(0, total_area - scrap_area)
            P_area = total_area/meta_area
            Q_area = buenas_area/total_area
            OEE_area = P_area*Q_area*100.0
        else:
            OEE_area=0.0
        escribir_daily(DAILY_CSV_INJECTOR, f, OEE_area, total_area, scrap_area, meta_area)

        self._refrescar_dia(); self._refrescar_hist(); self._refrescar_global(); self._update_save_state()
        messagebox.showinfo("Guardado",
                            f"Máquina: {self.active_machine['name']}\n"
                            f"OEE {OEE:.2f}% (A {A:.2f}% | P {P:.2f}% | Q {Q:.2f}%)")

    def _refrescar_dia(self):
        if not self.active_machine: return
        f=self.fecha_sel.get().strip()
        if self.oee_page and hasattr(self.oee_page, "lbl_dia"):
            self.oee_page.lbl_dia.configure(text=f"{dia_semana_es(f)} — {f}")
        a=acum_por_fecha(leer_csv_dict(self.active_machine["oee_csv"]), f)
        self.tot_day.set(str(a["total"])); self.scr_day.set(str(a["scrap"])); self.buen_day.set(str(a["buenas"]))
        self.perf_day.set(f"{a['perf_pct']:.2f}%"); self.qual_day.set(f"{a['qual_pct']:.2f}%"); self.oee_day.set(f"{a['oee_pct']:.2f}%")
        # info: no bloqueamos por DAILY_CSV_GLOBAL para permitir turnos múltiples
        self.day_info.set("Registros del día: "+str(a.get("count",0)) if a.get("count",0) else "Sin registros para la fecha.")

    def _refrescar_hist(self):
        self.oee_hist.set(f"{promedio_oee_daily(DAILY_CSV_GLOBAL):.2f}%")
    def _refrescar_global(self):
        if not self.active_machine: return
        g=acum_global(leer_csv_dict(self.active_machine["oee_csv"]))
        self.glob_total.set(str(g["total"])); self.glob_scrap.set(str(g["scrap"])); self.glob_buenas.set(str(g["buenas"]))
        self.glob_perf.set(f"{g['perf_pct']:.2f}%"); self.glob_qual.set(f"{g['qual_pct']:.2f}%"); self.glob_oee.set(f"{g['oee_pct']:.2f}%")
        self.glob_info.set(f"Registros: {g['registros']} | Días: {g['dias']}")

    def _reset_contadores(self):
        if self.paro_running:
            messagebox.showwarning("Paro activo","Detén el paro antes de resetear."); return
        self.total.set("0"); self.scrap.set("0"); self.paro_accum_secs=0
        self._refresh_paro_labels(); self._update_now()

    def _update_save_state(self):
        ready = bool(self.operador.get()) and bool(self.turno.get()) and bool(self.molde.get()) and self.active_machine
        if self.paro_running: ready=False
        try: self.btn_guardar.configure(state=("normal" if ready else "disabled"))
        except: pass

    def _apply_initial_scale(self):
        try:
            s=min(max(self.winfo_screenwidth()/1920.0, 0.95), 1.20)
            ctk.set_widget_scaling(s)
        except: pass
# ================================
# === Vista: Planificación + Milestones (compacta, con edición y calendar)
# ================================
class PlanningMilestonesView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.sel_orden_var = tk.StringVar(value="")
        self._build()

    # ------- helpers UI -------
    def _calendar_pick(self, entry: ctk.CTkEntry, init_date:str|None=None):
        try:
            if init_date: y,m,d=map(int,init_date.split("-")); init=date(y,m,d)
            else:
                now = (entry.get() or date.today().isoformat())
                y,m,d=map(int,now.split("-")); init=date(y,m,d)
        except:
            init=date.today()
        top=tk.Toplevel(self); top.title("Selecciona fecha"); top.transient(self); top.grab_set(); top.resizable(False,False)
        self.update_idletasks()
        top.geometry(f"+{self.winfo_rootx()+self.winfo_width()//2-180}+{self.winfo_rooty()+self.winfo_height()//2-170}")
        cal=Calendar(top, selectmode="day", year=init.year, month=init.month, day=init.day, date_pattern="yyyy-mm-dd",
                     firstweekday="monday", showweeknumbers=False)
        cal.pack(padx=14, pady=14)
        def choose():
            entry.delete(0,"end"); entry.insert(0, cal.get_date()); top.destroy()
        tk.Button(top, text="Seleccionar", command=choose).pack(side="left", padx=10, pady=10)
        tk.Button(top, text="Cerrar", command=top.destroy).pack(side="left", padx=10, pady=10)

    def _build(self):
        header=ctk.CTkFrame(self, corner_radius=0, fg_color=("white","#111111"))
        header.pack(fill="x", side="top")
        left=ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", command=self.app.go_menu, width=110, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text="Planificación + Milestones", font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")

        # layout principal
        body=ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=16, pady=16)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(1, weight=1)

        # --- Form Orden (compacto) ---
        form = ctk.CTkFrame(body, corner_radius=18)
        form.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=(0,12))
        ctk.CTkLabel(form, text="Nueva / Edición de Orden", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(form, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))

        r1=ctk.CTkFrame(form, fg_color="transparent"); r1.pack(fill="x", padx=12, pady=4)
        self.e_orden = ctk.CTkEntry(r1, placeholder_text="Número de Orden", width=130); self.e_orden.pack(side="left", padx=(0,8))
        self.e_parte = ctk.CTkEntry(r1, placeholder_text="Parte", width=130); self.e_parte.pack(side="left", padx=8)
        self.e_molde = ctk.CTkEntry(r1, placeholder_text="Molde ID", width=130); self.e_molde.pack(side="left", padx=8)
        # máquinas ids
        maquinas_ids = [m["id"] for m in MACHINES]
        self.om_maquina = ctk.CTkOptionMenu(r1, values=maquinas_ids, width=120)
        self.om_maquina.set(maquinas_ids[0]); self.om_maquina.pack(side="left", padx=8)

        r2=ctk.CTkFrame(form, fg_color="transparent"); r2.pack(fill="x", padx=12, pady=4)
        self.e_qty = ctk.CTkEntry(r2, placeholder_text="Cantidad total", width=130); self.e_qty.pack(side="left", padx=(0,8))
        self.e_setup = ctk.CTkEntry(r2, placeholder_text="Setup (min)", width=130); self.e_setup.pack(side="left", padx=8)
        self.e_ciclo = ctk.CTkEntry(r2, placeholder_text="Ciclo (s) opcional", width=130); self.e_ciclo.pack(side="left", padx=8)
        self.e_cavon = ctk.CTkEntry(r2, placeholder_text="Cav ON opcional", width=130); self.e_cavon.pack(side="left", padx=8)

        r3=ctk.CTkFrame(form, fg_color="transparent"); r3.pack(fill="x", padx=12, pady=4)
        self.e_inicio = ctk.CTkEntry(r3, placeholder_text="Inicio (YYYY-MM-DD)", width=170); self.e_inicio.pack(side="left", padx=(0,8))
        ctk.CTkButton(r3, text="📅", width=36, command=lambda:self._calendar_pick(self.e_inicio)).pack(side="left")
        self.e_fin    = ctk.CTkEntry(r3, placeholder_text="Fin estimado (YYYY-MM-DD)", width=190); self.e_fin.pack(side="left", padx=(12,8))
        ctk.CTkButton(r3, text="📅", width=36, command=lambda:self._calendar_pick(self.e_fin)).pack(side="left")

        r4=ctk.CTkFrame(form, fg_color="transparent"); r4.pack(fill="x", padx=12, pady=(6,12))
        ctk.CTkButton(r4, text="Guardar Orden", command=self._guardar_orden).pack(side="left", padx=(0,8))
        ctk.CTkButton(r4, text="Eliminar Orden", fg_color="#ef4444", hover_color="#dc2626", command=self._delete_orden).pack(side="left", padx=8)
        ctk.CTkButton(r4, text="Marcar como completada", fg_color="#10b981", hover_color="#059669", command=self._mark_done).pack(side="left", padx=8)

        # --- Milestones panel (derecha arriba) ---
        milcard = ctk.CTkFrame(body, corner_radius=18)
        milcard.grid(row=0, column=1, sticky="nsew", padx=(8,0), pady=(0,12))
        ctk.CTkLabel(milcard, text="Milestones de Entrega (por Orden)", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(milcard, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))

        fr5=ctk.CTkFrame(milcard, fg_color="transparent"); fr5.pack(fill="x", padx=12, pady=4)
        self.om_orden = ctk.CTkOptionMenu(fr5, values=["(elige orden)"], width=120)
        self.om_orden.set("(elige orden)"); self.om_orden.pack(side="left", padx=(0,8))
        ctk.CTkButton(fr5, text="↻ Cargar órdenes", width=130, command=self._reload_orders_combo).pack(side="left", padx=8)
        self.e_due = ctk.CTkEntry(fr5, placeholder_text="Fecha entrega (YYYY-MM-DD)", width=180); self.e_due.pack(side="left", padx=(12,6))
        ctk.CTkButton(fr5, text="📅", width=36, command=lambda:self._calendar_pick(self.e_due)).pack(side="left")
        self.e_dqty= ctk.CTkEntry(fr5, placeholder_text="Qty a entregar", width=120); self.e_dqty.pack(side="left", padx=8)
        ctk.CTkButton(fr5, text="Agregar / Guardar", command=self._agregar_milestone).pack(side="left", padx=8)

        self.mil_scroll = ctk.CTkScrollableFrame(milcard, corner_radius=14, height=360)
        self.mil_scroll.pack(fill="both", expand=True, padx=12, pady=(8,12))

        # --- Órdenes planificadas (abajo ancho) ---
        self.table_card=ctk.CTkFrame(self, corner_radius=18)
        self.table_card.pack(fill="both", expand=True, padx=16, pady=(0,16))
        ctk.CTkLabel(self.table_card, text="Órdenes planificadas", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(self.table_card, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))
        cols=("orden","parte","molde","maquina","qty_total","inicio","fin","setup","estado")
        self.tree=ttk.Treeview(self.table_card, columns=cols, show="headings", height=9)
        headers=[("orden","Orden",120),("parte","Parte",160),("molde","Molde",80),("maquina","Máquina",90),
                 ("qty_total","Qty",90),("inicio","Inicio",110),("fin","Fin Est.",110),("setup","Setup",70),("estado","Estado",100)]
        for k,t,w in headers:
            self.tree.heading(k, text=t); self.tree.column(k, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0,12))
        self.tree.bind("<<TreeviewSelect>>", self._on_select_order)

        self._reload_orders_combo()
        self._reload_orders_table()
        self._render_milestones_panel()

    # ------- CRUD Órdenes -------
    def _guardar_orden(self):
        orden=self.e_orden.get().strip()
        parte=self.e_parte.get().strip()
        molde=self.e_molde.get().strip()
        maquina=self.om_maquina.get().strip()
        qty=self.e_qty.get().strip()
        setup=self.e_setup.get().strip() or "0"
        inicio=self.e_inicio.get().strip()
        fin=self.e_fin.get().strip()
        ciclo=self.e_ciclo.get().strip() or ""
        cavon=self.e_cavon.get().strip() or ""
        if not (orden and parte and molde and maquina and qty and inicio and fin):
            messagebox.showwarning("Faltan datos","Completa: orden, parte, molde, máquina, qty, inicio y fin."); return
        rows=leer_csv_dict(PLANNING_CSV); found=False
        for r in rows:
            if r.get("orden")==orden:
                r.update({"parte":parte,"molde_id":molde,"maquina_id":maquina,"qty_total":qty,
                          "inicio_ts":inicio,"fin_est_ts":fin,"setup_min":setup,"estado":r.get("estado","plan") or "plan",
                          "ciclo_s":ciclo,"cav_on":cavon})
                found=True; break
        if not found:
            rows.append({"orden":orden,"parte":parte,"molde_id":molde,"maquina_id":maquina,"qty_total":qty,
                         "inicio_ts":inicio,"fin_est_ts":fin,"setup_min":setup,"estado":"plan",
                         "ciclo_s":ciclo,"cav_on":cavon})
        with open(PLANNING_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","parte","molde_id","maquina_id","qty_total","inicio_ts","fin_est_ts","setup_min","estado","ciclo_s","cav_on"])
            w.writeheader(); w.writerows(rows)
        messagebox.showinfo("Orden","Orden guardada.")
        self._reload_orders_combo(); self._reload_orders_table()

    def _delete_orden(self):
        orden = self.e_orden.get().strip() or self.sel_orden_var.get().strip()
        if not orden: messagebox.showwarning("Orden","Selecciona o escribe la orden a eliminar."); return
        if not messagebox.askyesno("Eliminar","¿Eliminar la orden "+orden+"?"): return
        rows=[r for r in leer_csv_dict(PLANNING_CSV) if r.get("orden")!=orden]
        with open(PLANNING_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","parte","molde_id","maquina_id","qty_total","inicio_ts","fin_est_ts","setup_min","estado","ciclo_s","cav_on"])
            w.writeheader(); w.writerows(rows)
        # también borrar milestones asociados
        miles=[r for r in leer_csv_dict(DELIV_CSV) if r.get("orden")!=orden]
        with open(DELIV_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","due_date","qty","cumplido"])
            w.writeheader(); w.writerows(miles)
        messagebox.showinfo("Orden","Orden eliminada.")
        self._reload_orders_combo(); self._reload_orders_table(); self._render_milestones_panel()

    def _mark_done(self):
        orden = self.e_orden.get().strip() or self.sel_orden_var.get().strip()
        if not orden: messagebox.showwarning("Orden","Selecciona o escribe la orden a completar."); return
        rows=leer_csv_dict(PLANNING_CSV)
        for r in rows:
            if r.get("orden")==orden:
                r["estado"]="done"
        with open(PLANNING_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","parte","molde_id","maquina_id","qty_total","inicio_ts","fin_est_ts","setup_min","estado","ciclo_s","cav_on"])
            w.writeheader(); w.writerows(rows)
        self._reload_orders_table()
        messagebox.showinfo("Orden","Orden marcada como completada.")

    def _reload_orders_combo(self):
        rows=leer_csv_dict(PLANNING_CSV)
        ordenes=[r["orden"] for r in rows] if rows else ["(elige orden)"]
        self.om_orden.configure(values=ordenes)
        if ordenes:
            self.om_orden.set(ordenes[0])
            self.sel_orden_var.set(ordenes[0])

    def _reload_orders_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in leer_csv_dict(PLANNING_CSV):
            self.tree.insert("", "end", values=(r.get("orden",""), r.get("parte",""), r.get("molde_id",""), r.get("maquina_id",""),
                                                r.get("qty_total",""), r.get("inicio_ts",""), r.get("fin_est_ts",""),
                                                r.get("setup_min",""), r.get("estado","")))

    def _on_select_order(self, *_):
        sel=self.tree.selection()
        if not sel: return
        v=self.tree.item(sel[0],"values")
        self.sel_orden_var.set(str(v[0]))
        try: self.om_orden.set(str(v[0]))
        except: pass
        # autopoblar formulario para edición rápida
        (orden,parte,molde,maq,qty,ini,fin,setup,estado) = v
        self.e_orden.delete(0,"end"); self.e_orden.insert(0,orden)
        self.e_parte.delete(0,"end"); self.e_parte.insert(0,parte)
        self.e_molde.delete(0,"end"); self.e_molde.insert(0,molde)
        try: self.om_maquina.set(maq)
        except: pass
        self.e_qty.delete(0,"end"); self.e_qty.insert(0,qty)
        self.e_inicio.delete(0,"end"); self.e_inicio.insert(0,ini)
        self.e_fin.delete(0,"end"); self.e_fin.insert(0,fin)
        self.e_setup.delete(0,"end"); self.e_setup.insert(0,setup)
        self._render_milestones_panel()

    # ------- Milestones -------
    def _agregar_milestone(self):
        orden = self.om_orden.get().strip()
        if not orden or orden=="(elige orden)":
            messagebox.showwarning("Orden","Primero elige/crea una orden."); return
        due=self.e_due.get().strip()
        qty=parse_int_str(self.e_dqty.get().strip(),0)
        if not (due and qty>0):
            messagebox.showwarning("Milestone","Captura fecha y cantidad (>0)."); return
        # restricción: no más que producción total del molde
        orden_row = next((r for r in leer_csv_dict(PLANNING_CSV) if r.get("orden")==orden), None)
        if not orden_row:
            messagebox.showwarning("Orden","No se encontró la orden."); return
        molde = orden_row.get("molde_id","").strip()
        producido = producido_por_molde_global(molde)  # total producido del molde
        miles=[r for r in leer_csv_dict(DELIV_CSV) if r.get("orden")==orden]
        ya_prog = sum(parse_int_str(r.get("qty","0")) for r in miles)
        if qty + ya_prog > producido:
            messagebox.showwarning("Restricción",
                f"No puedes programar {qty} pzs. Ya hay {ya_prog} pzs en milestones y la producción total del molde es {producido} pzs.")
            return
        # append
        with open(DELIV_CSV,"a",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow([orden, due, str(qty), "0"])
        self.e_due.delete(0,"end"); self.e_dqty.delete(0,"end")
        self._render_milestones_panel()

    def _render_milestones_panel(self):
        for w in self.mil_scroll.winfo_children(): w.destroy()
        orden = self.om_orden.get().strip()
        if not orden or orden=="(elige orden)":
            ctk.CTkLabel(self.mil_scroll, text="Selecciona una orden para ver sus milestones.").pack(padx=10, pady=10)
            return
        miles=[r for r in leer_csv_dict(DELIV_CSV) if r.get("orden")==orden]
        miles.sort(key=lambda r: (r.get("due_date",""), r.get("qty","")))
        if not miles:
            ctk.CTkLabel(self.mil_scroll, text="Sin milestones.").pack(padx=10, pady=10)
            return

        orden_row = next((r for r in leer_csv_dict(PLANNING_CSV) if r.get("orden")==orden), None)
        molde = orden_row.get("molde_id","").strip() if orden_row else ""
        prod_total = producido_por_molde_global(molde)
        sum_acum = 0
        # agrupar por mes
        grupos={}
        for r in miles:
            ym=(r.get("due_date","") or "")[:7]
            grupos.setdefault(ym,[]).append(r)

        for ym in sorted(grupos.keys()):
            bloque = ctk.CTkFrame(self.mil_scroll, corner_radius=14)
            bloque.pack(fill="x", padx=8, pady=(6,8))
            ctk.CTkLabel(bloque, text=f"Mes {ym}", font=ctk.CTkFont("Helvetica", 13, "bold")).pack(anchor="w", padx=10, pady=(8,4))
            cont = ctk.CTkFrame(bloque, corner_radius=12)
            cont.pack(fill="x", padx=8, pady=(0,10))
            all_ok=True
            for r in grupos[ym]:
                due=r.get("due_date","")
                q=parse_int_str(r.get("qty","0"))
                sum_acum += q
                cumplido = prod_total >= sum_acum
                if not cumplido: all_ok=False
                fg = "#065F46" if cumplido else "#991B1B"
                bg = "#DCFCE7" if cumplido else "#FEE2E2"
                row = ctk.CTkFrame(cont, corner_radius=12, fg_color=bg)
                row.pack(fill="x", padx=8, pady=6)
                ctk.CTkLabel(row, text=f"{due} — {q} pzs", font=ctk.CTkFont("Helvetica", 13, "bold"), text_color=fg).pack(side="left", padx=10, pady=8)
                # botones edición / delete
                def _mk_delete(orden=orden, due=due, q=q):
                    return lambda: self._delete_milestone(orden, due, q)
                def _mk_edit(orden=orden, due=due, q=q):
                    return lambda: self._edit_milestone_dialog(orden, due, q)
                ctk.CTkButton(row, text="🗑", width=36, fg_color="#ef4444", hover_color="#dc2626",
                              command=_mk_delete()).pack(side="right", padx=(6,8), pady=6)
                ctk.CTkButton(row, text="✎", width=36, command=_mk_edit()).pack(side="right", padx=(0,6), pady=6)
            if all_ok:
                try: bloque.configure(fg_color="#ECFDF5")
                except: pass

        # resumen abajo
        resumen = ctk.CTkLabel(self.mil_scroll, text=f"Programado: {sum_acum} pzs • Producidas (molde {molde}): {prod_total}",
                               text_color=("#6b7280","#9CA3AF"))
        resumen.pack(anchor="w", padx=12, pady=(2,6))

    def _delete_milestone(self, orden, due, qty):
        rows=leer_csv_dict(DELIV_CSV); deleted=False
        new=[]
        for r in rows:
            if not deleted and r.get("orden")==orden and r.get("due_date")==due and str(r.get("qty",""))==str(qty):
                deleted=True; continue
            new.append(r)
        with open(DELIV_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","due_date","qty","cumplido"])
            w.writeheader(); w.writerows(new)
        self._render_milestones_panel()

    def _edit_milestone_dialog(self, orden, due, qty):
        top = tk.Toplevel(self); top.title("Editar milestone"); top.transient(self); top.grab_set(); top.resizable(False,False)
        frm = ctk.CTkFrame(top, corner_radius=10); frm.pack(fill="both", expand=True, padx=12, pady=12)
        e_due=ctk.CTkEntry(frm, width=180); e_due.insert(0,due); e_due.pack(side="left", padx=(0,6))
        ctk.CTkButton(frm, text="📅", width=36, command=lambda:self._calendar_pick(e_due, due)).pack(side="left", padx=6)
        e_qty=ctk.CTkEntry(frm, width=120); e_qty.insert(0,str(qty)); e_qty.pack(side="left", padx=6)
        def save():
            new_due=e_due.get().strip(); new_qty=parse_int_str(e_qty.get().strip(),0)
            if not (new_due and new_qty>0):
                messagebox.showwarning("Milestone","Datos inválidos."); return
            # actualizar (delete + add)
            self._delete_milestone(orden, due, qty)
            with open(DELIV_CSV,"a",newline="",encoding="utf-8") as f:
                csv.writer(f).writerow([orden,new_due,new_qty,"0"])
            top.destroy(); self._render_milestones_panel()
        ctk.CTkButton(frm, text="Guardar", command=save).pack(side="left", padx=8)
        ctk.CTkButton(frm, text="Cancelar", fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                      command=top.destroy).pack(side="left", padx=8)

# ================================
# === Tablero de Órdenes PRO
# ================================
class OrdersBoardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._timer=None
        self._build()

    def _tone(self, frac):
        if frac >= 0.9: return ("#DCFCE7","#065F46")
        if frac >= 0.6: return ("#FEF9C3","#92400E")
        return ("#FEE2E2","#991B1B")

    def _build(self):
        header=ctk.CTkFrame(self, corner_radius=0, fg_color=("white","#111111"))
        header.pack(fill="x", side="top")
        left=ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", command=self.app.go_menu, width=110, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text="Tablero de Órdenes (Progreso)", font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")
        right=ctk.CTkFrame(header, fg_color="transparent"); right.pack(side="right", padx=16, pady=10)
        ctk.CTkButton(right, text="↻ Actualizar", command=self._refresh_cards).pack(side="right")
        body=ctk.CTkScrollableFrame(self, corner_radius=0)
        body.pack(fill="both", expand=True, padx=16, pady=16)
        self.cards_container = body
        self._refresh_cards()

    def _refresh_cards(self):
        for w in self.cards_container.winfo_children(): w.destroy()
        rows=leer_csv_dict(PLANNING_CSV)
        try: rows.sort(key=lambda r: r.get("fin_est_ts",""))
        except: pass

        for r in rows:
            orden=r.get("orden",""); parte=r.get("parte",""); molde=r.get("molde_id","")
            maquina=r.get("maquina_id",""); qty_total=parse_int_str(r.get("qty_total","0"))
            ini=r.get("inicio_ts",""); fin=r.get("fin_est_ts",""); setup=r.get("setup_min","0")
            estado=r.get("estado","plan")
            prod = producido_por_molde_global(molde)
            shipped = enviados_por_orden(orden)
            disp = max(0, prod - shipped)
            frac_prod = (prod/qty_total) if qty_total>0 else 0.0
            frac_ship = (shipped/qty_total) if qty_total>0 else 0.0
            bg,fg = self._tone(frac_prod)

            try:
                dleft = (datetime.strptime(fin,"%Y-%m-%d").date() - date.today()).days
                days_left = f"{dleft} días restantes"
            except:
                days_left = "—"

            card = ctk.CTkFrame(self.cards_container, corner_radius=18, fg_color=bg)
            card.pack(fill="x", padx=6, pady=8)
            head = ctk.CTkFrame(card, fg_color="transparent"); head.pack(fill="x", padx=12, pady=(10,6))
            ctk.CTkLabel(head, text=f"Orden {orden} — {parte}", font=ctk.CTkFont("Helvetica", 15, "bold"), text_color=fg).pack(side="left")
            ctk.CTkLabel(head, text=f"Molde {molde} • Máquina {maquina}", font=ctk.CTkFont("Helvetica", 12)).pack(side="left", padx=8)
            ctk.CTkLabel(head, text=f"Inicio {ini} • Fin {fin} • Setup {setup} min • Estado {estado}", font=ctk.CTkFont("Helvetica", 12),
                         text_color=("#6b7280","#9CA3AF")).pack(side="right")

            # progreso producción
            ctk.CTkLabel(card, text="Progreso de producción").pack(anchor="w", padx=12)
            barp=ctk.CTkProgressBar(card); barp.set(frac_prod); barp.pack(fill="x", padx=12)
            row1=ctk.CTkFrame(card, fg_color="transparent"); row1.pack(fill="x", padx=12, pady=(4,8))
            ctk.CTkLabel(row1, text=f"Producidas: {prod}/{qty_total} pzs").pack(side="left")
            ctk.CTkLabel(row1, text=days_left).pack(side="right")

            # progreso salidas
            ctk.CTkLabel(card, text="Progreso de salidas / embarques").pack(anchor="w", padx=12)
            bars=ctk.CTkProgressBar(card); bars.set(frac_ship); bars.pack(fill="x", padx=12)
            row2=ctk.CTkFrame(card, fg_color="transparent"); row2.pack(fill="x", padx=12, pady=(4,10))
            ctk.CTkLabel(row2, text=f"Enviado: {shipped}/{qty_total} pzs  •  Disponible: {disp}").pack(side="left")
            ctk.CTkButton(row2, text="Registrar salida", command=lambda o=orden: self.app.go_shipments(o)).pack(side="right", padx=(6,0))
            ctk.CTkButton(row2, text="Ver planificación", fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                          command=self.app.go_planning).pack(side="right")

        if self._timer: self.after_cancel(self._timer)
        self._timer = self.after(6000, self._refresh_cards)

# ================================
# === Salida de Piezas (Embarques)
# ================================
class ShipmentsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app=app
        self._build()

    def _calendar_pick(self, entry: ctk.CTkEntry):
        try:
            y,m,d=map(int,(entry.get() or date.today().isoformat()).split("-"))
            init=date(y,m,d)
        except:
            init=date.today()
        top=tk.Toplevel(self); top.title("Selecciona fecha"); top.transient(self); top.grab_set(); top.resizable(False,False)
        self.update_idletasks()
        top.geometry(f"+{self.winfo_rootx()+self.winfo_width()//2-180}+{self.winfo_rooty()+self.winfo_height()//2-170}")
        cal=Calendar(top, selectmode="day", year=init.year, month=init.month, day=init.day, date_pattern="yyyy-mm-dd",
                     firstweekday="monday", showweeknumbers=False)
        cal.pack(padx=14, pady=14)
        def choose():
            entry.delete(0,"end"); entry.insert(0, cal.get_date()); top.destroy()
        tk.Button(top, text="Seleccionar", command=choose).pack(side="left", padx=10, pady=10)
        tk.Button(top, text="Cerrar", command=top.destroy).pack(side="left", padx=10, pady=10)

    def _build(self):
        header=ctk.CTkFrame(self, corner_radius=0, fg_color=("white","#111111"))
        header.pack(fill="x", side="top")
        left=ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", command=self.app.go_menu, width=110, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text="Salida de Piezas (Embarques)", font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")

        body=ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=16, pady=16)
        body.grid_columnconfigure(0, weight=1); body.grid_columnconfigure(1, weight=1); body.grid_rowconfigure(1, weight=1)

        # --- formulario alta ---
        form=ctk.CTkFrame(body, corner_radius=18)
        form.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=(0,12))
        ctk.CTkLabel(form, text="Registrar salida", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(form, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))
        fr=ctk.CTkFrame(form, fg_color="transparent"); fr.pack(fill="x", padx=12, pady=4)

        self.om_order = ctk.CTkOptionMenu(fr, values=["(elige orden)"], width=120, command=lambda _v: self._refresh_stats())
        self.om_order.pack(side="left", padx=(0,8))
        ctk.CTkButton(fr, text="↻", width=36, command=self._reload_orders).pack(side="left", padx=6)

        self.e_date=ctk.CTkEntry(fr, placeholder_text="Fecha (YYYY-MM-DD)", width=170); self.e_date.pack(side="left", padx=(12,6))
        ctk.CTkButton(fr, text="📅", width=36, command=lambda:self._calendar_pick(self.e_date)).pack(side="left", padx=6)

        self.e_qty = ctk.CTkEntry(fr, placeholder_text="Cantidad", width=120); self.e_qty.pack(side="left", padx=8)
        self.e_dest= ctk.CTkEntry(fr, placeholder_text="Destino (opcional)", width=180); self.e_dest.pack(side="left", padx=8)
        self.e_note= ctk.CTkEntry(fr, placeholder_text="Nota (opcional)", width=180); self.e_note.pack(side="left", padx=8)
        ctk.CTkButton(fr, text="Guardar salida", command=self._save_shipment).pack(side="left", padx=8)

        # stats de orden
        self.stats = ctk.CTkLabel(form, text="—", text_color=("#6b7280","#9CA3AF"))
        self.stats.pack(anchor="w", padx=12, pady=(6,12))

        # --- tabla de salidas por orden ---
        listcard=ctk.CTkFrame(body, corner_radius=18)
        listcard.grid(row=0, column=1, sticky="nsew", padx=(8,0), pady=(0,12))
        ctk.CTkLabel(listcard, text="Salidas de la orden", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(listcard, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))
        cols=("fecha","qty","destino","nota")
        self.tree=ttk.Treeview(listcard, columns=cols, show="headings", height=9)
        for k,t,w in [("fecha","Fecha",120),("qty","Qty",80),("destino","Destino",160),("nota","Nota",240)]:
            self.tree.heading(k, text=t); self.tree.column(k, width=w, anchor="center" if k!="nota" else "w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0,10))
        btns=ctk.CTkFrame(listcard, fg_color="transparent"); btns.pack(fill="x", padx=12, pady=(0,12))
        ctk.CTkButton(btns, text="Eliminar selección", fg_color="#ef4444", hover_color="#dc2626", command=self._delete_selected).pack(side="left")

        # acceso rápido
        actions=ctk.CTkFrame(self, fg_color="transparent"); actions.pack(fill="x", padx=16, pady=(0,16))
        ctk.CTkButton(actions, text="← Tablero de Órdenes", command=self.app.go_orders_board).pack(side="left")
        ctk.CTkButton(actions, text="Ir a Planificación", fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                      command=self.app.go_planning).pack(side="left", padx=8)

        self._reload_orders()
        self.e_date.insert(0, date.today().isoformat())

    def set_order(self, orden: str):
        self._reload_orders()
        try: self.om_order.set(orden)
        except: pass
        self._refresh_stats()
        self._reload_table()

    def _reload_orders(self):
        ordenes=[r.get("orden","") for r in leer_csv_dict(PLANNING_CSV)]
        if not ordenes: ordenes=["(elige orden)"]
        self.om_order.configure(values=ordenes)
        if self.app._shipments_preselect_order and self.app._shipments_preselect_order in ordenes:
            self.om_order.set(self.app._shipments_preselect_order)
        else:
            self.om_order.set(ordenes[0])
        self._refresh_stats(); self._reload_table()

    def _refresh_stats(self):
        o=self.om_order.get().strip()
        if not o: self.stats.configure(text="—"); return
        orow = next((r for r in leer_csv_dict(PLANNING_CSV) if r.get("orden")==o), None)
        if not orow:
            self.stats.configure(text="—"); return
        molde = orow.get("molde_id","")
        qty_total = parse_int_str(orow.get("qty_total","0"))
        prod = producido_por_molde_global(molde)
        shipped = enviados_por_orden(o)
        disp = max(0, prod - shipped)
        self.stats.configure(text=f"Orden {o} • Molde {molde} • Qty total {qty_total} • Producidas {prod} • Enviadas {shipped} • Disponibles {disp}")

    def _reload_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        o=self.om_order.get().strip()
        for r in leer_csv_dict(SHIPMENTS_CSV):
            if r.get("orden")==o:
                self.tree.insert("", "end", values=(r.get("ship_date",""), r.get("qty",""), r.get("destino",""), r.get("nota","")))

    def _save_shipment(self):
        o=self.om_order.get().strip()
        if not o: messagebox.showwarning("Orden","Elige una orden."); return
        d=self.e_date.get().strip()
        q=parse_int_str(self.e_qty.get().strip(),0)
        if not (d and q>0):
            messagebox.showwarning("Salida","Fecha y cantidad (>0) obligatorias."); return
        orow = next((r for r in leer_csv_dict(PLANNING_CSV) if r.get("orden")==o), None)
        if not orow:
            messagebox.showwarning("Orden","No existe la orden."); return
        molde = orow.get("molde_id",""); prod = producido_por_molde_global(molde)
        shipped = enviados_por_orden(o); disp=max(0, prod - shipped)
        if q > disp:
            messagebox.showwarning("Límite","No puedes enviar más de lo disponible. Disp: "+str(disp)); return
        dest=self.e_dest.get().strip(); nota=self.e_note.get().strip()
        with open(SHIPMENTS_CSV,"a",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow([o,d,str(q),dest,nota])
        self.e_qty.delete(0,"end"); self.e_dest.delete(0,"end"); self.e_note.delete(0,"end")
        self._refresh_stats(); self._reload_table()
        messagebox.showinfo("Salida","Salida registrada.")

    def _delete_selected(self):
        sel=self.tree.selection()
        if not sel: return
        vals=self.tree.item(sel[0],"values")
        d,q,dest,nota=vals
        o=self.om_order.get().strip()
        rows=leer_csv_dict(SHIPMENTS_CSV); done=False; new=[]
        for r in rows:
            if not done and r.get("orden")==o and r.get("ship_date")==d and str(r.get("qty",""))==str(q) and r.get("destino","")==dest and r.get("nota","")==nota:
                done=True; continue
            new.append(r)
        with open(SHIPMENTS_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota"])
            w.writeheader(); w.writerows(new)
        self._refresh_stats(); self._reload_table()

# --- main ---
if __name__ == "__main__":
    try:
        import ctypes; ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app=App()
    app.mainloop()
