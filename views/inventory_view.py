from .base import *
from metrics import compute_fifo_assignments, order_metrics, mold_metrics, totals_from_fifo

class InventoryView(ctk.CTkFrame):
    """
    Inventario con UI súper profesional:
    - Dashboard de KPIs con iconos y colores inteligentes
    - Layout moderno con cards y gradientes
    - Tablas estilizadas con zebra y hover effects
    - Alertas visuales para acciones críticas
    - Navegación intuitiva y fluida
    """
    def __init__(self, master, app):
        super().__init__(master, fg_color=("#F8FAFC", "#0F172A"))
        self.app = app
        self._selected_order = ""
        self._ship_filter_status = tk.StringVar(value="Todas")
        self._log_filter_status = tk.StringVar(value="Todas")
        self._log_filter_text = tk.StringVar(value="")
        self._show_cards = tk.BooleanVar(value=True)
        self._build_professional_inventory()

    # ---------------------------
    # Helpers (sin cambios)
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

    # ----------- UI PROFESIONAL -----------
    def _build_professional_inventory(self):
        """Construye la interfaz profesional completa"""
        # =============== HEADER ELEGANTE ===============
        self._create_professional_header()
        
        # =============== MAIN CONTAINER ===============
        main_container = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # KPI Dashboard Superior
        self._create_kpi_dashboard(main_container)
        
        # Alertas y Flashcards
        self._create_alerts_section(main_container)
        
        # Layout Principal: 2 Columnas
        self._create_main_layout(main_container)
        
        # Bitácora Global (Full Width)
        self._create_global_log_section(main_container)
        
        # Inicializar datos
        self._reload_all()

    def _create_professional_header(self):
        """Header moderno con gradiente y controles avanzados"""
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#FFFFFF", "#1E293B"), height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Contenido del header
        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=24, pady=16)
        
        # Lado izquierdo: Navegación y título
        left_section = ctk.CTkFrame(header_content, fg_color="transparent")
        left_section.pack(side="left", fill="y")
        
        nav_row = ctk.CTkFrame(left_section, fg_color="transparent")
        nav_row.pack(fill="x", pady=(0, 4))
        
        ctk.CTkButton(nav_row, text="← Menú", command=self.app.go_menu, 
                     width=100, height=36, corner_radius=10,
                     fg_color="#E5E7EB", text_color="#374151", 
                     hover_color="#D1D5DB",
                     font=ctk.CTkFont("Helvetica", 12, "bold")).pack(side="left")
        
        # Título principal
        title_row = ctk.CTkFrame(left_section, fg_color="transparent")
        title_row.pack(fill="x")
        
        ctk.CTkLabel(title_row, text="📦 Gestión de Inventario",
                    font=ctk.CTkFont("Helvetica", 24, "bold"),
                    text_color=("#1E293B", "#F1F5F9")).pack(side="left")
        
        # Lado derecho: Controles avanzados
        right_section = ctk.CTkFrame(header_content, fg_color="transparent")
        right_section.pack(side="right", fill="y")
        
        controls_row = ctk.CTkFrame(right_section, fg_color="transparent")
        controls_row.pack(side="right", pady=4)
        
        # Toggle elegante para flashcards
        toggle_frame = ctk.CTkFrame(controls_row, corner_radius=20, fg_color=("#F0F9FF", "#1E40AF"))
        toggle_frame.pack(side="left", padx=(0, 12))
        
        ctk.CTkSwitch(toggle_frame, text="💡 Alertas Pendientes", 
                     variable=self._show_cards, command=self._toggle_cards,
                     font=ctk.CTkFont("Helvetica", 11, "bold")).pack(padx=16, pady=8)
        
        # Botón de actualización mejorado
        ctk.CTkButton(controls_row, text="🔄 Actualizar Todo", 
                     command=self._reload_all, width=140, height=40,
                     corner_radius=12, fg_color="#10B981", hover_color="#059669",
                     font=ctk.CTkFont("Helvetica", 12, "bold")).pack(side="right")

    def _create_kpi_dashboard(self, parent):
        """Dashboard de KPIs con diseño moderno tipo SaaS"""
        kpi_container = ctk.CTkFrame(parent, corner_radius=20, fg_color=("#FFFFFF", "#1E293B"))
        kpi_container.pack(fill="x", pady=(0, 20))
        
        # Header del dashboard
        kpi_header = ctk.CTkFrame(kpi_container, fg_color="transparent")
        kpi_header.pack(fill="x", padx=24, pady=(20, 16))
        
        ctk.CTkLabel(kpi_header, text="📊 Indicadores Clave de Inventario",
                    font=ctk.CTkFont("Helvetica", 18, "bold"),
                    text_color=("#1E293B", "#F1F5F9")).pack(side="left")
        
        # Separador visual
        separator = ctk.CTkFrame(kpi_container, height=2, fg_color=("#E5E7EB", "#374151"))
        separator.pack(fill="x", padx=24, pady=(0, 16))
        
        # Grid de KPIs mejorado
        kpi_grid = ctk.CTkFrame(kpi_container, fg_color="transparent")
        kpi_grid.pack(fill="x", padx=24, pady=(0, 24))
        
        # Configurar grid
        for i in range(5):
            kpi_grid.grid_columnconfigure(i, weight=1)
        
        # Definir KPIs con iconos y colores mejorados para mejor contraste
        self._kpi_definitions = [
            {"title": "Stock Neto Global", "icon": "📦", "color": "#1E40AF", "trend": "neutral"},
            {"title": "Sin Asignar", "icon": "⚠️", "color": "#D97706", "trend": "attention"},
            {"title": "Salidas Aprobadas", "icon": "✅", "color": "#059669", "trend": "positive"},
            {"title": "Pendientes Aprobación", "icon": "⏳", "color": "#DC2626", "trend": "critical"},
            {"title": "Órdenes Activas", "icon": "📋", "color": "#7C3AED", "trend": "info"}
        ]
        
        self._kpi_cards = []
        for i, kpi_def in enumerate(self._kpi_definitions):
            card = self._create_modern_kpi_card(kpi_grid, kpi_def, i)
            self._kpi_cards.append(card)

    def _create_modern_kpi_card(self, parent, kpi_def, column):
        """Crea una card KPI moderna más compacta con efectos visuales y mejor contraste"""
        # Card más pequeña con tamaño fijo
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=kpi_def["color"], 
                           width=160, height=90)  # Reducido de 180x100
        card.grid(row=0, column=column, padx=4, pady=4, sticky="ew")  # Menos padding
        card.grid_propagate(False)  # Mantener tamaño fijo
        
        # Contenido más compacto
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=8, pady=6)  # Menos padding
        
        # Icono y título en la parte superior
        header_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 2))  # Menos espacio
        
        # Icono más pequeño
        ctk.CTkLabel(header_frame, text=kpi_def["icon"], 
                    font=ctk.CTkFont("Helvetica", 14),  # Reducido de 24
                    text_color="white").pack(side="left")
        
        # Título más compacto
        title_label = ctk.CTkLabel(header_frame, text=kpi_def["title"],
                                  font=ctk.CTkFont("Helvetica", 9, "bold"),  # Reducido de 12
                                  text_color="white", 
                                  wraplength=80)  # Reducido de 90
        title_label.pack(side="right", anchor="e")
        
        # Valor principal más pequeño pero legible
        value_label = ctk.CTkLabel(content_frame, text="—",
                                  font=ctk.CTkFont("Helvetica", 18, "bold"),  # Reducido de 28
                                  text_color="white")
        value_label.pack(expand=True)
        
        return {"title": title_label, "value": value_label}

    def _create_alerts_section(self, parent):
        """Sección de alertas y flashcards mejorada con mejor contraste"""
        self.alerts_container = ctk.CTkFrame(parent, corner_radius=18, fg_color=("#FFFFFF", "#1E293B"),
                                           border_width=2, border_color=("#E5E7EB", "#374151"))
        self.alerts_container.pack(fill="x", pady=(0, 20))
        
        # Esta se muestra/oculta con el toggle
        self.pending_frame = self.alerts_container

    def _create_main_layout(self, parent):
        """Layout principal con dos columnas elegantes"""
        main_layout = ctk.CTkFrame(parent, fg_color="transparent")
        main_layout.pack(fill="x", pady=(0, 20))
        main_layout.grid_columnconfigure((0, 1), weight=1)
        
        # =============== COLUMNA IZQUIERDA: ÓRDENES FIFO ===============
        self._create_orders_section(main_layout)
        
        # =============== COLUMNA DERECHA: DETALLE DE ORDEN ===============
        self._create_order_detail_section(main_layout)

    def _create_orders_section(self, parent):
        """Sección de órdenes con tabla mejorada"""
        orders_card = ctk.CTkFrame(parent, corner_radius=20, fg_color=("#FFFFFF", "#1E293B"))
        orders_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        orders_card.grid_rowconfigure(2, weight=1)
        
        # Header elegante con mejor contraste
        header = ctk.CTkFrame(orders_card, corner_radius=16, fg_color=("#1E40AF", "#1E40AF"))
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 16))
        
        ctk.CTkLabel(header, text="🎯 Inventario por Orden (FIFO)",
                    font=ctk.CTkFont("Helvetica", 16, "bold"),
                    text_color="white").pack(pady=12)
        
        # Tabla con estilo profesional
        table_frame = ctk.CTkFrame(orders_card, fg_color="transparent")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        
        cols = ("orden", "parte", "molde", "objetivo", "enviado", "asignado", "progreso", "pendiente")
        self.tree_orders = ttk.Treeview(table_frame, columns=cols, show="headings", height=14)
        
        headers = [("orden", "Orden", 90), ("parte", "Parte", 150), ("molde", "Molde", 80),
                  ("objetivo", "Objetivo", 90), ("enviado", "Enviado ✅", 110),
                  ("asignado", "FIFO 📋", 120), ("progreso", "Progreso", 110), ("pendiente", "Pendiente", 110)]
        
        for k, t, w in headers:
            self.tree_orders.heading(k, text=t)
            self.tree_orders.column(k, width=w, anchor="center")
        
        # Scrollbar elegante
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree_orders.yview)
        self.tree_orders.configure(yscrollcommand=scrollbar.set)
        
        self.tree_orders.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.tree_orders.bind("<<TreeviewSelect>>", lambda e: self._on_order_select())
        
        # Footer con totales
        self.lbl_totals_orders = ctk.CTkLabel(orders_card, text="—",
                                             font=ctk.CTkFont("Helvetica", 11),
                                             text_color=("#6B7280", "#9CA3AF"))
        self.lbl_totals_orders.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))

    def _create_order_detail_section(self, parent):
        """Panel de detalle con diseño moderno"""
        detail_card = ctk.CTkFrame(parent, corner_radius=20, fg_color=("#FFFFFF", "#1E293B"))
        detail_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=0)
        detail_card.grid_rowconfigure(4, weight=1)
        
        # Header del detalle con mejor contraste
        detail_header = ctk.CTkFrame(detail_card, corner_radius=16, fg_color=("#059669", "#059669"))
        detail_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 16))
        
        ctk.CTkLabel(detail_header, text="🔍 Detalle de Orden Seleccionada",
                    font=ctk.CTkFont("Helvetica", 16, "bold"),
                    text_color="white").pack(pady=12)
        
        # Información de la orden
        info_frame = ctk.CTkFrame(detail_card, fg_color="transparent")
        info_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        
        self.lbl_order_header = ctk.CTkLabel(info_frame, text="Selecciona una orden para ver detalles...",
                                           font=ctk.CTkFont("Helvetica", 14, "bold"),
                                           text_color=("#374151", "#E5E7EB"))
        self.lbl_order_header.pack(anchor="w", pady=(0, 8))
        
        # Barra de progreso moderna
        progress_frame = ctk.CTkFrame(detail_card, fg_color="transparent")
        progress_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 16))
        
        ctk.CTkLabel(progress_frame, text="📊 Progreso de Producción:",
                    font=ctk.CTkFont("Helvetica", 12, "bold"),
                    text_color=("#374151", "#E5E7EB")).pack(anchor="w", pady=(0, 4))
        
        self.prog_bar = ctk.CTkProgressBar(progress_frame, height=20, corner_radius=10)
        self.prog_bar.set(0.0)
        self.prog_bar.pack(fill="x", pady=(0, 8))
        
        self.lbl_prog = ctk.CTkLabel(progress_frame, text="—",
                                    font=ctk.CTkFont("Helvetica", 11),
                                    text_color=("#6B7280", "#9CA3AF"))
        self.lbl_prog.pack(anchor="w")
        
        self.lbl_mold = ctk.CTkLabel(progress_frame, text="—",
                                    font=ctk.CTkFont("Helvetica", 11),
                                    text_color=("#6B7280", "#9CA3AF"))
        self.lbl_mold.pack(anchor="w", pady=(4, 0))
        
        # Filtros de salidas con mejor contraste
        filter_frame = ctk.CTkFrame(detail_card, corner_radius=12, fg_color=("#F1F5F9", "#334155"))
        filter_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
        
        filter_content = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_content.pack(fill="x", padx=16, pady=12)
        
        ctk.CTkLabel(filter_content, text="🚚 Salidas de esta orden:",
                    font=ctk.CTkFont("Helvetica", 12, "bold"),
                    text_color=("#1E293B", "#F1F5F9")).pack(side="left")
        
        ctk.CTkOptionMenu(filter_content, variable=self._ship_filter_status,
                         values=["Todas", "Aprobadas", "Pendientes"],
                         command=lambda _v: self._reload_shipments_for_order(),
                         width=140, corner_radius=8).pack(side="right")
        
        # Tabla de salidas
        shipments_frame = ctk.CTkFrame(detail_card, fg_color="transparent")
        shipments_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=(0, 16))
        
        cols2 = ("status", "fecha", "qty", "destino", "nota")
        self.tree_ship = ttk.Treeview(shipments_frame, columns=cols2, show="headings", height=8)
        
        for k, t, w in [("status", "Estado", 90), ("fecha", "Fecha", 110), ("qty", "Qty", 80),
                       ("destino", "Destino", 160), ("nota", "Nota", 200)]:
            self.tree_ship.heading(k, text=t)
            self.tree_ship.column(k, width=w, anchor="center" if k not in ("destino", "nota") else "w")
        
        self.tree_ship.pack(fill="both", expand=True)
        
        # Botones de acción elegantes
        actions_frame = ctk.CTkFrame(detail_card, fg_color="transparent")
        actions_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        # Botones principales
        btn_approve = ctk.CTkButton(actions_frame, text="✅ Aprobar Selección",
                                   command=self._approve_selected_in_order,
                                   fg_color="#10B981", hover_color="#059669",
                                   corner_radius=10, height=36)
        btn_approve.pack(side="left", padx=(0, 8))
        
        btn_delete = ctk.CTkButton(actions_frame, text="🗑️ Eliminar",
                                  command=self._delete_selected_in_order,
                                  fg_color="#EF4444", hover_color="#DC2626",
                                  corner_radius=10, height=36)
        btn_delete.pack(side="left", padx=8)
        
        btn_register = ctk.CTkButton(actions_frame, text="➕ Registrar Salida",
                                    command=self._open_shipments,
                                    fg_color="#8B5CF6", hover_color="#7C3AED",
                                    corner_radius=10, height=36)
        btn_register.pack(side="right")

    def _create_global_log_section(self, parent):
        """Bitácora global con diseño premium"""
        log_container = ctk.CTkFrame(parent, corner_radius=20, fg_color=("#FFFFFF", "#1E293B"))
        log_container.pack(fill="both", expand=True, pady=(20, 0))
        
        # Header con mejor contraste
        log_header = ctk.CTkFrame(log_container, corner_radius=16, fg_color=("#D97706", "#D97706"))
        log_header.pack(fill="x", padx=20, pady=(20, 16))
        
        ctk.CTkLabel(log_header, text="📋 Bitácora Global de Salidas",
                    font=ctk.CTkFont("Helvetica", 18, "bold"),
                    text_color="white").pack(pady=16)
        
        # Controles de filtro con mejor visibilidad
        filter_panel = ctk.CTkFrame(log_container, corner_radius=12, fg_color=("#F1F5F9", "#334155"))
        filter_panel.pack(fill="x", padx=20, pady=(0, 16))
        
        filter_row = ctk.CTkFrame(filter_panel, fg_color="transparent")
        filter_row.pack(fill="x", padx=16, pady=12)
        
        # Filtros organizados
        ctk.CTkOptionMenu(filter_row, variable=self._log_filter_status,
                         values=["Todas", "Aprobadas", "Pendientes"],
                         command=lambda _v: self._reload_log(),
                         width=120, corner_radius=8).pack(side="left")
        
        search_entry = ctk.CTkEntry(filter_row, textvariable=self._log_filter_text,
                                   placeholder_text="🔍 Buscar orden / destino / nota...",
                                   width=320, height=36, corner_radius=10)
        search_entry.pack(side="left", padx=12)
        
        # Botones de acción
        action_buttons = ctk.CTkFrame(filter_row, fg_color="transparent")
        action_buttons.pack(side="right")
        
        ctk.CTkButton(action_buttons, text="🔍 Filtrar", command=self._reload_log,
                     width=100, height=36, corner_radius=8).pack(side="left", padx=4)
        
        ctk.CTkButton(action_buttons, text="✅ Aprobar", command=self._approve_selected_in_log,
                     fg_color="#10B981", hover_color="#059669",
                     width=100, height=36, corner_radius=8).pack(side="left", padx=4)
        
        ctk.CTkButton(action_buttons, text="📊 Exportar", command=self._export_log_csv,
                     fg_color="#8B5CF6", hover_color="#7C3AED",
                     width=100, height=36, corner_radius=8).pack(side="left", padx=4)
        
        # Tabla global
        table_container = ctk.CTkFrame(log_container, fg_color="transparent")
        table_container.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        
        cols3 = ("orden", "molde", "status", "fecha", "qty", "destino", "nota")
        self.tree_log = ttk.Treeview(table_container, columns=cols3, show="headings", height=12)
        
        for k, t, w in [("orden", "Orden", 90), ("molde", "Molde", 80), ("status", "Estado", 90),
                       ("fecha", "Fecha", 110), ("qty", "Qty", 80), ("destino", "Destino", 220),
                       ("nota", "Nota", 300)]:
            self.tree_log.heading(k, text=t)
            self.tree_log.column(k, width=w, anchor="center" if k in ("orden", "molde", "status", "fecha", "qty") else "w")
        
        # Scrollbar para tabla global
        log_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree_log.yview)
        self.tree_log.configure(yscrollcommand=log_scrollbar.set)
        
        self.tree_log.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # Footer con estadísticas
        self.lbl_totals_log = ctk.CTkLabel(log_container, text="—",
                                          font=ctk.CTkFont("Helvetica", 12, "bold"),
                                          text_color=("#374151", "#E5E7EB"))
        self.lbl_totals_log.pack(anchor="w", padx=20, pady=(0, 20))

    # ------------
    # Navegación UI (sin cambios en lógica)
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
            self.alerts_container.pack(fill="x", pady=(0, 20), before=self.alerts_container.master.winfo_children()[2])
        else:
            self.alerts_container.pack_forget()

    # ----------------
    # Recargas de data (lógica sin cambios)
    # ----------------
    def _reload_all(self):
        self._reload_kpis()
        self._reload_orders_table()
        self._reload_pending_cards()
        self._reload_order_detail()
        self._reload_log()

    def _reload_kpis(self):
        """Actualiza KPIs con nueva información visual"""
        orders = leer_csv_dict(PLANNING_CSV)
        fifo = compute_fifo_assignments(orders)
        t = totals_from_fifo(fifo)

        total_orders = len(orders)
        pend = self._shipments_pending()
        pend_qty = self._sum_qty(pend)
        appr_qty = self._sum_qty(self._shipments_approved())

        # Valores actualizados
        values = [
            f"{t['neto']:,}",
            f"{t['sobrante']:,}",
            f"{appr_qty:,}",
            f"{pend_qty:,}",
            f"{total_orders:,}"
        ]
        
        for i, (card, value) in enumerate(zip(self._kpi_cards, values)):
            card["value"].configure(text=value)

    def _reload_orders_table(self):
        """Actualiza la tabla de órdenes con datos FIFO"""
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
            text=(f"📊 Órdenes: {len(orders)}  •  🎯 Objetivo: {tot_obj:,}  •  ✅ Enviado: {tot_env:,}  •  "
                  f"📋 Asignado FIFO: {tot_asig:,}  •  📈 Progreso: {tot_prog:,}  •  ⏳ Pendiente: {tot_pend:,}")
        )

    def _clear_order_detail(self):
        """Limpia el panel de detalle de orden"""
        self.lbl_order_header.configure(text="Selecciona una orden para ver detalles...")
        self.prog_bar.set(0.0)
        self.lbl_prog.configure(text="—")
        self.lbl_mold.configure(text="—")
        for i in self.tree_ship.get_children(): 
            self.tree_ship.delete(i)

    def _reload_order_detail(self):
        """Recarga el detalle de la orden seleccionada"""
        if not self._selected_order:
            self._clear_order_detail()
            return

        orders = leer_csv_dict(PLANNING_CSV)
        row = next((r for r in orders if (r.get("orden","") or "").strip() == self._selected_order), None)
        if not row:
            self._clear_order_detail()
            return

        fifo = compute_fifo_assignments(orders)
        m = order_metrics(row, fifo)
        
        # Actualizar información de la orden
        parte = (row.get("parte", "") or "").strip()
        molde = (row.get("molde_id", "") or "").strip()
        
        self.lbl_order_header.configure(
            text=f"📋 Orden: {self._selected_order} | 🔧 Parte: {parte}"
        )
        
        # Actualizar barra de progreso
        objetivo = m["objetivo"]
        progreso = m["progreso"]
        if objetivo > 0:
            percent = progreso / objetivo
            self.prog_bar.set(min(1.0, percent))
            self.lbl_prog.configure(
                text=f"📈 Progreso: {progreso:,} / {objetivo:,} ({percent*100:.1f}%)"
            )
        else:
            self.prog_bar.set(0.0)
            self.lbl_prog.configure(text="📈 Progreso: No definido")
        
        # Información del molde - CORREGIDO para evitar KeyError
        if molde:
            try:
                mold_info = mold_metrics(molde, fifo)
                # Usar .get() para evitar KeyError y proporcionar valores por defecto
                stock = mold_info.get('stock', 0)
                asignado = mold_info.get('asignado', 0)
                neto = mold_info.get('neto', 0)
                
                # Mostrar información disponible
                info_parts = []
                if 'stock' in mold_info or 'neto' in mold_info:
                    info_parts.append(f"Stock: {max(stock, neto):,}")
                if 'asignado' in mold_info:
                    info_parts.append(f"Asignado: {asignado:,}")
                
                if info_parts:
                    self.lbl_mold.configure(
                        text=f"🏭 Molde {molde}: {' | '.join(info_parts)}"
                    )
                else:
                    self.lbl_mold.configure(
                        text=f"🏭 Molde {molde}: Información en cálculo..."
                    )
            except Exception as e:
                # Fallback seguro si mold_metrics falla
                self.lbl_mold.configure(
                    text=f"🏭 Molde {molde}: Info no disponible"
                )
        else:
            self.lbl_mold.configure(text="🏭 Molde: No especificado")
        
        # Recargar tabla de salidas
        self._reload_shipments_for_order()

    def _reload_shipments_for_order(self):
        """Recarga las salidas de la orden seleccionada"""
        for i in self.tree_ship.get_children():
            self.tree_ship.delete(i)
            
        if not self._selected_order:
            return
            
        all_ships = self._shipments_all()
        ships = [r for r in all_ships if (r.get("orden","") or "").strip() == self._selected_order]
        
        # Aplicar filtro de estado
        status_filter = self._ship_filter_status.get()
        if status_filter == "Aprobadas":
            ships = [r for r in ships if str(r.get("approved","0")).strip() == "1"]
        elif status_filter == "Pendientes":
            ships = [r for r in ships if str(r.get("approved","0")).strip() != "1"]
        
        # Ordenar por fecha descendente
        ships.sort(key=lambda x: x.get("fecha", ""), reverse=True)
        
        for r in ships:
            fecha = r.get("fecha", "")
            qty = r.get("qty", "0")
            destino = r.get("destino", "")
            nota = r.get("nota", "")
            status = self._status_label(r)
            
            # Insertar con tag para colorear
            item_id = self.tree_ship.insert("", "end", values=(status, fecha, qty, destino, nota))
            if status == "Aprobada":
                self.tree_ship.set(item_id, "status", "✅ Aprobada")
            else:
                self.tree_ship.set(item_id, "status", "⏳ Pendiente")

    def _reload_pending_cards(self):
        """Actualiza las tarjetas de alertas pendientes"""
        # Limpiar contenido anterior
        for widget in self.pending_frame.winfo_children():
            widget.destroy()
            
        pend = self._shipments_pending()
        if not pend:
            # Mostrar mensaje de "todo bien"
            success_frame = ctk.CTkFrame(self.pending_frame, fg_color="transparent")
            success_frame.pack(fill="x", padx=20, pady=16)
            
            ctk.CTkLabel(success_frame, text="🎉 ¡Excelente! No hay salidas pendientes de aprobación",
                        font=ctk.CTkFont("Helvetica", 14, "bold"),
                        text_color=("#059669", "#10B981")).pack()
            return
            
        # Header de alertas
        alert_header = ctk.CTkFrame(self.pending_frame, fg_color="transparent")
        alert_header.pack(fill="x", padx=20, pady=(16, 8))
        
        ctk.CTkLabel(alert_header, text=f"⚠️ {len(pend)} Salidas Pendientes de Aprobación",
                    font=ctk.CTkFont("Helvetica", 16, "bold"),
                    text_color=("#DC2626", "#F87171")).pack(side="left")
        
        # Cards de alertas
        cards_frame = ctk.CTkFrame(self.pending_frame, fg_color="transparent")
        cards_frame.pack(fill="x", padx=20, pady=(0, 16))
        
        # Agrupar por orden
        from collections import defaultdict
        by_order = defaultdict(list)
        for r in pend:
            orden = (r.get("orden", "") or "").strip()
            by_order[orden].append(r)
        
        # Mostrar solo las primeras 3 órdenes con más salidas pendientes
        sorted_orders = sorted(by_order.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        
        for i, (orden, ships) in enumerate(sorted_orders):
            card = ctk.CTkFrame(cards_frame, corner_radius=12, fg_color=("#FEE2E2", "#7F1D1D"))
            card.pack(fill="x", pady=4)
            
            card_content = ctk.CTkFrame(card, fg_color="transparent")
            card_content.pack(fill="x", padx=16, pady=12)
            
            # Información de la orden con mejor contraste
            info_text = f"📋 Orden {orden}: {len(ships)} salidas pendientes"
            total_qty = sum(int(float(r.get("qty", 0) or 0)) for r in ships)
            if total_qty > 0:
                info_text += f" ({total_qty:,} unidades)"
            
            ctk.CTkLabel(card_content, text=info_text,
                        font=ctk.CTkFont("Helvetica", 12, "bold"),
                        text_color=("#991B1B", "#FECACA")).pack(side="left")
            
            # Botón de acción rápida
            ctk.CTkButton(card_content, text="👀 Ver Detalles",
                         command=lambda o=orden: self._select_order_by_name(o),
                         width=120, height=28, corner_radius=8,
                         fg_color="#DC2626", hover_color="#B91C1C").pack(side="right")

    def _select_order_by_name(self, orden):
        """Selecciona una orden específica en la tabla"""
        # Buscar el item en el tree
        for item in self.tree_orders.get_children():
            values = self.tree_orders.item(item, "values")
            if values and values[0] == orden:
                self.tree_orders.selection_set(item)
                self.tree_orders.focus(item)
                self.tree_orders.see(item)
                self._on_order_select()
                break

    def _reload_log(self):
        """Recarga la bitácora global con filtros"""
        for i in self.tree_log.get_children():
            self.tree_log.delete(i)
            
        all_ships = self._shipments_all()
        ships = all_ships.copy()
        
        # Aplicar filtro de estado
        status_filter = self._log_filter_status.get()
        if status_filter == "Aprobadas":
            ships = [r for r in ships if str(r.get("approved","0")).strip() == "1"]
        elif status_filter == "Pendientes":
            ships = [r for r in ships if str(r.get("approved","0")).strip() != "1"]
        
        # Aplicar filtro de texto
        text_filter = self._log_filter_text.get().strip().lower()
        if text_filter:
            ships = [r for r in ships if (
                text_filter in (r.get("orden", "") or "").lower() or
                text_filter in (r.get("destino", "") or "").lower() or
                text_filter in (r.get("nota", "") or "").lower()
            )]
        
        # Ordenar por fecha descendente
        ships.sort(key=lambda x: x.get("fecha", ""), reverse=True)
        
        # Poblar tabla
        total_qty = 0
        for r in ships:
            orden = r.get("orden", "")
            molde = r.get("molde_id", "")
            fecha = r.get("fecha", "")
            qty = r.get("qty", "0")
            destino = r.get("destino", "")
            nota = r.get("nota", "")
            status = self._status_label(r)
            
            try:
                total_qty += int(float(qty or 0))
            except:
                pass
                
            # Insertar con formato
            status_display = "✅ Aprobada" if status == "Aprobada" else "⏳ Pendiente"
            self.tree_log.insert("", "end", values=(orden, molde, status_display, fecha, qty, destino, nota))
        
        # Actualizar totales
        approved_count = len([r for r in ships if str(r.get("approved","0")).strip() == "1"])
        pending_count = len(ships) - approved_count
        
        self.lbl_totals_log.configure(
            text=(f"📊 Total: {len(ships)} salidas  •  ✅ Aprobadas: {approved_count}  •  "
                  f"⏳ Pendientes: {pending_count}  •  📦 Cantidad Total: {total_qty:,}")
        )

    # ----------------
    # Acciones de botones
    # ----------------
    def _approve_selected_in_order(self):
        """Aprueba las salidas seleccionadas en el detalle de orden"""
        sel = self.tree_ship.selection()
        if not sel:
            messagebox.showwarning("Selección", "Selecciona al menos una salida para aprobar")
            return
            
        count = 0
        all_ships = leer_shipments()
        
        for item in sel:
            values = self.tree_ship.item(item, "values")
            if not values:
                continue
                
            fecha, qty, destino, nota = values[1:5]
            
            # Buscar y actualizar en la lista completa
            for r in all_ships:
                if (r.get("orden", "") == self._selected_order and
                    r.get("fecha", "") == fecha and
                    r.get("qty", "") == qty and
                    r.get("destino", "") == destino and
                    r.get("nota", "") == nota and
                    str(r.get("approved", "0")).strip() != "1"):
                    
                    r["approved"] = "1"
                    count += 1
                    break
        
        if count > 0:
            guardar_shipments(all_ships)
            messagebox.showinfo("Éxito", f"Se aprobaron {count} salida(s)")
            self._reload_all()
        else:
            messagebox.showinfo("Info", "No se encontraron salidas para aprobar")

    def _delete_selected_in_order(self):
        """Elimina las salidas seleccionadas en el detalle de orden"""
        sel = self.tree_ship.selection()
        if not sel:
            messagebox.showwarning("Selección", "Selecciona al menos una salida para eliminar")
            return
            
        if not messagebox.askyesno("Confirmar", f"¿Eliminar {len(sel)} salida(s) seleccionada(s)?"):
            return
            
        count = 0
        all_ships = leer_shipments()
        
        for item in reversed(sel):  # Procesar en reversa para evitar problemas de índices
            values = self.tree_ship.item(item, "values")
            if not values:
                continue
                
            fecha, qty, destino, nota = values[1:5]
            
            # Buscar y eliminar
            for i, r in enumerate(all_ships):
                if (r.get("orden", "") == self._selected_order and
                    r.get("fecha", "") == fecha and
                    r.get("qty", "") == qty and
                    r.get("destino", "") == destino and
                    r.get("nota", "") == nota):
                    
                    all_ships.pop(i)
                    count += 1
                    break
        
        if count > 0:
            guardar_shipments(all_ships)
            messagebox.showinfo("Éxito", f"Se eliminaron {count} salida(s)")
            self._reload_all()
        else:
            messagebox.showinfo("Info", "No se encontraron salidas para eliminar")

    def _approve_selected_in_log(self):
        """Aprueba las salidas seleccionadas en la bitácora global"""
        sel = self.tree_log.selection()
        if not sel:
            messagebox.showwarning("Selección", "Selecciona al menos una salida para aprobar")
            return
            
        count = 0
        all_ships = leer_shipments()
        
        for item in sel:
            values = self.tree_log.item(item, "values")
            if not values or "Aprobada" in values[2]:
                continue
                
            orden, molde, status, fecha, qty, destino, nota = values
            
            # Buscar y aprobar
            for r in all_ships:
                if (r.get("orden", "") == orden and
                    r.get("fecha", "") == fecha and
                    r.get("qty", "") == qty and
                    r.get("destino", "") == destino and
                    r.get("nota", "") == nota and
                    str(r.get("approved", "0")).strip() != "1"):
                    
                    r["approved"] = "1"
                    count += 1
                    break
        
        if count > 0:
            guardar_shipments(all_ships)
            messagebox.showinfo("Éxito", f"Se aprobaron {count} salida(s)")
            self._reload_all()
        else:
            messagebox.showinfo("Info", "No se encontraron salidas para aprobar")

    def _export_log_csv(self):
        """Exporta la bitácora actual a CSV"""
        try:
            from tkinter import filedialog
            import csv
            
            filename = filedialog.asksaveasfilename(
                title="Exportar Bitácora",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if not filename:
                return
                
            # Obtener datos actuales (con filtros aplicados)
            data = []
            for item in self.tree_log.get_children():
                values = self.tree_log.item(item, "values")
                if values:
                    data.append(values)
            
            # Escribir CSV
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Orden", "Molde", "Estado", "Fecha", "Cantidad", "Destino", "Nota"])
                writer.writerows(data)
            
            messagebox.showinfo("Éxito", f"Bitácora exportada a:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar: {str(e)}")
