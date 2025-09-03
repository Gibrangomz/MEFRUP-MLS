from .base import *

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
        if getattr(self.app, 'dashboard_page', None):
            try:
                self.app.dashboard_page._refresh_now()
            except Exception:
                logging.exception("Error al actualizar tablero en vivo")

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
        if getattr(self.app, 'dashboard_page', None):
            try:
                self.app.dashboard_page._refresh_now()
            except Exception:
                logging.exception("Error al actualizar tablero en vivo")

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
        if getattr(self.app, 'dashboard_page', None):
            try:
                self.app.dashboard_page._refresh_now()
            except Exception:
                logging.exception("Error al actualizar tablero en vivo")
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
from .base import *

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
        if getattr(self.app, 'dashboard_page', None):
            try:
                self.app.dashboard_page._refresh_now()
            except Exception:
                logging.exception("Error al actualizar tablero en vivo")

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
        if getattr(self.app, 'dashboard_page', None):
            try:
                self.app.dashboard_page._refresh_now()
            except Exception:
                logging.exception("Error al actualizar tablero en vivo")

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
        if getattr(self.app, 'dashboard_page', None):
            try:
                self.app.dashboard_page._refresh_now()
            except Exception:
                logging.exception("Error al actualizar tablero en vivo")
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
        
        # Se busca la orden para asegurar que existe, pero ya no se usa para restringir la cantidad.
        orden_row = next((r for r in leer_csv_dict(PLANNING_CSV) if r.get("orden")==orden), None)
        if not orden_row:
            messagebox.showwarning("Orden","No se encontró la orden."); return

        # << ======================= CAMBIO REALIZADO AQUÍ ======================= >>
        # Se ha eliminado la restricción que impedía programar hitos si la suma
        # de sus cantidades excedía el total de la orden. Esto permite planificar
        # todas las entregas desde el inicio.
        
        # CÓDIGO ANTERIOR (COMENTADO):
        # qty_total = parse_int_str(orden_row.get("qty_total","0"))
        # miles=[r for r in leer_csv_dict(DELIV_CSV) if r.get("orden")==orden]
        # ya_prog = sum(parse_int_str(r.get("qty","0")) for r in miles)
        # if qty + ya_prog > qty_total:
        #     messagebox.showwarning("Restricción",
        #         f"No puedes programar {qty} pzs. Ya hay {ya_prog} pzs en milestones y la orden es de {qty_total} pzs.")
        #     return
        # << ======================= FIN DEL CAMBIO ======================= >>
        
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
