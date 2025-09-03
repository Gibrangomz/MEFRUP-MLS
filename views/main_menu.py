from .base import *

class MainMenu(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=("#F8FAFC", "#0F172A"))
        self.app = app
        self._build_professional_menu()
    
    def _build_professional_menu(self):
        # =============== HEADER SECTION ===============
        self._create_header()
        
        # =============== MAIN CONTENT ===============
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=32, pady=(0, 32))
        
        # Quick Actions Bar (Top)
        self._create_quick_actions(main_container)
        
        # Main Module Grid
        self._create_module_grid(main_container)
        
        # Footer with system info
        self._create_footer(main_container)
    
    def _create_header(self):
        """Header con logo, título y información de estado"""
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#FFFFFF", "#1E293B"), height=120)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        # Logo y título lado izquierdo
        left_section = ctk.CTkFrame(header, fg_color="transparent")
        left_section.pack(side="left", fill="y", padx=32, pady=20)
        
        try:
            img = Image.open(LOGO_PATH)
            logo = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 32))
            ctk.CTkLabel(left_section, image=logo, text="").pack(side="left", padx=(0, 16))
            self.logo = logo
        except:
            pass
        
        # Título y subtítulo
        title_frame = ctk.CTkFrame(left_section, fg_color="transparent")
        title_frame.pack(side="left", fill="y")
        
        ctk.CTkLabel(title_frame, 
                    text="MEFRUP MLS", 
                    font=ctk.CTkFont("Helvetica", 28, "bold"),
                    text_color=("#1E293B", "#F1F5F9")).pack(anchor="w")
        
        ctk.CTkLabel(title_frame, 
                    text="Manufacturing Execution System", 
                    font=ctk.CTkFont("Helvetica", 14),
                    text_color=("#64748B", "#94A3B8")).pack(anchor="w")
        
        # Estado del sistema lado derecho
        right_section = ctk.CTkFrame(header, fg_color="transparent")
        right_section.pack(side="right", fill="y", padx=32, pady=20)
        
        # Indicador de estado en tiempo real
        status_frame = ctk.CTkFrame(right_section, corner_radius=12, 
                                  fg_color=("#F0FDF4", "#064E3B"))
        status_frame.pack(side="right")
        
        ctk.CTkLabel(status_frame, 
                    text="🟢 Sistema Activo", 
                    font=ctk.CTkFont("Helvetica", 12, "bold"),
                    text_color=("#166534", "#22C55E")).pack(padx=16, pady=8)
        
        # Fecha y hora
        from datetime import datetime
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        ctk.CTkLabel(right_section, 
                    text=now, 
                    font=ctk.CTkFont("Helvetica", 12),
                    text_color=("#64748B", "#94A3B8")).pack(side="right", padx=(0, 16))
    
    def _create_quick_actions(self, parent):
        """Barra de acciones rápidas"""
        quick_frame = ctk.CTkFrame(parent, corner_radius=16, 
                                 fg_color=("#FFFFFF", "#1E293B"), height=80)
        quick_frame.pack(fill="x", pady=(0, 24))
        quick_frame.pack_propagate(False)
        
        # Título de sección
        ctk.CTkLabel(quick_frame, 
                    text="⚡ Acceso Rápido", 
                    font=ctk.CTkFont("Helvetica", 16, "bold"),
                    text_color=("#1E293B", "#F1F5F9")).pack(side="left", padx=24, pady=24)
        
        # Botones de acceso rápido
        quick_btns = [
            {"text": "📊 Dashboard", "command": self.app.go_dashboard, "color": "#3B82F6"},
            {"text": "⚙️ OEE Live", "command": self.app.go_oee_select_machine, "color": "#10B981"},
            {"text": "📋 Órdenes", "command": self.app.go_orders_board, "color": "#F59E0B"},
            {"text": "📦 Inventario", "command": self.app.go_inventory, "color": "#8B5CF6"},
        ]
        
        btn_container = ctk.CTkFrame(quick_frame, fg_color="transparent")
        btn_container.pack(side="right", padx=24, pady=16)
        
        for i, btn in enumerate(quick_btns):
            ctk.CTkButton(btn_container, 
                         text=btn["text"],
                         command=btn["command"],
                         width=120,
                         height=48,
                         corner_radius=12,
                         fg_color=btn["color"],
                         hover_color=self._darken_color(btn["color"]),
                         font=ctk.CTkFont("Helvetica", 12, "bold")).pack(side="left", padx=8)
    
    def _create_module_grid(self, parent):
        """Grid principal con módulos organizados por categorías"""
        grid_container = ctk.CTkFrame(parent, fg_color="transparent")
        grid_container.pack(fill="both", expand=True)
        grid_container.grid_columnconfigure((0, 1, 2), weight=1)
        grid_container.grid_rowconfigure((0, 1), weight=1)
        
        # =============== COLUMNA 1: MONITOREO Y CONTROL ===============
        monitoring_card = self._create_category_card(
            grid_container, 
            "📊 Monitoreo y Control",
            "Supervisión en tiempo real",
            "#3B82F6"
        )
        monitoring_card.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        
        monitoring_modules = [
            {
                "title": "Dashboard en Vivo",
                "subtitle": "Área de Inyección",
                "icon": "📈",
                "command": self.app.go_dashboard,
                "priority": "high"
            },
            {
                "title": "OEE y Producción",
                "subtitle": "Registro por máquina",
                "icon": "⚙️",
                "command": self.app.go_oee_select_machine,
                "priority": "high"
            },
            {
                "title": "Reportes Avanzados",
                "subtitle": "Analytics y exportación",
                "icon": "📄",
                "command": self.app.go_reports,
                "priority": "medium"
            }
        ]
        
        self._add_modules_to_card(monitoring_card, monitoring_modules)
        
        # =============== COLUMNA 2: PLANIFICACIÓN Y ÓRDENES ===============
        planning_card = self._create_category_card(
            grid_container,
            "📋 Planificación y Órdenes", 
            "Gestión de producción",
            "#10B981"
        )
        planning_card.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")
        
        planning_modules = [
            {
                "title": "Planificación",
                "subtitle": "Órdenes y milestones",
                "icon": "📅",
                "command": self.app.go_planning,
                "priority": "high"
            },
            {
                "title": "Tablero de Órdenes",
                "subtitle": "Progreso visual",
                "icon": "📊",
                "command": self.app.go_orders_board,
                "priority": "high"
            },
            {
                "title": "Inventario FIFO",
                "subtitle": "Gestión inteligente",
                "icon": "📦",
                "command": self.app.go_inventory,
                "priority": "medium"
            },
            {
                "title": "Embarques",
                "subtitle": "Salida de piezas",
                "icon": "🚚",
                "command": self.app.go_shipments,
                "priority": "medium"
            }
        ]
        
        self._add_modules_to_card(planning_card, planning_modules)
        
        # =============== COLUMNA 3: CONFIGURACIÓN Y HERRAMIENTAS ===============
        config_card = self._create_category_card(
            grid_container,
            "⚙️ Configuración y Herramientas",
            "Maestros y configuración",
            "#8B5CF6"
        )
        config_card.grid(row=0, column=2, padx=12, pady=12, sticky="nsew")
        
        config_modules = [
            {
                "title": "Recetas Básicas",
                "subtitle": "Moldes y partes",
                "icon": "📝",
                "command": self.app.go_recipes,
                "priority": "medium"
            },
            {
                "title": "Recetas de Máquina",
                "subtitle": "Parámetros técnicos",
                "icon": "🔧",
                "command": self.app.go_machine_recipes,
                "priority": "medium"
            },
            {
                "title": "MEFRUP AI",
                "subtitle": "Asistente inteligente",
                "icon": "🤖",
                "command": self.app.go_calculo,
                "priority": "low"
            }
        ]
        
        self._add_modules_to_card(config_card, config_modules)
        
        # =============== FILA 2: MÉTRICAS RÁPIDAS ===============
        metrics_card = ctk.CTkFrame(grid_container, corner_radius=16, 
                                   fg_color=("#FFFFFF", "#1E293B"))
        metrics_card.grid(row=1, column=0, columnspan=3, padx=12, pady=(12, 0), sticky="ew")
        
        self._create_metrics_dashboard(metrics_card)
    
    def _create_category_card(self, parent, title, subtitle, accent_color):
        """Crea una tarjeta de categoría con estilo profesional"""
        card = ctk.CTkFrame(parent, corner_radius=16, fg_color=("#FFFFFF", "#1E293B"))
        
        # Header de la categoría
        header = ctk.CTkFrame(card, corner_radius=12, fg_color=(accent_color, accent_color))
        header.pack(fill="x", padx=16, pady=(16, 12))
        
        ctk.CTkLabel(header,
                    text=title,
                    font=ctk.CTkFont("Helvetica", 16, "bold"),
                    text_color="white").pack(pady=(12, 4))
        
        ctk.CTkLabel(header,
                    text=subtitle,
                    font=ctk.CTkFont("Helvetica", 12),
                    text_color="white").pack(pady=(0, 12))
        
        return card
    
    def _add_modules_to_card(self, card, modules):
        """Añade módulos a una tarjeta de categoría"""
        for module in modules:
            self._create_module_button(card, module)
    
    def _create_module_button(self, parent, module):
        """Crea un botón de módulo individual"""
        priority_colors = {
            "high": ("#EF4444", "#DC2626"),
            "medium": ("#3B82F6", "#2563EB"), 
            "low": ("#6B7280", "#4B5563")
        }
        
        fg_color, hover_color = priority_colors.get(module["priority"], priority_colors["medium"])
        
        # Botón principal con texto completo
        button_text = f"{module['icon']} {module['title']}\n{module['subtitle']}"
        
        btn = ctk.CTkButton(
            parent,
            text=button_text,
            command=module["command"],
            height=70,
            corner_radius=12,
            fg_color=fg_color,
            hover_color=hover_color,
            border_width=0,
            font=ctk.CTkFont("Helvetica", 13, "bold"),
            text_color="white",
            anchor="w"
        )
        btn.pack(fill="x", padx=16, pady=6)
    
    def _create_metrics_dashboard(self, parent):
        """Panel de métricas rápidas en tiempo real"""
        # Header
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 12))
        
        ctk.CTkLabel(header,
                    text="📊 Métricas del Sistema",
                    font=ctk.CTkFont("Helvetica", 16, "bold"),
                    text_color=("#1E293B", "#F1F5F9")).pack(side="left")
        
        # Contenedor de métricas con grid para evitar conflictos
        metrics_container = ctk.CTkFrame(parent, fg_color="transparent")
        metrics_container.pack(fill="x", padx=20, pady=(0, 16))
        
        # Configurar columnas del grid
        for i in range(5):
            metrics_container.grid_columnconfigure(i, weight=1)
        
        # Métricas simuladas (en producción conectar con datos reales)
        metrics = [
            {"label": "OEE Promedio", "value": "87.5%", "color": "#10B981", "trend": "↗"},
            {"label": "Máquinas Activas", "value": "3/4", "color": "#3B82F6", "trend": "→"},
            {"label": "Órdenes Activas", "value": "12", "color": "#F59E0B", "trend": "↗"},
            {"label": "Inventario", "value": "15,234", "color": "#8B5CF6", "trend": "↘"},
            {"label": "Producción Hoy", "value": "2,847", "color": "#EF4444", "trend": "↗"}
        ]
        
        for i, metric in enumerate(metrics):
            self._create_metric_tile(metrics_container, metric, i)
    
    def _create_metric_tile(self, parent, metric, index):
        """Crea una baldosa de métrica individual usando grid"""
        tile = ctk.CTkFrame(parent, corner_radius=12, fg_color=metric["color"])
        tile.grid(row=0, column=index, padx=4, pady=0, sticky="ew")
        
        # Valor principal
        ctk.CTkLabel(tile,
                    text=metric["value"],
                    font=ctk.CTkFont("Helvetica", 20, "bold"),
                    text_color="white").pack(pady=(12, 4))
        
        # Label y tendencia en una sola línea
        ctk.CTkLabel(tile,
                    text=f"{metric['label']} {metric['trend']}",
                    font=ctk.CTkFont("Helvetica", 10),
                    text_color="white").pack(pady=(0, 12))
    
    def _create_footer(self, parent):
        """Footer con información del sistema"""
        footer = ctk.CTkFrame(parent, corner_radius=12, height=50,
                            fg_color=("#F1F5F9", "#374151"))
        footer.pack(fill="x", pady=(24, 0))
        footer.pack_propagate(False)
        
        # Información del sistema
        ctk.CTkLabel(footer,
                    text="MEFRUP MLS v2.1.0 | Sistema de Monitoreo y Producción | ©2024 MEFRUP Technologies",
                    font=ctk.CTkFont("Helvetica", 11),
                    text_color=("#64748B", "#9CA3AF")).pack(expand=True)
    
    def _darken_color(self, hex_color):
        """Oscurece un color hex para efecto hover"""
        # Función simple para oscurecer colores
        color_map = {
            "#3B82F6": "#2563EB",
            "#10B981": "#059669", 
            "#F59E0B": "#D97706",
            "#8B5CF6": "#7C3AED",
            "#EF4444": "#DC2626"
        }
        return color_map.get(hex_color, hex_color)
