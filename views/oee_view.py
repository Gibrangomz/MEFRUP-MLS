from .base import *

class OEEView(ctk.CTkFrame):
    def __init__(self, master, app, machine):
        super().__init__(master, fg_color="transparent")
        self.app=app
        self.machine=machine
        self._build_header()
        self._build_body()

    def _build_header(self):
        header=ctk.CTkFrame(self, corner_radius=0, fg_color=("white","#111111"))
        header.pack(fill="x", side="top")
        left=ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Elegir máquina", command=self.app.go_oee_select_machine, width=140, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text=f"OEE — Registro de Producción ({self.machine['name']})",
                     font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")

        right=ctk.CTkFrame(header, fg_color="transparent"); right.pack(side="right", padx=16, pady=10)
        self.clock_lbl = ctk.CTkLabel(right, text="", font=ctk.CTkFont("Helvetica",13))
        self.clock_lbl.pack(side="right", padx=(8,0))
        theme = ctk.CTkSegmentedButton(right, values=["Claro","Oscuro"],
                                       command=lambda v: ctk.set_appearance_mode("dark" if v=="Oscuro" else "light"))
        theme.set("Claro"); theme.pack(side="right", padx=10)
        try:
            img=Image.open(LOGO_PATH); logo=ctk.CTkImage(light_image=img, dark_image=img, size=(120,48))
            ctk.CTkLabel(right, image=logo, text="").pack(side="right", padx=10); self.logo=logo
        except: pass

    def _build_body(self):
        body=ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=16, pady=16)
        body.grid_rowconfigure(0, weight=1); body.grid_columnconfigure(0, weight=1); body.grid_columnconfigure(1, weight=1)

        # izquierda
        left=ctk.CTkScrollableFrame(body, corner_radius=18); left.grid(row=0, column=0, sticky="nsew", padx=(0,10))

        # Fecha
        sec=self._sec(left,"Fecha"); sec.pack(fill="x", padx=14, pady=(14,8))
        row=ctk.CTkFrame(sec, fg_color="transparent"); row.pack(fill="x")
        ctk.CTkLabel(row, text="YYYY-MM-DD").pack(side="left")
        ctk.CTkEntry(row, width=140, textvariable=self.app.fecha_sel, justify="center").pack(side="left", padx=8)
        ctk.CTkButton(row, text="Usar", command=self.app._on_fecha_change).pack(side="left", padx=8)
        ctk.CTkButton(row, text="📅", width=40, command=self.app._open_calendar).pack(side="left", padx=6)
        self.lbl_dia=ctk.CTkLabel(sec, text="", font=ctk.CTkFont("Helvetica", 12, "bold")); self.lbl_dia.pack(anchor="w", pady=(6,0))
        self.app.lbl_dia=self.lbl_dia

        # Operador
        sec=self._sec(left,"Operador"); sec.pack(fill="x", padx=14, pady=8)
        op=ctk.CTkOptionMenu(sec, values=["Selecciona"]+[o.capitalize() for o in OPERADORES],
                             command=lambda v: self.app._set_operador(v.lower()) if v!="Selecciona" else None)
        op.set("Selecciona"); op.pack(fill="x", padx=4, pady=4)

        # Turno
        sec=self._sec(left,"Turno"); sec.pack(fill="x", padx=14, pady=8)
        tu=ctk.CTkOptionMenu(sec, values=["Selecciona","1","2","3"],
                             command=lambda v: self.app._set_turno(v) if v.isdigit() else None)
        tu.set("Selecciona"); tu.pack(fill="x", padx=4, pady=4)

        # Molde / Receta
        sec=self._sec(left,"Molde / Receta"); sec.pack(fill="x", padx=14, pady=8)
        valores_moldes = ["Selecciona"] + sorted([k for k in self.app.recipe_map.keys()])
        self.molde_menu = ctk.CTkOptionMenu(sec, values=valores_moldes)
        self.molde_menu.pack(fill="x", padx=4, pady=4)
        self.molde_menu.configure(command=lambda v: self.app._set_molde(v) if v.isdigit() else None)

        info = ctk.CTkFrame(sec, fg_color="transparent"); info.pack(fill="x", pady=(6,0))
        ctk.CTkLabel(info, text="Ciclo ideal (s):").grid(row=0, column=0, sticky="w", padx=(0,6))
        ctk.CTkLabel(info, textvariable=self.app.ciclo_s, font=ctk.CTkFont("Helvetica",12,"bold")).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(info, text="# Parte:").grid(row=1, column=0, sticky="w", padx=(0,6), pady=(4,0))
        self.lbl_parte = ctk.CTkLabel(info, text="", font=ctk.CTkFont("Helvetica",12,"bold"))
        self.lbl_parte.grid(row=1, column=1, sticky="w", pady=(4,0))
        ctk.CTkLabel(info, text="Cavidades (ON/Tot):").grid(row=2, column=0, sticky="w", padx=(0,6), pady=(4,0))
        self.lbl_cavs = ctk.CTkLabel(info, text="", font=ctk.CTkFont("Helvetica",12,"bold"))
        self.lbl_cavs.grid(row=2, column=1, sticky="w", pady=(4,0))
        self.app.lbl_parte = self.lbl_parte
        self.app.lbl_cavs  = self.lbl_cavs

        # Producción
        sec=self._sec(left,"Producción (turno)"); sec.pack(fill="x", padx=14, pady=8)
        self._counter(sec,"Total",self.app.total)
        self._counter(sec,"Scrap",self.app.scrap)
        actions=ctk.CTkFrame(sec, fg_color="transparent"); actions.pack(fill="x", pady=(10,0))
        self.btn_guardar=ctk.CTkButton(actions, text="Guardar (Ctrl+Enter)", corner_radius=12, command=self.app._guardar)
        self.btn_guardar.pack(side="left", expand=True, fill="x", padx=(0,6))
        ctk.CTkButton(actions, text="Reset contadores", corner_radius=12, fg_color="#E5E7EB",
                      text_color="#111", hover_color="#D1D5DB", command=self.app._reset_contadores)\
            .pack(side="left", expand=True, fill="x", padx=(6,0))
        self.app.btn_guardar=self.btn_guardar

        # Paros
        sec=self._sec(left,"Paros (cronómetro)"); sec.pack(fill="x", padx=14, pady=8)
        picker=ctk.CTkFrame(sec, fg_color="transparent"); picker.pack(fill="x", pady=(0,8))
        ctk.CTkLabel(picker, text="Motivo").pack(side="left")
        self.motivo_menu = ctk.CTkOptionMenu(picker, values=MOTIVOS_PARO); self.motivo_menu.pack(side="left", padx=8)
        ctk.CTkLabel(picker, text="Nota").pack(side="left", padx=(12,0))
        self.nota_entry=ctk.CTkEntry(picker, width=220, placeholder_text="opcional"); self.nota_entry.pack(side="left", padx=8)

        r1=ctk.CTkFrame(sec, fg_color="transparent"); r1.pack(fill="x", pady=(2,2))
        ctk.CTkLabel(r1, text="Paro actual").pack(side="left")
        self.lbl_paro_actual=ctk.CTkLabel(r1, text="00:00:00", font=ctk.CTkFont("Helvetica",16,"bold")); self.lbl_paro_actual.pack(side="right")

        r2=ctk.CTkFrame(sec, fg_color="transparent"); r2.pack(fill="x", pady=(2,8))
        ctk.CTkLabel(r2, text="Paro acumulado (turno)").pack(side="left")
        self.lbl_paro_acum=ctk.CTkLabel(r2, text="00:00:00", font=ctk.CTkFont("Helvetica",16,"bold")); self.lbl_paro_acum.pack(side="right")

        rbtn=ctk.CTkFrame(sec, fg_color="transparent"); rbtn.pack(fill="x", pady=(0,8))
        self.btn_toggle_paro=ctk.CTkButton(rbtn, text="Iniciar paro", height=44, corner_radius=14,
                                           command=self.app.toggle_paro, fg_color="#ef4444", hover_color="#dc2626")
        self.btn_toggle_paro.pack(side="left", expand=True, fill="x", padx=(0,8))
        ctk.CTkButton(rbtn, text="Reset paros", height=44, corner_radius=14, fg_color="#E5E7EB",
                      text_color="#111", hover_color="#D1D5DB", command=self.app.reset_paros)\
            .pack(side="left", expand=True, fill="x", padx=(8,0))

        # bitácora
        table_card=ctk.CTkFrame(sec, corner_radius=10); table_card.pack(fill="both", expand=True, pady=(10,0))
        cols=("inicio","fin","motivo","nota","dur_min")
        self.tree=ttk.Treeview(table_card, columns=cols, show="headings", height=6)
        for c, txt, w, anchor in [("inicio","Inicio",135,"center"),("fin","Fin",135,"center"),
                                  ("motivo","Motivo",160,"w"),("nota","Nota",220,"w"),("dur_min","Dur (min)",80,"e")]:
            self.tree.heading(c, text=txt); self.tree.column(c, width=w, anchor=anchor)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        style=ttk.Style(); style.configure("Treeview", rowheight=24, font=("Helvetica",10))
        style.configure("Treeview.Heading", font=("Helvetica",10,"bold"))

        # derecha
        right=ctk.CTkFrame(body, corner_radius=18); right.grid(row=0, column=1, sticky="nsew", padx=(10,0))
        sec=self._sec(right,"Metas"); sec.pack(fill="x", padx=14, pady=(14,8))
        r=ctk.CTkFrame(sec, fg_color="transparent"); r.pack(fill="x")
        ctk.CTkLabel(r, text="Meta planificada (pzs)").pack(side="left")
        self.meta_plan_val=ctk.CTkLabel(r, text="0", font=ctk.CTkFont("Helvetica",16,"bold")); self.meta_plan_val.pack(side="left", padx=6)
        r=ctk.CTkFrame(sec, fg_color="transparent"); r.pack(fill="x", pady=(6,0))
        ctk.CTkLabel(r, text="Meta operativa (pzs)").pack(side="left")
        self.meta_oper_val=ctk.CTkLabel(r, text="0", font=ctk.CTkFont("Helvetica",16,"bold")); self.meta_oper_val.pack(side="left", padx=6)

        bars=ctk.CTkFrame(right, fg_color="transparent"); bars.pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(bars, text="Disponibilidad").pack(anchor="w")
        self.pb_avail=ctk.CTkProgressBar(bars); self.pb_avail.set(0.0); self.pb_avail.pack(fill="x", pady=(2,8))
        ctk.CTkLabel(bars, text="Avance a meta (operativa)").pack(anchor="w")
        self.pb_meta=ctk.CTkProgressBar(bars); self.pb_meta.set(0.0); self.pb_meta.pack(fill="x", pady=(2,8))
        ctk.CTkLabel(bars, text="Calidad (Buenas / Total)").pack(anchor="w")
        self.pb_quality=ctk.CTkProgressBar(bars); self.pb_quality.set(0.0); self.pb_quality.pack(fill="x", pady=(2,8))

        sec=self._sec(right,"Tiempo real (turno)"); sec.pack(fill="x", padx=14, pady=8)
        self._metric(sec,"Availability (RT)",self.app.avail_rt)
        self._metric(sec,"Performance (RT)",self.app.perf_rt)
        self._metric(sec,"Quality (RT)",self.app.qual_rt)
        self._metric(sec,"OEE (RT)",self.app.oee_rt)

        sec=self._sec(right,"Día seleccionado (acumulado)"); sec.pack(fill="x", padx=14, pady=8)
        self._metric(sec,"Total día",self.app.tot_day)
        self._metric(sec,"Scrap día",self.app.scr_day)
        self._metric(sec,"Buenas día",self.app.buen_day)
        self._metric(sec,"Performance día",self.app.perf_day)
        self._metric(sec,"Quality día",self.app.qual_day)
        self._metric(sec,"OEE día",self.app.oee_day)
        ctk.CTkLabel(sec, textvariable=self.app.day_info, text_color=("#6b7280","#9CA3AF")).pack(anchor="w", pady=(6,0))

        sec=self._sec(right,"Histórico (promedio OEE día)"); sec.pack(fill="x", padx=14, pady=8)
        self._metric(sec,"OEE histórico",self.app.oee_hist)

        sec=self._sec(right,"Global (todos los registros)"); sec.pack(fill="x", padx=14, pady=(8,14))
        self._metric(sec,"Total global",self.app.glob_total)
        self._metric(sec,"Scrap global",self.app.glob_scrap)
        self._metric(sec,"Buenas global",self.app.glob_buenas)
        self._metric(sec,"Performance global",self.app.glob_perf)
        self._metric(sec,"Quality global",self.app.glob_qual)
        self._metric(sec,"OEE global",self.app.glob_oee)
        ctk.CTkLabel(sec, textvariable=self.app.glob_info, text_color=("#6b7280","#9CA3AF")).pack(anchor="w", pady=(6,0))

        # refs
        self.app.meta_plan_val=self.meta_plan_val; self.app.meta_oper_val=self.meta_oper_val
        self.app.pb_avail=self.pb_avail; self.app.pb_meta=self.pb_meta; self.app.pb_quality=self.pb_quality
        self.app.lbl_paro_actual=self.lbl_paro_actual; self.app.lbl_paro_acum=self.lbl_paro_acum
        self.app.btn_toggle_paro=self.btn_toggle_paro
        self.app.motivo_menu=self.motivo_menu; self.app.nota_entry=self.nota_entry; self.app.tree=self.tree
        self.app.molde_menu=self.molde_menu
        self.app._clock_label = self.clock_lbl

    # helpers UI
    def _sec(self, parent, title):
        card=ctk.CTkFrame(parent, corner_radius=16)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont("Helvetica",13,"bold")).pack(anchor="w", padx=8, pady=(8,0))
        ctk.CTkFrame(card, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=8, pady=(6,8))
        return card
    def _counter(self, parent, label, var):
        r=ctk.CTkFrame(parent, fg_color="transparent"); r.pack(fill="x", pady=6)
        ctk.CTkLabel(r, text=label).pack(side="left")
        e=ctk.CTkEntry(r, width=140, textvariable=var, justify="center"); e.pack(side="left", padx=8)
        ctk.CTkButton(r, text="-", width=44, height=40, command=lambda: self.app._nudge(var,-1), corner_radius=14).pack(side="left", padx=4)
        ctk.CTkButton(r, text="+", width=44, height=40, command=lambda: self.app._nudge(var,+1), corner_radius=14).pack(side="left", padx=4)
        e.bind("<FocusOut>", lambda ev: self.app._sanitize(var)); e.bind("<Return>", lambda ev: self.app._sanitize(var))
    def _metric(self, parent, label, var):
        r=ctk.CTkFrame(parent, fg_color="transparent"); r.pack(fill="x", pady=4)
        ctk.CTkLabel(r, text=label).pack(side="left")
        ctk.CTkLabel(r, textvariable=var, font=ctk.CTkFont("Helvetica",16,"bold")).pack(side="right")

# ===== TABLERO EN VIVO (mejorado) =====
