from .base import *

class ShipmentsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app=app
        self._build()

    def _calendar_pick(self, entry: ctk.CTkEntry):
        try:
            y,m,d=map(int,(entry.get() or date.today().isoformat()).split("-"))
            init=date(y,m,d)
        except:
            init=date.today()
        top=tk.Toplevel(self); top.title("Selecciona fecha"); top.transient(self); top.grab_set(); top.resizable(False,False)
        self.update_idletasks()
        top.geometry(f"+{self.winfo_rootx()+self.winfo_width()//2-180}+{self.winfo_rooty()+self.winfo_height()//2-170}")
        cal=Calendar(top, selectmode="day", year=init.year, month=init.month, day=init.day, date_pattern="yyyy-mm-dd",
                     firstweekday="monday", showweeknumbers=False)
        cal.pack(padx=14, pady=14)
        def choose():
            entry.delete(0,"end"); entry.insert(0, cal.get_date()); top.destroy()
        tk.Button(top, text="Seleccionar", command=choose).pack(side="left", padx=10, pady=10)
        tk.Button(top, text="Cerrar", command=top.destroy).pack(side="left", padx=10, pady=10)

    def _build(self):
        header=ctk.CTkFrame(self, corner_radius=0, fg_color=("white","#111111"))
        header.pack(fill="x", side="top")
        left=ctk.CTkFrame(header, fg_color="transparent"); left.pack(side="left", padx=16, pady=10)
        ctk.CTkButton(left, text="← Menú", command=self.app.go_menu, width=110, corner_radius=10,
                      fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB").pack(side="left", padx=(0,10))
        ctk.CTkLabel(left, text="Salida de Piezas (Embarques)", font=ctk.CTkFont("Helvetica", 20, "bold")).pack(side="left")

        body=ctk.CTkFrame(self, fg_color="transparent"); body.pack(fill="both", expand=True, padx=16, pady=16)
        body.grid_columnconfigure(0, weight=1); body.grid_columnconfigure(1, weight=1); body.grid_rowconfigure(1, weight=1)

        # --- formulario alta ---
        form=ctk.CTkFrame(body, corner_radius=18)
        form.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=(0,12))
        ctk.CTkLabel(form, text="Registrar salida", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(form, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))
        fr=ctk.CTkFrame(form, fg_color="transparent"); fr.pack(fill="x", padx=12, pady=4)

        self.om_order = ctk.CTkOptionMenu(fr, values=["(elige orden)"], width=120, command=lambda _v: self._refresh_stats())
        self.om_order.pack(side="left", padx=(0,8))
        ctk.CTkButton(fr, text="↻", width=36, command=self._reload_orders).pack(side="left", padx=6)

        self.e_date=ctk.CTkEntry(fr, placeholder_text="Fecha (YYYY-MM-DD)", width=170); self.e_date.pack(side="left", padx=(12,6))
        ctk.CTkButton(fr, text="📅", width=36, command=lambda:self._calendar_pick(self.e_date)).pack(side="left", padx=6)

        self.e_qty = ctk.CTkEntry(fr, placeholder_text="Cantidad", width=120); self.e_qty.pack(side="left", padx=8)
        self.e_dest= ctk.CTkEntry(fr, placeholder_text="Destino (opcional)", width=180); self.e_dest.pack(side="left", padx=8)
        self.e_note= ctk.CTkEntry(fr, placeholder_text="Nota (opcional)", width=180); self.e_note.pack(side="left", padx=8)
        ctk.CTkButton(fr, text="Guardar salida", command=self._save_shipment).pack(side="left", padx=8)

        # stats de orden
        self.stats = ctk.CTkLabel(form, text="—", text_color=("#6b7280","#9CA3AF"))
        self.stats.pack(anchor="w", padx=12, pady=(6,12))

        # --- tabla de salidas por orden ---
        listcard=ctk.CTkFrame(body, corner_radius=18)
        listcard.grid(row=0, column=1, sticky="nsew", padx=(8,0), pady=(0,12))
        ctk.CTkLabel(listcard, text="Salidas de la orden", font=ctk.CTkFont("Helvetica", 14, "bold")).pack(anchor="w", padx=12, pady=(10,6))
        ctk.CTkFrame(listcard, height=1, fg_color=("#E5E7EB","#2B2B2B")).pack(fill="x", padx=12, pady=(0,10))
        cols=("fecha","qty","destino","nota")
        self.tree=ttk.Treeview(listcard, columns=cols, show="headings", height=9)
        for k,t,w in [("fecha","Fecha",120),("qty","Qty",80),("destino","Destino",160),("nota","Nota",240)]:
            self.tree.heading(k, text=t); self.tree.column(k, width=w, anchor="center" if k!="nota" else "w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0,10))
        btns=ctk.CTkFrame(listcard, fg_color="transparent"); btns.pack(fill="x", padx=12, pady=(0,12))
        ctk.CTkButton(btns, text="Eliminar selección", fg_color="#ef4444", hover_color="#dc2626", command=self._delete_selected).pack(side="left")

        # acceso rápido
        actions=ctk.CTkFrame(self, fg_color="transparent"); actions.pack(fill="x", padx=16, pady=(0,16))
        ctk.CTkButton(actions, text="← Tablero de Órdenes", command=self.app.go_orders_board).pack(side="left")
        ctk.CTkButton(actions, text="Ir a Planificación", fg_color="#E5E7EB", text_color="#111", hover_color="#D1D5DB",
                      command=self.app.go_planning).pack(side="left", padx=8)

        self._reload_orders()
        self.e_date.insert(0, date.today().isoformat())

    def set_order(self, orden: str):
        self._reload_orders()
        try: self.om_order.set(orden)
        except: pass
        self._refresh_stats()
        self._reload_table()

    def _reload_orders(self):
        ordenes=[r.get("orden","") for r in leer_csv_dict(PLANNING_CSV)]
        if not ordenes: ordenes=["(elige orden)"]
        self.om_order.configure(values=ordenes)
        if self.app._shipments_preselect_order and self.app._shipments_preselect_order in ordenes:
            self.om_order.set(self.app._shipments_preselect_order)
        else:
            self.om_order.set(ordenes[0])
        self._refresh_stats(); self._reload_table()

    def _refresh_stats(self):
        o=self.om_order.get().strip()
        if not o: self.stats.configure(text="—"); return
        orow = next((r for r in leer_csv_dict(PLANNING_CSV) if r.get("orden")==o), None)
        if not orow:
            self.stats.configure(text="—"); return
        molde = orow.get("molde_id","")
        qty_total = parse_int_str(orow.get("qty_total","0"))
        prod = producido_por_molde_global(molde)
        shipped_order = enviados_por_orden(o)
        shipped_total = enviados_por_molde(molde)
        disp = max(0, prod - shipped_total)
        self.stats.configure(
            text=(
                f"Orden {o} • Molde {molde} • Qty total {qty_total} • Producidas {prod}"
                f" • Enviadas orden {shipped_order} • Enviadas molde {shipped_total}"
                f" • Disponibles {disp}"
            )
        )

    def _reload_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        o=self.om_order.get().strip()
        for r in leer_shipments():
            if r.get("orden") == o and r.get("approved", "0") == "1":
                self.tree.insert("", "end", values=(r.get("ship_date",""), r.get("qty",""), r.get("destino",""), r.get("nota","")))

    def _save_shipment(self):
        o=self.om_order.get().strip()
        if not o: messagebox.showwarning("Orden","Elige una orden."); return
        d=self.e_date.get().strip()
        q=parse_int_str(self.e_qty.get().strip(),0)
        if not (d and q>0):
            messagebox.showwarning("Salida","Fecha y cantidad (>0) obligatorias."); return
        orow = next((r for r in leer_csv_dict(PLANNING_CSV) if r.get("orden")==o), None)
        if not orow:
            messagebox.showwarning("Orden","No existe la orden."); return
        molde = orow.get("molde_id",""); prod = producido_por_molde_global(molde)
        shipped_total = enviados_por_molde(molde); disp=max(0, prod - shipped_total)
        if q > disp:
            messagebox.showwarning("Límite","No puedes enviar más de lo disponible. Disp: "+str(disp)); return
        dest=self.e_dest.get().strip(); nota=self.e_note.get().strip()
        with open(SHIPMENTS_CSV,"a",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow([o,d,str(q),dest,nota,"0"])
        self.e_qty.delete(0,"end"); self.e_dest.delete(0,"end"); self.e_note.delete(0,"end")
        self._refresh_stats(); self._reload_table()
        messagebox.showinfo("Salida","Salida registrada. Pendiente de aprobación.")

    def _delete_selected(self):
        sel=self.tree.selection()
        if not sel: return
        vals=self.tree.item(sel[0],"values")
        d,q,dest,nota=vals
        o=self.om_order.get().strip()
        rows=leer_shipments(); done=False; new=[]
        for r in rows:
            if (
                not done and r.get("orden") == o and r.get("ship_date") == d
                and str(r.get("qty", "")) == str(q)
                and r.get("destino", "") == dest
                and r.get("nota", "") == nota
                and r.get("approved", "0") == "1"
            ):
                done=True; continue
            new.append(r)
        with open(SHIPMENTS_CSV,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=["orden","ship_date","qty","destino","nota","approved"])
            w.writeheader(); w.writerows(new)
        self._refresh_stats(); self._reload_table()

