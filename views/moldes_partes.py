from .base import *  # ctk, tk, ttk, messagebox, filedialog, leer_csv_dict, RECIPES_CSV
import csv
from statistics import mean


class MoldesPartesView(ctk.CTkFrame):
    """
    Gestor PRO de Moldes/Partes/Ciclos
    - UI tipo dashboard: header con subtítulo, toolbar compacta, KPIs en cards
    - Filtro con CTkSegmentedButton (Todas / Activas / Inactivas) + búsqueda en vivo
    - Tabla con zebra, ordenación con flechas, fila inactiva atenuada
    - Formulario minimalista con validación y atajos: Ctrl+N / Ctrl+S / Supr
    - Importar / Exportar CSV
    """
    FIELDS = [
        "molde_id", "parte", "ciclo_ideal_s",
        "cavidades", "cavidades_habilitadas",
        "scrap_esperado_pct", "activo",
    ]

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._all_rows: list[dict] = []
        self._sort_state: dict[str, bool] = {}  # {"col": reverse_bool}
        self._kpi = {"total": 0, "act": 0, "avg_ciclo": 0.0, "avg_scrap": 0.0}
        self._build()
        self._load()

    # ===================== UI =====================
    def _build(self):
        # ===== Header =====
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
        ctk.CTkLabel(title_box, text="Molde/Partes", font=ctk.CTkFont("Helvetica", 22, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            title_box, text="Catálogo de moldes/partes/ciclos para referencia de OEE y planeación",
            text_color=("#6b7280", "#9CA3AF"), font=ctk.CTkFont(size=12)
        ).pack(anchor="w")

        # ===== Toolbar =====
        tools = ctk.CTkFrame(self, fg_color=("white", "#0e1117"))
        tools.pack(fill="x", padx=16, pady=(6, 0))

        self.search_var = tk.StringVar()
        self.act_filter_var = tk.StringVar(value="Todas")

        ctk.CTkEntry(
            tools, placeholder_text="Buscar por Molde o #Parte…",
            textvariable=self.search_var, width=320
        ).pack(side="left", padx=(0, 10))

        self.seg = ctk.CTkSegmentedButton(
            tools, values=["Todas", "Activas", "Inactivas"],
            variable=self.act_filter_var, command=lambda *_: self._refresh_table()
        )
        self.seg.pack(side="left", padx=(0, 10))

        # Botonera compacta (iconos)
        ctk.CTkButton(tools, text="⟳", width=40, command=self._load,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=6)
        ctk.CTkButton(tools, text="⤴", width=40, command=self._import_csv, fg_color="#1d4ed8").pack(side="left", padx=6)
        ctk.CTkButton(tools, text="⤵", width=40, command=self._export_csv, fg_color="#1d4ed8").pack(side="left", padx=6)
        ctk.CTkLabel(tools, text="", width=8).pack(side="left", padx=4)
        ctk.CTkButton(tools, text="+ Nuevo", command=self._new, corner_radius=10).pack(side="left", padx=4)
        ctk.CTkButton(tools, text="💾 Guardar", command=self._save, corner_radius=10, fg_color="#0ea5e9").pack(side="left", padx=4)
        ctk.CTkButton(tools, text="⎘ Duplicar", command=self._duplicate).pack(side="left", padx=4)
        # Eliminar SOLO emoji:
        ctk.CTkButton(tools, text="🗑", width=40, fg_color="#ef4444", hover_color="#dc2626",
                      command=self._delete).pack(side="left", padx=6)

        # ===== KPIs (cards) =====
        kpis = ctk.CTkFrame(self, fg_color="transparent")
        kpis.pack(fill="x", padx=16, pady=(12, 0))

        def card(parent, title, bg, name_attr):
            c = ctk.CTkFrame(parent, corner_radius=14, fg_color=bg)
            c.pack(side="left", padx=8, ipadx=12, ipady=10, fill="x", expand=True)
            ctk.CTkLabel(c, text=title, text_color=("black", "white")).pack(anchor="w")
            lbl = ctk.CTkLabel(c, text="—", font=ctk.CTkFont(size=20, weight="bold"),
                               text_color=("black", "white"))
            lbl.pack(anchor="w")
            setattr(self, name_attr, lbl)

        if ctk.get_appearance_mode() == "Dark":
            card(kpis, "Total moldes", "#111827", "kpi_total_lbl")
            card(kpis, "Activas", "#064e3b", "kpi_act_lbl")
            card(kpis, "Ciclo prom (s)", "#1f2937", "kpi_ciclo_lbl")
            card(kpis, "Scrap prom (%)", "#1f2937", "kpi_scrap_lbl")
        else:
            card(kpis, "Total moldes", "#F3F4F6", "kpi_total_lbl")
            card(kpis, "Activas", "#DCFCE7", "kpi_act_lbl")
            card(kpis, "Ciclo prom (s)", "#F3F4F6", "kpi_ciclo_lbl")
            card(kpis, "Scrap prom (%)", "#FEF9C3", "kpi_scrap_lbl")

        # ===== Split =====
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=16)

        # -------- Tabla (izquierda) --------
        table_card = ctk.CTkFrame(body, corner_radius=18)
        table_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        head = ctk.CTkFrame(table_card, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(12, 0))
        ctk.CTkLabel(head, text="Listado", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self.lbl_tot = ctk.CTkLabel(head, text="—", text_color=("#6b7280", "#9CA3AF"))
        self.lbl_tot.pack(side="right")

        ctk.CTkFrame(table_card, height=1, fg_color=("#E5E7EB", "#2B2B2B")).pack(fill="x", padx=12, pady=(6, 8))

        cols = tuple(self.FIELDS)
        tree_wrap = ctk.CTkFrame(table_card, fg_color="transparent")
        tree_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.tree = ttk.Treeview(tree_wrap, columns=cols, show="headings",
                                 height=18, selectmode="browse")
        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)

        # Estilo tabla
        style = ttk.Style(self)
        style.configure("MoldesPartes.Treeview", rowheight=26, font=("Helvetica", 10))
        style.configure("MoldesPartes.Treeview.Heading", font=("Helvetica", 10, "bold"))
        # Mejor foco selección
        style.map("MoldesPartes.Treeview", background=[("selected", "#2563eb")], foreground=[("selected", "white")])
        self.tree.configure(style="MoldesPartes.Treeview")

        headers = [
            ("molde_id", "Molde", 130),
            ("parte", "# Parte", 180),
            ("ciclo_ideal_s", "Ciclo (s)", 90),
            ("cavidades", "Cav.", 70),
            ("cavidades_habilitadas", "Cav. ON", 90),
            ("scrap_esperado_pct", "Scrap %", 90),
            ("activo", "Estado", 100),
        ]
        for key, txt, w in headers:
            self.tree.heading(key, text=txt, command=lambda c=key: self._sort_by(c))
            self.tree.column(key, width=w, anchor="center")

        # Colores zebra / inactiva
        if ctk.get_appearance_mode() == "Dark":
            even_bg, odd_bg, inactive_fg = "#0b1220", "#0f172a", "#fca5a5"
        else:
            even_bg, odd_bg, inactive_fg = "#F9FAFB", "#FFFFFF", "#B91C1C"
        self.tree.tag_configure("even", background=even_bg)
        self.tree.tag_configure("odd", background=odd_bg)
        self.tree.tag_configure("inactive", foreground=inactive_fg)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._on_select())
        self.tree.bind("<Delete>", lambda e: self._delete())

        # -------- Formulario (derecha) --------
        form = ctk.CTkFrame(body, corner_radius=18)
        form.pack(side="left", fill="y", padx=(10, 0))

        ctk.CTkLabel(form, text="Editar molde/parte", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(12, 0))
        ctk.CTkFrame(form, height=1, fg_color=("#E5E7EB", "#2B2B2B")).pack(fill="x", padx=12, pady=(6, 8))

        def frow(lbl, var, width=190, typ="entry", ph=""):
            r = ctk.CTkFrame(form, fg_color="transparent"); r.pack(fill="x", padx=12, pady=5)
            ctk.CTkLabel(r, text=lbl, width=160, anchor="w").pack(side="left")
            if typ == "entry":
                e = ctk.CTkEntry(r, width=width, textvariable=var, justify="center", placeholder_text=ph)
                e.pack(side="right"); return e
            elif typ == "switch":
                sw = ctk.CTkSwitch(r, text="", variable=var, onvalue="1", offvalue="0")
                sw.pack(side="right"); return sw
            else:
                om = ctk.CTkOptionMenu(r, values=["1", "0"], variable=var)
                om.pack(side="right"); return om

        self.var_molde = tk.StringVar()
        self.var_parte = tk.StringVar()
        self.var_ciclo = tk.StringVar()
        self.var_cavs = tk.StringVar()
        self.var_cavs_on = tk.StringVar()
        self.var_scrap = tk.StringVar()
        self.var_activo = tk.StringVar(value="1")

        self.e_molde = frow("Molde ID", self.var_molde, ph="Ej. MLD-045")
        self.e_parte = frow("# Parte", self.var_parte, ph="Ej. 123-ABC")
        self.e_ciclo = frow("Ciclo ideal (s)", self.var_ciclo, ph="≥ 0.5")
        self.e_cavs = frow("Cavidades", self.var_cavs, ph="≥ 1")
        self.e_cavs_on = frow("Cavidades habilitadas", self.var_cavs_on, ph="≤ Cavidades")
        self.e_scrap = frow("Scrap esperado (%)", self.var_scrap, ph="0–100")
        self.sw_activo = frow("Activo", self.var_activo, typ="switch")

        ctk.CTkLabel(
            form, text="Tip: si dejas 'Cav. ON' vacío y escribes 'Cavidades', se copiará automáticamente.",
            wraplength=320, text_color=("#6b7280", "#9CA3AF")
        ).pack(anchor="w", padx=12, pady=(2, 8))

        fb = ctk.CTkFrame(form, fg_color="transparent"); fb.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkButton(fb, text="💾 Guardar (Ctrl+S)", command=self._save, fg_color="#0ea5e9").pack(side="left", padx=4)
        ctk.CTkButton(fb, text="+ Nuevo (Ctrl+N)", command=self._new).pack(side="left", padx=4)
        ctk.CTkButton(fb, text="⎘ Duplicar", command=self._duplicate).pack(side="left", padx=4)

        # Listeners
        self.search_var.trace_add("write", lambda *_: self._refresh_table())
        self.var_cavs.trace_add("write", lambda *_: self._auto_copy_cavs_on())

        # Atajos (sin bind_all)
        root = self.winfo_toplevel()
        try:
            root.bind("<Control-s>", lambda e: self._save(), add="+")
            root.bind("<Control-n>", lambda e: self._new(), add="+")
            root.bind("<Delete>", lambda e: self._delete(), add="+")
        except Exception:
            self.bind("<Control-s>", lambda e: self._save())
            self.bind("<Control-n>", lambda e: self._new())
            self.bind("<Delete>", lambda e: self._delete())

    # ===================== Data IO =====================
    def _load(self):
        try:
            self._all_rows = list(leer_csv_dict(RECIPES_CSV))
        except Exception:
            self._all_rows = []
        self._refresh_table()
        try:
            self.app._refresh_moldes_from_recipes()
        except Exception:
            pass

    def _save_to_disk(self):
        with open(RECIPES_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.FIELDS)
            w.writeheader(); w.writerows(self._all_rows)
        try:
            self.app._refresh_moldes_from_recipes()
            self.app._on_molde_change(); self.app._update_now()
        except Exception:
            pass

    def _export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path: return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.FIELDS)
            w.writeheader(); w.writerows(self._all_rows)
        messagebox.showinfo("Exportar", "Se exportaron los moldes/partes.")

    def _import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path: return
        try:
            rows = []
            with open(path, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    rows.append({k: (r.get(k, "") or "").strip() for k in self.FIELDS})
            if not rows:
                messagebox.showwarning("Importar", "El archivo está vacío."); return
            if not messagebox.askyesno("Importar", "¿Reemplazar todos los moldes/partes por el archivo seleccionado?"):
                return
            self._all_rows = rows
            self._save_to_disk()
            self._refresh_table()
            messagebox.showinfo("Importar", "Moldes/partes importados.")
        except Exception as e:
            messagebox.showerror("Importar", f"No se pudo importar:\n{e}")

    # ===================== Tabla =====================
    def _refresh_table(self):
        q = (self.search_var.get() or "").strip().lower()
        mode = self.act_filter_var.get()

        def match(r: dict) -> bool:
            if q and (q not in r.get("molde_id", "").lower()) and (q not in r.get("parte", "").lower()):
                return False
            if mode == "Activas" and str(r.get("activo", "1")).strip() != "1":
                return False
            if mode == "Inactivas" and str(r.get("activo", "1")).strip() == "1":
                return False
            return True

        rows = [r for r in self._all_rows if match(r)]

        # ordenar si procede
        if self._sort_state:
            col, rev = next(iter(self._sort_state.items()))
            rows.sort(key=lambda r: self._sort_key(col, r), reverse=rev)

        # limpiar e insertar
        for i in self.tree.get_children():
            self.tree.delete(i)

        total = len(rows)
        act = sum(1 for r in rows if str(r.get("activo", "1")).strip() == "1")

        avg_ciclo = self._avg([self._to_float(r.get("ciclo_ideal_s")) for r in rows])
        avg_scrap = self._avg([self._to_float(r.get("scrap_esperado_pct")) for r in rows])
        self._kpi.update(total=total, act=act, avg_ciclo=avg_ciclo, avg_scrap=avg_scrap)
        self._render_kpis()

        for idx, r in enumerate(rows):
            tags = ("even",) if idx % 2 == 0 else ("odd",)
            activo = str(r.get("activo", "1")).strip() == "1"
            if not activo:
                tags = tags + ("inactive",)
                estado = "● Inactivo"
            else:
                estado = "● Activo"
            vals = (
                r.get("molde_id", ""), r.get("parte", ""),
                r.get("ciclo_ideal_s", ""), r.get("cavidades", ""),
                r.get("cavidades_habilitadas", ""), r.get("scrap_esperado_pct", ""),
                estado
            )
            self.tree.insert("", "end", values=vals, tags=tags)

        self.lbl_tot.configure(text=f"Moldes: {total}  •  Activos: {act}  •  Inactivos: {total - act}")
        self._refresh_headers()

    def _render_kpis(self):
        self.kpi_total_lbl.configure(text=f"{self._kpi['total']}")
        self.kpi_act_lbl.configure(text=f"{self._kpi['act']}")
        self.kpi_ciclo_lbl.configure(text=f"{self._kpi['avg_ciclo']:.3f}")
        self.kpi_scrap_lbl.configure(text=f"{self._kpi['avg_scrap']:.2f}%")

    def _sort_key(self, col, r):
        v = (r.get(col, "") or "").strip()
        if col == "activo":
            v = (r.get("activo", "") or "").strip()
        try:
            if col in ("ciclo_ideal_s", "cavidades", "cavidades_habilitadas", "scrap_esperado_pct", "activo"):
                return float(v or 0)
        except Exception:
            pass
        return v.lower()

    def _sort_by(self, col):
        self._sort_state = {col: not self._sort_state.get(col, False)}
        self._refresh_table()

    def _refresh_headers(self):
        arrows = {True: " ▼", False: " ▲"}
        active = next(iter(self._sort_state.keys()), None) if self._sort_state else None
        mapping = {
            "molde_id": "Molde",
            "parte": "# Parte",
            "ciclo_ideal_s": "Ciclo (s)",
            "cavidades": "Cav.",
            "cavidades_habilitadas": "Cav. ON",
            "scrap_esperado_pct": "Scrap %",
            "activo": "Estado",
        }
        for col, base in mapping.items():
            label = base + (arrows[self._sort_state[col]] if active == col else "")
            self.tree.heading(col, text=label, command=lambda c=col: self._sort_by(c))

    # ===================== Formulario =====================
    def _on_select(self, *_):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0], "values")
        molde = vals[0]
        row = next((r for r in self._all_rows if r.get("molde_id", "") == molde), None)
        activo_real = (row or {}).get("activo", "1")
        (self.var_molde.set(vals[0]), self.var_parte.set(vals[1]), self.var_ciclo.set(vals[2]),
         self.var_cavs.set(vals[3]), self.var_cavs_on.set(vals[4]), self.var_scrap.set(vals[5]),
         self.var_activo.set(activo_real))

    def _new(self):
        self.var_molde.set(""); self.var_parte.set(""); self.var_ciclo.set("")
        self.var_cavs.set(""); self.var_cavs_on.set(""); self.var_scrap.set("")
        self.var_activo.set("1"); self.e_molde.focus_set()

    def _duplicate(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Duplicar", "Selecciona un molde/parte para duplicar."); return
        vals = self.tree.item(sel[0], "values")
        self.var_molde.set((vals[0] or "") + "-copy")
        self.var_parte.set(vals[1]); self.var_ciclo.set(vals[2])
        self.var_cavs.set(vals[3]); self.var_cavs_on.set(vals[4])
        self.var_scrap.set(vals[5]); self.var_activo.set("1")

    def _auto_copy_cavs_on(self):
        if self.var_cavs.get().strip() and not self.var_cavs_on.get().strip():
            self.var_cavs_on.set(self.var_cavs.get().strip())

    def _validate(self):
        errs = []
        m = self.var_molde.get().strip()
        sel = self.tree.selection()
        selected_id = self.tree.item(sel[0], "values")[0] if sel else None
        editing_same = bool(selected_id) and (selected_id == m)

        exists = any((r.get("molde_id", "").strip() == m) for r in self._all_rows)
        if not m:
            errs.append("Molde ID es obligatorio.")
        elif exists and not editing_same:
            errs.append(f"Ya existe un molde/parte con Molde ID '{m}'.")

        def num(name, val, minv=None, maxv=None, as_int=False):
            s = (val or "").strip()
            if s == "":
                errs.append(f"{name} es obligatorio."); return None
            try:
                v = int(s) if as_int else float(s)
            except Exception:
                errs.append(f"{name} debe ser numérico."); return None
            if minv is not None and v < minv: errs.append(f"{name} debe ser ≥ {minv}.")
            if maxv is not None and v > maxv: errs.append(f"{name} debe ser ≤ {maxv}.")
            return v

        ciclo = num("Ciclo ideal (s)", self.var_ciclo.get(), minv=0.5)
        cavs = num("Cavidades", self.var_cavs.get(), minv=1, as_int=True)
        cavs_on = num("Cavidades habilitadas", self.var_cavs_on.get(), minv=1, as_int=True)
        scrap = num("Scrap esperado (%)", self.var_scrap.get(), minv=0, maxv=100)
        if cavs is not None and cavs_on is not None and cavs_on > cavs:
            errs.append("Cavidades habilitadas no puede exceder Cavidades.")

        activo = "1" if (self.var_activo.get() or "1") == "1" else "0"

        return errs, {
            "molde_id": m,
            "parte": self.var_parte.get().strip(),
            "ciclo_ideal_s": f"{float(ciclo):.3f}" if ciclo is not None else "",
            "cavidades": str(cavs if cavs is not None else ""),
            "cavidades_habilitadas": str(cavs_on if cavs_on is not None else ""),
            "scrap_esperado_pct": f"{float(scrap):.2f}" if scrap is not None else "",
            "activo": activo
        }

    def _save(self):
        errs, row = self._validate()
        if errs:
            messagebox.showwarning("Validación", "\n".join(errs)); return
        sel = self.tree.selection()
        old_id = self.tree.item(sel[0], "values")[0] if sel else None
        if old_id:
            idx = next((i for i, r in enumerate(self._all_rows) if r.get("molde_id", "") == old_id), None)
            if idx is not None: self._all_rows[idx] = row
            else: self._upsert_by_id(row)
        else:
            self._upsert_by_id(row)
        self._save_to_disk(); self._refresh_table()
        messagebox.showinfo("Molde/Parte", "Registro guardado.")

    def _upsert_by_id(self, row: dict):
        for r in self._all_rows:
            if r.get("molde_id", "").strip() == row["molde_id"]:
                r.update(row); return
        self._all_rows.append(row)

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Eliminar", "Selecciona un molde/parte."); return
        molde = self.tree.item(sel[0], "values")[0]
        if not messagebox.askyesno("Eliminar", f"¿Eliminar el registro del molde {molde}?"):
            return
        self._all_rows = [r for r in self._all_rows if r.get("molde_id", "") != molde]
        self._save_to_disk(); self._refresh_table()

    # ===================== Utils =====================
    def _to_float(self, s):
        try: return float((s or "").strip())
        except Exception: return None

    def _avg(self, arr):
        arr = [x for x in arr if isinstance(x, (int, float))]
        return round(mean(arr), 3) if arr else 0.0
