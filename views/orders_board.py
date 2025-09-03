from .base import *
from metrics import compute_fifo_assignments, order_metrics, mold_metrics

class OrdersBoardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=("#F8FAFC", "#0F172A"))
        self.app = app
        self._timer = None
        self._build()

    def _tone(self, frac, state):
        # Paleta de colores profesional para MODO CLARO
        if state == 'done': return "#FFFFFF"
        if frac >= 0.99: return "#F0FDF4"  # Verde muy sutil
        if frac >= 0.75: return "#FEFCE8"  # Amarillo muy sutil
        if frac > 0: return "#FEF2F2"      # Rojo muy sutil
        return "#FFFFFF"                  # Blanco neutro

    def _tone_dark(self, frac, state):
        # Paleta de colores profesional para MODO OSCURO
        if state == 'done': return "#1E293B"
        if frac >= 0.99: return "#162E21"
        if frac >= 0.75: return "#2C2413"
        if frac > 0: return "#2E1818"
        return "#1E293B"

    def _build(self):
        # =============== HEADER PROFESIONAL ===============
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#FFFFFF", "#1E293B"), height=70,
                              border_width=1, border_color=("#E5E7EB", "#374151"))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=24, pady=12)

        left_section = ctk.CTkFrame(header_content, fg_color="transparent")
        left_section.pack(side="left", fill="y")

        ctk.CTkButton(left_section, text="← Menú", command=self.app.go_menu,
                      width=100, height=36, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#374151",
                      hover_color="#D1D5DB",
                      font=ctk.CTkFont("Helvetica", 12, "bold")).pack(side="left")

        ctk.CTkLabel(left_section, text="📋 Tablero de Órdenes",
                     font=ctk.CTkFont("Helvetica", 24, "bold"),
                     text_color=("#1E293B", "#F1F5F9")).pack(side="left", padx=20)

        right_section = ctk.CTkFrame(header_content, fg_color="transparent")
        right_section.pack(side="right", fill="y")

        ctk.CTkButton(right_section, text="🔄 Actualizar",
                      command=self._refresh_cards, width=140, height=40,
                      corner_radius=12, fg_color="#3B82F6", hover_color="#2563EB",
                      font=ctk.CTkFont("Helvetica", 12, "bold")).pack(side="right")

        # =============== CUERPO DEL TABLERO (LAYOUT EN FILAS) ===============
        self.board_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.board_container.pack(fill="both", expand=True, padx=24, pady=24)

        self.sections = {
            "active": {"title": "⚙️ ÓRDENES EN PROCESO", "color": ("#2563EB", "#60A5FA")},
            "done": {"title": "✅ ÓRDENES TERMINADAS", "color": ("#9333EA", "#C084FC")}
        }
        self.card_containers = {}

        for state, config in self.sections.items():
            section_frame = ctk.CTkFrame(self.board_container, fg_color="transparent")
            section_frame.pack(fill="x", pady=(0, 24))

            header_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
            header_frame.pack(fill="x", pady=(0, 12))
            ctk.CTkLabel(header_frame, text=config["title"],
                         font=ctk.CTkFont("Helvetica", 16, "bold"),
                         text_color=config["color"]).pack(side="left")

            card_area = ctk.CTkFrame(section_frame, fg_color="transparent")
            card_area.pack(fill="x")
            self.card_containers[state] = card_area
        
        self._refresh_cards()

    def _refresh_cards(self):
        for container in self.card_containers.values():
            for widget in container.winfo_children():
                widget.destroy()

        rows = leer_csv_dict(PLANNING_CSV)
        fifo = compute_fifo_assignments(rows)

        orders_by_state = {"active": [], "done": []}
        for r in rows:
            estado = r.get("estado", "plan").lower()
            if estado == "done":
                orders_by_state["done"].append(r)
            else:
                orders_by_state["active"].append(r)

        for state, orders in orders_by_state.items():
            orders.sort(key=lambda r: r.get("fin_est_ts", ""))
            container = self.card_containers[state]
            if not orders:
                ctk.CTkLabel(container, text="Sin órdenes en este estado.",
                             text_color=("#6B7280", "#9CA3AF"), font=ctk.CTkFont(size=12)).pack(pady=40, padx=20)
            else:
                for r in orders:
                    card = self._create_order_card(container, r, fifo)
                    card.pack(fill="x", pady=8)

        if self._timer:
            self.after_cancel(self._timer)
        self._timer = self.after(15000, self._refresh_cards)

    def _create_order_card(self, parent, r, fifo):
        orden = r.get("orden", "N/A"); parte = r.get("parte", "N/A"); molde = r.get("molde_id", "N/A")
        objetivo = parse_int_str(r.get("qty_total", "0"))
        estado = r.get("estado", "plan").lower()

        m = order_metrics(r, fifo)
        mm = mold_metrics(molde, fifo)
        
        progreso = m["progreso"]; enviado = m["enviado"]; pendiente = m["pendiente"]
        neto_molde = mm["neto"]
        
        frac_prog = (progreso / objetivo) if objetivo > 0 else 0.0

        bg_color = (self._tone(frac_prog, estado), self._tone_dark(frac_prog, estado))
        
        card = ctk.CTkFrame(parent, corner_radius=16, fg_color=bg_color,
                              border_width=1, border_color=("#E5E7EB", "#374151"))
        
        card.grid_columnconfigure(0, weight=3) # Info principal
        card.grid_columnconfigure(1, weight=2) # KPIs
        card.grid_columnconfigure(2, weight=1) # Botones

        # --- Columna 1: Info General y Progreso ---
        info_col = ctk.CTkFrame(card, fg_color="transparent")
        info_col.grid(row=0, column=0, sticky="nsew", padx=20, pady=15)
        
        ctk.CTkLabel(info_col, text=f"Orden {orden}", font=ctk.CTkFont("Helvetica", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(info_col, text=f"{parte} | Molde: {molde}", font=ctk.CTkFont("Helvetica", 13)).pack(anchor="w", pady=(0, 10))

        prog_text = f"Progreso: {progreso:,} / {objetivo:,} pzs ({frac_prog:.1%})"
        ctk.CTkLabel(info_col, text=prog_text, font=ctk.CTkFont("Helvetica", 12)).pack(anchor="w")
        barp = ctk.CTkProgressBar(info_col, height=12, corner_radius=6)
        barp.set(frac_prog)
        barp.pack(fill="x", pady=(4, 0))

        # --- Columna 2: KPIs ---
        kpi_col = ctk.CTkFrame(card, fg_color="transparent")
        kpi_col.grid(row=0, column=1, sticky="ns", pady=15)
        kpi_col.grid_columnconfigure((0, 1, 2), weight=1)
        kpi_col.grid_rowconfigure(0, weight=1)

        def create_kpi(parent, col, title, value, color, dark_color):
            kpi_frame = ctk.CTkFrame(parent, fg_color="transparent")
            kpi_frame.grid(row=0, column=col, padx=10)
            ctk.CTkLabel(kpi_frame, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color=(color, dark_color)).pack()
            ctk.CTkLabel(kpi_frame, text=f"{value:,}", font=ctk.CTkFont(size=20, weight="bold")).pack()

        create_kpi(kpi_col, 0, "ENVIADO ✅", enviado, "#059669", "#6EE7B7")
        create_kpi(kpi_col, 1, "PENDIENTE ⏳", pendiente, "#DC2626", "#F87171")
        create_kpi(kpi_col, 2, "INV. NETO MOLDE 📦", neto_molde, "#3B82F6", "#93C5FD")

        # --- Columna 3: Acciones ---
        action_col = ctk.CTkFrame(card, fg_color="transparent")
        action_col.grid(row=0, column=2, sticky="e", padx=20, pady=15)
        
        ctk.CTkButton(action_col, text="Registrar Salida", width=120, height=36, corner_radius=8,
                      command=lambda o=orden: self.app.go_shipments(o)).pack(pady=(0, 8))
        ctk.CTkButton(action_col, text="Plan", width=120, height=32, corner_radius=8,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                      command=self.app.go_planning).pack()

        return card
