from .base import *

class MachineChooser(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app=app
        box=ctk.CTkFrame(self, corner_radius=20); box.pack(expand=True, fill="both", padx=40, pady=40)
        ctk.CTkLabel(box, text="Selecciona máquina", font=ctk.CTkFont("Helvetica",26,"bold")).pack(pady=(18,8))
        grid=ctk.CTkFrame(box, fg_color="transparent"); grid.pack(pady=10)
        for i, m in enumerate(MACHINES):
            ctk.CTkButton(grid, text=m["name"], height=56, corner_radius=16,
                          command=lambda mm=m: self.app.go_oee(mm)).grid(row=i, column=0, pady=8, padx=8, sticky="ew")
        ctk.CTkButton(box, text="← Volver al menú", height=44, corner_radius=12,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                      command=self.app.go_menu).pack(pady=(18,0))

