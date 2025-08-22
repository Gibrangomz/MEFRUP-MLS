# -*- coding: utf-8 -*-
# Recetas de Máquina (layout estilo SELOGICA)
from .base import *  # ctk, tk, ttk, messagebox, filedialog, BASE_DIR
import os, json, csv
from datetime import datetime

RECIPES_DIR = os.path.join(BASE_DIR, "machine_recipes")
HISTORY_CSV = os.path.join(RECIPES_DIR, "_history.csv")
os.makedirs(RECIPES_DIR, exist_ok=True)

# Ajusta si quieres poblar automáticamente desde tu hoja Excel
EXCEL_MAP = {
    "program": "B3", "mould_desig": "B4", "material": "B5",
    "date_of_entry": "E3", "cavities": "E4", "machine": "E5",
    "cycle_time_s": "E7", "injection_time_s": "E8", "holding_press_time_s": "E9",
    "rem_cooling_time_s": "E10", "dosage_time_s": "E11", "screw_stroke_mm": "E12",
    "mould_stroke_mm": "E13", "ejector_stroke_mm": "E14", "shot_weight_g": "E15",
    "plasticising_flow_kgh": "E16", "dosage_capacity_gs": "E17", "dosage_volume_ccm": "E18",
    "material_cushion_ccm": "E19", "max_inj_pressure_bar": "E20",
}

# --------- Helpers de disco ----------
def _safe_id(s: str) -> str:
    return str(s).replace("/", "_").replace("\\", "_").strip()

def _path_json(mold_id: str) -> str:
    return os.path.join(RECIPES_DIR, f"{_safe_id(mold_id)}.json")

def _load_json(mold_id: str) -> dict:
    p = _path_json(mold_id)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return {}

