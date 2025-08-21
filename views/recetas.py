from .base import *

class RecetasView(ctk.CTkFrame):
    """Panel vacío de recetas"""
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text="Recetas", font=ctk.CTkFont("Helvetica", 22, "bold")).pack(pady=20)
