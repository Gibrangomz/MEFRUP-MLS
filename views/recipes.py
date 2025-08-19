from .base import *

class RecipesView(ctk.CTkFrame):
    """Gestor de Recetas (molde/parte/ciclo...)"""
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app=app
        self._build()

    def _build(self):
        header=ctk.CTkFrame(self, corner_radius=0, fg_color=("white","#111111"))
        header.pack(fill="x", side="top")
        left=ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", command=self.app.go_menu, width=100, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text="Recetas — Moldes/Partes", font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")

        body=ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=16, pady=16)
        table_card=ctk.CTkFrame(body, corner_radius=18)
        table_card.pack(side="left", fill="both", expand=True, padx=(0,10))
        ctk.CTkLabel(table_card, text="Recetas", font=ctk.CTkFont("Helvetica",13,"bold")).pack(anchor="w", padx=8, pady=(8,0))
        ctk.CTkFrame(table_card, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=8, pady=(6,8))

        cols=("molde_id","parte","ciclo_ideal_s","cavidades","cavidades_habilitadas","scrap_esperado_pct","activo")
        self.tree=ttk.Treeview(table_card, columns=cols, show="headings", height=12)
        heads=[("molde_id","Molde",90),("parte","# Parte",140),("ciclo_ideal_s","Ciclo (s)",90),
               ("cavidades","Cav.",70),("cavidades_habilitadas","Cav. ON",80),
               ("scrap_esperado_pct","Scrap %",80),("activo","Activo",70)]
        for key,txt,w in heads:
            self.tree.heading(key, text=txt); self.tree.column(key, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        btnbar=ctk.CTkFrame(table_card, fg_color="transparent"); btnbar.pack(fill="x", padx=8, pady=(0,10))
        ctk.CTkButton(btnbar, text="Nuevo", command=self._new).pack(side="left", padx=(0,8))
        ctk.CTkButton(btnbar, text="Guardar", command=self._save).pack(side="left", padx=8)
        ctk.CTkButton(btnbar, text="Eliminar", fg_color="#ef4444", hover_color="#dc2626", command=self._delete).pack(side="left", padx=8)
        ctk.CTkButton(btnbar, text="↻ Recargar", fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB", command=self._load).pack(side="left", padx=8)
        ctk.CTkButton(btnbar, text="Ir a OEE", command=self.app.go_oee_select_machine).pack(side="right")

        # Formulario
        form=ctk.CTkFrame(body, corner_radius=18)
        form.pack(side="left", fill="both", expand=False, padx=(10,0))
        ctk.CTkLabel(form, text="Editar receta", font=ctk.CTkFont("Helvetica",13,"bold")).pack(anchor="w", padx=8, pady=(8,0))
        ctk.CTkFrame(form, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=8, pady=(6,8))

        def frow(lbl, var, width=160, typ="entry"):
            r=ctk.CTkFrame(form, fg_color="transparent"); r.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(r, text=lbl).pack(side="left")
            if typ=="entry":
                e=ctk.CTkEntry(r, width=width, textvariable=var, justify="center")
                e.pack(side="right"); return e
            else:
                om=ctk.CTkOptionMenu(r, values=["0","1"], variable=var); om.pack(side="right"); return om

        self.var_molde = tk.StringVar()
        self.var_parte = tk.StringVar()
        self.var_ciclo = tk.StringVar()
        self.var_cavs  = tk.StringVar()
        self.var_cavs_on = tk.StringVar()
        self.var_scrap = tk.StringVar()
        self.var_activo= tk.StringVar(value="1")

        frow("Molde ID", self.var_molde)
        frow("# Parte", self.var_parte)
        frow("Ciclo ideal (s)", self.var_ciclo)
        frow("Cavidades", self.var_cavs)
        frow("Cavidades habilitadas", self.var_cavs_on)
        frow("Scrap esperado (%)", self.var_scrap)
        frow("Activo (1/0)", self.var_activo, typ="om")

        self._load()

    def _load(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in leer_csv_dict(RECIPES_CSV):
            self.tree.insert("", "end", values=(r["molde_id"], r["parte"], r["ciclo_ideal_s"],
                                                r["cavidades"], r["cavidades_habilitadas"],
                                                r["scrap_esperado_pct"], r["activo"]))
        # refresca catálogo de moldes en App
        self.app._refresh_moldes_from_recipes()

    def _on_select(self, *_):
        sel=self.tree.selection()
        if not sel: return
        vals=self.tree.item(sel[0],"values")
        (self.var_molde.set(vals[0]), self.var_parte.set(vals[1]), self.var_ciclo.set(vals[2]),
         self.var_cavs.set(vals[3]), self.var_cavs_on.set(vals[4]), self.var_scrap.set(vals[5]),
         self.var_activo.set(vals[6]))

    def _new(self):
        self.var_molde.set(""); self.var_parte.set(""); self.var_ciclo.set("")
        self.var_cavs.set(""); self.var_cavs_on.set(""); self.var_scrap.set(""); self.var_activo.set("1")

    def _save(self):
        m=self.var_molde.get().strip()
        if not (m and self.var_ciclo.get().strip()):
            messagebox.showwarning("Faltan datos","Molde y ciclo ideal son obligatorios."); return
        rows=leer_csv_dict(RECIPES_CSV); found=False
        for r in rows:
            if r["molde_id"]==m:
                r.update({
                    "parte": self.var_parte.get().strip(),
                    "ciclo_ideal_s": self.var_ciclo.get().strip(),
                    "cavidades": self.var_cavs.get().strip(),
                    "cavidades_habilitadas": self.var_cavs_on.get().strip(),
                    "scrap_esperado_pct": self.var_scrap.get().strip(),
                    "activo": self.var_activo.get().strip() or "1"
                })
                found=True; break
        if not found:
            rows.append({
                "molde_id": m,
                "parte": self.var_parte.get().strip(),
                "ciclo_ideal_s": self.var_ciclo.get().strip(),
                "cavidades": self.var_cavs.get().strip(),
                "cavidades_habilitadas": self.var_cavs_on.get().strip(),
                "scrap_esperado_pct": self.var_scrap.get().strip(),
                "activo": self.var_activo.get().strip() or "1"
            })
        with open(RECIPES_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["molde_id","parte","ciclo_ideal_s",
                                            "cavidades","cavidades_habilitadas","scrap_esperado_pct","activo"])
            w.writeheader(); w.writerows(rows)
        self._load()
        messagebox.showinfo("Recetas","Receta guardada.")
        self.app._refresh_moldes_from_recipes()
        try:
            self.app._on_molde_change(); self.app._update_now()
        except: pass

    def _delete(self):
        sel=self.tree.selection()
        if not sel: return
        molde = self.tree.item(sel[0],"values")[0]
        if not messagebox.askyesno("Eliminar","¿Eliminar la receta del molde "+str(molde)+"?"): return
        rows=[r for r in leer_csv_dict(RECIPES_CSV) if r["molde_id"]!=molde]
        with open(RECIPES_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["molde_id","parte","ciclo_ideal_s",
                                            "cavidades","cavidades_habilitadas","scrap_esperado_pct","activo"])
            w.writeheader(); w.writerows(rows)
        self._load()
        self.app._refresh_moldes_from_recipes()
        try:
            self.app._on_molde_change(); self.app._update_now()
        except: pass

