from .base import *
from metrics import compute_fifo_assignments, order_metrics, mold_metrics, totals_from_fifo

class InventoryView(ctk.CTkFrame):
    """
    Inventario con UI mejorada:
    - KPIs globales
    - Tabla de órdenes (FIFO)
    - Panel de detalle por orden (barras + salidas por orden)
    - Bitácora global de salidas con filtros y acciones
    """
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._selected_order = ""
        self._ship_filter_status = tk.StringVar(value="Todas")      # filtro por orden (detalle)
        self._log_filter_status = tk.StringVar(value="Todas")        # filtro bitácora global
        self._log_filter_text   = tk.StringVar(value="")             # búsqueda bitácora
        self._show_cards = tk.BooleanVar(value=True)                 # mostrar/ocultar flashcards
        self._build()

    # ---------------------------
    # Helpers (shipments / filters)
    # ---------------------------
    def _shipments_all(self):
        try:
            return leer_shipments()
        except Exception:
            return []

    def _shipments_approved(self):
        return [r for r in self._shipments_all() if str(r.get("approved","0")).strip() == "1"]

    def _shipments_pending(self):
        return [r for r in self._shipments_all() if str(r.get("approved","0")).strip() != "1"]

    def _status_label(self, r):
        return "Aprobada" if str(r.get("approved","0")).strip() == "1" else "Pendiente"

    def _sum_qty(self, rows):
        s = 0
        for r in rows:
            try: s += int(float(r.get("qty",0) or 0))
            except: pass
        return s

    # ----------- UI -----------
    def _build(self):
        # Header
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#111111"))
        header.pack(fill="x", side="top")
        left = ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", command=self.app.go_menu, width=110, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text="Inventario", font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")
        right = ctk.CTkFrame(header, fg_color="transparent"); right.pack(side="right", padx=16, pady=10)
        ctk.CTkSwitch(right, text="Ver tarjetas pendientes", variable=self._show_cards,
                      command=self._toggle_cards).pack(side="left", padx=(0,10))
        ctk.CTkButton(right, text="↻ Actualizar", command=self._reload_all).pack(side="right")

        # Body grid
        body = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=16)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(3, weight=1)

        # --- KPI cards (fila 0) ---
        self.kpi_row = ctk.CTkFrame(body, fg_color="transparent")
        self.kpi_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,12))
        self._kpi_cards = []
        for _ in range(5):
            card = ctk.CTkFrame(self.kpi_row, corner_radius=16)
            card.pack(side="left", expand=True, fill="x", padx=6)
            title = ctk.CTkLabel(card, text="—", font=ctk.CTkFont("Helvetica", 12))
            title.pack(anchor="w", padx=12, pady=(8,0))
            value = ctk.CTkLabel(card, text="—", font=ctk.CTkFont("Helvetica", 20, "bold"))
            value.pack(anchor="w", padx=12, pady=(0,10))
            self._kpi_cards.append((title, value))

        # --- Flashcards de pendientes (fila 1) ---
        self.pending_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.pending_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,12))

        # --- Tabla de órdenes (fila 2, col 0) ---
        orders_card = ctk.CTkFrame(body, corner_radius=18)
        orders_card.grid(row=2, column=0, sticky="nsew", padx=(0,8))
        ctk.CTkLabel(orders_card, text="Inventario por Orden (FIFO)",
                     font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(orders_card, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))
        cols=("orden","parte","molde","objetivo","enviado","asignado","progreso","pendiente")
        self.tree_orders=ttk.Treeview(orders_card, columns=cols, show="headings", height=12)
        headers=[("orden","Orden",90),("parte","Parte",150),("molde","Molde",80),
                 ("objetivo","Obj.",90),("enviado","Enviado ✔",110),
                 ("asignado","Asignado FIFO",120),("progreso","Progreso",110),("pendiente","Pendiente",110)]
        for k,t,w in headers:
            self.tree_orders.heading(k, text=t); self.tree_orders.column(k, width=w, anchor="center")
        self.tree_orders.pack(fill="both", expand=True, padx=12, pady=(0,10))
        self.tree_orders.bind("<<TreeviewSelect>>", lambda e: self._on_order_select())

        self.lbl_totals_orders = ctk.CTkLabel(orders_card, text="—", text_color=("#6b7280","#9CA3AF"))
        self.lbl_totals_orders.pack(anchor="w", padx=12, pady=(0,10))

        # --- Detalle de orden (fila 2, col 1) ---
        detail = ctk.CTkFrame(body, corner_radius=18)
        detail.grid(row=2, column=1, sticky="nsew", padx=(8,0))
        ctk.CTkLabel(detail, text="Detalle de Orden", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(detail, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))

        # Info / barras
        self.lbl_order_header = ctk.CTkLabel(detail, text="—", font=ctk.CTkFont("Helvetica", 13))
        self.lbl_order_header.pack(anchor="w", padx=12)
        self.prog_bar = ctk.CTkProgressBar(detail); self.prog_bar.set(0.0); self.prog_bar.pack(fill="x", padx=12)
        self.lbl_prog = ctk.CTkLabel(detail, text="—", text_color=("#6b7280","#9CA3AF"))
        self.lbl_prog.pack(anchor="w", padx=12, pady=(2,6))

        self.lbl_mold = ctk.CTkLabel(detail, text="—", text_color=("#6b7280","#9CA3AF"))
        self.lbl_mold.pack(anchor="w", padx=12, pady=(0,8))

        # Filtros de salidas por orden
        filt = ctk.CTkFrame(detail, fg_color="transparent"); filt.pack(fill="x", padx=12, pady=(0,4))
        ctk.CTkLabel(filt, text="Salidas de esta orden:").pack(side="left")
        ctk.CTkOptionMenu(filt, variable=self._ship_filter_status, values=["Todas","Aprobadas","Pendientes"],
                          command=lambda _v: self._reload_shipments_for_order()).pack(side="left", padx=8)

        cols2=("status","fecha","qty","destino","nota")
        self.tree_ship=ttk.Treeview(detail, columns=cols2, show="headings", height=8)
        for k,t,w in [("status","Estado",90),("fecha","Fecha",110),("qty","Qty",80),("destino","Destino",160),("nota","Nota",240)]:
            self.tree_ship.heading(k, text=t); self.tree_ship.column(k, width=w, anchor="center" if k not in ("destino","nota") else "w")
        self.tree_ship.pack(fill="both", expand=True, padx=12, pady=(0,8))

        # Acciones sobre salidas de la orden
        rowbtn = ctk.CTkFrame(detail, fg_color="transparent"); rowbtn.pack(fill="x", padx=12, pady=(0,10))
        ctk.CTkButton(rowbtn, text="Aprobar selección", command=self._approve_selected_in_order).pack(side="left")
        ctk.CTkButton(rowbtn, text="Eliminar selección", fg_color="#ef4444", hover_color="#dc2626",
                      command=self._delete_selected_in_order).pack(side="left", padx=8)
        ctk.CTkButton(rowbtn, text="Registrar salida", command=self._open_shipments).pack(side="right")

        # --- Bitácora global de salidas (fila 3, 2 cols) ---
        logcard = ctk.CTkFrame(body, corner_radius=18)
        logcard.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(12,0))
        ctk.CTkLabel(logcard, text="Bitácora Global de Salidas", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(logcard, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))

        lf = ctk.CTkFrame(logcard, fg_color="transparent"); lf.pack(fill="x", padx=12, pady=(0,8))
        ctk.CTkOptionMenu(lf, variable=self._log_filter_status, values=["Todas","Aprobadas","Pendientes"],
                          command=lambda _v: self._reload_log()).pack(side="left")
        ctk.CTkEntry(lf, textvariable=self._log_filter_text, placeholder_text="Buscar orden / destino / nota...",
                     width=280).pack(side="left", padx=8)
        ctk.CTkButton(lf, text="Filtrar", command=self._reload_log).pack(side="left", padx=6)
        ctk.CTkButton(lf, text="Aprobar selección", command=self._approve_selected_in_log).pack(side="left", padx=6)
        ctk.CTkButton(lf, text="Exportar CSV", command=self._export_log_csv).pack(side="left", padx=6)

        cols3=("orden","molde","status","fecha","qty","destino","nota")
        self.tree_log=ttk.Treeview(logcard, columns=cols3, show="headings", height=10)
        for k,t,w in [("orden","Orden",90),("molde","Molde",80),("status","Estado",90),("fecha","Fecha",110),
                      ("qty","Qty",80),("destino","Destino",220),("nota","Nota",320)]:
            self.tree_log.heading(k, text=t); self.tree_log.column(k, width=w, anchor="center" if k in ("orden","molde","status","fecha","qty") else "w")
        self.tree_log.pack(fill="both", expand=True, padx=12, pady=(0,10))

        self.lbl_totals_log = ctk.CTkLabel(logcard, text="—", text_color=("#6b7280","#9CA3AF"))
        self.lbl_totals_log.pack(anchor="w", padx=12, pady=(0,12))

        # Inicializar datos
        self._reload_all()

    # ------------
    # Navegación UI
    # ------------
    def _open_shipments(self):
        sel = self.tree_orders.selection()
        pre = ""
        if sel:
            pre = self.tree_orders.item(sel[0], "values")[0]
        try:
            self.app.go_shipments(pre or "")
        except:
            self.app.go_shipments("")

    def _on_order_select(self):
        sel = self.tree_orders.selection()
        if not sel:
            self._selected_order = ""
            self._clear_order_detail()
            return
        self._selected_order = self.tree_orders.item(sel[0], "values")[0]
        self._reload_order_detail()

    def _toggle_cards(self):
        if self._show_cards.get():
            self.pending_frame.grid()
        else:
            self.pending_frame.grid_remove()

    # ----------------
    # Recargas de data
    # ----------------
    def _reload_all(self):
        self._reload_kpis()
        self._reload_orders_table()
        self._reload_pending_cards()
        self._reload_order_detail()
        self._reload_log()

    # --- KPIs
    def _reload_kpis(self):
        orders = leer_csv_dict(PLANNING_CSV)
        fifo = compute_fifo_assignments(orders)
        t = totals_from_fifo(fifo)

        total_orders = len(orders)
        pend = self._shipments_pending()
        pend_qty = self._sum_qty(pend)
        appr_qty = self._sum_qty(self._shipments_approved())

        labels = [
            ("Stock neto global", f"{t['neto']:,} pzs"),
            ("Sobrante sin asignar", f"{t['sobrante']:,} pzs"),
            ("Salidas aprobadas", f"{appr_qty:,} pzs"),
            ("Pendientes por aprobar", f"{pend_qty:,} pzs"),
            ("Órdenes activas", f"{total_orders:,}")
        ]
        for (title, value), (lt, lv) in zip(labels, self._kpi_cards):
            lt.configure(text=title); lv.configure(text=value)

    # --- Órdenes (tabla FIFO)
    def _reload_orders_table(self):
        for i in self.tree_orders.get_children():
            self.tree_orders.delete(i)

        orders = leer_csv_dict(PLANNING_CSV)
        fifo = compute_fifo_assignments(orders)

        tot_obj = tot_env = tot_asig = tot_prog = tot_pend = 0
        for r in orders:
            orden = (r.get("orden", "") or "").strip()
            parte = (r.get("parte", "") or "").strip()
            molde = (r.get("molde_id", "") or "").strip()

            m = order_metrics(r, fifo)
            self.tree_orders.insert("", "end", values=(
                orden, parte, molde, m["objetivo"], m["enviado"], m["asignado"], m["progreso"], m["pendiente"]
            ))

            tot_obj += m["objetivo"]; tot_env += m["enviado"]; tot_asig += m["asignado"]
            tot_prog += m["progreso"]; tot_pend += m["pendiente"]

        self.lbl_totals_orders.configure(
            text=(f"Órdenes: {len(orders)}  •  Obj: {tot_obj:,}  •  Enviado✔: {tot_env:,}  •  "
                  f"Asignado FIFO: {tot_asig:,}  •  Progreso: {tot_prog:,}  •  Pendiente: {tot_pend:,}")
        )

    # --- Detalle de Orden (barras + salidas)
    def _clear_order_detail(self):
        self.lbl_order_header.configure(text="—")
        self.prog_bar.set(0.0)
        self.lbl_prog.configure(text="—")
        self.lbl_mold.configure(text="—")
        for i in self.tree_ship.get_children(): self.tree_ship.delete(i)

    def _reload_order_detail(self):
        if not self._selected_order:
            self._clear_order_detail()
            return

        orders = leer_csv_dict(PLANNING_CSV)
        row = next((r for r in orders if (r.get("orden","") or "").strip() == self._selected_order), None)
        if not row:
            self._clear_order_detail()
            return

        molde = (row.get("molde_id","") or "").strip()
        parte = (row.get("parte","") or "").strip()
        fifo = compute_fifo_assignments(orders)
        m = order_metrics(row, fifo)
        mm = mold_metrics(molde, fifo)

        # Header / barras
        objetivo = m["objetivo"]; enviado = m["enviado"]; asignado = m["asignado"]
        progreso = m["progreso"]; pendiente = m["pendiente"]
        frac = (progreso/objetivo) if objetivo>0 else 0.0

        self.lbl_order_header.configure(text=f"Orden {self._selected_order} — {parte}  •  Obj {objetivo:,}")
        self.prog_bar.set(frac)
        self.lbl_prog.configure(text=f"Progreso: {progreso:,}  (= Enviado {enviado:,} + Asignado {asignado:,})  •  Pendiente: {pendiente:,}")
        self.lbl_mold.configure(text=f"Molde {molde}  •  Neto molde: {mm['neto']:,}  •  Sobrante sin asignar: {mm['sobrante']:,}")

        # Tabla de salidas (filtrada)
        self._reload_shipments_for_order()

    def _get_order_shipments_filtered(self, orden):
        status = self._ship_filter_status.get()
        rows = [r for r in self._shipments_all() if (r.get("orden","") or "").strip() == (orden or "")]
        if status == "Aprobadas":
            rows = [r for r in rows if str(r.get("approved","0")).strip() == "1"]
        elif status == "Pendientes":
            rows = [r for r in rows if str(r.get("approved","0")).strip() != "1"]
        return rows

    def _reload_shipments_for_order(self):
        for i in self.tree_ship.get_children():
            self.tree_ship.delete(i)

        if not self._selected_order: return
        rows = self._get_order_shipments_filtered(self._selected_order)
        # ordenar por fecha asc si posible
        try:
            rows.sort(key=lambda r: r.get("ship_date",""))
        except:
            pass

        for r in rows:
            self.tree_ship.insert("", "end", values=(
                self._status_label(r),
                r.get("ship_date",""),
                r.get("qty",""),
                r.get("destino",""),
                r.get("nota",""),
            ))

    def _approve_selected_in_order(self):
        sel = self.tree_ship.selection()
        if not sel: return
        rows = leer_shipments()
        changed=False

        selected_rows = []
        for iid in sel:
            status, fecha, qty, dest, nota = self.tree_ship.item(iid,"values")
            if status == "Aprobada":  # ya aprobada
                continue
            selected_rows.append((fecha, str(qty), dest, nota))

        for r in rows:
            if (r.get("orden","") or "").strip() == self._selected_order and r.get("approved","0") != "1":
                key = (r.get("ship_date",""), str(r.get("qty","")), r.get("destino",""), r.get("nota",""))
                if key in selected_rows:
                    r["approved"] = "1"; changed=True

        if changed:
            with open(SHIPMENTS_CSV,"w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved"])
                w.writeheader(); w.writerows(rows)
            self._reload_all()

    def _delete_selected_in_order(self):
        sel = self.tree_ship.selection()
        if not sel: return
        # elimina cualquier estado (aprob/pte) de la orden seleccionada
        rows = leer_shipments()
        new = []
        delete_set = set()
        for iid in sel:
            status, fecha, qty, dest, nota = self.tree_ship.item(iid,"values")
            delete_set.add((self._selected_order, fecha, str(qty), dest, nota, "1" if status=="Aprobada" else "0"))

        for r in rows:
            key = (r.get("orden",""), r.get("ship_date",""), str(r.get("qty","")), r.get("destino",""), r.get("nota",""), r.get("approved","0"))
            if key in delete_set:
                continue
            new.append(r)

        with open(SHIPMENTS_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved"])
            w.writeheader(); w.writerows(new)
        self._reload_all()

    # --- Flashcards de pendientes
    def _reload_pending_cards(self):
        for w in self.pending_frame.winfo_children():
            w.destroy()

        pending = self._shipments_pending()
        if not pending:
            if self._show_cards.get():
                ctk.CTkLabel(self.pending_frame, text="No hay salidas pendientes.",
                             text_color=("#6b7280","#9CA3AF")).pack(anchor="w", padx=12, pady=6)
            return

        # Mapeo orden->molde
        orden_a_molde = {
            (r.get("orden","") or "").strip(): (r.get("molde_id","") or "").strip()
            for r in leer_csv_dict(PLANNING_CSV)
        }

        title = ctk.CTkLabel(self.pending_frame, text="Salidas pendientes de aprobación",
                             font=ctk.CTkFont("Helvetica", 13, "bold"))
        title.pack(anchor="w", padx=4, pady=(0,6))

        for r in pending:
            orden = (r.get("orden","") or "").strip()
            molde = orden_a_molde.get(orden, "")
            qty = r.get("qty", "0"); destino = (r.get("destino","") or "").strip()
            nota = (r.get("nota","") or "").strip(); fecha = (r.get("ship_date","") or "").strip()

            card = ctk.CTkFrame(self.pending_frame, corner_radius=12)
            card.pack(fill="x", pady=6)
            left = ctk.CTkFrame(card, fg_color="transparent"); left.pack(side="left", padx=10, pady=8)
            right = ctk.CTkFrame(card, fg_color="transparent"); right.pack(side="right", padx=10, pady=8)

            head = f"Orden {orden} • Molde {molde} • {qty} pzs"
            sub  = f"Fecha: {fecha or '—'}  •  Destino: {destino or '—'}"
            if nota: sub += f"  •  Nota: {nota}"

            ctk.CTkLabel(left, text=head, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(left, text=sub, text_color=("#6b7280","#9CA3AF")).pack(anchor="w", pady=(2,0))
            ctk.CTkButton(right, text="Aprobar", width=110,
                          command=lambda row=r: self._approve_shipment_row(row)).pack(side="right")

    def _approve_shipment_row(self, row):
        rows = leer_shipments()
        for r in rows:
            if (
                (r.get("orden","") or "") == (row.get("orden","") or "")
                and (r.get("ship_date","") or "") == (row.get("ship_date","") or "")
                and str(r.get("qty","") or "") == str(row.get("qty","") or "")
                and (r.get("destino","") or "") == (row.get("destino","") or "")
                and (r.get("nota","") or "") == (row.get("nota","") or "")
                and str(r.get("approved","0") or "0") != "1"
            ):
                r["approved"] = "1"
                break

        with open(SHIPMENTS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["orden", "ship_date", "qty", "destino", "nota", "approved"])
            w.writeheader(); w.writerows(rows)

        self._reload_all()

    # --- Bitácora global
    def _reload_log(self):
        for i in self.tree_log.get_children(): self.tree_log.delete(i)

        status = self._log_filter_status.get()
        text = (self._log_filter_text.get() or "").lower().strip()

        plan = leer_csv_dict(PLANNING_CSV)
        orden_a_molde = {(r.get("orden","") or "").strip(): (r.get("molde_id","") or "").strip() for r in plan}

        rows = self._shipments_all()
        # status
        if status == "Aprobadas":
            rows = [r for r in rows if str(r.get("approved","0")).strip() == "1"]
        elif status == "Pendientes":
            rows = [r for r in rows if str(r.get("approved","0")).strip() != "1"]
        # búsqueda
        if text:
            rows2 = []
            for r in rows:
                blob = " ".join([
                    (r.get("orden","") or ""), (r.get("destino","") or ""), (r.get("nota","") or "")
                ]).lower()
                if text in blob:
                    rows2.append(r)
            rows = rows2

        # ordenar por fecha
        try:
            rows.sort(key=lambda r: r.get("ship_date",""))
        except:
            pass

        total_qty = 0
        for r in rows:
            status_lbl = self._status_label(r)
            qty = r.get("qty","0")
            try: total_qty += int(float(qty))
            except: pass
            orden = (r.get("orden","") or "").strip()
            molde = orden_a_molde.get(orden, "")
            self.tree_log.insert("", "end", values=(
                orden, molde, status_lbl, r.get("ship_date",""), qty, r.get("destino",""), r.get("nota","")
            ))

        self.lbl_totals_log.configure(
            text=f"Registros: {len(rows)}  •  Cantidad total: {total_qty:,} pzs"
        )

    def _approve_selected_in_log(self):
        sel = self.tree_log.selection()
        if not sel: return
        rows = leer_shipments()
        changed=False
        approve_set = set()
        for iid in sel:
            orden, molde, status, fecha, qty, dest, nota = self.tree_log.item(iid,"values")
            if status == "Aprobada":  # ya aprobada
                continue
            approve_set.add((orden, fecha, str(qty), dest, nota))

        for r in rows:
            key = ((r.get("orden","") or ""), r.get("ship_date",""), str(r.get("qty","")), r.get("destino",""), r.get("nota",""))
            if key in approve_set and r.get("approved","0") != "1":
                r["approved"] = "1"; changed=True

        if changed:
            with open(SHIPMENTS_CSV,"w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved"])
                w.writeheader(); w.writerows(rows)
            self._reload_all()

    def _export_log_csv(self):
        # exporta lo que está visible en la tabla de bitácora a un CSV
        try:
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")], initialfile="bitacora_salidas.csv")
        except:
            path = None
        if not path: return
        # recolectar filas visibles
        data = []
        for iid in self.tree_log.get_children():
            data.append(self.tree_log.item(iid,"values"))
        # escribir
        with open(path,"w",newline="",encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["orden","molde","estado","fecha","qty","destino","nota"])
            w.writerows(data)
        messagebox.showinfo("Exportar", f"Archivo guardado:\n{path}")
