"""The user's workspace: backup/ (deliverable) · temp/ (deletable) · workstation/ (the kit's own files)."""
import os

from .util import REPO, read_json, write_json, write_text, now_iso

POINTER = os.path.join(REPO, ".workspace")  # last workspace used by init (git-ignored, per machine)
ENV_TEMPLATE = (
    "# Figma personal access token. Paste it after the = sign. Never share this file.\n"
    "FIGMA_TOKEN=\n"
)


class Workspace:
    def __init__(self, root):
        self.root = os.path.abspath(os.path.expanduser(root))
        self.backup = os.path.join(self.root, "backup")
        self.temp = os.path.join(self.root, "temp")
        self.station = os.path.join(self.root, "workstation")
        self.logs = os.path.join(self.station, "logs")
        self.config_path = os.path.join(self.station, "config.json")
        self.state_path = os.path.join(self.station, "state.json")
        self.doctor_path = os.path.join(self.station, "doctor.json")
        self.report_path = os.path.join(self.root, "REPORT.md")  # at the top, where people look
        self.old_report_path = os.path.join(self.station, "REPORT.md")  # before 1.2; moved on the next update
        self.env_path = os.path.join(self.station, ".env")

    def exists(self):
        return os.path.isdir(self.station)

    def create(self):
        for d in (self.backup, self.temp, self.station, self.logs):
            os.makedirs(d, exist_ok=True)
        if not os.path.exists(self.env_path):
            write_text(self.env_path, ENV_TEMPLATE)

    def config(self):
        return read_json(self.config_path)

    def state(self):
        return read_json(self.state_path, {})

    def set_phase(self, phase, **extra):
        st = self.state()
        st.update(extra, phase=phase, updated=now_iso())
        write_json(self.state_path, st)


def clean_token(raw):
    """A pasted token without spaces, quotes or a pasted 'FIGMA_TOKEN=' in front."""
    tok = (raw or "").strip()
    if tok.upper().startswith("FIGMA_TOKEN="):
        tok = tok.split("=", 1)[1]
    return "".join(tok.split()).strip("\"'")


def save_token(ws, raw):
    """Write the token into <workspace>/workstation/.env, keeping the explanation line. Never prints it."""
    write_text(ws.env_path, ENV_TEMPLATE.replace("FIGMA_TOKEN=\n", f"FIGMA_TOKEN={clean_token(raw)}\n"))
    if os.name != "nt":
        os.chmod(ws.env_path, 0o600)


TOKEN_FILE = "Figma token.txt"  # visible file next to Start in the download, easy to find
TOKEN_FILE_TEMPLATE = (
    "# Paste your Figma token right after FIGMA_TOKEN= on the last line, save (Ctrl+S, or Cmd+S on a Mac),\n"
    "# then double-click Start. Start moves the token into <your backup folder>/workstation/.env\n"
    "# and empties this file again. How to make a token: guides/figma-token.md\n"
    "# توکن فیگما را درست بعد از FIGMA_TOKEN= در خط آخر بچسبانید، ذخیره کنید و بعد Start را باز کنید.\n"
    "\n"
    "FIGMA_TOKEN=\n"
)


def token_file_path():
    """The visible token file next to Start.bat / Start.command, in the download only (app/ next to guides/)."""
    top = os.path.dirname(REPO)
    if os.path.basename(REPO) == "app" and os.path.isdir(os.path.join(top, "guides")):
        return os.path.join(top, TOKEN_FILE)
    return None


def take_token_file(ws, path=None):
    """If the visible token file holds a token, save it in the workspace .env and empty the file. True if moved."""
    path = path or token_file_path()
    if not path or not os.path.exists(path):
        return False
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        # the part of each line before any '#' (tokens have none), so a token pasted on the first line also counts
        found = [clean_token(ln.split("#", 1)[0]) for ln in f]
    tok = next((x for x in reversed(found) if x), "")
    if not tok:
        return False
    save_token(ws, tok)
    write_text(path, TOKEN_FILE_TEMPLATE)
    return True


def resolve(arg=None):
    """--workspace, then $FIGMA_KIT_WORKSPACE, then the pointer left by the last init. None if nothing is set."""
    path = arg or os.environ.get("FIGMA_KIT_WORKSPACE")
    if not path and os.path.exists(POINTER):
        with open(POINTER, encoding="utf-8") as f:
            path = f.read().strip()
    return Workspace(path) if path else None


def remember(ws):
    write_text(POINTER, ws.root + "\n")
