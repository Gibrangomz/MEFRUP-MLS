from .base import *

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
        self.lbl_totals = ctk.CTkLabel(self, text="—", text_color=("#6b7280","#9CA3AF"))
        self.lbl_totals.pack(anchor="w", padx=16, pady=(0,10))
        self._refresh_cards()

    def _refresh_cards(self):
        for w in self.cards_container.winfo_children(): w.destroy()
        rows=leer_csv_dict(PLANNING_CSV)
        try: rows.sort(key=lambda r: r.get("fin_est_ts",""))
        except: pass

        datos, totales = inventario_fifo()
        info_by_order = {d["orden"]: d for d in datos}

        for r in rows:
            orden=r.get("orden",""); parte=r.get("parte",""); molde=r.get("molde_id","")
            maquina=r.get("maquina_id",""); qty_total=parse_int_str(r.get("qty_total","0"))
            ini=r.get("inicio_ts",""); fin=r.get("fin_est_ts",""); setup=r.get("setup_min","0")
            estado=r.get("estado","plan")
            info = info_by_order.get(orden, dict(objetivo=qty_total,enviado=0,asignado=0,progreso=0,pendiente=qty_total))
            progreso = info.get("progreso",0)
            enviado = info.get("enviado",0)
            asignado = info.get("asignado",0)
            pendiente = info.get("pendiente",qty_total)
            frac = (progreso/qty_total) if qty_total>0 else 0.0
            bg,fg = self._tone(frac)

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

            # progreso total (enviado + asignado)
            ctk.CTkLabel(card, text="Progreso de orden").pack(anchor="w", padx=12)
            barp=ctk.CTkProgressBar(card); barp.set(frac); barp.pack(fill="x", padx=12)
            row1=ctk.CTkFrame(card, fg_color="transparent"); row1.pack(fill="x", padx=12, pady=(4,8))
            ctk.CTkLabel(row1, text=f"Progreso: {progreso}/{qty_total} pzs").pack(side="left")
            ctk.CTkLabel(row1, text=days_left).pack(side="right")

            row2=ctk.CTkFrame(card, fg_color="transparent"); row2.pack(fill="x", padx=12, pady=(0,10))
            ctk.CTkLabel(
                row2,
                text=(
                    f"Enviado {enviado}  •  Asignado {asignado}  •  Pendiente {pendiente}"
                ),
            ).pack(side="left")
            ctk.CTkButton(row2, text="Registrar salida", command=lambda o=orden: self.app.go_shipments(o)).pack(side="right", padx=(6,0))
            ctk.CTkButton(row2, text="Ver planificación", fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB", command=self.app.go_planning).pack(side="right")

        self.lbl_totals.configure(
            text=(
                f"Órdenes: {len(datos)} • Producción: {totales['produccion']}"
                f" • Enviadas(✔): {totales['enviados']} • Stock neto: {totales['stock']}"
            )
        )

        if self._timer: self.after_cancel(self._timer)
        self._timer = self.after(6000, self._refresh_cards)

# ================================
# === Inventario de Piezas
# ================================
