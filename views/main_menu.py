from .base import *

class MainMenu(ctk.CTkFrame):

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        box = ctk.CTkFrame(self, corner_radius=20)
        box.pack(expand=True, fill="both", padx=40, pady=40)

        try:
            img = Image.open(LOGO_PATH)
            logo = ctk.CTkImage(light_image=img, dark_image=img, size=(240, 96))
            ctk.CTkLabel(box, image=logo, text="").pack(pady=(30, 10))
            self.logo = logo
        except:
            ctk.CTkLabel(box, text="MEFRUP", font=ctk.CTkFont("Helvetica", 36, "bold"))\
                .pack(pady=(50, 10))

        ctk.CTkLabel(box, text="Mefrup MLS", font=ctk.CTkFont("Helvetica", 28, "bold"))\
            .pack(pady=(0, 6))
        ctk.CTkLabel(box, text="Sistema de Monitoreo y Producción",
                      font=ctk.CTkFont("Helvetica", 14)).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(box, fg_color="transparent")
        btn_frame.pack(expand=True, fill="both")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        btns = [
            {"text": "Tablero en vivo (Área Inyección)", "command": app.go_dashboard, "height": 48},
            {"text": "OEE y Registro de Producción", "command": app.go_oee_select_machine, "height": 48},
            {"text": "Molde/Partes", "command": app.go_moldes_partes, "height": 44,
             "fg_color": "#E5E7EB", "text_color": "#111", "hover_color": "#D1D5DB"},
            {"text": "Recetas", "command": app.go_recetas, "height": 44},
            {"text": "Planificación + Milestones", "command": app.go_planning, "height": 44},
            {"text": "Tablero de Órdenes (Progreso)", "command": app.go_orders_board, "height": 44},
            {"text": "Reportes de Producción", "command": app.go_reports, "height": 44},
            {"text": "Inventario", "command": app.go_inventory, "height": 44},
            {"text": "Salida de Piezas (Embarques)", "command": app.go_shipments, "height": 44},
        ]

        for i, kwargs in enumerate(btns):
            r, c = divmod(i, 2)
            ctk.CTkButton(btn_frame, corner_radius=14, **kwargs)\
                .grid(row=r, column=c, padx=8, pady=8, sticky="ew")

# ---------- App ----------
