# -*- coding: utf-8 -*-
# Requisitos:
#   pip install customtkinter pillow tkcalendar matplotlib plotly kaleido pandas fpdf openpyxl

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from tkcalendar import Calendar
import csv, os, logging, traceback
from datetime import datetime, date, timedelta

from config import *
from csv_utils import *
from metrics import *

from views.recipes import RecipesView
from views.machine_recipes import MachineRecipesView
from views.machine_chooser import MachineChooser
from views.oee_view import OEEView
from views.live_dashboard import LiveDashboard
from views.reports_view import ReportsView
from views.main_menu import MainMenu
from views.planning import PlanningMilestonesView
from views.orders_board import OrdersBoardView
from views.inventory_view import InventoryView
from views.shipments_view import ShipmentsView
from views.calculo_view import CalculoView

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme(os.path.join(BASE_DIR, "ios_blue.json"))
        self.title("Mefrup — ALS")
        try:
            self.state("zoomed")
        except:
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}")
        self.configure(fg_color="#F5F5F7")

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
        self.inventory_page = None
        self.shipments_page = None
        self.calculo_page = None
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
        self.machine_recipes_page=MachineRecipesView(self.container, self)
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
        try:
            # refresco inmediato para mostrar datos actuales
            self.dashboard_page._refresh_now(date.today().isoformat())
        except Exception:
            logging.exception("Error al refrescar tablero en vivo")

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

    def go_machine_recipes(self):
        self._unbind_shortcuts_oee()
        self._pack_only(self.machine_recipes_page)

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

    def go_inventory(self):
        if not self.inventory_page:
            self.inventory_page = InventoryView(self.container, self)
        self._pack_only(self.inventory_page)

    def go_shipments(self, preselect_order: str|None=None):
        self._shipments_preselect_order = preselect_order
        if not self.shipments_page:
            self.shipments_page = ShipmentsView(self.container, self)
        self._pack_only(self.shipments_page)
        if preselect_order:
            self.shipments_page.set_order(preselect_order)

    def go_calculo(self):
        self._unbind_shortcuts_oee()
        pwd = ctk.CTkInputDialog(text="Contraseña:", title="Acceso a Calculo").get_input()
        if pwd == "15211521Gg":
            if not self.calculo_page:
                self.calculo_page = CalculoView(self.container, self)
            self._pack_only(self.calculo_page)
        elif pwd is not None:
            messagebox.showerror("Acceso denegado", "Contraseña incorrecta.")

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
        total_area = scrap_area = meta_area = 0
        suma_oee = 0.0
        for m in MACHINES:
            r = resumen_hoy_maquina(m, f)
            suma_oee += r["oee"]
            total_area += r["total"]
            scrap_area += r["scrap"]
            meta_area += r["meta"]
        if MACHINES:
            OEE_area = suma_oee / len(MACHINES)
        else:
            OEE_area = 0.0
        escribir_daily(DAILY_CSV_INJECTOR, f, OEE_area, total_area, scrap_area, meta_area)

        self._refrescar_dia(); self._refrescar_hist(); self._refrescar_global(); self._update_save_state()
        if getattr(self, 'dashboard_page', None):
            try:
                self.dashboard_page._refresh_now(f)
            except Exception:
                logging.exception("Error al actualizar tablero en vivo")
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
if __name__ == "__main__":
    try:
        import ctypes; ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app=App()
    app.mainloop()
