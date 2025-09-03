from .base import *
from metrics import compute_fifo_assignments, order_metrics, mold_metrics, parse_int_str
from tkinter import simpledialog

class ShipmentsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=("#F8FAFC", "#0F172A"))
        self.app = app
        self._ship_filter_status = tk.StringVar(value="Todas")
        self._approve_on_save = tk.BooleanVar(value=False)
        self._selected_order = ""
        self._note_has_placeholder = True
        self._build_professional_ui()

    # ========== Helpers ==========
    def _shipments_all(self):
        try: return leer_csv_dict(config.SHIPMENTS_CSV)
        except Exception: return []

    def _status_label(self, r):
        return "Aprobada" if str(r.get("approved", "0")).strip() == "1" else "Pendiente"

    def _calendar_pick(self, entry: ctk.CTkEntry):
        try:
            y,m,d = map(int, (entry.get() or date.today().isoformat()).split("-"))
            init = date(y,m,d)
        except: init = date.today()
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
        try:
            self._om_order.set(orden)
            self._selected_order = orden
            self._reload_all()
        except: pass

    # ========== UI Profesional ==========
    def _build_professional_ui(self):
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#FFFFFF", "#1E2B3B"), height=70,
                              border_width=1, border_color=("#E2E8F0", "#334155"))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=24, pady=12)

        left_section = ctk.CTkFrame(header_content, fg_color="transparent")
        left_section.pack(side="left", fill="y")
        ctk.CTkButton(left_section, text="← Menú", command=self.app.go_menu,
                      width=100, height=36, corner_radius=10, fg_color="#E5E7EB",
                      text_color="#374151", hover_color="#D1D5DB",
                      font=ctk.CTkFont("Helvetica", 12, "bold")).pack(side="left")
        ctk.CTkLabel(left_section, text="🚚 Salidas y Embarques",
                     font=ctk.CTkFont("Helvetica", 24, "bold"),
                     text_color=("#1E293B", "#F1F5F9")).pack(side="left", padx=20)
        
        right_section = ctk.CTkFrame(header_content, fg_color="transparent")
        right_section.pack(side="right", fill="y")
        ctk.CTkButton(right_section, text="🔄 Actualizar Todo", command=self._reload_all,
                      width=140, height=40, corner_radius=12, fg_color="#3B82F6",
                      hover_color="#2563EB", font=ctk.CTkFont("Helvetica", 12, "bold")).pack(side="right")

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=24, pady=24)
        main_container.grid_columnconfigure(0, weight=1, minsize=380)
        main_container.grid_columnconfigure(1, weight=3)
        main_container.grid_rowconfigure(0, weight=1)

        self._build_sidebar_form(main_container)
        
        content_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        content_scroll.grid(row=0, column=1, sticky="nsew", padx=(24, 0))
        
        self._build_order_dashboard(content_scroll)
        
        self._reload_all()

    def _build_sidebar_form(self, parent):
        sidebar = ctk.CTkFrame(parent, width=380, corner_radius=16, fg_color=("#FFFFFF", "#1E293B"),
                               border_width=1, border_color=("#E2E8F0", "#334155"))
        sidebar.grid(row=0, column=0, sticky="nswe")
        sidebar.pack_propagate(False)
        
        scroll_area = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        scroll_area.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(scroll_area, text="➕ Registrar Nueva Salida", font=ctk.CTkFont("Helvetica", 18, "bold"),
                     text_color=("#3B82F6", "#93C5FD")).pack(anchor="w", padx=20, pady=(20, 10))
        
        ordenes = [r.get("orden", "") for r in leer_csv_dict(config.PLANNING_CSV)] or ["(Sin órdenes)"]
        self._om_order = ctk.CTkOptionMenu(scroll_area, values=ordenes, height=36,
                                           command=lambda v: self.set_order(v))
        self._om_order.pack(fill="x", padx=20, pady=5)
        
        self._e_date = ctk.CTkEntry(scroll_area, placeholder_text="Fecha (YYYY-MM-DD)", height=36)
        self._e_date.pack(fill="x", padx=20, pady=5)
        self._e_qty = ctk.CTkEntry(scroll_area, placeholder_text="Cantidad a enviar", height=36)
        self._e_qty.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(scroll_area, text="Destino (Cliente):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 0))
        self._om_dest = ctk.CTkOptionMenu(scroll_area, height=36, values=["(Sin clientes)"])
        self._om_dest.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(scroll_area, text="Quién Entrega:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 0))
        self._om_entrega = ctk.CTkOptionMenu(scroll_area, height=36, values=["(Sin personal)"])
        self._om_entrega.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(scroll_area, text="Quién Autoriza:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(10, 0))
        self._om_autoriza = ctk.CTkOptionMenu(scroll_area, height=36, values=["(Sin personal)"])
        self._om_autoriza.pack(fill="x", padx=20, pady=5)

        self._e_note = ctk.CTkTextbox(scroll_area, height=80, border_width=1, border_color=("#D1D5DB", "#4B5563"))
        self._e_note.pack(fill="both", expand=True, padx=20, pady=5)
        self._note_focus_out()
        self._e_note.bind("<FocusIn>", self._note_focus_in)
        self._e_note.bind("<FocusOut>", self._note_focus_out)
        
        ctk.CTkCheckBox(scroll_area, text="Aprobar al guardar", variable=self._approve_on_save).pack(anchor="w", padx=20, pady=10)
        
        ctk.CTkButton(scroll_area, text="Guardar Salida", height=40, command=self._save_shipment,
                      font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=20, pady=10)

        admin_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        admin_frame.pack(fill="x", padx=20, pady=(0, 20))
        admin_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(admin_frame, text="Personal", height=32,
                      fg_color="#6B7280", hover_color="#4B5563",
                      command=self._open_personnel_manager).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        ctk.CTkButton(admin_frame, text="Clientes", height=32,
                      fg_color="#6B7280", hover_color="#4B5563",
                      command=self._open_client_manager).grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
        self._e_date.insert(0, date.today().isoformat())
        if ordenes and ordenes[0] != "(Sin órdenes)":
            self._om_order.set(ordenes[0])
            self._selected_order = ordenes[0]
            
    def _build_order_dashboard(self, parent):
        self.order_dashboard = ctk.CTkFrame(parent, fg_color="transparent")
        self.order_dashboard.pack(fill="x")
        
        self.lbl_order_header = ctk.CTkLabel(self.order_dashboard, text="Seleccione una Orden",
                                             font=ctk.CTkFont("Helvetica", 20, "bold"))
        self.lbl_order_header.pack(anchor="w", pady=(0, 10))

        kpi_grid = ctk.CTkFrame(self.order_dashboard, fg_color="transparent")
        kpi_grid.pack(fill="x", pady=(0, 20))
        kpi_grid.grid_columnconfigure((0, 1, 2), weight=1)

        self.kpi_prog = self._create_kpi_card(kpi_grid, 0, "PROGRESO TOTAL", ("#3B82F6", "#93C5FD"))
        self.kpi_pend = self._create_kpi_card(kpi_grid, 1, "PENDIENTE POR SURTIR", ("#EF4444", "#F87171"))
        self.kpi_neto = self._create_kpi_card(kpi_grid, 2, "INVENTARIO NETO (MOLDE)", ("#10B981", "#6EE7B7"))
        
        table_frame = ctk.CTkFrame(self.order_dashboard, corner_radius=12, fg_color=("#FFFFFF", "#1E293B"),
                                   border_width=1, border_color=("#E2E8F0", "#334155"))
        table_frame.pack(fill="both", expand=True)
        
        controls_frame = ctk.CTkFrame(table_frame, fg_color="transparent")
        controls_frame.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(controls_frame, text="Salidas de esta orden:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkOptionMenu(controls_frame, variable=self._ship_filter_status, values=["Todas","Aprobadas","Pendientes"],
                          command=lambda v: self._reload_order_detail()).pack(side="left", padx=8)
        ctk.CTkButton(controls_frame, text="Aprobar Selección", command=self._approve_selected_in_order, height=32).pack(side="right", padx=4)
        ctk.CTkButton(controls_frame, text="Eliminar", command=self._delete_selected_in_order, height=32,
                      fg_color="#EF4444", hover_color="#DC2626").pack(side="right")

        cols=("status","fecha","qty","destino","entrega","autoriza","nota")
        self._tree_ord = ttk.Treeview(table_frame, columns=cols, show="headings", height=15)
        for k,t,w in [("status","Estado",100),("fecha","Fecha",100),("qty","Cantidad",80),
                      ("destino","Destino",150), ("entrega", "Entrega", 120), ("autoriza", "Autoriza", 120),
                      ("nota","Nota",200)]:
            self._tree_ord.heading(k, text=t); self._tree_ord.column(k, width=w, anchor="w")
        self._tree_ord.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _create_kpi_card(self, parent, col, title, colors):
        card = ctk.CTkFrame(parent, fg_color=("#FFFFFF", "#1E293B"), corner_radius=12,
                           border_width=1, border_color=("#E2E8F0", "#334155"))
        card.grid(row=0, column=col, sticky="nsew", padx=4)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color=colors).pack(pady=(12, 4))
        value_label = ctk.CTkLabel(card, text="—", font=ctk.CTkFont(size=24, weight="bold"))
        value_label.pack(pady=(0, 12))
        return value_label
        
    def _open_personnel_manager(self):
        top = ctk.CTkToplevel(self)
        top.title("Administrar Personal")
        top.geometry("400x350")
        top.transient(self); top.grab_set()

        ctk.CTkLabel(top, text="Agregar Nuevo Personal", font=ctk.CTkFont(weight="bold")).pack(pady=(10,5))
        
        entry_name = ctk.CTkEntry(top, placeholder_text="Nombre completo")
        entry_name.pack(fill="x", padx=20, pady=5)
        
        role_var = tk.StringVar(value="Entrega")
        ctk.CTkSegmentedButton(top, values=["Entrega", "Autoriza"], variable=role_var).pack(pady=5)
        
        def add_person():
            name = entry_name.get().strip()
            role = role_var.get()
            if not name:
                messagebox.showwarning("Dato requerido", "El nombre no puede estar vacío.", parent=top)
                return
            
            rows = leer_csv_dict(config.PERSONNEL_CSV)
            if any(r["nombre"].lower() == name.lower() for r in rows):
                messagebox.showwarning("Duplicado", f"El nombre '{name}' ya existe.", parent=top)
                return

            with open(config.PERSONNEL_CSV, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([name, role])
            
            entry_name.delete(0, "end")
            self._populate_personnel_dropdowns()
            messagebox.showinfo("Éxito", f"'{name}' agregado al rol de '{role}'.", parent=top)

        ctk.CTkButton(top, text="Agregar Persona", command=add_person).pack(pady=10)

        ctk.CTkFrame(top, height=1, fg_color="gray50").pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(top, text="El personal agregado aparecerá en los menús desplegables.",
                     wraplength=360, font=ctk.CTkFont(size=11)).pack(pady=5)
        ctk.CTkButton(top, text="Cerrar", command=top.destroy).pack(pady=10)

    def _open_client_manager(self):
        top = ctk.CTkToplevel(self)
        top.title("Administrar Clientes/Destinos")
        top.geometry("450x400")
        top.transient(self); top.grab_set()

        ctk.CTkLabel(top, text="Agregar Nuevo Cliente", font=ctk.CTkFont(weight="bold")).pack(pady=(10,5))
        
        entry_name = ctk.CTkEntry(top, placeholder_text="Nombre del Cliente/Empresa")
        entry_name.pack(fill="x", padx=20, pady=5)
        entry_addr = ctk.CTkEntry(top, placeholder_text="Dirección (opcional)")
        entry_addr.pack(fill="x", padx=20, pady=5)
        entry_contact = ctk.CTkEntry(top, placeholder_text="Contacto (opcional)")
        entry_contact.pack(fill="x", padx=20, pady=5)

        def add_client():
            name = entry_name.get().strip()
            addr = entry_addr.get().strip()
            contact = entry_contact.get().strip()
            if not name:
                messagebox.showwarning("Dato requerido", "El nombre del cliente no puede estar vacío.", parent=top)
                return
            
            rows = leer_csv_dict(config.CLIENTS_CSV)
            if any(r["nombre"].lower() == name.lower() for r in rows):
                messagebox.showwarning("Duplicado", f"El cliente '{name}' ya existe.", parent=top)
                return

            with open(config.CLIENTS_CSV, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([name, addr, contact])
            
            entry_name.delete(0, "end"); entry_addr.delete(0, "end"); entry_contact.delete(0, "end")
            self._populate_clients_dropdown()
            messagebox.showinfo("Éxito", f"Cliente '{name}' agregado.", parent=top)

        ctk.CTkButton(top, text="Agregar Cliente", command=add_client).pack(pady=10)
        ctk.CTkButton(top, text="Cerrar", command=top.destroy).pack(pady=10)

    def _note_focus_in(self, event=None):
        if self._note_has_placeholder:
            self._e_note.delete("1.0", "end")
            text_color = ctk.ThemeManager.theme["CTkTextbox"]["text_color"]
            self._e_note.configure(text_color=text_color)
            self._note_has_placeholder = False

    def _note_focus_out(self, event=None):
        if not self._e_note.get("1.0", "end-1c").strip():
            placeholder_color = ("gray50", "gray50")
            self._e_note.configure(text_color=placeholder_color)
            self._e_note.insert("1.0", "Notas adicionales...")
            self._note_has_placeholder = True

    def _reload_all(self):
        self._populate_personnel_dropdowns()
        self._populate_clients_dropdown()
        self._reload_orders_list()
        self._reload_order_detail()

    def _populate_personnel_dropdowns(self):
        personnel = leer_csv_dict(config.PERSONNEL_CSV)
        entrega_list = [""] + sorted([p["nombre"] for p in personnel if p.get("rol") == "Entrega"])
        autoriza_list = [""] + sorted([p["nombre"] for p in personnel if p.get("rol") == "Autoriza"])
        
        self._om_entrega.configure(values=entrega_list if len(entrega_list) > 1 else ["(Sin personal)"])
        self._om_autoriza.configure(values=autoriza_list if len(autoriza_list) > 1 else ["(Sin personal)"])
        self._om_entrega.set(entrega_list[0])
        self._om_autoriza.set(autoriza_list[0])

    def _populate_clients_dropdown(self):
        clients = leer_csv_dict(config.CLIENTS_CSV)
        client_names = [""] + sorted([c["nombre"] for c in clients])
        self._om_dest.configure(values=client_names if len(client_names) > 1 else ["(Sin clientes)"])
        self._om_dest.set(client_names[0])

    def _reload_orders_list(self):
        ordenes = [r.get("orden","") for r in leer_csv_dict(config.PLANNING_CSV)] or ["(Sin órdenes)"]
        self._om_order.configure(values=ordenes)
        if self._selected_order not in ordenes and ordenes[0] != "(Sin órdenes)":
            self._selected_order = ordenes[0]
        self._om_order.set(self._selected_order or ordenes[0])

    def _reload_order_detail(self):
        if not self._selected_order or self._selected_order == "(Sin órdenes)":
            self.lbl_order_header.configure(text="Seleccione una Orden para ver sus detalles")
            self.kpi_prog.configure(text="—")
            self.kpi_pend.configure(text="—")
            self.kpi_neto.configure(text="—")
            for i in self._tree_ord.get_children(): self._tree_ord.delete(i)
            return

        plan = leer_csv_dict(config.PLANNING_CSV)
        row = next((r for r in plan if (r.get("orden","") or "").strip() == self._selected_order), None)
        if not row: return

        molde = (row.get("molde_id","") or "").strip(); parte = (row.get("parte","") or "").strip()
        fifo = compute_fifo_assignments(plan); m = order_metrics(row, fifo); mm = mold_metrics(molde, fifo)
        
        self.lbl_order_header.configure(text=f"Orden {self._selected_order} — {parte}")
        self.kpi_prog.configure(text=f"{m['progreso']:,} / {m['objetivo']:,}")
        self.kpi_pend.configure(text=f"{m['pendiente']:,}")
        self.kpi_neto.configure(text=f"{mm['neto']:,}")

        for i in self._tree_ord.get_children(): self._tree_ord.delete(i)
        
        status_filter = self._ship_filter_status.get()
        order_shipments = [r for r in self._shipments_all() if r.get("orden") == self._selected_order]

        if status_filter == "Aprobadas":
            order_shipments = [r for r in order_shipments if str(r.get("approved","0")).strip()=="1"]
        elif status_filter == "Pendientes":
            order_shipments = [r for r in order_shipments if str(r.get("approved","0")).strip()!="1"]
        
        order_shipments.sort(key=lambda r: r.get("ship_date",""), reverse=True)
        
        for r in order_shipments:
            self._tree_ord.insert("", "end", values=(
                self._status_label(r), r.get("ship_date",""), r.get("qty",""),
                r.get("destino",""), r.get("entrega", ""), r.get("autoriza", ""), r.get("nota","")
            ))
                                                     
    def _save_shipment(self):
        o=self._om_order.get().strip()
        if not o or o=="(Sin órdenes)":
            messagebox.showwarning("Orden", "Debe seleccionar una orden válida."); return
        d=self._e_date.get().strip()
        try:
            qty_val = int(self._e_qty.get().strip())
            if qty_val <= 0: raise ValueError()
        except (ValueError, TypeError):
            messagebox.showwarning("Datos Inválidos", "La cantidad debe ser un número entero positivo."); return
        
        dest = self._om_dest.get()
        if dest == "(Sin clientes)": dest = ""
        nota = "" if self._note_has_placeholder else self._e_note.get("1.0", "end-1c").strip()
        entrega = self._om_entrega.get()
        if entrega == "(Sin personal)": entrega = ""
        autoriza = self._om_autoriza.get()
        if autoriza == "(Sin personal)": autoriza = ""

        plan=leer_csv_dict(config.PLANNING_CSV)
        orow=next((r for r in plan if r.get("orden") == o), None)
        if not orow:
            messagebox.showerror("Error", "La orden seleccionada ya no existe en la planificación."); return

        if self._approve_on_save.get():
            fifo = compute_fifo_assignments(plan)
            m = order_metrics(orow, fifo)
            disponible_para_enviar = m['progreso'] - m['enviado']
            if qty_val > disponible_para_enviar:
                messagebox.showwarning("Límite Excedido", f"No se puede aprobar esta cantidad.\n\nInventario disponible para esta orden: {disponible_para_enviar:,} pzs.\nCantidad solicitada: {qty_val:,} pzs.")
                return

        approved_flag = "1" if self._approve_on_save.get() else "0"
        with open(config.SHIPMENTS_CSV, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([o, d, str(qty_val), dest, nota, approved_flag, entrega, autoriza])
        
        self._e_qty.delete(0,"end"); self._e_note.delete("1.0", "end")
        self._note_focus_out()
        self._reload_all()
        messagebox.showinfo("Éxito", "Salida registrada correctamente.")

    def _approve_selected_in_order(self):
        sel=self._tree_ord.selection()
        if not sel: return
        
        plan=leer_csv_dict(config.PLANNING_CSV)
        fifo=compute_fifo_assignments(plan)
        orow=next((r for r in plan if r.get("orden") == self._selected_order), None)
        m = order_metrics(orow, fifo)
        disponible = m['progreso'] - m['enviado']

        qty_a_aprobar = 0; items_a_aprobar = []
        for iid in sel:
            status, fecha, qty_str, dest, entrega, autoriza, nota = self._tree_ord.item(iid, "values")
            if status == "Pendiente":
                qty_a_aprobar += parse_int_str(qty_str)
                items_a_aprobar.append((fecha, qty_str, dest, nota, entrega, autoriza))

        if qty_a_aprobar == 0: return

        if qty_a_aprobar > disponible:
            messagebox.showwarning("Límite Excedido", f"No se pueden aprobar las salidas seleccionadas.\n\nInventario disponible: {disponible:,} pzs.\nCantidad a aprobar: {qty_a_aprobar:,} pzs.")
            return

        rows=self._shipments_all(); changed=False
        for r in rows:
            if r.get("orden") == self._selected_order and r.get("approved","0") != "1":
                key = (r.get("ship_date",""), r.get("qty",""), r.get("destino",""), r.get("nota",""), r.get("entrega",""), r.get("autoriza",""))
                if key in items_a_aprobar:
                    r["approved"]="1"; changed=True

        if changed:
            with open(config.SHIPMENTS_CSV, "w", newline="", encoding="utf-8") as f:
                w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved", "entrega", "autoriza"])
                w.writeheader(); w.writerows(rows)
            self._reload_all()

    def _delete_selected_in_order(self):
        sel=self._tree_ord.selection()
        if not sel: return
        if not messagebox.askyesno("Confirmar", f"¿Eliminar {len(sel)} registro(s) de salida?"): return
        
        rows=self._shipments_all(); new_rows=[]
        keys_to_delete = set()
        for iid in sel:
            status, fecha, qty, dest, entrega, autoriza, nota = self._tree_ord.item(iid, "values")
            approved = "1" if status == "Aprobada" else "0"
            keys_to_delete.add((self._selected_order, fecha, str(qty), dest, nota, approved, entrega, autoriza))
        
        for r in rows:
            key=(r.get("orden",""), r.get("ship_date",""), str(r.get("qty","")), r.get("destino",""), r.get("nota",""), r.get("approved","0"), r.get("entrega",""), r.get("autoriza",""))
            if key not in keys_to_delete:
                new_rows.append(r)
        
        with open(config.SHIPMENTS_CSV, "w", newline="", encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved", "entrega", "autoriza"])
            w.writeheader(); w.writerows(new_rows)
        self._reload_all()
