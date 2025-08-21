from .base import *
from metrics import compute_fifo_assignments, order_metrics, mold_metrics


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

        fifo = compute_fifo_assignments(rows)  # <<— núcleo FIFO una sola vez

        for r in rows:
            orden=r.get("orden",""); parte=r.get("parte",""); molde=r.get("molde_id","")
            maquina=r.get("maquina_id",""); objetivo=parse_int_str(r.get("qty_total","0"))
            ini=r.get("inicio_ts",""); fin=r.get("fin_est_ts",""); setup=r.get("setup_min","0")
            estado=r.get("estado","plan")

            m = order_metrics(r, fifo)
            progreso = m["progreso"]
            enviado  = m["enviado"]
            asignado = m["asignado"]
            frac_prog = (progreso/objetivo) if objetivo>0 else 0.0
            frac_ship = (enviado/objetivo) if objetivo>0 else 0.0
            bg,fg = self._tone(frac_prog)

            # métricas de molde (sobrante sin asignar)
            mm = mold_metrics(molde, fifo)
            sobrante = mm["sobrante"]
            enviado_mol = mm["enviado"]

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

            # progreso "producción" (en realidad capacidad disponible para cumplir la orden)
            ctk.CTkLabel(card, text="Progreso de producción").pack(anchor="w", padx=12)
            barp=ctk.CTkProgressBar(card); barp.set(frac_prog); barp.pack(fill="x", padx=12)
            row1=ctk.CTkFrame(card, fg_color="transparent"); row1.pack(fill="x", padx=12, pady=(4,8))
            ctk.CTkLabel(row1, text=f"Progreso: {progreso}/{objetivo} pzs (Enviado {enviado} + Asignado {asignado})").pack(side="left")
            ctk.CTkLabel(row1, text=days_left).pack(side="right")

            # progreso salidas
            ctk.CTkLabel(card, text="Progreso de salidas / embarques").pack(anchor="w", padx=12)
            bars=ctk.CTkProgressBar(card); bars.set(frac_ship); bars.pack(fill="x", padx=12)
            row2=ctk.CTkFrame(card, fg_color="transparent"); row2.pack(fill="x", padx=12, pady=(4,10))
            ctk.CTkLabel(
                row2,
                text=(f"Enviado ord: {enviado}/{objetivo} pzs  •  Enviado mol: {enviado_mol} pzs  •  Disponible (molde sin asignar): {sobrante}")
            ).pack(side="left")
            ctk.CTkButton(row2, text="Registrar salida", command=lambda o=orden: self.app.go_shipments(o)).pack(side="right", padx=(6,0))
            ctk.CTkButton(row2, text="Ver planificación", fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                          command=self.app.go_planning).pack(side="right")

        if self._timer: self.after_cancel(self._timer)
        self._timer = self.after(6000, self._refresh_cards)
