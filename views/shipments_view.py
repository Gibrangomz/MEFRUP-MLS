from .base import *
from metrics import compute_fifo_assignments, order_metrics, mold_metrics, totals_from_fifo

class ShipmentsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app=app
        self._tab=None
        self._ship_filter_status = tk.StringVar(value="Todas")     # filtro en "Por Orden"
        self._log_filter_status  = tk.StringVar(value="Todas")     # filtro en "Global"
        self._log_filter_text    = tk.StringVar(value="")
        self._log_dt_from        = tk.StringVar(value="")
        self._log_dt_to          = tk.StringVar(value="")
        self._approve_on_save    = tk.BooleanVar(value=False)      # "Aprobar al guardar"
        self._selected_order     = ""
        self._build()

    # ========== Helpers ==========
    def _shipments_all(self):
        try: return leer_shipments()
        except Exception: return []

    def _shipments_approved(self):
        return [r for r in self._shipments_all() if str(r.get("approved","0")).strip()=="1"]

    def _shipments_pending(self):
        return [r for r in self._shipments_all() if str(r.get("approved","0")).strip()!="1"]

    def _status_label(self, r):
        return "Aprobada" if str(r.get("approved","0")).strip()=="1" else "Pendiente"

    def _sum_qty(self, rows):
        s=0
        for r in rows:
            try: s += int(float(r.get("qty",0) or 0))
            except: pass
        return s

    def _calendar_pick(self, entry: ctk.CTkEntry):
        try:
            y,m,d = map(int, (entry.get() or date.today().isoformat()).split("-"))
            init = date(y,m,d)
        except:
            init = date.today()
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

    def set_order(self, orden: str):
        # llamado desde otras vistas para precargar una orden
        try:
            self._om_order.set(orden)
            self._selected_order = orden
            self._refresh_order_header()
            self._reload_order_shipments()
        except:
            pass

    # ========== UI ==========
    def _build(self):
        # Header
        header=ctk.CTkFrame(self, corner_radius=0, fg_color=("white","#111111"))
        header.pack(fill="x", side="top")
        left=ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", command=self.app.go_menu, width=110, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text="Salidas / Embarques", font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")
        right=ctk.CTkFrame(header, fg_color="transparent"); right.pack(side="right", padx=16, pady=10)
        ctk.CTkButton(right, text="↻ Actualizar todo", command=self._reload_all).pack(side="right")

        # Tabs
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=16, pady=16)
        self._tab = tabs
        tab_order  = tabs.add("Por Orden")
        tab_global = tabs.add("Global")
        tab_analytics = tabs.add("Analytics")

        # ===== Tab: Por Orden =====
        tab_order.grid_columnconfigure(0, weight=1)
        tab_order.grid_columnconfigure(1, weight=1)
        tab_order.grid_rowconfigure(2, weight=1)

        # Form alta a la izquierda
        form=ctk.CTkFrame(tab_order, corner_radius=18)
        form.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,10))
        ctk.CTkLabel(form, text="Alta de salida", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(form, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))

        fr = ctk.CTkFrame(form, fg_color="transparent"); fr.pack(fill="x", padx=12, pady=6)
        ordenes = [r.get("orden","") for r in leer_csv_dict(PLANNING_CSV)] or ["(elige orden)"]
        self._om_order = ctk.CTkOptionMenu(fr, values=ordenes, width=150,
                                           command=lambda _v: (self._on_order_change()))
        self._om_order.pack(side="left")
        ctk.CTkButton(fr, text="↻", width=40, command=self._reload_orders_list).pack(side="left", padx=6)

        self._e_date=ctk.CTkEntry(fr, placeholder_text="Fecha (YYYY-MM-DD)", width=170); self._e_date.pack(side="left", padx=(16,6))
        ctk.CTkButton(fr, text="📅", width=36, command=lambda: self._calendar_pick(self._e_date)).pack(side="left", padx=6)
        self._e_qty = ctk.CTkEntry(fr, placeholder_text="Cantidad", width=120); self._e_qty.pack(side="left", padx=6)
        self._e_dest= ctk.CTkEntry(fr, placeholder_text="Destino (opcional)", width=220); self._e_dest.pack(side="left", padx=6)
        self._e_note= ctk.CTkEntry(fr, placeholder_text="Nota (opcional)", width=220); self._e_note.pack(side="left", padx=6)
        ctk.CTkCheckBox(fr, text="Aprobar al guardar", variable=self._approve_on_save).pack(side="left", padx=12)
        ctk.CTkButton(fr, text="Guardar salida", command=self._save_shipment).pack(side="right", padx=(6,0))

        # KPIs/Resumen orden + molde
        self._lbl_order = ctk.CTkLabel(tab_order, text="—", font=ctk.CTkFont("Helvetica", 13))
        self._lbl_order.grid(row=1, column=0, sticky="w", padx=6, pady=(0,6))
        self._lbl_mold  = ctk.CTkLabel(tab_order, text="—", text_color=("#6b7280","#9CA3AF"))
        self._lbl_mold.grid(row=1, column=1, sticky="e", padx=6, pady=(0,6))

        # Tabla envíos por orden + filtros
        left=ctk.CTkFrame(tab_order, corner_radius=18); left.grid(row=2, column=0, sticky="nsew", padx=(0,8))
        left.grid_rowconfigure(2, weight=1)

        head=ctk.CTkFrame(left, fg_color="transparent"); head.grid(row=0, column=0, sticky="ew", padx=12, pady=(10,4))
        ctk.CTkLabel(head, text="Salidas de esta orden", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(side="left")
        ctk.CTkOptionMenu(head, variable=self._ship_filter_status, values=["Todas","Aprobadas","Pendientes"],
                          command=lambda _v: self._reload_order_shipments()).pack(side="right")

        ctk.CTkFrame(left, height=1, fg_color=("#E5E7EB","#2B2B2B")).grid(row=1, column=0, sticky="ew", padx=12, pady=(0,6))
        cols=("status","fecha","qty","destino","nota")
        self._tree_ord = ttk.Treeview(left, columns=cols, show="headings", height=12)
        for k,t,w in [("status","Estado",90),("fecha","Fecha",110),("qty","Qty",80),("destino","Destino",180),("nota","Nota",260)]:
            self._tree_ord.heading(k, text=t); self._tree_ord.column(k, width=w, anchor="center" if k not in ("destino","nota") else "w")
        self._tree_ord.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0,6))

        act=ctk.CTkFrame(left, fg_color="transparent"); act.grid(row=3, column=0, sticky="ew", padx=12, pady=(0,10))
        ctk.CTkButton(act, text="Aprobar selección", command=self._approve_selected_in_order).pack(side="left")
        ctk.CTkButton(act, text="Editar...", command=self._edit_selected_in_order).pack(side="left", padx=6)
        ctk.CTkButton(act, text="Duplicar", command=self._clone_selected_in_order).pack(side="left", padx=6)
        ctk.CTkButton(act, text="Eliminar", fg_color="#ef4444", hover_color="#dc2626", command=self._delete_selected_in_order).pack(side="left", padx=6)
        ctk.CTkButton(act, text="Exportar CSV (orden)", command=self._export_order_csv).pack(side="right")

        # Panel derecho: progreso y barras
        right=ctk.CTkFrame(tab_order, corner_radius=18); right.grid(row=2, column=1, sticky="nsew", padx=(8,0))
        ctk.CTkLabel(right, text="Progreso de la Orden", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(right, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))
        self._bar_prog = ctk.CTkProgressBar(right); self._bar_prog.set(0.0); self._bar_prog.pack(fill="x", padx=12)
        self._lbl_prog  = ctk.CTkLabel(right, text="—", text_color=("#6b7280","#9CA3AF")); self._lbl_prog.pack(anchor="w", padx=12, pady=(2,6))
        self._lbl_kpis  = ctk.CTkLabel(right, text="—", text_color=("#6b7280","#9CA3AF")); self._lbl_kpis.pack(anchor="w", padx=12, pady=(4,10))

        # ===== Tab: Global =====
        tab_global.grid_rowconfigure(2, weight=1)

        flt=ctk.CTkFrame(tab_global, corner_radius=18); flt.grid(row=0, column=0, sticky="ew", pady=(0,8))
        ctk.CTkLabel(flt, text="Filtros", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(flt, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))

        frf=ctk.CTkFrame(flt, fg_color="transparent"); frf.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(frf, text="Desde").pack(side="left")
        e_from=ctk.CTkEntry(frf, textvariable=self._log_dt_from, placeholder_text="YYYY-MM-DD", width=140); e_from.pack(side="left", padx=6)
        ctk.CTkButton(frf, text="📅", width=36, command=lambda: self._calendar_pick(e_from)).pack(side="left", padx=(0,10))
        ctk.CTkLabel(frf, text="Hasta").pack(side="left")
        e_to=ctk.CTkEntry(frf, textvariable=self._log_dt_to, placeholder_text="YYYY-MM-DD", width=140); e_to.pack(side="left", padx=6)
        ctk.CTkButton(frf, text="📅", width=36, command=lambda: self._calendar_pick(e_to)).pack(side="left", padx=(0,10))

        ordenes_plus = ["(todas)"] + ordenes
        self._om_log_order = ctk.CTkOptionMenu(frf, values=ordenes_plus, width=150)
        self._om_log_order.pack(side="left", padx=(10,6))
        ctk.CTkOptionMenu(frf, variable=self._log_filter_status, values=["Todas","Aprobadas","Pendientes"]).pack(side="left", padx=6)
        ctk.CTkEntry(frf, textvariable=self._log_filter_text, placeholder_text="Buscar orden / destino / nota...", width=280).pack(side="left", padx=8)
        ctk.CTkButton(frf, text="Filtrar", command=self._reload_log).pack(side="left", padx=6)
        ctk.CTkButton(frf, text="Limpiar", command=self._clear_log_filters).pack(side="left", padx=6)

        cols3=("orden","molde","status","fecha","qty","destino","nota")
        self._tree_log=ttk.Treeview(tab_global, columns=cols3, show="headings", height=12)
        for k,t,w in [("orden","Orden",90),("molde","Molde",80),("status","Estado",90),("fecha","Fecha",110),
                      ("qty","Qty",80),("destino","Destino",220),("nota","Nota",320)]:
            self._tree_log.heading(k, text=t); self._tree_log.column(k, width=w, anchor="center" if k in ("orden","molde","status","fecha","qty") else "w")
        self._tree_log.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0,6))

        actg=ctk.CTkFrame(tab_global, fg_color="transparent"); actg.grid(row=3, column=0, sticky="ew", padx=6, pady=(0,12))
        ctk.CTkButton(actg, text="Aprobar selección", command=self._approve_selected_in_log).pack(side="left")
        ctk.CTkButton(actg, text="Eliminar selección", fg_color="#ef4444", hover_color="#dc2626", command=self._delete_selected_in_log).pack(side="left", padx=6)
        ctk.CTkButton(actg, text="Exportar CSV (vista)", command=self._export_log_csv).pack(side="right")

        self._lbl_totals_log = ctk.CTkLabel(tab_global, text="—", text_color=("#6b7280","#9CA3AF"))
        self._lbl_totals_log.grid(row=4, column=0, sticky="w", padx=6, pady=(0,6))

        # ===== Tab: Analytics =====
        tab_analytics.grid_columnconfigure(0, weight=1)
        tab_analytics.grid_columnconfigure(1, weight=1)

        # por orden
        cardA=ctk.CTkFrame(tab_analytics, corner_radius=18); cardA.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        ctk.CTkLabel(cardA, text="Resumen por Orden (aprobadas)", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(cardA, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))
        colsA=("orden","parte","molde","objetivo","enviado","avance","pendiente")
        self._tree_agg_ord = ttk.Treeview(cardA, columns=colsA, show="headings", height=12)
        for k,t,w in [("orden","Orden",90),("parte","Parte",160),("molde","Molde",80),("objetivo","Obj.",90),
                      ("enviado","Enviado✔",110),("avance","Avance %",90),("pendiente","Pend.",90)]:
            self._tree_agg_ord.heading(k, text=t); self._tree_agg_ord.column(k, width=w, anchor="center" if k!="parte" else "w")
        self._tree_agg_ord.pack(fill="both", expand=True, padx=12, pady=(0,10))

        # por molde
        cardB=ctk.CTkFrame(tab_analytics, corner_radius=18); cardB.grid(row=0, column=1, sticky="nsew", padx=(8,0))
        ctk.CTkLabel(cardB, text="Resumen por Molde", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(cardB, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))
        colsB=("molde","bruto","enviado","neto","sobrante")
        self._tree_agg_mold = ttk.Treeview(cardB, columns=colsB, show="headings", height=12)
        for k,t,w in [("molde","Molde",90),("bruto","Bruto",100),("enviado","Enviado✔",110),("neto","Neto",100),("sobrante","Sobrante",110)]:
            self._tree_agg_mold.heading(k, text=t); self._tree_agg_mold.column(k, width=w, anchor="center")
        self._tree_agg_mold.pack(fill="both", expand=True, padx=12, pady=(0,10))

        # init
        self._e_date.insert(0, date.today().isoformat())
        if ordenes and ordenes[0]:
            self._om_order.set(ordenes[0])
            self._selected_order = ordenes[0]
        self._reload_all()

    # ========== Data reloads ==========
    def _reload_all(self):
        # Por Orden
        self._refresh_order_header()
        self._reload_order_shipments()
        # Global
        self._reload_log()
        # Analytics
        self._reload_analytics()

    def _reload_orders_list(self):
        ordenes=[r.get("orden","") for r in leer_csv_dict(PLANNING_CSV)] or ["(elige orden)"]
        self._om_order.configure(values=ordenes)

    def _on_order_change(self):
        self._selected_order = self._om_order.get().strip()
        self._refresh_order_header()
        self._reload_order_shipments()

    # --- Encabezados y barras (Por Orden)
    def _refresh_order_header(self):
        if not self._selected_order:
            self._lbl_order.configure(text="—"); self._lbl_mold.configure(text="—")
            self._bar_prog.set(0.0); self._lbl_prog.configure(text="—"); self._lbl_kpis.configure(text="—")
            return
        plan = leer_csv_dict(PLANNING_CSV)
        row = next((r for r in plan if (r.get("orden","") or "").strip()==self._selected_order), None)
        if not row:
            self._lbl_order.configure(text="—"); self._lbl_mold.configure(text="—")
            self._bar_prog.set(0.0); self._lbl_prog.configure(text="—"); self._lbl_kpis.configure(text="—")
            return

        molde=(row.get("molde_id","") or "").strip()
        parte=(row.get("parte","") or "").strip()
        fifo = compute_fifo_assignments(plan)
        m = order_metrics(row, fifo)
        mm= mold_metrics(molde, fifo)

        objetivo=m["objetivo"]; enviado=m["enviado"]; asignado=m["asignado"]; progreso=m["progreso"]; pendiente=m["pendiente"]
        frac = (progreso/objetivo) if objetivo>0 else 0.0

        self._lbl_order.configure(text=f"Orden {self._selected_order} — {parte}  •  Obj {objetivo:,}")
        self._bar_prog.set(frac)
        self._lbl_prog.configure(text=f"Progreso: {progreso:,}  (= Enviado {enviado:,} + Asignado {asignado:,})  •  Pendiente: {pendiente:,}")
        self._lbl_mold.configure(text=f"Molde {molde}  •  Neto molde: {mm['neto']:,}  •  Sobrante sin asignar: {mm['sobrante']:,}")
        self._lbl_kpis.configure(text=f"Envíos aprobados (orden): {enviado:,} pzs")

    # --- Tabla envíos de la orden
    def _get_order_shipments_filtered(self, orden):
        rows = [r for r in self._shipments_all() if (r.get("orden","") or "").strip()==(orden or "")]
        st = self._ship_filter_status.get()
        if st=="Aprobadas":
            rows = [r for r in rows if str(r.get("approved","0")).strip()=="1"]
        elif st=="Pendientes":
            rows = [r for r in rows if str(r.get("approved","0")).strip()!="1"]
        try: rows.sort(key=lambda r: r.get("ship_date",""))
        except: pass
        return rows

    def _reload_order_shipments(self):
        for i in self._tree_ord.get_children(): self._tree_ord.delete(i)
        if not self._selected_order: return
        rows = self._get_order_shipments_filtered(self._selected_order)
        for r in rows:
            self._tree_ord.insert("", "end", values=(self._status_label(r), r.get("ship_date",""), r.get("qty",""),
                                                     r.get("destino",""), r.get("nota","")))

    # --- Guardar (alta) con validación FIFO y “aprobar al guardar”
    def _save_shipment(self):
        o=self._om_order.get().strip()
        if not o or o=="(elige orden)":
            messagebox.showwarning("Orden","Elige una orden."); return
        d=self._e_date.get().strip()
        q=parse_int_str(self._e_qty.get().strip(),0)
        if not (d and q>0):
            messagebox.showwarning("Salida","Fecha y cantidad (>0) obligatorias."); return
        dest=self._e_dest.get().strip(); nota=self._e_note.get().strip()

        plan=leer_csv_dict(PLANNING_CSV)
        orow=next((r for r in plan if (r.get("orden","") or "")==o), None)
        if not orow:
            messagebox.showwarning("Orden","La orden no existe."); return

        # Si se va a aprobar en el guardado: validar contra asignado FIFO
        if self._approve_on_save.get():
            fifo = compute_fifo_assignments(plan)
            asignado = order_metrics(orow, fifo)["asignado"]
            if q > asignado:
                messagebox.showwarning("Límite", f"No puedes aprobar {q} pzs: asignado FIFO a la orden = {asignado} pzs.")
                return

        approved_flag = "1" if self._approve_on_save.get() else "0"
        with open(SHIPMENTS_CSV, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([o, d, str(q), dest, nota, approved_flag])

        self._e_qty.delete(0,"end"); self._e_dest.delete(0,"end"); self._e_note.delete(0,"end")
        self._refresh_order_header(); self._reload_order_shipments(); self._reload_log(); self._reload_analytics()
        messagebox.showinfo("Salida", "Salida registrada " + ("(aprobada)" if approved_flag=="1" else "y pendiente de aprobación."))

    # --- Aprobar / Editar / Duplicar / Eliminar en "Por Orden"
    def _approve_selected_in_order(self):
        sel=self._tree_ord.selection()
        if not sel: return
        # calcular total a aprobar (solo pendientes)
        approve_list=[]
        tot_to_approve=0
        for iid in sel:
            status, fecha, qty, dest, nota = self._tree_ord.item(iid,"values")
            if status=="Aprobada": continue
            approve_list.append((fecha, str(qty), dest, nota))
            try: tot_to_approve += int(float(qty))
            except: pass

        if not approve_list: return

        plan=leer_csv_dict(PLANNING_CSV)
        orow=next((r for r in plan if (r.get("orden","") or "")==self._selected_order), None)
        fifo=compute_fifo_assignments(plan)
        asignado = order_metrics(orow, fifo)["asignado"]

        if tot_to_approve > asignado:
            messagebox.showwarning("Límite", f"No puedes aprobar {tot_to_approve} pzs: asignado FIFO a la orden = {asignado} pzs.")
            return

        rows=leer_shipments(); changed=False
        for r in rows:
            if (r.get("orden","") or "")==self._selected_order and r.get("approved","0")!="1":
                key=(r.get("ship_date",""), str(r.get("qty","")), r.get("destino",""), r.get("nota",""))
                if key in approve_list:
                    r["approved"]="1"; changed=True

        if changed:
            with open(SHIPMENTS_CSV,"w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved"])
                w.writeheader(); w.writerows(rows)
            self._refresh_order_header(); self._reload_order_shipments(); self._reload_log(); self._reload_analytics()

    def _edit_selected_in_order(self):
        sel=self._tree_ord.selection()
        if not sel: return
        status, fecha, qty, dest, nota = self._tree_ord.item(sel[0], "values")
        self._open_edit_dialog(self._selected_order, fecha, qty, dest, nota, status=="Aprobada")

    def _clone_selected_in_order(self):
        sel=self._tree_ord.selection()
        if not sel: return
        status, fecha, qty, dest, nota = self._tree_ord.item(sel[0], "values")
        # prellenar el form con los datos (como duplicado, queda pendiente por default)
        self._e_date.delete(0,"end"); self._e_date.insert(0, fecha)
        self._e_qty.delete(0,"end"); self._e_qty.insert(0, qty)
        self._e_dest.delete(0,"end"); self._e_dest.insert(0, dest)
        self._e_note.delete(0,"end"); self._e_note.insert(0, nota)
        self._approve_on_save.set(False)

    def _delete_selected_in_order(self):
        sel=self._tree_ord.selection()
        if not sel: return
        if not messagebox.askyesno("Eliminar", "¿Eliminar registros seleccionados?"): return
        rows=leer_shipments(); new=[]
        keys=set()
        for iid in sel:
            status, fecha, qty, dest, nota = self._tree_ord.item(iid,"values")
            keys.add((self._selected_order, fecha, str(qty), dest, nota, "1" if status=="Aprobada" else "0"))
        for r in rows:
            k=(r.get("orden",""), r.get("ship_date",""), str(r.get("qty","")), r.get("destino",""), r.get("nota",""), r.get("approved","0"))
            if k in keys: continue
            new.append(r)
        with open(SHIPMENTS_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved"])
            w.writeheader(); w.writerows(new)
        self._refresh_order_header(); self._reload_order_shipments(); self._reload_log(); self._reload_analytics()

    def _export_order_csv(self):
        if not self._selected_order: return
        try:
            path=filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")],
                                              initialfile=f"salidas_{self._selected_order}.csv")
        except: path=None
        if not path: return
        with open(path,"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["estado","fecha","qty","destino","nota"])
            for iid in self._tree_ord.get_children():
                w.writerow(self._tree_ord.item(iid,"values"))
        messagebox.showinfo("Exportar", f"Archivo guardado:\n{path}")

    # --- Edit dialog
    def _open_edit_dialog(self, orden, fecha, qty, dest, nota, is_approved):
        top=ctk.CTkToplevel(self); top.title(f"Editar salida — Orden {orden}")
        top.geometry("+{}+{}".format(self.winfo_rootx()+120, self.winfo_rooty()+120))
        top.grab_set()

        ctk.CTkLabel(top, text=f"Orden {orden}", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=14, pady=(12,6))
        frm=ctk.CTkFrame(top); frm.pack(fill="x", padx=14, pady=(0,10))
        e_date=ctk.CTkEntry(frm, width=170); e_date.insert(0, fecha); e_date.pack(side="left", padx=(0,6))
        ctk.CTkButton(frm, text="📅", width=36, command=lambda: self._calendar_pick(e_date)).pack(side="left", padx=(0,8))
        e_qty=ctk.CTkEntry(frm, width=120); e_qty.insert(0, str(qty)); e_qty.pack(side="left", padx=6)
        e_dest=ctk.CTkEntry(frm, width=220); e_dest.insert(0, dest); e_dest.pack(side="left", padx=6)
        e_note=ctk.CTkEntry(frm, width=260); e_note.insert(0, nota); e_note.pack(side="left", padx=6)
        var_approved = tk.BooleanVar(value=is_approved)
        ctk.CTkCheckBox(top, text="Aprobada", variable=var_approved).pack(anchor="w", padx=14, pady=(0,8))

        def save_edit():
            new_d = e_date.get().strip()
            new_q = parse_int_str(e_qty.get().strip(),0)
            new_dest = e_dest.get().strip()
            new_note = e_note.get().strip()
            new_appr = "1" if var_approved.get() else "0"
            if not (new_d and new_q>0):
                messagebox.showwarning("Editar","Fecha y cantidad (>0) obligatorias."); return

            # si se cambia a aprobada (o aumenta qty aprobada), validar asignado FIFO
            if new_appr=="1":
                plan=leer_csv_dict(PLANNING_CSV)
                orow=next((r for r in plan if (r.get("orden","") or "")==orden), None)
                fifo=compute_fifo_assignments(plan)
                asignado = order_metrics(orow, fifo)["asignado"]
                # considerar si antes ya estaba aprobada y la qty cambia
                prev_q_approved = parse_int_str(qty,0) if is_approved else 0
                delta = max(0, new_q - prev_q_approved)
                if delta > asignado:
                    messagebox.showwarning("Límite",
                        f"No puedes aprobar +{delta} pzs: asignado FIFO disponible = {asignado} pzs.")
                    return

            # aplicar cambios
            rows=leer_shipments(); done=False
            for r in rows:
                if (r.get("orden","")==orden and r.get("ship_date","")==fecha and str(r.get("qty",""))==str(qty)
                    and r.get("destino","")==dest and r.get("nota","")==nota and r.get("approved","0")==("1" if is_approved else "0")
                    and not done):
                    r["ship_date"]=new_d; r["qty"]=str(new_q); r["destino"]=new_dest; r["nota"]=new_note; r["approved"]=new_appr
                    done=True
            with open(SHIPMENTS_CSV,"w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved"])
                w.writeheader(); w.writerows(rows)
            top.destroy()
            self._refresh_order_header(); self._reload_order_shipments(); self._reload_log(); self._reload_analytics()

        btns=ctk.CTkFrame(top, fg_color="transparent"); btns.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkButton(btns, text="Guardar", command=save_edit).pack(side="left")
        ctk.CTkButton(btns, text="Cancelar", fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                      command=top.destroy).pack(side="left", padx=8)

    # ====== Global (log) ======
    def _clear_log_filters(self):
        self._log_filter_status.set("Todas")
        self._log_filter_text.set("")
        self._log_dt_from.set("")
        self._log_dt_to.set("")
        try: self._om_log_order.set("(todas)")
        except: pass
        self._reload_log()

    def _reload_log(self):
        for i in self._tree_log.get_children(): self._tree_log.delete(i)

        plan = leer_csv_dict(PLANNING_CSV)
        orden_a_molde = {(r.get("orden","") or "").strip(): (r.get("molde_id","") or "").strip() for r in plan}

        rows = self._shipments_all()

        # filtros de estado
        st=self._log_filter_status.get()
        if st=="Aprobadas":
            rows=[r for r in rows if str(r.get("approved","0")).strip()=="1"]
        elif st=="Pendientes":
            rows=[r for r in rows if str(r.get("approved","0")).strip()!="1"]

        # filtro orden
        try:
            ord_sel = self._om_log_order.get()
            if ord_sel and ord_sel!="(todas)":
                rows=[r for r in rows if (r.get("orden","") or "")==ord_sel]
        except:
            pass

        # filtro fechas
        dtf=(self._log_dt_from.get() or "").strip()
        dtt=(self._log_dt_to.get() or "").strip()
        def in_range(d):
            if not d: return True
            if dtf and d<dtf: return False
            if dtt and d>dtt: return False
            return True
        rows=[r for r in rows if in_range((r.get("ship_date","") or ""))]

        # filtro texto
        txt=(self._log_filter_text.get() or "").lower().strip()
        if txt:
            r2=[]
            for r in rows:
                blob=" ".join([(r.get("orden","") or ""), (r.get("destino","") or ""), (r.get("nota","") or "")]).lower()
                if txt in blob: r2.append(r)
            rows=r2

        try: rows.sort(key=lambda r: r.get("ship_date",""))
        except: pass

        total_qty=0
        for r in rows:
            try: total_qty += int(float(r.get("qty","0") or 0))
            except: pass
            orden=(r.get("orden","") or "").strip()
            self._tree_log.insert("", "end", values=(
                orden,
                orden_a_molde.get(orden, ""),
                self._status_label(r),
                r.get("ship_date",""),
                r.get("qty",""),
                r.get("destino",""),
                r.get("nota",""),
            ))
        self._lbl_totals_log.configure(text=f"Registros: {len(rows)}  •  Cantidad total: {total_qty:,} pzs")

    def _approve_selected_in_log(self):
        sel=self._tree_log.selection()
        if not sel: return
        # agrupar por orden para validar contra asignado FIFO
        approve_map = {}
        for iid in sel:
            orden, molde, status, fecha, qty, dest, nota = self._tree_log.item(iid,"values")
            if status=="Aprobada": continue
            approve_map.setdefault(orden, 0)
            try: approve_map[orden] += int(float(qty))
            except: pass

        if approve_map:
            plan=leer_csv_dict(PLANNING_CSV); fifo=compute_fifo_assignments(plan)
            for orden, qty_sum in approve_map.items():
                orow = next((r for r in plan if (r.get("orden","") or "")==orden), None)
                asignado = order_metrics(orow, fifo)["asignado"]
                if qty_sum > asignado:
                    messagebox.showwarning("Límite", f"Orden {orden}: no puedes aprobar {qty_sum} pzs; asignado FIFO = {asignado} pzs.")
                    return

        # aplicar aprobaciones
        rows=leer_shipments(); changed=False
        approve_keys=set()
        for iid in sel:
            orden, molde, status, fecha, qty, dest, nota = self._tree_log.item(iid,"values")
            if status=="Aprobada": continue
            approve_keys.add((orden, fecha, str(qty), dest, nota))
        for r in rows:
            k=((r.get("orden","") or ""), r.get("ship_date",""), str(r.get("qty","")), r.get("destino",""), r.get("nota",""))
            if k in approve_keys and r.get("approved","0")!="1":
                r["approved"]="1"; changed=True
        if changed:
            with open(SHIPMENTS_CSV,"w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved"])
                w.writeheader(); w.writerows(rows)
            self._refresh_order_header(); self._reload_order_shipments(); self._reload_log(); self._reload_analytics()

    def _delete_selected_in_log(self):
        sel=self._tree_log.selection()
        if not sel: return
        if not messagebox.askyesno("Eliminar","¿Eliminar registros seleccionados?"): return
        rows=leer_shipments(); new=[]
        delset=set()
        for iid in sel:
            orden, molde, status, fecha, qty, dest, nota = self._tree_log.item(iid,"values")
            delset.add((orden, fecha, str(qty), dest, nota, "1" if status=="Aprobada" else "0"))
        for r in rows:
            k=((r.get("orden","") or ""), r.get("ship_date",""), str(r.get("qty","")), r.get("destino",""), r.get("nota",""), r.get("approved","0"))
            if k in delset: continue
            new.append(r)
        with open(SHIPMENTS_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved"])
            w.writeheader(); w.writerows(new)
        self._refresh_order_header(); self._reload_order_shipments(); self._reload_log(); self._reload_analytics()

    def _export_log_csv(self):
        try:
            path=filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")], initialfile="bitacora_salidas_filtrada.csv")
        except: path=None
        if not path: return
        with open(path,"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["orden","molde","estado","fecha","qty","destino","nota"])
            for iid in self._tree_log.get_children():
                w.writerow(self._tree_log.item(iid,"values"))
        messagebox.showinfo("Exportar", f"Archivo guardado:\n{path}")

    # ====== Analytics ======
    def _reload_analytics(self):
        for i in self._tree_agg_ord.get_children(): self._tree_agg_ord.delete(i)
        for i in self._tree_agg_mold.get_children(): self._tree_agg_mold.delete(i)

        plan=leer_csv_dict(PLANNING_CSV)
        fifo=compute_fifo_assignments(plan)

        # por orden (aprobadas)
        for r in plan:
            orden=(r.get("orden","") or "").strip()
            parte=(r.get("parte","") or "").strip()
            molde=(r.get("molde_id","") or "").strip()
            m=order_metrics(r, fifo)
            objetivo=m["objetivo"]; enviado=m["enviado"]; pendiente=max(0, objetivo - enviado)
            avance = (enviado/objetivo*100.0) if objetivo>0 else 0.0
            self._tree_agg_ord.insert("", "end", values=(orden, parte, molde, objetivo, enviado, f"{avance:.1f}%", pendiente))

        # por molde
        molds=sorted({(r.get("molde_id","") or "").strip() for r in plan if r.get("molde_id")})
        for m_id in molds:
            mm=mold_metrics(m_id, fifo)
            self._tree_agg_mold.insert("", "end", values=(m_id, mm["bruto"], mm["enviado"], mm["neto"], mm["sobrante"]))
