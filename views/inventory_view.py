from .base import *

class InventoryView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()

    # ---------------------------
    # Helpers (aprobadas / totales)
    # ---------------------------
    def _shipments_all(self):
        try:
            return leer_shipments()
        except Exception:
            return []

    def _shipments_approved(self):
        return [r for r in self._shipments_all() if str(r.get("approved","0")).strip() == "1"]

    def _sum_shipped_by_order(self, orden: str) -> int:
        orden = (orden or "").strip()
        total = 0
        for r in self._shipments_approved():
            if (r.get("orden","") or "").strip() == orden:
                try: total += int(float(r.get("qty",0) or 0))
                except ValueError: pass
        return total

    def _sum_shipped_by_mold(self, molde_id: str) -> int:
        molde_id = (molde_id or "").strip()
        orden_a_molde = {
            (r.get("orden","") or "").strip(): (r.get("molde_id","") or "").strip()
            for r in leer_csv_dict(PLANNING_CSV)
        }
        total = 0
        for r in self._shipments_approved():
            ord_ = (r.get("orden","") or "").strip()
            if orden_a_molde.get(ord_, "") == molde_id:
                try: total += int(float(r.get("qty",0) or 0))
                except ValueError: pass
        return total

    def _sum_shipped_total_approved(self) -> int:
        total = 0
        for r in self._shipments_approved():
            try: total += int(float(r.get("qty",0) or 0))
            except ValueError: pass
        return total

    # ----------- UI -----------
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

        self.pending_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.pending_frame.pack(fill="x", padx=12, pady=(10,6))

        ctk.CTkLabel(body, text="Inventario por Orden", font=ctk.CTkFont("Helvetica", 14, "bold"))\
            .pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(body, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))

        cols=("orden","parte","molde","objetivo","enviado","asignado","progreso","pendiente")
        self.tree=ttk.Treeview(body, columns=cols, show="headings", height=12)
        headers=[
            ("orden","Orden",90),
            ("parte","Parte",150),
            ("molde","Molde",80),
            ("objetivo","Objetivo",90),
            ("enviado","Enviado",90),
            ("asignado","Asignado",100),
            ("progreso","Progreso",100),
            ("pendiente","Pendiente",100)
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

    # ----------- Carga tabla -----------
    def _reload_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        datos, totales = inventario_fifo()
        for r in datos:
            self.tree.insert(
                "",
                "end",
                values=(
                    r["orden"],
                    r["parte"],
                    r["molde"],
                    r["objetivo"],
                    r["enviado"],
                    r["asignado"],
                    r["progreso"],
                    r["pendiente"],
                ),
            )

        self.lbl_totals.configure(
            text=(
                f"Órdenes: {len(datos)} • Producción: {totales['produccion']}"
                f" • Enviadas(✔): {totales['enviados']} • Stock neto: {totales['stock']}"
            )
        )

        self._reload_pending_cards()

    # -------- Flashcards pendientes --------
    def _reload_pending_cards(self):
        for w in self.pending_frame.winfo_children():
            w.destroy()

        pending = [r for r in self._shipments_all() if str(r.get("approved","0")).strip() != "1"]
        if not pending:
            return

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
            qty = r.get("qty", "0")
            destino = (r.get("destino","") or "").strip()
            nota = (r.get("nota","") or "").strip()
            fecha = (r.get("ship_date","") or "").strip()

            card = ctk.CTkFrame(self.pending_frame, corner_radius=12)
            card.pack(fill="x", pady=6)

            left = ctk.CTkFrame(card, fg_color="transparent"); left.pack(side="left", padx=10, pady=8)
            right = ctk.CTkFrame(card, fg_color="transparent"); right.pack(side="right", padx=10, pady=8)

            head = f"Orden {orden} • Molde {molde} • {qty} pzs"
            sub  = f"Fecha: {fecha or '—'}  •  Destino: {destino or '—'}"
            if nota: sub += f"  •  Nota: {nota}"

            ctk.CTkLabel(left, text=head, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(left, text=sub, text_color=("#6b7280","#9CA3AF")).pack(anchor="w", pady=(2,0))

            ctk.CTkButton(right, text="Aprobar salida", width=120,
                          command=lambda row=r: self._approve_shipment(row)).pack(side="right")

    def _approve_shipment(self, row):
        rows = self._shipments_all()
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

        self._reload_table()
