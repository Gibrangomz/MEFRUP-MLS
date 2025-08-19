from .base import *

class ReportsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._plot_imgs = []
        self._plot_bytes = []
        self._last_data = []
        self._last_stats = {}
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#1c1c1e"))
        header.pack(fill="x", side="top")
        ctk.CTkButton(
            header,
            text="← Menú",
            command=self.app.go_menu,
            width=110,
            corner_radius=10,
            fg_color="#E5E7EB",
            text_color="#111",
            hover_color="#D1D5DB",
        ).pack(side="left", padx=(16, 10), pady=10)
        ctk.CTkLabel(
            header,
            text="Reportes de Producción",
            font=ctk.CTkFont("Helvetica", 20, "bold"),
        ).pack(side="left", pady=10)

        body = ctk.CTkFrame(self, fg_color=("#F5F5F7", "#121212"))
        body.pack(fill="both", expand=True, padx=40, pady=40)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        filtros = ctk.CTkFrame(body, corner_radius=12, fg_color=("white", "#1c1c1e"))
        filtros.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        filtros.grid_columnconfigure(1, weight=1)

        opciones = [m["id"] for m in MACHINES]
        self.machine_var = tk.StringVar(value=opciones[0])
        ctk.CTkLabel(filtros, text="Máquina:").grid(row=0, column=0, sticky="w", pady=6, padx=12)
        ctk.CTkOptionMenu(filtros, values=opciones, variable=self.machine_var).grid(
            row=0, column=1, sticky="ew", padx=12
        )

        ctk.CTkLabel(filtros, text="Desde:").grid(row=1, column=0, sticky="w", pady=6, padx=12)
        r1 = ctk.CTkFrame(filtros, fg_color="transparent")
        r1.grid(row=1, column=1, sticky="w", padx=12)
        self.desde_entry = ctk.CTkEntry(r1, width=120)
        self.desde_entry.pack(side="left")
        ctk.CTkButton(
            r1,
            text="📅",
            width=36,
            command=lambda: self._calendar_pick(self.desde_entry),
        ).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(filtros, text="Hasta:").grid(row=2, column=0, sticky="w", pady=6, padx=12)
        r2 = ctk.CTkFrame(filtros, fg_color="transparent")
        r2.grid(row=2, column=1, sticky="w", padx=12)
        self.hasta_entry = ctk.CTkEntry(r2, width=120)
        self.hasta_entry.pack(side="left")
        ctk.CTkButton(
            r2,
            text="📅",
            width=36,
            command=lambda: self._calendar_pick(self.hasta_entry),
        ).pack(side="left", padx=(6, 0))

        ctk.CTkButton(
            filtros,
            text="Generar",
            command=self._generar,
            corner_radius=10,
        ).grid(row=3, column=0, columnspan=2, pady=(14, 10))

        # tarjetas de estadísticos
        stats = ctk.CTkFrame(body, corner_radius=12, fg_color=("white", "#1c1c1e"))
        stats.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_total, self.lbl_total = self._create_card(stats, "Total", ("#E5E7EB", "#2B2B2B"))
        self.card_total.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.card_buenas, self.lbl_buenas = self._create_card(stats, "Buenas", ("#DCFCE7", "#065F46"))
        self.card_buenas.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        self.card_scrap, self.lbl_scrap = self._create_card(stats, "Scrap", ("#FEE2E2", "#991B1B"))
        self.card_scrap.grid(row=0, column=2, sticky="nsew", padx=6, pady=6)
        self.card_oee, self.lbl_oee = self._create_card(stats, "OEE Prom", ("#FEF9C3", "#92400E"))
        self.card_oee.grid(row=0, column=3, sticky="nsew", padx=6, pady=6)

        self.chart_frame = ctk.CTkFrame(body, corner_radius=20, fg_color=("white", "#1c1c1e"))
        self.chart_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 20))
        self.chart_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(body, text="Exportar", command=self._exportar).grid(row=3, column=0, sticky="e")

    def _tone(self, oee: float):
        if oee >= 85:
            return ("#DCFCE7", "#065F46")
        if oee >= 60:
            return ("#FEF9C3", "#92400E")
        return ("#FEE2E2", "#991B1B")

    def _create_card(self, parent, title: str, color):
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=color)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont("Helvetica", 14, "bold")).pack(
            anchor="w", padx=12, pady=(8, 0)
        )
        lbl = ctk.CTkLabel(card, text="0", font=ctk.CTkFont("Helvetica", 20, "bold"))
        lbl.pack(anchor="w", padx=12, pady=(0, 8))
        return card, lbl

    def _add_plot_card(self, title: str, fig, row: int, col: int):
        buf = io.BytesIO()
        if hasattr(fig, "to_image"):
            buf.write(fig.to_image(format="png", width=CHART_W, height=CHART_H, scale=2))
        else:
            fig.set_size_inches(CHART_W / 100, CHART_H / 100)
            fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", pad_inches=0.2)
            plt.close(fig)
        img_bytes = buf.getvalue()
        image = Image.open(io.BytesIO(img_bytes))
        ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(CHART_W, CHART_H))
        card = ctk.CTkFrame(self.chart_frame, corner_radius=12, fg_color=("white", "#1c1c1e"))
        card.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
        self.chart_frame.grid_rowconfigure(row, weight=1)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont("Helvetica", 14, "bold")).pack(
            anchor="w", padx=12, pady=(8, 0)
        )
        lbl = ctk.CTkLabel(card, image=ctk_img, text="")
        lbl.image = ctk_img
        lbl.pack(padx=12, pady=(0, 12), expand=True, fill="both")
        self._plot_imgs.append(ctk_img)
        self._plot_bytes.append(img_bytes)

    def _exportar(self):
        if not self._last_data:
            messagebox.showwarning("Exportar", "Genera un reporte primero")
            return
        if messagebox.askyesno("Exportar", "¿Exportar como PDF? (No = Excel)"):
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF","*.pdf")])
            if path:
                self._export_pdf(path)
        else:
            path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")])
            if path:
                self._export_excel(path)

    def _export_excel(self, path: str):
        df = pd.DataFrame(self._last_data)
        df.to_excel(path, index=False, startrow=4)
        wb = load_workbook(path)
        ws = wb.active
        if os.path.exists(LOGO_PATH):
            logo = XLImage(LOGO_PATH)
            logo.width, logo.height = 120, 48
            ws.add_image(logo, "A1")
        start_row = len(df) + 7
        for img_bytes in self._plot_bytes:
            stream = io.BytesIO(img_bytes)
            img = XLImage(stream)
            img.width, img.height = CHART_W, CHART_H
            ws.add_image(img, f"A{start_row}")
            start_row += int(CHART_H / 15) + 2
        wb.save(path)

    def _export_pdf(self, path: str):
        df = pd.DataFrame(self._last_data)
        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        if os.path.exists(LOGO_PATH):
            pdf.image(LOGO_PATH, x=10, y=8, w=30)
        pdf.set_font("Arial", "B", 14)
        pdf.set_y(15)
        pdf.cell(0, 10, "Reporte de Producción", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 9)
        col_w = (pdf.w - 2 * pdf.l_margin) / len(df.columns)
        for c in df.columns:
            pdf.cell(col_w, 8, c, border=1)
        pdf.ln(8)
        pdf.set_font("Arial", "", 8)
        for _, row in df.iterrows():
            for c in df.columns:
                pdf.cell(col_w, 8, str(row[c]), border=1)
            pdf.ln(8)
        pdf.ln(4)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, "Resumen", ln=True)
        pdf.set_font("Arial", "", 8)
        stats_lines = [
            ("Total", self._last_stats.get("total", 0)),
            ("Buenas", self._last_stats.get("buenas", 0)),
            ("Scrap", self._last_stats.get("scrap", 0)),
            ("OEE Prom (%)", self._last_stats.get("oee_prom", 0)),
            ("Availability Prom (%)", self._last_stats.get("avail_prom", 0)),
            ("Effectivity Prom (%)", self._last_stats.get("perf_prom", 0)),
            ("Quality Prom (%)", self._last_stats.get("qual_prom", 0)),
            ("Paro total (min)", self._last_stats.get("paro_min_total", 0)),
        ]
        for k, v in stats_lines:
            pdf.cell(0, 6, f"{k}: {v}", ln=True)
        pdf.ln(4)
        for img_bytes in self._plot_bytes:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(img_bytes)
                tmp_path = tmp.name
            img_w = pdf.w - 2 * pdf.l_margin
            img_h = img_w * CHART_H / CHART_W
            pdf.image(tmp_path, w=img_w, h=img_h)
            os.remove(tmp_path)
            pdf.ln(4)
        pdf.output(path)

    def _calendar_pick(self, entry: ctk.CTkEntry):
        try:
            y,m,d=map(int,(entry.get() or date.today().isoformat()).split("-"))
            init=date(y,m,d)
        except:
            init=date.today()
        top=tk.Toplevel(self); top.title("Selecciona fecha"); top.transient(self); top.grab_set(); top.resizable(False,False)
        self.update_idletasks()
        top.geometry(f"+{self.winfo_rootx()+self.winfo_width()//2-180}+{self.winfo_rooty()+self.winfo_height()//2-170}")
        cal=Calendar(top, selectmode="day", year=init.year, month=init.month, day=init.day, date_pattern="yyyy-mm-dd", firstweekday="monday", showweeknumbers=False)
        cal.pack(padx=14, pady=14)
        def choose():
            entry.delete(0,"end"); entry.insert(0, cal.get_date()); top.destroy()
        tk.Button(top, text="Seleccionar", command=choose).pack(side="left", padx=10, pady=10)
        tk.Button(top, text="Cerrar", command=top.destroy).pack(side="left", padx=10, pady=10)

    def _generar(self):
        mid=self.machine_var.get()
        machine=next((m for m in MACHINES if m["id"]==mid), None)
        if not machine:
            messagebox.showerror("Error","Máquina inválida")
            return
        desde=self.desde_entry.get().strip()
        hasta=self.hasta_entry.get().strip()
        stats, data = resumen_rango_maquina(machine, desde, hasta)
        self._last_stats = stats
        self._last_data = data
        self.lbl_total.configure(text=str(stats["total"]))
        self.lbl_buenas.configure(text=str(stats["buenas"]))
        self.lbl_scrap.configure(text=str(stats["scrap"]))
        self.lbl_oee.configure(text=f"{stats['oee_prom']:.2f}%")
        self.card_oee.configure(fg_color=self._tone(stats["oee_prom"]))

        for w in self.chart_frame.winfo_children():
            w.destroy()
        self._plot_imgs.clear()
        self._plot_bytes.clear()
        if not data:
            ctk.CTkLabel(self.chart_frame, text="Sin datos para el rango seleccionado").pack(expand=True)
            return

        fechas = [d["fecha"] for d in data]
        avail = [d["availability"] for d in data]
        perf = [d["performance"] for d in data]
        qual = [d["quality"] for d in data]
        oees = [d["oee"] for d in data]

        fig_ind = go.Figure()
        fig_ind.add_trace(go.Bar(name="Availability", x=fechas, y=avail, marker_color="#10b981"))
        fig_ind.add_trace(go.Bar(name="Effectivity", x=fechas, y=perf, marker_color="#f59e0b"))
        fig_ind.add_trace(go.Bar(name="Quality rate", x=fechas, y=qual, marker_color="#3b82f6"))
        fig_ind.add_trace(go.Scatter(name="OEE", x=fechas, y=oees, mode="lines+markers", marker=dict(color="#111827")))
        fig_ind.update_layout(
            barmode="group",
            yaxis_title="%",
            xaxis_tickangle=-45,
            template="plotly_white",
            width=CHART_W,
            height=CHART_H,
            margin=dict(l=60, r=30, t=40, b=80),
        )

        fig_sum = go.Figure()
        fig_sum.add_trace(
            go.Bar(
                y=["OEE", "Availability", "Effectivity", "Quality rate"],
                x=[stats["oee_prom"], stats["avail_prom"], stats["perf_prom"], stats["qual_prom"]],
                orientation="h",
                marker_color=["#111827", "#10b981", "#f59e0b", "#3b82f6"],
                text=[
                    f"{stats['oee_prom']:.0f}%",
                    f"{stats['avail_prom']:.0f}%",
                    f"{stats['perf_prom']:.0f}%",
                    f"{stats['qual_prom']:.0f}%",
                ],
                textposition="inside",
            )
        )
        fig_sum.update_layout(
            xaxis=dict(title="%", range=[0, 110]),
            template="plotly_white",
            width=CHART_W,
            height=CHART_H,
            margin=dict(l=120, r=30, t=40, b=40),
        )

        self._add_plot_card("Indicadores", fig_ind, 0, 0)
        self._add_plot_card("Resumen", fig_sum, 0, 1)

# ---------- Menú ----------
