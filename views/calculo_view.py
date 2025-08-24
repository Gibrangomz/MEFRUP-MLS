# views/calculo_view.py - redesigned calculation panel
from .base import *  # ctk, tk, ttk, messagebox, filedialog, BASE_DIR
import os, json, uuid, time, threading, traceback, datetime as dt
from dataclasses import dataclass, asdict
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI

# ================== Configuración ==================
load_dotenv()

PROMPT_ID       = "pmpt_68ab8b2a833481949260b55a82cfcff70181ad7500c4cbe6"
PROMPT_VERSION  = "3"
VECTOR_STORE_ID = None
TEMPERATURE     = 0.2
MAX_OUTPUT_TOKENS = 1200

SESSIONS_DIR = os.path.join(BASE_DIR, "chat_sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# ================== Modelos de datos ==================
@dataclass
class ChatMessage:
    role: str
    content: str
    ts: float

@dataclass
class ChatSession:
    id: str
    title: str
    created_at: float
    updated_at: float
    messages: List[ChatMessage]

    @staticmethod
    def new():
        sid = dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        now = time.time()
        return ChatSession(id=sid, title="Nuevo chat", created_at=now, updated_at=now, messages=[])

    @property
    def path(self):
        return os.path.join(SESSIONS_DIR, f"{self.id}.json")

    def save(self):
        self.updated_at = time.time()
        data = asdict(self)
        data["messages"] = [asdict(m) for m in self.messages]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sess = ChatSession(
            id=data["id"],
            title=data.get("title", "Chat"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            messages=[ChatMessage(**m) for m in data.get("messages", [])],
        )
        return sess

# ================== Vista ==================
class CalculoView(ctk.CTkFrame):
    """Panel de cálculo con un diseño moderno."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.client: Optional[OpenAI] = None
        self.current_session: Optional[ChatSession] = None
        self._loading = False

        # manejo de sesiones
        self._session_buttons: List[ctk.CTkButton] = []
        self._sel_idx: Optional[int] = None

        # ======= Layout principal =======
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # ---- Header ----
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#1c1c1e"), height=56)
        header.grid(row=0, column=0, sticky="nsew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            header,
            text="← Menú",
            command=self.app.go_menu,
            width=110,
            corner_radius=10,
            fg_color="#E5E7EB",
            text_color="#111",
            hover_color="#D1D5DB",
        ).grid(row=0, column=0, padx=(16, 10), pady=10)

        ctk.CTkLabel(
            header,
            text="Cálculo (Chat)",
            font=ctk.CTkFont("Helvetica", 20, "bold"),
        ).grid(row=0, column=1, sticky="w", pady=10)

        # ---- Body: sidebar + chat ----
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(body, width=260, fg_color=("white", "#0F1115"))
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        self.sidebar.grid_propagate(False)
        self.sidebar.rowconfigure(3, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="Conversaciones",
            anchor="w",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        ctk.CTkButton(
            self.sidebar,
            text="➕ Nuevo chat",
            command=self.new_chat,
            height=36,
            corner_radius=10,
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        self.sessions_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.sessions_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.sessions_frame.grid_columnconfigure(0, weight=1)

        tools = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        tools.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))

        ctk.CTkButton(
            tools,
            text="📝 Renombrar",
            command=self.rename_chat,
            height=32,
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(
            tools,
            text="🗑️ Borrar",
            command=self.delete_chat,
            height=32,
            fg_color="#fee2e2",
            text_color="#7f1d1d",
            hover_color="#fecaca",
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

        # Main area
        self.main = ctk.CTkFrame(body, fg_color=("white", "#0F1115"))
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.rowconfigure(0, weight=1)
        self.main.columnconfigure(0, weight=1)

        self.history = ctk.CTkScrollableFrame(self.main, fg_color=("white", "#0F1115"))
        self.history.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        bottom = ctk.CTkFrame(self.main, fg_color=("white", "#0F1115"))
        bottom.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        bottom.columnconfigure(0, weight=1)

        self.entry = ctk.CTkTextbox(
            bottom,
            height=60,
            corner_radius=8,
            border_width=1,
            border_color="#9CA3AF",
        )
        self.entry.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.entry.bind("<Shift-Return>", lambda e: self.send())

        self.send_btn = ctk.CTkButton(bottom, text="Enviar", command=self.send, height=60)
        self.send_btn.grid(row=0, column=1)

        # ---- Inicializa cliente OpenAI ----
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY no está configurada (usa .env).")
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            self._bubble("system", f"⚠️ Error inicializando OpenAI: {e}")

        # ---- Carga sesiones existentes ----
        self.refresh_sessions_list()
        if not self._session_buttons:
            self.new_chat()
        else:
            self.select_chat(0)

        # Mensaje de bienvenida si el chat está vacío
        if self.current_session and len(self.current_session.messages) == 0:
            self._bubble(
                "assistant",
                "Hola, soy **MEFRUP Calc**.\n"
                "- Pídeme operaciones, estimaciones de ciclo, balances de materiales.\n"
                "- Dame datos como: material, husillo, cavidades, pared, colada (fría/hot runner), etc.\n"
                "- Si quieres **formato JSON**, pide: `JSON RecetaInyeccion`.",
            )

    # ============ Gestor de sesiones ============
    def refresh_sessions_list(self):
        for btn in self._session_buttons:
            btn.destroy()
        self._session_buttons.clear()
        files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]
        files.sort(reverse=True)
        self._session_paths = [os.path.join(SESSIONS_DIR, f) for f in files]
        for idx, p in enumerate(self._session_paths):
            try:
                sess = ChatSession.load(p)
                ts = dt.datetime.fromtimestamp(sess.updated_at).strftime("%m/%d %H:%M")
                text = f"{sess.title}\n{ts}"
            except Exception:
                text = os.path.basename(p)
            btn = ctk.CTkButton(
                self.sessions_frame,
                text=text,
                anchor="w",
                height=48,
                command=lambda i=idx: self.select_chat(i),
                fg_color="transparent",
                text_color=("black", "white"),
                hover_color=("#D1D5DB", "#2d2d2d"),
            )
            btn.grid(row=idx, column=0, sticky="ew", pady=(0, 4))
            self._session_buttons.append(btn)

    def select_chat(self, idx: int):
        self._sel_idx = idx
        for i, btn in enumerate(self._session_buttons):
            if i == idx:
                btn.configure(fg_color=("#3B82F6", "#1E3A8A"), text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("black", "white"))
        self.open_selected_session()

    def open_selected_session(self):
        if self._sel_idx is None:
            return
        path = self._session_paths[self._sel_idx]
        sess = ChatSession.load(path)
        self.current_session = sess
        for child in self.history.winfo_children():
            child.destroy()
        for m in self.current_session.messages:
            self._bubble(m.role, m.content, save=False)

    def new_chat(self):
        self.current_session = ChatSession.new()
        self.current_session.save()
        self.refresh_sessions_list()
        self.select_chat(0)

    def rename_chat(self):
        if not self.current_session:
            return
        new_title = simple_input(self, "Renombrar chat", "Nuevo título:")
        if new_title:
            self.current_session.title = new_title.strip()[:80]
            self.current_session.save()
            self.refresh_sessions_list()
            self.select_chat(0)

    def delete_chat(self):
        if not self.current_session:
            return
        if messagebox.askyesno("Borrar chat", "¿Seguro que deseas borrar esta conversación?"):
            try:
                os.remove(self.current_session.path)
            except Exception:
                pass
            self.current_session = None
            self.refresh_sessions_list()
            if self._session_buttons:
                self.select_chat(0)
            else:
                self.new_chat()

    # ============ Envío y respuesta ============
    def send(self):
        txt = self.entry.get("1.0", "end").strip()
        if not txt:
            return
        self.entry.delete("1.0", "end")
        self._bubble("user", txt)
        self._ask_openai_async(txt)
        if self.current_session and self.current_session.title == "Nuevo chat":
            title = (txt[:48] + "…") if len(txt) > 48 else txt
            self.current_session.title = title
            self.current_session.save()
            self.refresh_sessions_list()
            self.select_chat(0)

    def _ask_openai_async(self, user_text: str):
        if self._loading:
            return

        def worker():
            self._set_busy(True)
            try:
                if not self.client:
                    self._bubble("system", "⚠️ Cliente OpenAI no inicializado. Revisa tu .env.")
                    return

                history = []
                if self.current_session:
                    history = [{"role": m.role, "content": m.content} for m in self.current_session.messages]
                history.append({"role": "user", "content": user_text})

                kwargs = {
                    "prompt": {"id": PROMPT_ID, "version": PROMPT_VERSION},
                    "input": history,
                    "temperature": TEMPERATURE,
                    "max_output_tokens": MAX_OUTPUT_TOKENS,
                    "stream": True,
                }
                if VECTOR_STORE_ID:
                    kwargs["tools"] = [{"type": "file_search", "vector_store_ids": [VECTOR_STORE_ID]}]

                lbl = self._bubble("assistant", "", save=False)
                chunks = []
                with self.client.responses.stream(**kwargs) as stream:
                    for event in stream:
                        if event.type == "response.output_text.delta":
                            chunks.append(event.delta)
                            lbl.configure(text="".join(chunks))
                            try:
                                self.history._parent_canvas.yview_moveto(1)
                            except Exception:
                                pass
                        elif event.type == "response.completed":
                            break

                out = "".join(chunks).strip()
                if not out:
                    out = "No recibí texto de salida. Revisa el Prompt o el input."

                if self.current_session:
                    self.current_session.messages.append(ChatMessage(role="assistant", content=out, ts=time.time()))
                    self.current_session.save()

            except Exception as e:
                self._bubble("system", f"⚠️ Error API: {e}\n\n{traceback.format_exc(limit=1)}")
            finally:
                self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    # ============ Utilidades UI ============
    def _bubble(self, role: str, text: str, save: bool = True):
        if self.current_session and save:
            self.current_session.messages.append(ChatMessage(role=role, content=text, ts=time.time()))
            self.current_session.save()

        wrap = ctk.CTkFrame(self.history, fg_color="transparent")
        wrap.pack(fill="x", padx=10, pady=6)

        is_user = (role == "user")
        bubble_color = "#2563EB" if is_user else "#374151"
        text_color = "white"
        anchor = "e" if is_user else "w"

        inner = ctk.CTkFrame(wrap, fg_color=bubble_color, corner_radius=14)
        inner.pack(anchor=anchor, padx=6)

        lbl = ctk.CTkLabel(
            inner,
            text=text,
            justify="left",
            wraplength=820,
            text_color=text_color,
            font=ctk.CTkFont(size=14),
        )
        lbl.pack(padx=12, pady=(8, 2), anchor="w")

        controls = ctk.CTkFrame(inner, fg_color="transparent")
        controls.pack(fill="x", padx=8, pady=(0, 6))

        ctk.CTkLabel(
            controls,
            text=dt.datetime.now().strftime("%H:%M"),
            font=ctk.CTkFont(size=10),
            text_color=text_color,
        ).pack(side="left")

        def copy_text(txt=text):
            try:
                self.clipboard_clear()
                self.clipboard_append(txt)
            except Exception:
                pass

        ctk.CTkButton(
            controls,
            text="Copiar",
            width=60,
            height=20,
            command=copy_text,
            fg_color="#1E3A8A" if is_user else "#4B5563",
            text_color="white",
            hover_color="#4338CA" if is_user else "#6B7280",
        ).pack(side="right")

        try:
            self.history._parent_canvas.yview_moveto(1)
        except Exception:
            pass

        return lbl

    def _set_busy(self, busy: bool):
        self._loading = busy
        state = "disabled" if busy else "normal"
        try:
            self.send_btn.configure(state=state)
            self.entry.configure(state=state)
        except Exception:
            pass

# ================== Diálogo simple de entrada ==================
def simple_input(parent, title, prompt):
    top = ctk.CTkToplevel(parent)
    top.title(title)
    top.geometry("420x140")
    top.grab_set()

    ctk.CTkLabel(top, text=prompt).pack(padx=16, pady=(16, 6))
    var = tk.StringVar()
    ent = ctk.CTkEntry(top, textvariable=var)
    ent.pack(fill="x", padx=16, pady=6)
    ent.focus_set()

    resp = {"ok": False}

    def ok():
        resp["ok"] = True
        top.destroy()

    def cancel():
        top.destroy()

    row = ctk.CTkFrame(top, fg_color="transparent"); row.pack(fill="x", padx=16, pady=12)
    ctk.CTkButton(row, text="Aceptar", command=ok).pack(side="right", padx=(6, 0))
    ctk.CTkButton(row, text="Cancelar", command=cancel, fg_color="#E5E7EB", text_color="#111").pack(side="right")

    parent.wait_window(top)
    return var.get() if resp["ok"] else None
