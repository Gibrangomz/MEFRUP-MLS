from .base import *

class CalculoView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#1c1c1e"))
        header.pack(fill="x", side="top")
        ctk.CTkButton(
            header,
            text="\u2190 Men\u00fa",
            command=self.app.go_menu,
            width=110,
            corner_radius=10,
            fg_color="#E5E7EB",
            text_color="#111",
            hover_color="#D1D5DB",
        ).pack(side="left", padx=(16, 10), pady=10)
        ctk.CTkLabel(
            header,
            text="Calculo",
            font=ctk.CTkFont("Helvetica", 20, "bold"),
        ).pack(side="left", pady=10)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(expand=True, fill="both", padx=16, pady=16)
        ctk.CTkLabel(body, text="Bienvenido al panel de c\u00e1lculo").pack(pady=20)