def _save_json(mold_id: str, data: dict):
    with open(_path_json(mold_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
#                         VIEW
# ============================================================
class MachineRecipesView(ctk.CTkFrame):
    """Panel de recetas de máquina con layout que replica tu SELOGICA."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.vars = {}          # id -> StringVar
        self.current_mold = ""

        self._build()

    # --------------------------- UI ---------------------------
    def _build(self):
        # Header
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#0e1117"))
        header.pack(fill="x", side="top")

        left = ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", width=110, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                      command=self.app.go_menu).pack(side="left", padx=(0, 10))
        title = ctk.CTkFrame(left, fg_color="transparent"); title.pack(side="left")
        ctk.CTkLabel(title, text="Recetas de Máquina", font=ctk.CTkFont("Helvetica", 22, "bold")).pack(anchor="w")
        ctk.CTkLabel(title, text="Layout estilo SELOGICA • Historial y motivo de cambio",
                     text_color=("#6b7280", "#9CA3AF")).pack(anchor="w")

        # Toolbar
        tools = ctk.CTkFrame(self, fg_color="transparent"); tools.pack(fill="x", padx=16, pady=(8, 0))
        opciones = ["— Selecciona —"] + list(getattr(self.app, "recipe_map", {}).keys())
        self.mold_var = tk.StringVar(value=opciones[0])
        self.mold_menu = ctk.CTkOptionMenu(tools, values=opciones, variable=self.mold_var, width=220,
                                           command=lambda *_: self._on_pick_mold())
        self.mold_menu.pack(side="left", padx=(0, 8))

        ctk.CTkButton(tools, text="📥 Importar Excel", command=self._import_excel).pack(side="left", padx=6)
        ctk.CTkButton(tools, text="🕓 Historial", command=self._open_history).pack(side="left", padx=6)

        right = ctk.CTkFrame(tools, fg_color="transparent"); right.pack(side="right")
        self.motivo_var = tk.StringVar()
        ctk.CTkEntry(right, width=420, textvariable=self.motivo_var,
                     placeholder_text="Motivo del cambio (obligatorio)").pack(side="left", padx=8)
        ctk.CTkButton(right, text="💾 Guardar", command=self._save).pack(side="left")
        ctk.CTkButton(right, text="🗑", fg_color="#ef4444", hover_color="#dc2626",
                      width=44, command=self._clear_all).pack(side="left", padx=(8, 0))

        # CONTENIDO con scroll
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # ---- Hoja: dos columnas principales ----
        sheet = ctk.CTkFrame(self.scroll, corner_radius=14, fg_color=("white", "#111827"))
        sheet.pack(fill="x", padx=2, pady=2)
        sheet.grid_columnconfigure(0, weight=3)   # columna izquierda (bloques)
        sheet.grid_columnconfigure(1, weight=2)   # columna derecha (Key data)

        # 1) Cabecera (izquierda arriba)
        hdr = self._card(sheet, "Parameter overview (Cabecera)", row=0, col=0)
        self._header_grid(hdr)

        # 2) Key data (derecha arriba)
        key = self._card(sheet, "Key data", row=0, col=1)
        self._keydata_table(key)

        # 3) Injection unit + Injection + Plasticizing + Holding pressure + Temperatures + Mould movements + Clamping
        blocks = self._card(sheet, "", row=1, col=0, col_span=2)
        self._full_left_side(blocks)

    # ------------- Builders de layout -------------
    def _card(self, parent, title, row=0, col=0, col_span=1):
        card = ctk.CTkFrame(parent, corner_radius=14, fg_color=("white", "#111827"))
        card.grid(row=row, column=col, columnspan=col_span, padx=8, pady=8, sticky="nsew")
        if title:
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont("Helvetica", 13, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
            ctk.CTkFrame(card, height=1, fg_color=("#E5E7EB", "#2B2B2B")).pack(fill="x", padx=10, pady=(6, 10))
        return card

    def _lbl(self, parent, text, **grid):
        l = ctk.CTkLabel(parent, text=text)
        l.grid(**grid)
        return l

    def _ent(self, parent, fid, w=110, justify="center", **grid):
        v = self.vars.setdefault(fid, tk.StringVar())
        e = ctk.CTkEntry(parent, textvariable=v, width=w, justify=justify)
        e.grid(**grid)
        return e

    # ------ Sección cabecera (Program / Mould desig. / Material vs Date/Cavities/Machine) ------
    def _header_grid(self, parent):
        g = ctk.CTkFrame(parent, fg_color="transparent"); g.pack(fill="x", padx=10, pady=10)
        for i in range(6): g.grid_columnconfigure(i, weight=1)

        # Primera fila
        self._lbl(g, "Program",               row=0, column=0, sticky="w", padx=4, pady=4)
        self._ent(g, "program",               row=0, column=1, sticky="ew", padx=4, pady=4)
        self._lbl(g, "Date of entry:",        row=0, column=2, sticky="w", padx=4, pady=4)
        self._ent(g, "date_of_entry",         row=0, column=3, sticky="ew", padx=4, pady=4)
        self._lbl(g, "Cavities",              row=0, column=4, sticky="w", padx=4, pady=4)
        self._ent(g, "cavities",              row=0, column=5, sticky="ew", padx=4, pady=4)

        # Segunda fila
        self._lbl(g, "Mould desig.",          row=1, column=0, sticky="w", padx=4, pady=4)
        self._ent(g, "mould_desig",           row=1, column=1, sticky="ew", padx=4, pady=4)
        self._lbl(g, "Machine",               row=1, column=2, sticky="w", padx=4, pady=4)
        self._ent(g, "machine",               row=1, column=3, sticky="ew", padx=4, pady=4)

        # Tercera fila
        self._lbl(g, "Material",              row=2, column=0, sticky="w", padx=4, pady=4)
        self._ent(g, "material",              row=2, column=1, sticky="ew", padx=4, pady=4)

    # ------ Key data (derecha) ------
    def _keydata_table(self, parent):
        grid = ctk.CTkFrame(parent, fg_color="transparent"); grid.pack(fill="x", padx=10, pady=10)
        for i in range(2): grid.grid_columnconfigure(i, weight=1)

        rows = [
            ("cycle_time_s",           "Cycle time [s]"),
            ("injection_time_s",       "Injection time [s]"),
            ("holding_press_time_s",   "Holding press. time [s]"),
            ("rem_cooling_time_s",     "Rem. cooling time [s]"),
            ("dosage_time_s",          "Dosage time [s]"),
            ("screw_stroke_mm",        "Screw stroke [mm]"),
            ("mould_stroke_mm",        "Mould stroke [mm]"),
            ("ejector_stroke_mm",      "Ejector stroke [mm]"),
            ("shot_weight_g",          "Shot weight [g]"),
            ("plasticising_flow_kgh",  "Plasticising flow [kg/h]"),
            ("dosage_capacity_gs",     "Dosage capacity [g/s]"),
            ("dosage_volume_ccm",      "Dosage volume [ccm]"),
            ("material_cushion_ccm",   "Material cushion [ccm]"),
            ("max_inj_pressure_bar",   "max. inj. pressure [bar]"),
        ]
        for r, (fid, label) in enumerate(rows):
            self._lbl(grid, label, row=r, column=0, sticky="w", padx=4, pady=4)
            self._ent(grid, fid, row=r, column=1, sticky="ew", padx=4, pady=4)

    # ------ Bloque izquierdo de tablas -------
    def _full_left_side(self, parent):
        # Subtítulo "Injection unit"
        ctk.CTkLabel(parent, text="Injection unit", font=ctk.CTkFont("Helvetica", 12, "bold")
                     ).pack(anchor="center", pady=(4, 0))

        inj_unit = ctk.CTkFrame(parent, fg_color="transparent"); inj_unit.pack(fill="x", padx=10, pady=(0, 8))
        inj_unit.grid_columnconfigure((0,1,2,3,4), weight=1)
        self._lbl(inj_unit, "Screw Ø [mm]", row=0, column=0, sticky="e", padx=6, pady=4)
        self._ent(inj_unit, "screw_d_mm", w=80, row=0, column=1, sticky="w", padx=4, pady=4)
        self._lbl(inj_unit, "Pcs. 1", row=0, column=3, sticky="e", padx=6, pady=4)
        self._ent(inj_unit, "pcs_1", w=80, row=0, column=4, sticky="w", padx=4, pady=4)

        # ---------------- Injection ----------------
        self._section_table(parent, "Injection", [
            # label,  lista de ids (columnas), placeholders opcionales
            ("Injection press. limiting [bar]", ["inj_press_lim_1", "inj_press_lim_2", "inj_press_lim_3"]),
            ("Injection speed [mm/s]",          ["inj_speed_1", "inj_speed_2", "inj_speed_3"]),
            ("End of stage [mm]",                ["inj_end_stage_mm_1", "inj_end_stage_mm_2", "inj_end_stage_mm_3"]),
            ("Injection flow [ccm/s]",          ["inj_flow_1", "inj_flow_2", "inj_flow_3"]),
            ("End of stage [ccm]",              ["inj_end_stage_ccm_1", "inj_end_stage_ccm_2", "inj_end_stage_ccm_3"]),
        ])

        # ---------------- Plasticizing ----------------
        self._section_table(parent, "Plasticizing (St.1)", [
            ("Screw speed [m/min]",             ["plast_screw_speed"]),
            ("Back pressure [bar]",             ["plast_back_pressure"]),
            ("End of stage [ccm]",              ["plast_end_stage_ccm"]),
        ])

        # ---------------- Holding pressure ----------------
        self._section_table(parent, "Holding pressure (Pcs.2)", [
            ("Time [s]",                         ["hp_time_1", "hp_time_3", "hp_time_2"]),
            ("Pressure [bar]",                   ["hp_press_1", "hp_press_2", "hp_press_3", "hp_press_4"]),
        ])

        # ---------------- Temperatures ----------------
        self._section_table(parent, "Temperatures (1..5)", [
            ("Cylinder temp. [°C]",              ["temp_c1", "temp_c2", "temp_c3", "temp_c4", "temp_c5"]),
            ("Tolerances [°C]",                  ["tol_c1", "tol_c2", "tol_c3", "tol_c4", "tol_c5"]),
            ("Feed yoke temperature [°C]",       ["feed_yoke_temp"]),
            ("Lower enable tol. [°C]",           ["lower_enable_tol"]),
            ("Upper switch-off tol. [°C]",       ["upper_switch_off_tol"]),
        ])

        # ---------------- Mould movements ----------------
        # Opening
        self._section_table(parent, "Mould movements — Opening (St.1 / St.2 / St.3)", [
            ("End of stage [mm]",                ["open_end_mm_1", "open_end_mm_2", "open_end_mm_3"]),
            ("Speed [mm/s]",                     ["open_speed_1", "open_speed_2", "open_speed_3"]),
            ("Force [kN]",                       ["open_force_1", "open_force_2", "open_force_3"]),
        ])
        # Closing
        self._section_table(parent, "Mould movements — Closing (St.1 / St.2 / St.3 / An. HD)", [
            ("End of stage [mm]",                ["close_end_mm_1", "close_end_mm_2", "close_end_mm_3", "close_end_mm_4"]),
            ("Speed [mm/s]",                     ["close_speed_1", "close_speed_2", "close_speed_3", "close_speed_4"]),
            ("Force [kN]",                       ["close_force_1", "close_force_2", "close_force_3"]),
        ])

        # ---------------- Clamping ----------------
        self._section_table(parent, "Clamping", [
            ("Mould closed [kN]",                ["mould_closed_kn"]),
        ])

    def _section_table(self, parent, title, rows):
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=("white", "#111a27"))
        card.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=(8, 6))

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=(0, 10))
        # Determinar el máximo número de columnas de entrada
        max_cols = max(len(cols) for _, cols in rows)
        for i in range(max_cols + 1):
            grid.grid_columnconfigure(i, weight=1)

        for r, (label, ids) in enumerate(rows):
            self._lbl(grid, label, row=r, column=0, sticky="w", padx=4, pady=4)
            for c, fid in enumerate(ids, start=1):
                self._ent(grid, fid, w=90, row=r, column=c, sticky="ew", padx=4, pady=4)

    # --------------------------- Eventos / Acciones ---------------------------
    def _on_pick_mold(self):
        mid = (self.mold_var.get() or "").strip()
        self.current_mold = "" if (not mid or mid.startswith("—")) else mid
        # Limpia
        for v in self.vars.values():
            v.set("")
        if self.current_mold:
            data = _load_json(self.current_mold)
            for k, v in self.vars.items():
                v.set(str(data.get(k, "")))

    def _collect(self) -> dict:
        return {k: (v.get() or "").strip() for k, v in self.vars.items()}

    def _save(self):
        if not self.current_mold:
            messagebox.showwarning("Molde", "Selecciona un molde."); return
        motivo = (self.motivo_var.get() or "").strip()
        if not motivo:
            messagebox.showwarning("Motivo requerido", "Escribe el motivo del cambio para guardar."); return

        old = _load_json(self.current_mold)
        new = self._collect()
        _save_json(self.current_mold, new)

        # Historial (diff textual simple)
        diffs = []
        for k, nv in new.items():
            ov = str(old.get(k, ""))
            if (nv or "") != (ov or ""):
                diffs.append(f"{k}: '{ov}' → '{nv}'")
        diff_text = "; ".join(diffs) if diffs else "(sin cambios)"

        exists = os.path.exists(HISTORY_CSV)
        with open(HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["ts", "molde_id", "usuario", "motivo", "cambios"])
            w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        self.current_mold,
                        getattr(self.app, "operador", tk.StringVar(value="")).get(),
                        motivo, diff_text])
        self.motivo_var.set("")
        messagebox.showinfo("Recetas de Máquina", "Parámetros guardados y registrado en historial.")

    def _clear_all(self):
        if not self.current_mold:
            for v in self.vars.values(): v.set("")
            return
        if messagebox.askyesno("Limpiar", f"¿Limpiar todos los campos del molde {self.current_mold}?"):
            for v in self.vars.values(): v.set("")

    def _open_history(self):
        top = tk.Toplevel(self); top.title("Historial de cambios — Recetas de Máquina")
        top.geometry("1100x540+120+90")
        wrap = ctk.CTkFrame(top, fg_color=("white", "#0e1117")); wrap.pack(fill="both", expand=True)
        cols = ("ts", "molde", "usuario", "motivo", "cambios")
        tree = ttk.Treeview(wrap, columns=cols, show="headings", height=18)
        for key, text, w in [
            ("ts", "Fecha/Hora", 150), ("molde", "Molde", 140), ("usuario", "Usuario", 140),
            ("motivo", "Motivo", 260), ("cambios", "Cambios", 640),
        ]:
            tree.heading(key, text=text); tree.column(key, width=w, anchor="w")
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview); tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True, padx=12, pady=12); vsb.pack(side="left", fill="y", pady=12)

        if os.path.exists(HISTORY_CSV):
            with open(HISTORY_CSV, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if self.current_mold and r.get("molde_id") != self.current_mold:
                        continue
                    tree.insert("", "end", values=(r.get("ts",""), r.get("molde_id",""),
                                                   r.get("usuario",""), r.get("motivo",""),
                                                   r.get("cambios","")))
        else:
            messagebox.showinfo("Historial", "Aún no hay historial.")

    def _import_excel(self):
        try:
            from openpyxl import load_workbook
        except Exception:
            messagebox.showwarning("Falta dependencia", "Instala openpyxl: pip install openpyxl")
            return

        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx;*.xlsm;*.xls")])
        if not path: return
        try:
            wb = load_workbook(path, data_only=True, keep_vba=True); ws = wb.active
            for fid, cell in EXCEL_MAP.items():
                try: val = ws[cell].value
                except Exception: val = None
                if fid in self.vars and val is not None:
                    self.vars[fid].set(str(val))
            messagebox.showinfo("Importar", "Se mapearon celdas básicas. Ajusta EXCEL_MAP para cubrir más campos.")
        except Exception as e:
            messagebox.showerror("Importar Excel", f"No se pudo leer el archivo:\n{e}")
