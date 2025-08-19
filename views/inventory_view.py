from .base import *

class InventoryView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#111111"))
        header.pack(fill="x", side="top")
        left = ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", command=self.app.go_menu, width=110, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text="Inventario", font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")
        right = ctk.CTkFrame(header, fg_color="transparent"); right.pack(side="right", padx=16, pady=10)
        ctk.CTkButton(right, text="↻ Actualizar", command=self._reload_table).pack(side="right")

        body = ctk.CTkFrame(self, corner_radius=18)
        body.pack(fill="both", expand=True, padx=16, pady=16)

        # flashcards de salidas pendientes
        self.pending_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.pending_frame.pack(fill="x", padx=12, pady=(10,6))

        ctk.CTkLabel(body, text="Inventario por Orden", font=ctk.CTkFont("Helvetica", 14, "bold"))\
            .pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(body, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))
        cols=("orden","parte","molde","producidas","env_ord","env_molde","disp")
        self.tree=ttk.Treeview(body, columns=cols, show="headings", height=12)
        headers=[
            ("orden","Orden",90),
            ("parte","Parte",150),
            ("molde","Molde",80),
            ("producidas","Producidas",110),
            ("env_ord","Env. ord",90),
            ("env_molde","Env. molde",110),
            ("disp","Disp.",90)
        ]
        for k,t,w in headers:
            self.tree.heading(k, text=t); self.tree.column(k, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0,12))

        self.lbl_totals = ctk.CTkLabel(body, text="—", text_color=("#6b7280","#9CA3AF"))
        self.lbl_totals.pack(anchor="w", padx=12, pady=(0,10))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(0,16))
        ctk.CTkButton(btns, text="Registrar salida", command=self._open_shipments).pack(side="left")
        ctk.CTkButton(btns, text="↻ Actualizar", command=self._reload_table).pack(side="right")

        self._reload_table()

    def _open_shipments(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Orden", "Selecciona una orden.")
            return
        order = self.tree.item(sel[0], "values")[0]
        self.app.go_shipments(order)

    def _reload_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        orders = leer_csv_dict(PLANNING_CSV)
        ordenes_total = len(orders)
        moldes_unicos = {r.get("molde_id", "") for r in orders}
        prod_total = sum(producido_por_molde_global(m) for m in moldes_unicos)

        for r in orders:
            orden = r.get("orden", "")
            parte = r.get("parte", "")
            molde = r.get("molde_id", "")
            prod = producido_por_molde_global(molde)
            shipped_ord = enviados_por_orden(orden)
            shipped_total = enviados_por_molde(molde)
            disp = max(0, prod - shipped_total)
            self.tree.insert("", "end", values=(orden, parte, molde, prod, shipped_ord, shipped_total, disp))

        self.lbl_totals.configure(text=f"Órdenes: {ordenes_total} • Producidas: {prod_total}")
        self._reload_pending_cards()

    def _reload_pending_cards(self):
        for w in self.pending_frame.winfo_children():
            w.destroy()
        pending = [r for r in leer_shipments() if r.get("approved", "0") != "1"]
        if not pending:
            return
        orden_a_molde = {
            r.get("orden", "").strip(): r.get("molde_id", "").strip()
            for r in leer_csv_dict(PLANNING_CSV)
        }
        for r in pending:
            molde = orden_a_molde.get(r.get("orden", ""), "")
            card = ctk.CTkFrame(self.pending_frame, corner_radius=12)
            card.pack(fill="x", pady=4)
            txt = f"Salida: {r.get('qty')} pzs • Molde {molde}"
            ctk.CTkLabel(card, text=txt).pack(side="left", padx=8, pady=8)
            ctk.CTkButton(card, text="Aprobar", width=80,
                          command=lambda row=r: self._approve_shipment(row)).pack(side="right", padx=8, pady=8)

    def _approve_shipment(self, row):
        rows = leer_shipments()
        for r in rows:
            if (
                r.get("orden") == row.get("orden")
                and r.get("ship_date") == row.get("ship_date")
                and r.get("qty") == row.get("qty")
                and r.get("destino", "") == row.get("destino", "")
                and r.get("nota", "") == row.get("nota", "")
                and r.get("approved", "0") != "1"
            ):
                r["approved"] = "1"
                break
        with open(SHIPMENTS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["orden", "ship_date", "qty", "destino", "nota", "approved"])
            w.writeheader(); w.writerows(rows)
        self._reload_table()


# ================================
# === Salida de Piezas (Embarques)
# ================================
