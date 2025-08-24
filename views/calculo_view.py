# views/calculo_view.py
from .base import *  # ctk, tk, ttk, messagebox, filedialog, BASE_DIR
import os, json, uuid, time, threading, traceback, datetime as dt
from dataclasses import dataclass, asdict
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI

# ================== Configuración ==================
load_dotenv()  # lee .env (OPENAI_API_KEY, etc.)

# Tu Prompt publicado
PROMPT_ID        = "pmpt_68ab8b2a833481949260b55a82cfcff70181ad7500c4cbe6"
PROMPT_VERSION   = "3"     # usa la versión que publicaste (ajústala)
# (Opcional) Vector Store para tu PDF de inyección
VECTOR_STORE_ID  = None    # ej. "vs_abc123..."; si no usas, deja None

TEMPERATURE      = 0.2
MAX_OUTPUT_TOKENS = 1200

SESSIONS_DIR     = os.path.join(BASE_DIR, "chat_sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# ================== Modelos de datos ==================
@dataclass
class ChatMessage:
    role: str      # "user" | "assistant" | "system"
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
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.client: Optional[OpenAI] = None
        self.current_session: Optional[ChatSession] = None
        self._loading = False

        # ---- Header ----
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#1c1c1e"))
        header.pack(fill="x", side="top")
        ctk.CTkButton(
            header, text="← Menú", command=self.app.go_menu,
            width=110, corner_radius=10, fg_color="#E5E7EB", text_color="#111",
            hover_color="#D1D5DB",
        ).pack(side="left", padx=(16, 10), pady=10)

        ctk.CTkLabel(header, text="Cálculo (Chat)", font=ctk.CTkFont("Helvetica", 20, "bold")
        ).pack(side="left", pady=10)

        # ---- Body split: sidebar + chat ----
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(expand=True, fill="both", padx=12, pady=12)

        self.sidebar = ctk.CTkFrame(body, width=260, fg_color=("white", "#0F1115"))
        self.sidebar.pack(side="left", fill="y", padx=(0, 12))
        self.sidebar.pack_propagate(False)

        self.main = ctk.CTkFrame(body, fg_color=("white", "#0F1115"))
        self.main.pack(side="left", expand=True, fill="both")

        # ---- Sidebar content ----
        ctk.CTkLabel(self.sidebar, text="Conversaciones", anchor="w",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(fill="x", padx=12, pady=(12, 6))

        btn_new = ctk.CTkButton(self.sidebar, text="➕ Nuevo chat", command=self.new_chat,
                                height=36, corner_radius=10)
        btn_new.pack(fill="x", padx=12, pady=(0, 12))

        self.chats_list = tk.Listbox(self.sidebar, activestyle="none", height=20)
        self.chats_list.pack(expand=True, fill="both", padx=12, pady=(0, 8))
        self.chats_list.bind("<<ListboxSelect>>", self.on_select_chat)

        tools = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        tools.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(tools, text="📝 Renombrar", command=self.rename_chat, height=32).pack(side="left", expand=True, fill="x", padx=(0,6))
        ctk.CTkButton(tools, text="🗑️ Borrar",    command=self.delete_chat,  height=32, fg_color="#fee2e2", text_color="#7f1d1d", hover_color="#fecaca").pack(side="left", expand=True, fill="x", padx=(6,0))

        # ---- Main chat area ----
        self.history = ctk.CTkScrollableFrame(self.main, fg_color=("white", "#0F1115"))
        self.history.pack(expand=True, fill="both", padx=8, pady=8)

        bottom = ctk.CTkFrame(self.main, fg_color=("white", "#0F1115"))
        bottom.pack(fill="x", padx=8, pady=(0, 8))

        self.entry = ctk.CTkEntry(bottom, placeholder_text="Escribe tu cálculo o pregunta técnica…", height=44)
        self.entry.pack(side="left", expand=True, fill="x", padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self.send())

        self.send_btn = ctk.CTkButton(bottom, text="Enviar", command=self.send, height=44)
        self.send_btn.pack(side="left")

        # ---- Inicializa cliente OpenAI ----
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY no está configurada (usa .env).")
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            self._bubble("system", f"⚠️ Error inicializando OpenAI: {e}")

        # ---- Carga sesiones existentes + crea una si no hay ----
        self.refresh_sessions_list()
        if self.chats_list.size() == 0:
            self.new_chat()
        else:
            # abre el primero por comodidad
            self.chats_list.select_set(0)
            self.open_selected_session()

        # Mensaje de bienvenida si el chat está vacío
        if self.current_session and len(self.current_session.messages) == 0:
            self._bubble("assistant",
                "Hola, soy **MEFRUP Calc**.\n"
                "- Pídeme operaciones, estimaciones de ciclo, balances de materiales.\n"
                "- Dame datos como: material, husillo, cavidades, pared, colada (fría/hot runner), etc.\n"
                "- Si quieres **formato JSON**, pide: `JSON RecetaInyeccion`."
            )

    # ============ Gestor de sesiones ============
    def refresh_sessions_list(self):
        self.chats_list.delete(0, "end")
        files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]
        files.sort(reverse=True)  # más recientes primero
        self._session_paths = [os.path.join(SESSIONS_DIR, f) for f in files]
        for p in self._session_paths:
            try:
                sess = ChatSession.load(p)
                ts = dt.datetime.fromtimestamp(sess.updated_at).strftime("%m/%d %H:%M")
                self.chats_list.insert("end", f"{sess.title}   ·  {ts}")
            except Exception:
                self.chats_list.insert("end", os.path.basename(p))

    def on_select_chat(self, _evt=None):
        self.open_selected_session()

    def open_selected_session(self):
        sel = self.chats_list.curselection()
        if not sel: 
            return
        idx = sel[0]
        path = self._session_paths[idx]
        sess = ChatSession.load(path)
        self.current_session = sess
        # pinta historial
        for child in self.history.winfo_children():
            child.destroy()
        for m in self.current_session.messages:
            self._bubble(m.role, m.content, save=False)

    def new_chat(self):
        self.current_session = ChatSession.new()
        self.current_session.save()
        self.refresh_sessions_list()
        # selecciona el nuevo
        self.chats_list.select_clear(0, "end")
        self.chats_list.select_set(0)
        self.open_selected_session()

    def rename_chat(self):
        if not self.current_session: 
            return
        new_title = simple_input(self, "Renombrar chat", "Nuevo título:")
        if new_title:
            self.current_session.title = new_title.strip()[:80]
            self.current_session.save()
            self.refresh_sessions_list()

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
            if self.chats_list.size() == 0:
                self.new_chat()
            else:
                self.chats_list.select_set(0)
                self.open_selected_session()

    # ============ Envío y respuesta ============
    def send(self):
        txt = self.entry.get().strip()
        if not txt:
            return
        self.entry.delete(0, "end")
        self._bubble("user", txt)
        self._ask_openai_async(txt)

        # si el título es "Nuevo chat", usa primeras ~6 palabras del primer msg
        if self.current_session and self.current_session.title == "Nuevo chat":
            title = (txt[:48] + "…") if len(txt) > 48 else txt
            self.current_session.title = title
            self.current_session.save()
            self.refresh_sessions_list()

    def _ask_openai_async(self, user_text: str):
        if self._loading:
            return
        def worker():
            self._set_busy(True)
            try:
                if not self.client:
                    self._bubble("system", "⚠️ Cliente OpenAI no inicializado. Revisa tu .env.")
                    return

                kwargs = {
                    "prompt": {"id": PROMPT_ID, "version": PROMPT_VERSION},
                    "input": user_text,
                    "temperature": TEMPERATURE,
                    "max_output_tokens": MAX_OUTPUT_TOKENS,
                }
                if VECTOR_STORE_ID:
                    kwargs["tools"] = [{"type": "file_search", "vector_store_ids": [VECTOR_STORE_ID]}]

                resp = self.client.responses.create(**kwargs)
                out  = (getattr(resp, "output_text", "") or "").strip()
                if not out:
                    out = "No recibí texto de salida. Revisa el Prompt o el input."

                self._bubble("assistant", out)

            except Exception as e:
                self._bubble("system", f"⚠️ Error API: {e}\n\n{traceback.format_exc(limit=1)}")
            finally:
                self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    # ============ Utilidades UI ============
    def _bubble(self, role: str, text: str, save: bool=True):
        if self.current_session and save:
            self.current_session.messages.append(ChatMessage(role=role, content=text, ts=time.time()))
            self.current_session.save()

        wrap = ctk.CTkFrame(self.history, fg_color="transparent")
        wrap.pack(fill="x", padx=10, pady=6)

        is_user = (role == "user")
        bubble_color = "#E5E7EB" if is_user or role=="system" else "#DCFCE7"
        text_color   = "#111" if is_user or role=="system" else "#064E3B"
        anchor       = "e" if is_user else "w"

        inner = ctk.CTkFrame(wrap, fg_color=bubble_color, corner_radius=14)
        inner.pack(anchor=anchor, padx=6)

        lbl = ctk.CTkLabel(inner, text=text, justify="left", wraplength=820,
                           text_color=text_color, font=ctk.CTkFont(size=14))
        lbl.pack(padx=12, pady=8)

        # autoscroll
        try:
            self.history._parent_canvas.yview_moveto(1)
        except Exception:
            pass

    def _set_busy(self, busy: bool):
        self._loading = busy
        try:
            self.send_btn.configure(state=("disabled" if busy else "normal"))
            self.entry.configure(state=("disabled" if busy else "normal"))
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
    ctk.CTkButton(row, text="Aceptar", command=ok).pack(side="right", padx=(6,0))
    ctk.CTkButton(row, text="Cancelar", command=cancel, fg_color="#E5E7EB", text_color="#111").pack(side="right")

    parent.wait_window(top)
    return var.get() if resp["ok"] else None
