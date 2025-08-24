import os, json, uuid, time, traceback, sys
import datetime as dt
from dataclasses import dataclass, asdict
from typing import List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QListWidget, QTextEdit, QLineEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QListWidgetItem, QLabel,
    QMessageBox, QInputDialog, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal

from config import BASE_DIR

load_dotenv()

PROMPT_ID       = "pmpt_68ab8b2a833481949260b55a82cfcff70181ad7500c4cbe6"
PROMPT_VERSION  = "3"
VECTOR_STORE_ID = None
TEMPERATURE     = 0.2
MAX_OUTPUT_TOKENS = 1200

SESSIONS_DIR = os.path.join(BASE_DIR, "chat_sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# ======== Modelos ========
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
        return ChatSession(
            id=data["id"],
            title=data.get("title", "Chat"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            messages=[ChatMessage(**m) for m in data.get("messages", [])],
        )

# ======== Worker OpenAI ========
class OpenAIWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, client, history):
        super().__init__()
        self.client = client
        self.history = history

    def run(self):
        try:
            kwargs = {
                "prompt": {"id": PROMPT_ID, "version": PROMPT_VERSION},
                "input": self.history,
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "stream": True,
            }
            if VECTOR_STORE_ID:
                kwargs["tools"] = [{"type": "file_search", "vector_store_ids": [VECTOR_STORE_ID]}]
            chunks = []
            with self.client.responses.stream(**kwargs) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        chunks.append(event.delta)
                    elif event.type == "response.completed":
                        break
            out = "".join(chunks).strip() or "No recibí texto de salida. Revisa el Prompt o el input."
            self.finished.emit(out)
        except Exception as e:
            self.error.emit(f"⚠️ Error API: {e}\n{traceback.format_exc(limit=1)}")

# ======== UI ========
class CalculoWindow(QMainWindow):
    """Panel de cálculo con PySide6."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MEFRUP Calc (Qt)")
        self.resize(1000, 600)

        self.client: Optional[OpenAI] = None
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)
        except Exception:
            pass

        self.current_session: Optional[ChatSession] = None
        self.sessions: List[ChatSession] = []

        self._build_ui()
        self.refresh_sessions_list()
        if not self.sessions:
            self.new_chat()
        else:
            self.select_row(0)

        if self.current_session and not self.current_session.messages:
            self.append_message(
                "assistant",
                "Hola, soy <b>MEFRUP Calc</b>.<br>- Pídeme operaciones y estimaciones.",
            )

    def _build_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # Sidebar
        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.addWidget(QLabel("Conversaciones"))
        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(lambda item: self.select_row(self.session_list.row(item)))
        side_layout.addWidget(self.session_list)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("Nuevo")
        new_btn.clicked.connect(self.new_chat)
        rename_btn = QPushButton("Renombrar")
        rename_btn.clicked.connect(self.rename_chat)
        del_btn = QPushButton("Borrar")
        del_btn.clicked.connect(self.delete_chat)
        for b in (new_btn, rename_btn, del_btn):
            btn_row.addWidget(b)
        side_layout.addLayout(btn_row)
        splitter.addWidget(side)

        # Main area
        main = QWidget()
        main_layout = QVBoxLayout(main)
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        main_layout.addWidget(self.history)

        entry_row = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.returnPressed.connect(self.send)
        entry_row.addWidget(self.entry)
        send_btn = QPushButton("Enviar")
        send_btn.clicked.connect(self.send)
        entry_row.addWidget(send_btn)
        main_layout.addLayout(entry_row)
        splitter.addWidget(main)
        splitter.setSizes([220, 780])

        # Style
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2f; }
            QWidget { color: #e0e0e0; font: 14px 'Segoe UI'; }
            QListWidget { background-color: #2d2d3f; border: none; }
            QTextEdit { background-color: #252537; border: none; }
            QLineEdit { background-color: #252537; border: 1px solid #3b3b4d; padding: 6px; }
            QPushButton { background-color: #3b82f6; border: none; padding: 6px 12px; border-radius:4px; }
            QPushButton:hover { background-color: #1e40af; }
        """)

    # ====== Sesiones ======
    def refresh_sessions_list(self):
        self.session_list.clear()
        self.sessions = []
        files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]
        files.sort(reverse=True)
        for p in [os.path.join(SESSIONS_DIR, f) for f in files]:
            try:
                sess = ChatSession.load(p)
            except Exception:
                continue
            self.sessions.append(sess)
            ts = dt.datetime.fromtimestamp(sess.updated_at).strftime("%m/%d %H:%M")
            item = QListWidgetItem(f"{sess.title}\n{ts}")
            self.session_list.addItem(item)

    def select_row(self, row: int):
        if row < 0 or row >= len(self.sessions):
            return
        self.session_list.setCurrentRow(row)
        self.current_session = self.sessions[row]
        self.history.clear()
        for m in self.current_session.messages:
            self.append_message(m.role, m.content, save=False)

    def new_chat(self):
        self.current_session = ChatSession.new()
        self.current_session.save()
        self.refresh_sessions_list()
        self.select_row(0)

    def rename_chat(self):
        if not self.current_session:
            return
        new_title, ok = QInputDialog.getText(self, "Renombrar chat", "Nuevo título:")
        if ok and new_title:
            self.current_session.title = new_title.strip()[:80]
            self.current_session.save()
            self.refresh_sessions_list()
            self.select_row(0)

    def delete_chat(self):
        if not self.current_session:
            return
        if QMessageBox.question(self, "Borrar chat", "¿Seguro que deseas borrar esta conversación?") == QMessageBox.Yes:
            try:
                os.remove(self.current_session.path)
            except Exception:
                pass
            self.current_session = None
            self.refresh_sessions_list()
            if self.sessions:
                self.select_row(0)
            else:
                self.new_chat()

    # ====== Envío ======
    def append_message(self, role: str, text: str, save: bool = True):
        color = "#3b82f6" if role == "user" else ("#ef4444" if role == "system" else "#d1d5db")
        self.history.append(f"<p style='color:{color};'><b>{role}:</b> {text}</p>")
        if self.current_session and save:
            self.current_session.messages.append(ChatMessage(role=role, content=text, ts=time.time()))
            self.current_session.save()

    def send(self):
        text = self.entry.text().strip()
        if not text:
            return
        self.entry.clear()
        self.append_message("user", text)
        history = []
        if self.current_session:
            history = [{"role": m.role, "content": m.content} for m in self.current_session.messages]
        history.append({"role": "user", "content": text})
        if not self.client:
            self.append_message("system", "⚠️ Cliente OpenAI no inicializado. Revisa tu .env.")
            return
        self.worker = OpenAIWorker(self.client, history)
        self.worker.finished.connect(lambda reply: self.append_message("assistant", reply))
        self.worker.error.connect(lambda err: self.append_message("system", err))
        self.worker.start()


def main():
    app = QApplication(sys.argv)
    win = CalculoWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
