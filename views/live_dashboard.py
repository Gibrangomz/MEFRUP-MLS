from .base import *

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
        self.lbl_area_title = ctk.CTkLabel(
            self.card_area, text="OEE Área", font=ctk.CTkFont("Helvetica", 16, "bold")
        )
        self.lbl_area_title.pack(anchor="w", padx=12, pady=(10,0))
        self.lbl_area = ctk.CTkLabel(
            self.card_area, text="0.00 %", font=ctk.CTkFont("Helvetica", 28, "bold")
        )
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

            order_card = ctk.CTkFrame(card, corner_radius=12, fg_color=("white", "#1c1c1e"))
            order_card.pack(fill="x", padx=12, pady=(8,0))
            self.cards[m["id"]]["order_card"] = order_card

            self.cards[m["id"]]["order_title"] = ctk.CTkLabel(
                order_card,
                text="Sin orden asignada",
                font=ctk.CTkFont("Helvetica", 13, "bold"),
            )
            self.cards[m["id"]]["order_title"].pack(anchor="w", padx=8, pady=(8,4))

            ctk.CTkLabel(order_card, text="Progreso de producción").pack(anchor="w", padx=8)
            self.cards[m["id"]]["pb_prod"] = ctk.CTkProgressBar(order_card)
            self.cards[m["id"]]["pb_prod"].set(0)
            self.cards[m["id"]]["pb_prod"].pack(fill="x", padx=8)
            r1 = ctk.CTkFrame(order_card, fg_color="transparent")
            r1.pack(fill="x", padx=8, pady=(2,6))
            self.cards[m["id"]]["lbl_prod"] = ctk.CTkLabel(r1, text="Producidas: 0/0 pzs")
            self.cards[m["id"]]["lbl_prod"].pack(side="left")
            self.cards[m["id"]]["lbl_days"] = ctk.CTkLabel(r1, text="")
            self.cards[m["id"]]["lbl_days"].pack(side="right")

            ctk.CTkLabel(order_card, text="Progreso de salidas / embarques").pack(anchor="w", padx=8)
            self.cards[m["id"]]["pb_ship"] = ctk.CTkProgressBar(order_card)
            self.cards[m["id"]]["pb_ship"].set(0)
            self.cards[m["id"]]["pb_ship"].pack(fill="x", padx=8)
            r2 = ctk.CTkFrame(order_card, fg_color="transparent")
            r2.pack(fill="x", padx=8, pady=(2,8))
            self.cards[m["id"]]["lbl_ship"] = ctk.CTkLabel(
                r2,
                text="Enviado ord: 0/0 pzs  •  Enviado mol: 0 pzs  •  Disponible: 0",
            )
            self.cards[m["id"]]["lbl_ship"].pack(anchor="w")

            self.cards[m["id"]]["paro"] = ctk.CTkLabel(card, text="Último paro: -", wraplength=520, justify="left")
            self.cards[m["id"]]["paro"].pack(anchor="w", padx=12, pady=(4,10))

        self._refresh_now()

    def _refresh_now(self, fecha=None):
        """Actualiza métricas en vivo y programa la siguiente actualización."""
        if self._timer:
            try:
                self.after_cancel(self._timer)
            except Exception:
                pass
            self._timer = None
        try:
            # reloj
            self.clock_lbl.configure(text=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            if fecha is not None:
                self.current_date = fecha
            else:
                self.current_date = getattr(self, "current_date", date.today().isoformat())
            hoy = self.current_date
            self.lbl_area_title.configure(text="OEE Área (Histórico)")

            # por máquina y promedio de área
            suma_oee = 0.0
            plan_rows = leer_csv_dict(PLANNING_CSV)
            for m in MACHINES:
                r_hist = resumen_historico_maquina(m)
                r_day = resumen_hoy_maquina(m, hoy)
                suma_oee += r_hist["oee"]

                card = self.cards[m["id"]]
                card["oee"].configure(text=f"OEE {r_hist['oee']:.2f}%")
                card["A"].configure(text=f"A {r_hist['A']:.2f}%")
                card["P"].configure(text=f"P {r_hist['P']:.2f}%")
                card["Q"].configure(text=f"Q {r_hist['Q']:.2f}%")
                bg, fg = self._tone(r_hist["oee"])
                try:
                    card["wrap"].configure(fg_color=bg)
                    card["oee"].configure(text_color=fg)
                    card["A"].configure(text_color=fg)
                    card["P"].configure(text_color=fg)
                    card["Q"].configure(text_color=fg)
                except Exception:
                    pass

                futuros = [
                    p
                    for p in plan_rows
                    if p.get("maquina_id") == m["id"]
                    and (p.get("estado", "plan").lower() != "done")
                ]
                try:
                    futuros.sort(key=lambda p: p.get("inicio_ts", ""))
                except Exception:
                    pass
                if futuros:
                    p = futuros[0]
                    orden = p.get("orden", "")
                    parte = p.get("parte", "")
                    molde = p.get("molde_id", "")
                    qty_total = parse_int_str(p.get("qty_total", "0"))
                    prod = producido_por_molde_global(molde)
                    shipped_order = enviados_por_orden(orden)
                    shipped_total = enviados_por_molde(molde)
                    disp = max(0, prod - shipped_total)
                    frac_prod = (prod / qty_total) if qty_total > 0 else 0.0
                    frac_ship = (shipped_order / qty_total) if qty_total > 0 else 0.0
                    try:
                        dleft = (
                            datetime.strptime(p.get("fin_est_ts", ""), "%Y-%m-%d").date()
                            - date.today()
                        ).days
                        days_left = f"{dleft} días restantes"
                    except Exception:
                        days_left = ""
                    card["order_title"].configure(
                        text=f"Orden {orden} — {parte} • Molde {molde}"
                    )
                    self.app._set_pb_if_changed(card["pb_prod"], frac_prod)
                    self.app._set_pb_if_changed(card["pb_ship"], frac_ship)
                    card["lbl_prod"].configure(
                        text=f"Producidas: {prod}/{qty_total} pzs"
                    )
                    card["lbl_ship"].configure(
                        text=(
                            f"Enviado ord: {shipped_order}/{qty_total} pzs  •  "
                            f"Enviado mol: {shipped_total} pzs  •  Disponible: {disp}"
                        )
                    )
                    card["lbl_days"].configure(text=days_left)
                else:
                    card["order_title"].configure(text="Sin orden asignada")
                    self.app._set_pb_if_changed(card["pb_prod"], 0)
                    self.app._set_pb_if_changed(card["pb_ship"], 0)
                    card["lbl_prod"].configure(text="Producidas: 0/0 pzs")
                    card["lbl_ship"].configure(
                        text="Enviado ord: 0/0 pzs  •  Enviado mol: 0 pzs  •  Disponible: 0"
                    )
                    card["lbl_days"].configure(text="")
                card["paro"].configure(text=f"Último paro: {r_day['ultimo_paro']}")

            if MACHINES:
                area_oee = suma_oee / len(MACHINES)
                self.lbl_area.configure(text=f"{area_oee:.2f} %")
                bg, fg = self._tone(area_oee)
                try:
                    self.card_area.configure(fg_color=bg)
                    self.lbl_area.configure(text_color=fg)
                    self.lbl_area_title.configure(text_color=fg)
                except Exception:
                    pass
            else:
                self.lbl_area.configure(text="0.00 %")

        except Exception:
            logging.exception("Error al refrescar tablero en vivo")
        finally:
            self._timer = self.after(DASH_REFRESH_MS, self._refresh_now)

# ---------- Reportes ----------
