"""
Servidor web para exponer la CLI de The Big Data Theory en una terminal
interactiva desde el navegador.
"""

import os
import platform
import select
import signal
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"
MAIN_FILE = PROJECT_ROOT / "src" / "main.py"

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

_sessions = {}
_sessions_lock = threading.Lock()


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


def _python_command():
    return [sys.executable, "-u", str(MAIN_FILE)]


def _env():
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


class LinuxPtySession:
    def __init__(self, sid, rows=24, cols=80):
        import fcntl  # type: ignore[import-not-found]
        import pty
        import struct
        import termios  # type: ignore[import-not-found]

        self.sid = sid
        self.rows = rows
        self.cols = cols
        self.master_fd, slave_fd = pty.openpty()
        self._fcntl = fcntl
        self._struct = struct
        self._termios = termios
        self.process = subprocess.Popen(
            _python_command(),
            cwd=str(PROJECT_ROOT),
            env=_env(),
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
            close_fds=True,
        )
        os.close(slave_fd)
        self.resize(rows, cols)

    def read_loop(self):
        try:
            while self.process.poll() is None:
                ready, _, _ = select.select([self.master_fd], [], [], 0.1)
                if ready:
                    data = os.read(self.master_fd, 4096)
                    if not data:
                        break
                    socketio.emit("output", data.decode("utf-8", errors="replace"), to=self.sid)
        except OSError:
            pass
        finally:
            socketio.emit("exit", to=self.sid)
            self.close()

    def write(self, data):
        os.write(self.master_fd, data.encode("utf-8", errors="replace"))

    def resize(self, rows, cols):
        rows = max(int(rows or self.rows), 1)
        cols = max(int(cols or self.cols), 1)
        size = self._struct.pack("HHHH", rows, cols, 0, 0)
        self._fcntl.ioctl(self.master_fd, self._termios.TIOCSWINSZ, size)
        if self.process.poll() is None:
            killpg = getattr(os, "killpg", None)
            getpgid = getattr(os, "getpgid", None)
            sigwinch = getattr(signal, "SIGWINCH", None)
            if killpg is not None and getpgid is not None and sigwinch is not None:
                killpg(getpgid(self.process.pid), sigwinch)
        self.rows = rows
        self.cols = cols

    def close(self):
        with _sessions_lock:
            _sessions.pop(self.sid, None)
        if self.process.poll() is None:
            try:
                killpg = getattr(os, "killpg", None)
                getpgid = getattr(os, "getpgid", None)
                if killpg and getpgid:
                    killpg(getpgid(self.process.pid), signal.SIGTERM)
                else:
                    self.process.terminate()
            except OSError:
                self.process.terminate()
        try:
            os.close(self.master_fd)
        except OSError:
            pass


class WindowsPtySession:
    def __init__(self, sid, rows=24, cols=80):
        from winpty import PtyProcess  # type: ignore[import-not-found]

        self.sid = sid
        self.rows = int(rows or 24)
        self.cols = int(cols or 80)
        self.process = PtyProcess.spawn(
            " ".join(f'"{part}"' if " " in part else part for part in _python_command()),
            cwd=str(PROJECT_ROOT),
            env=_env(),
            dimensions=(self.rows, self.cols),
        )

    def read_loop(self):
        try:
            while self.process.isalive():
                data = self.process.read(4096)
                if data:
                    socketio.emit("output", data, to=self.sid)
        except Exception:
            pass
        finally:
            socketio.emit("exit", to=self.sid)
            self.close()

    def write(self, data):
        self.process.write(data)

    def resize(self, rows, cols):
        self.rows = max(int(rows or self.rows), 1)
        self.cols = max(int(cols or self.cols), 1)
        if hasattr(self.process, "setwinsize"):
            self.process.setwinsize(self.rows, self.cols)
        elif hasattr(self.process, "set_size"):
            self.process.set_size(self.rows, self.cols)

    def close(self):
        with _sessions_lock:
            _sessions.pop(self.sid, None)
        try:
            if self.process.isalive():
                self.process.terminate(force=True)
        except Exception:
            pass


class WindowsPipeSession:
    def __init__(self, sid, rows=24, cols=80):
        self.sid = sid
        self.rows = int(rows or 24)
        self.cols = int(cols or 80)
        self.process = subprocess.Popen(
            _python_command(),
            cwd=str(PROJECT_ROOT),
            env=_env(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def read_loop(self):
        try:
            while self.process.poll() is None:
                data = self.process.stdout.read(1)
                if data:
                    socketio.emit("output", data, to=self.sid)
                else:
                    break
        finally:
            socketio.emit("exit", to=self.sid)
            self.close()

    def write(self, data):
        if self.process.stdin and self.process.poll() is None:
            self.process.stdin.write(data)
            self.process.stdin.flush()

    def resize(self, rows, cols):
        self.rows = max(int(rows or self.rows), 1)
        self.cols = max(int(cols or self.cols), 1)

    def close(self):
        with _sessions_lock:
            _sessions.pop(self.sid, None)
        if self.process.poll() is None:
            self.process.terminate()


def _create_session(sid):
    if platform.system().lower() == "windows":
        try:
            return WindowsPtySession(sid)
        except ImportError:
            return WindowsPipeSession(sid)
    return LinuxPtySession(sid)


@socketio.on("connect")
def handle_connect():
    session = _create_session(request.sid)
    with _sessions_lock:
        _sessions[request.sid] = session
    socketio.start_background_task(session.read_loop)
    emit("output", "\r\nConectado a The Big Data Theory...\r\n")


@socketio.on("disconnect")
def handle_disconnect():
    with _sessions_lock:
        session = _sessions.get(request.sid)
    if session:
        session.close()


@socketio.on("input")
def handle_input(data):
    with _sessions_lock:
        session = _sessions.get(request.sid)
    if session:
        session.write(data)


@socketio.on("resize")
def handle_resize(size):
    with _sessions_lock:
        session = _sessions.get(request.sid)
    if session:
        session.resize(size.get("rows"), size.get("cols"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
