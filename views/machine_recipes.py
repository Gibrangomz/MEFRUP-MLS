from .base import *

class MachineRecipesView(ctk.CTkFrame):
    """Panel vacío para gestionar recetas por máquina."""
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#0e1117"))
        header.pack(fill="x", side="top")
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=16, pady=12)
        ctk.CTkButton(
            left, text="← Menú", command=self.app.go_menu, width=110, corner_radius=10,
            fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB"
        ).pack(side="left", padx=(0, 10))
        title_box = ctk.CTkFrame(left, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="Machine Recipes", font=ctk.CTkFont("Helvetica", 22, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            title_box, text="En construcción", text_color=("#6b7280", "#9CA3AF"), font=ctk.CTkFont(size=12)
        ).pack(anchor="w")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
