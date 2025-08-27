# -*- coding: utf-8 -*-
from .base import *  # ctk, tk, ttk, messagebox, filedialog
from .machine_recipes_constants import *
import json, os, sys

def open_history(view):
    self = view
    if not self.current_mold:
        messagebox.showwarning("Historial", "Selecciona un molde para ver su historial."); return

    top = tk.Toplevel(self); top.title(f"Historial y versiones — {self.current_mold}")
    try: top.state('zoomed')
    except Exception: top.geometry("1280x800+60+40")

    wrap = ctk.CTkFrame(top, fg_color=("white", "#0e1117")); wrap.pack(fill="both", expand=True)

    # Barra superior
    bar = ctk.CTkFrame(wrap, fg_color="transparent"); bar.pack(fill="x", padx=12, pady=(10, 6))
    ctk.CTkLabel(bar, text=f"Molde: {self.current_mold}", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
    srch_var = tk.StringVar()
    ctk.CTkEntry(bar, textvariable=srch_var, placeholder_text="Buscar en motivo/cambios...", width=380
                ).pack(side="left", padx=(12,4))
    ctk.CTkButton(bar, text="Buscar", command=lambda: load_versions()).pack(side="left")
    ctk.CTkButton(bar, text="Mostrar todo", command=lambda: (srch_var.set(""), load_versions())
                 ).pack(side="left", padx=(8,0))
    ctk.CTkButton(bar, text="Abrir carpeta de versiones",
                  command=lambda: self._open_folder(_versions_dir(self.current_mold))
                 ).pack(side="right")
    ctk.CTkButton(bar, text="Cerrar", fg_color="#6b7280", hover_color="#4b5563",
                  command=top.destroy).pack(side="right", padx=(8,0))

    # Paneles
    main = ctk.CTkFrame(wrap, fg_color="transparent"); main.pack(fill="both", expand=True, padx=12, pady=(0,12))
    main.grid_columnconfigure(0, weight=3)
    main.grid_columnconfigure(1, weight=5)
    main.grid_rowconfigure(0, weight=1)

    # IZQUIERDA: versiones
    left = ctk.CTkFrame(main, fg_color=("white", "#111827")); left.grid(row=0, column=0, sticky="nsew", padx=(0,8))
    cols = ("version","fecha","usuario","motivo","cambios")
    tree = ttk.Treeview(left, columns=cols, show="headings", height=24)
    headers = [("version","Versión",80),("fecha","Fecha/Hora",150),("usuario","Usuario",140),
               ("motivo","Motivo (resumen)",280),("cambios","Cambios (preview)",400)]
    for key, text, w in headers:
        tree.heading(key, text=text); tree.column(key, width=w, anchor="w")
    vsb = ttk.Scrollbar(left, orient="vertical", command=tree.yview); tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True, padx=12, pady=12); vsb.pack(side="left", fill="y", pady=12)

    # DERECHA: detalle (grilla)
    right = ctk.CTkFrame(main, fg_color=("white", "#111827")); right.grid(row=0, column=1, sticky="nsew", padx=(8,0))
    header_box = ctk.CTkFrame(right, fg_color="transparent"); header_box.pack(fill="x", padx=12, pady=(12,0))
    detail_title = ctk.CTkLabel(header_box, text="Detalle de versión", font=ctk.CTkFont(size=14, weight="bold"))
    detail_title.pack(side="left")

    export_box = ctk.CTkFrame(header_box, fg_color="transparent"); export_box.pack(side="right")
    btn_xlsx = ctk.CTkButton(export_box, text="⬇ Exportar Excel", state="disabled")
    btn_pdf  = ctk.CTkButton(export_box, text="⬇ Exportar PDF", state="disabled")
    btn_pdf.pack(side="right", padx=(8,0)); btn_xlsx.pack(side="right")

    detail_wrap = ctk.CTkScrollableFrame(right, fg_color=("white","#111827"))
    detail_wrap.pack(fill="both", expand=True, padx=12, pady=(6,12))

    # placeholder de secciones
    def clear_detail():
        for w in detail_wrap.winfo_children():
            w.destroy()

    # ----- grilla estilo Excel por secciones -----
    def section(title):
        card = ctk.CTkFrame(detail_wrap, corner_radius=12, fg_color=("white", "#111a27"))
        card.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=(10,6))
        grid = ctk.CTkFrame(card, fg_color="transparent"); grid.pack(fill="x", padx=10, pady=(0,10))
        return grid

    def row_labeled(grid, r, label, values, start_col=0):
        ctk.CTkLabel(grid, text=label).grid(row=r, column=start_col, sticky="w", padx=4, pady=4)
        for i, val in enumerate(values, start=1):
            e = ctk.CTkEntry(grid, width=110, justify="center")
            e.insert(0, str(val))
            e.configure(state="disabled")
            e.grid(row=r, column=start_col+i, sticky="ew", padx=4, pady=4)

    # datos actuales en detalle
    last_snap = {"_meta": {}}

    def load_versions():
        tree.delete(*tree.get_children())
        q = (srch_var.get() or "").lower()
        snaps = _list_versions(self.current_mold)
        if not snaps:
            current = _load_json(self.current_mold)
            if current:
                usuario = self._resolve_usuario()
                motivo = "(baseline) Estado inicial importado desde receta actual"
                _save_version_snapshot(self.current_mold, current, usuario, motivo, "")
                snaps = _list_versions(self.current_mold)
        for ver, path in snaps:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    snap = json.load(f)
            except Exception:
                continue
            meta = snap.get("_meta", {})
            ts = meta.get("saved_at",""); usuario = meta.get("usuario","")
            motivo = meta.get("motivo",""); cambios = meta.get("diffs","")
            rowtxt = (motivo + " " + cambios).lower()
            if q and q not in rowtxt: continue
            tree.insert("", "end", values=(ver, ts, usuario, motivo, cambios))

        # --- AUTOSELECT last ---
        items = tree.get_children()
        if items:
            tree.selection_set(items[-1]); tree.see(items[-1]); on_select()

    def on_select(*_):
        nonlocal last_snap
        clear_detail()
        sel = tree.selection()
        if not sel:
            detail_title.configure(text="Detalle de versión")
            btn_xlsx.configure(state="disabled"); btn_pdf.configure(state="disabled")
            return
        ver = tree.item(sel[0], "values")[0]
        snap = _load_version_snapshot(self.current_mold, ver)
        last_snap = snap
        meta = snap.get("_meta", {})
        clean = dict(snap); clean.pop("_meta", None)

        detail_title.configure(text=f"Detalle de versión — {ver}")
        btn_xlsx.configure(state="normal")
        btn_pdf.configure(state="normal")

        # Parameter overview
        g = section("Parameter overview")
        g.grid_columnconfigure((0,1,2,3,4,5), weight=1)
        row_labeled(g, 0, "Program",      [clean.get("program",""), "Date of entry", clean.get("date_of_entry",""),
                                           "Cavities", clean.get("cavities","")], start_col=0)
        row_labeled(g, 1, "Mould desig.", [clean.get("mould_desig",""), "Machine", clean.get("machine",""),
                                           "Material", clean.get("material","")], start_col=0)

        # Key data
        k = section("Key data")
        items = [
            ("Cycle time [s]", "cycle_time_s"),
            ("Injection time [s]", "injection_time_s"),
            ("Holding press. time [s]", "holding_press_time_s"),
            ("Rem. cooling time [s]", "rem_cooling_time_s"),
            ("Dosage time [s]", "dosage_time_s"),
            ("Screw stroke [mm]", "screw_stroke_mm"),
            ("Mould stroke [mm]", "mould_stroke_mm"),
            ("Ejector stroke [mm]", "ejector_stroke_mm"),
            ("Shot weight [g]", "shot_weight_g"),
            ("Plasticising flow [kg/h]", "plasticising_flow_kgh"),
            ("Dosage capacity [g/s]", "dosage_capacity_gs"),
            ("Dosage volume [ccm]", "dosage_volume_ccm"),
            ("Material cushion [ccm]", "material_cushion_ccm"),
            ("max. inj. pressure [bar]", "max_inj_pressure_bar"),
        ]
        k.grid_columnconfigure((0,1,2), weight=1)
        rr = 0
        for label, fid in items:
            row_labeled(k, rr, label, [clean.get(fid,"")], start_col=0)
            rr += 1

        # Injection unit
        iu = section("Injection unit")
        iu.grid_columnconfigure((0,1,2,3), weight=1)
        row_labeled(iu, 0, "Screw Ø [mm]", [clean.get("screw_d_mm",""), "Pcs. 1", clean.get("pcs_1","")], start_col=0)

        # Injection
        inj = section("Injection")
        inj.grid_columnconfigure((0,1,2,3,4), weight=1)
        row_labeled(inj, 0, "Injection press. limiting [bar]",
                    [clean.get("inj_press_lim_1",""), clean.get("inj_press_lim_2",""), clean.get("inj_press_lim_3","")])
        row_labeled(inj, 1, "Injection speed [mm/s]",
                    [clean.get("inj_speed_1",""), clean.get("inj_speed_2",""), clean.get("inj_speed_3","")])
        row_labeled(inj, 2, "End of stage [mm]",
                    [clean.get("inj_end_stage_mm_1",""), clean.get("inj_end_stage_mm_2",""), clean.get("inj_end_stage_mm_3","")])
        row_labeled(inj, 3, "Injection flow [ccm/s]",
                    [clean.get("inj_flow_1",""), clean.get("inj_flow_2",""), clean.get("inj_flow_3","")])
        row_labeled(inj, 4, "End of stage [ccm]",
                    [clean.get("inj_end_stage_ccm_1",""), clean.get("inj_end_stage_ccm_2",""), clean.get("inj_end_stage_ccm_3","")])

        # Plasticizing
        pl = section("Plasticizing (St.1)")
        pl.grid_columnconfigure((0,1), weight=1)
        row_labeled(pl, 0, "Screw speed [m/min]", [clean.get("plast_screw_speed","")])
        row_labeled(pl, 1, "Back pressure [bar]", [clean.get("plast_back_pressure","")])
        row_labeled(pl, 2, "End of stage [ccm]", [clean.get("plast_end_stage_ccm","")])

        # Holding pressure
        hp = section("Holding pressure (Pcs.2)")
        hp.grid_columnconfigure((0,1,2,3,4), weight=1)
        row_labeled(hp, 0, "Time [s]",     [clean.get("hp_time_1",""), clean.get("hp_time_2",""), clean.get("hp_time_3","")])
        row_labeled(hp, 1, "Pressure [bar]", [clean.get("hp_press_1",""), clean.get("hp_press_2",""),
                                              clean.get("hp_press_3",""), clean.get("hp_press_4","")])

        # Temperatures
        tp = section("Temperatures (1..5)")
        tp.grid_columnconfigure((0,1,2,3,4,5), weight=1)
        row_labeled(tp, 0, "Cylinder temp. [°C]", [clean.get("temp_c1",""), clean.get("temp_c2",""),
                                                   clean.get("temp_c3",""), clean.get("temp_c4",""),
                                                   clean.get("temp_c5","")])
        row_labeled(tp, 1, "Tolerances [°C]", [clean.get("tol_c1",""), clean.get("tol_c2",""),
                                               clean.get("tol_c3",""), clean.get("tol_c4",""),
                                               clean.get("tol_c5","")])
        row_labeled(tp, 2, "Feed yoke temperature [°C]", [clean.get("feed_yoke_temp","")])
        row_labeled(tp, 3, "Lower enable tol. [°C]",     [clean.get("lower_enable_tol","")])
        row_labeled(tp, 4, "Upper switch-off tol. [°C]", [clean.get("upper_switch_off_tol","")])

        # Mould movements Opening
        mo = section("Mould movements — Opening (St.1 / St.2 / St.3)")
        mo.grid_columnconfigure((0,1,2,3), weight=1)
        row_labeled(mo, 0, "End of stage [mm]", [clean.get("open_end_mm_1",""), clean.get("open_end_mm_2",""), clean.get("open_end_mm_3","")])
        row_labeled(mo, 1, "Speed [mm/s]",      [clean.get("open_speed_1",""), clean.get("open_speed_2",""), clean.get("open_speed_3","")])
        row_labeled(mo, 2, "Force [kN]",        [clean.get("open_force_1",""), clean.get("open_force_2",""), clean.get("open_force_3","")])

        # Mould movements Closing
        mc = section("Mould movements — Closing (St.1 / St.2 / St.3 / An. HD)")
        mc.grid_columnconfigure((0,1,2,3,4), weight=1)
        row_labeled(mc, 0, "End of stage [mm]", [clean.get("close_end_mm_1",""), clean.get("close_end_mm_2",""),
                                                 clean.get("close_end_mm_3",""), clean.get("close_end_mm_4","")])
        row_labeled(mc, 1, "Speed [mm/s]",      [clean.get("close_speed_1",""), clean.get("close_speed_2",""),
                                                 clean.get("close_speed_3",""), clean.get("close_speed_4","")])
        row_labeled(mc, 2, "Force [kN]",        [clean.get("close_force_1",""), clean.get("close_force_2",""),
                                                 clean.get("close_force_3","")])

        # Clamping
        cl = section("Clamping")
        cl.grid_columnconfigure((0,1), weight=1)
        row_labeled(cl, 0, "Mould closed [kN]", [clean.get("mould_closed_kn","")])

    # ---------------------- EXPORTS (integrados) ----------------------
    def export_excel():
        sel = tree.selection()
        if not sel:
            return
        ver = tree.item(sel[0], "values")[0]
        ver_label = f"V.{ver[1:]}" if str(ver).lower().startswith("v") else str(ver)

        # 1) Elegir dónde guardar
        default_name = f"{self.current_mold}_{ver}.xlsx"
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=default_name
        )
        if not path:
            return

        try:
            # 2) Encontrar plantilla
            template_path = _find_excel_template()
            if not template_path:
                # Si no está, deja elegirla manualmente una sola vez
                messagebox.showwarning(
                    "Plantilla no encontrada",
                    "No encontré 'formatorecta.xlsx' en las rutas conocidas.\n"
                    "Selecciona la plantilla (se usará esta vez):"
                )
                template_path = filedialog.askopenfilename(
                    title="Selecciona formatorecta.xlsx",
                    filetypes=[("Excel", "*.xlsx")]
                )
                if not template_path:
                    return

            # 3) Obtener snapshot del árbol (la versión seleccionada)
            snap = _load_version_snapshot(self.current_mold, ver)
            if not snap:
                messagebox.showwarning("Exportar Excel", "No se pudo cargar el snapshot de la versión.")
                return
            # Limpia metadatos para que solo queden campos
            snap_clean = dict(snap)
            snap_clean.pop("_meta", None)

            # 4) Exportar a plantilla usando el EXCEL_MAP
            if sys.platform.startswith("win") and HAS_EXCEL_COM:
                # normaliza ruta destino (por si el diálogo devuelve barras '/')
                path = _normalize_win_path(path)
                _export_with_excel_com(snapshot=snap_clean, out_path=path, template_path=template_path)
            else:
                # Aviso explícito: sin COM Excel podría meter reparaciones; usamos fallback seguro
                messagebox.showinfo(
                    "Exportar Excel",
                    "No se encontró Excel/pywin32. Usaré el modo 'limpio' sin vínculos ni dibujos para evitar reparaciones."
                )
                _export_snapshot_to_template(snapshot=snap_clean, out_path=path, template_path=template_path)

            messagebox.showinfo("Exportar Excel", f"Archivo generado correctamente:\n{path}")
        except ModuleNotFoundError:
            messagebox.showwarning("Dependencia faltante",
                "Falta openpyxl para exportar en plantilla:\n\npip install openpyxl")
        except Exception as e:
            messagebox.showerror("Exportar Excel", f"No se pudo exportar:\n{e}")

    def export_pdf():
        sel = tree.selection()
        if not sel:
            return
        ver = tree.item(sel[0], "values")[0]
        ver_label = f"V.{ver[1:]}" if str(ver).lower().startswith("v") else str(ver)
        title_txt = f"Receta {ver_label}"
        path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                            filetypes=[("PDF", "*.pdf")],
                                            initialfile=f"{self.current_mold}_{ver}.pdf")
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
            from reportlab.lib.utils import ImageReader

            snap = dict(last_snap); _ = snap.pop("_meta", {})
            W, H = landscape(A4)
            margin = 12*mm
            col_gap = 18*mm
            col_w = (W - margin*2 - col_gap) / 2.0
            row_h = 10*mm

            logo_path = LOGO_PATH if os.path.exists(LOGO_PATH) else ""
            c = canvas.Canvas(path, pagesize=landscape(A4))
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.setLineWidth(0.5)

            def new_page():
                c.showPage()
                return W, H, margin, H - margin

            def draw_head(txt):
                c.setFillColorRGB(0.86, 0.92, 1)
                c.rect(x, y - row_h, col_w, row_h, stroke=0, fill=1)
                c.setFillColorRGB(0.11, 0.30, 0.85)
                c.setFont("Helvetica-Bold", 12)
                c.drawString(x + 2, y - row_h + 3, _safe_pdf(txt))
                c.setFillColorRGB(0, 0, 0)

            def draw_box(lbl, val, w, h=row_h, center=False):
                c.setFillColorRGB(0.96, 0.96, 0.96)
                c.rect(x, y - h, w, h, stroke=1, fill=1)
                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica-Bold", 9)
                c.drawString(x+2, y - 12, _safe_pdf(lbl))
                if val is not None:
                    c.setFont("Helvetica", 10)
                    if center:
                        c.drawCentredString(x + w/2, y - h/2 - 3, _safe_pdf(val))
                    else:
                        c.drawString(x+2, y - h + 4, _safe_pdf(val))

            def advance(h=row_h+6):
                nonlocal y, x, col
                y -= h
                if y < margin + row_h*5:
                    if col == 0:
                        col = 1; x = margin + col_w + col_gap; y = H - margin - 24
                    else:
                        col = 0; x = margin
                        _, _, _, y0 = new_page(); y = y0 - 24
                    # logo + título por página
                    if logo_path:
                        try:
                            img = ImageReader(logo_path)
                            c.drawImage(img, W-60*mm, H-18*mm, width=50*mm, height=12*mm,
                                        preserveAspectRatio=True, mask='auto')
                        except Exception:
                            pass
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(margin, H - margin - 8, _safe_pdf(title_txt))

            # logo + título primera página
            if logo_path:
                try:
                    img = ImageReader(logo_path)
                    c.drawImage(img, W-60*mm, H-18*mm, width=50*mm, height=12*mm,
                                preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass
            c.setFont("Helvetica-Bold", 14)
            c.drawString(margin, H - margin - 8, _safe_pdf(title_txt))

            x, y = margin, H - margin - 24
            col = 0

            # Cabecera
            draw_box("Program", snap.get("program",""), w=40*mm); advance()
            draw_box("Date of entry:", snap.get("date_of_entry",""), w=60*mm); advance()
            draw_box("Cavities", snap.get("cavities",""), w=30*mm); advance()
            draw_box("Mould desig.", snap.get("mould_desig",""), w=40*mm); advance()
            draw_box("Machine", snap.get("machine",""), w=40*mm); advance()
            draw_box("Material", snap.get("material",""), w=40*mm); advance(h=10)

            # Injection unit
            draw_head("Injection unit"); advance(h=12)
            draw_box("Screw Ø [mm]", snap.get("screw_d_mm",""), w=35*mm); advance()
            draw_box("Pcs. 1", snap.get("pcs_1",""), w=25*mm); advance(h=14)

            # Forzar salto para Key data si falta espacio
            if y < margin + row_h*18 and col == 0:
                col = 1; x = margin + col_w + col_gap; y = H - margin - 24

            # Key data
            draw_head("Key data"); advance(h=12)
            kd = [
                ("Cycle time [s]", "cycle_time_s"),
                ("Injection time [s]", "injection_time_s"),
                ("Holding press. time [s]", "holding_press_time_s"),
                ("Rem. cooling time [s]", "rem_cooling_time_s"),
                ("Dosage time [s]", "dosage_time_s"),
                ("Screw stroke [mm]", "screw_stroke_mm"),
                ("Mould stroke [mm]", "mould_stroke_mm"),
                ("Ejector stroke [mm]", "ejector_stroke_mm"),
                ("Shot weight [g]", "shot_weight_g"),
                ("Plasticising flow [kg/h]", "plasticising_flow_kgh"),
                ("Dosage capacity [g/s]", "dosage_capacity_gs"),
                ("Dosage volume [ccm]", "dosage_volume_ccm"),
                ("Material cushion [ccm]", "material_cushion_ccm"),
                ("max. inj. pressure [bar]", "max_inj_pressure_bar"),
            ]
            for lab, fid in kd:
                draw_box(lab, snap.get(fid,""), w=col_w); advance()

            # Volver a primera col si conviene
            col = 0; x = margin; y = y if y > H/2 else H - margin - 24

            # Injection (3 columnas)
            draw_head("Injection"); advance(h=12)
            def triple(lbl, k1, k2, k3):
                wlbl = 65*mm; wcell = (col_w - wlbl)/3.0
                draw_box(lbl, None, w=wlbl)
                c.rect(x+wlbl, y - row_h, wcell, row_h, 1, 0)
                c.drawCentredString(x+wlbl + wcell/2, y - row_h/2 - 3, _safe_pdf(snap.get(k1,"")))
                c.rect(x+wlbl+wcell, y - row_h, wcell, row_h, 1, 0)
                c.drawCentredString(x+wlbl + wcell*1.5, y - row_h/2 - 3, _safe_pdf(snap.get(k2,"")))
                c.rect(x+wlbl+wcell*2, y - row_h, wcell, row_h, 1, 0)
                c.drawCentredString(x+wlbl + wcell*2.5, y - row_h/2 - 3, _safe_pdf(snap.get(k3,"")))
                advance()
            triple("Injection press. limiting [bar]", "inj_press_lim_1","inj_press_lim_2","inj_press_lim_3")
            triple("Injection speed [mm/s]",          "inj_speed_1","inj_speed_2","inj_speed_3")
            triple("End of stage [mm]",               "inj_end_stage_mm_1","inj_end_stage_mm_2","inj_end_stage_mm_3")
            triple("Injection flow [ccm/s]",          "inj_flow_1","inj_flow_2","inj_flow_3")
            triple("End of stage [ccm]",              "inj_end_stage_ccm_1","inj_end_stage_ccm_2","inj_end_stage_ccm_3")

            # Plasticizing
            draw_head("Plasticizing (St.1)"); advance(h=12)
            draw_box("Screw speed [m/min]", snap.get("plast_screw_speed",""), w=col_w); advance()
            draw_box("Back pressure [bar]", snap.get("plast_back_pressure",""), w=col_w); advance()
            draw_box("End of stage [ccm]",  snap.get("plast_end_stage_ccm",""), w=col_w); advance(h=10)

            # Holding pressure
            draw_head("Holding pressure (Pcs.2)"); advance(h=12)
            triple("Time [s]", "hp_time_1","hp_time_2","hp_time_3")
            # presión (4 columnas)
            wlbl = 65*mm; wcell = (col_w - wlbl)/4.0
            draw_box("Pressure [bar]", None, w=wlbl)
            keys = ["hp_press_1","hp_press_2","hp_press_3","hp_press_4"]
            for i,k in enumerate(keys):
                cx = x + wlbl + i*wcell
                c.rect(cx, y - row_h, wcell, row_h, 1, 0)
                c.drawCentredString(cx + wcell/2, y - row_h/2 - 3, _safe_pdf(snap.get(k,"")))
            advance(h=row_h+4)

            # Temperatures
            draw_head("Temperatures"); advance(h=12)
            def five(lbl, keys):
                wlbl = 65*mm; wcell = (col_w - wlbl)/5.0
                draw_box(lbl, None, w=wlbl)
                for i,k in enumerate(keys):
                    cx = x + wlbl + i*wcell
                    c.rect(cx, y - row_h, wcell, row_h, 1, 0)
                    c.drawCentredString(cx + wcell/2, y - row_h/2 - 3, _safe_pdf(snap.get(k,"")))
                advance()
            five("Cylinder temp. [°C]", ["temp_c1","temp_c2","temp_c3","temp_c4","temp_c5"])
            five("Tolerances [°C]",     ["tol_c1","tol_c2","tol_c3","tol_c4","tol_c5"])
            draw_box("Feed yoke temperature [°C]", snap.get("feed_yoke_temp",""), w=col_w); advance()
            # doble columna en fila
            whalf = (col_w - 4*mm)/2
            draw_box("Lower enable tol. [°C]", snap.get("lower_enable_tol",""), w=whalf)
            c.rect(x+whalf+4*mm, y - row_h, whalf, row_h, 1, 0)
            c.setFont("Helvetica-Bold", 9); c.drawString(x+whalf+4*mm+2, y - 12, _safe_pdf("Upper switch-off tol. [°C]"))
            c.setFont("Helvetica", 10); c.drawString(x+whalf+4*mm+2, y - row_h + 4, _safe_pdf(snap.get("upper_switch_off_tol","")))
            advance(h=row_h+6)

            # Opening
            draw_head("Mould movements — Opening (St.1 / St.2 / St.3)"); advance(h=12)
            triple("End of stage [mm]", "open_end_mm_1","open_end_mm_2","open_end_mm_3")
            triple("Speed [mm/s]",      "open_speed_1","open_speed_2","open_speed_3")
            triple("Force [kN]",        "open_force_1","open_force_2","open_force_3")

            # Closing
            draw_head("Mould movements — Closing (St.1 / St.2 / St.3 / An. HD)"); advance(h=12)
            def quad(lbl, keys):
                wlbl = 65*mm; wcell = (col_w - wlbl)/4.0
                draw_box(lbl, None, w=wlbl)
                for i,k in enumerate(keys):
                    cx = x + wlbl + i*wcell
                    c.rect(cx, y - row_h, wcell, row_h, 1, 0)
                    c.drawCentredString(cx + wcell/2, y - row_h/2 - 3, _safe_pdf(snap.get(k,"")))
                advance()
            quad("End of stage [mm]", ["close_end_mm_1","close_end_mm_2","close_end_mm_3","close_end_mm_4"])
            quad("Speed [mm/s]",      ["close_speed_1","close_speed_2","close_speed_3","close_speed_4"])
            # 3 columnas para force
            wlbl = 65*mm; wcell = (col_w - wlbl)/4.0
            draw_box("Force [kN]", None, w=wlbl)
            for i,k in enumerate(["close_force_1","close_force_2","close_force_3"]):
                cx = x + wlbl + i*wcell
                c.rect(cx, y - row_h, wcell, row_h, 1, 0)
                c.drawCentredString(cx + wcell/2, y - row_h/2 - 3, _safe_pdf(snap.get(k,"")))
            advance()

            # Clamping
            draw_head("Clamping"); advance(h=12)
            draw_box("Mould closed [kN]", snap.get("mould_closed_kn",""), w=col_w); advance()

            c.showPage(); c.save()
            messagebox.showinfo("Exportar PDF","Archivo PDF generado correctamente.")
        except ModuleNotFoundError:
            messagebox.showwarning("Dependencia faltante",
                "Para exportar PDF instala reportlab:\n\npip install reportlab")
        except Exception as e:
            messagebox.showerror("Exportar PDF", f"No se pudo exportar:\n{e}")

    tree.bind("<<TreeviewSelect>>", on_select)
    btn_xlsx.configure(command=export_excel)
    btn_pdf.configure(command=export_pdf)
    load_versions()

