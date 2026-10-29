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
        self.report_path = os.path.join(self.station, "REPORT.md")
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


def resolve(arg=None):
    """--workspace, then $FIGMA_KIT_WORKSPACE, then the pointer left by the last init. None if nothing is set."""
    path = arg or os.environ.get("FIGMA_KIT_WORKSPACE")
    if not path and os.path.exists(POINTER):
        with open(POINTER, encoding="utf-8") as f:
            path = f.read().strip()
    return Workspace(path) if path else None


def remember(ws):
    write_text(POINTER, ws.root + "\n")
