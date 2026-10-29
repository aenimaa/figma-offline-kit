"""A fake Figma REST API with made-up data, for tests and the demo gallery. No real Figma data anywhere.

Team "Example Team": Mobile App (Onboarding: design, Flows: FigJam) and Website (Landing: design).
Landing has a very tall frame (PNG below @2x), a frame with no SVG render (→ PDF) and an empty frame."""
import json
import struct
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TOKEN = "figd_FAKE-test-token-0000"
TEAM_ID = "1234567890"
NO_SVG = {"3:2", "3:3"}   # Figma returns no SVG render for these
NO_PDF = {"3:3"}          # …and no PDF either: an empty frame


def paint(hexc, var=None):
    c = {k: int(hexc[1 + 2 * i:3 + 2 * i], 16) / 255 for i, k in enumerate("rgb")}
    p = {"type": "SOLID", "color": dict(c, a=1)}
    if var:
        p["boundVariables"] = {"color": {"type": "VARIABLE_ALIAS", "id": var}}
    return p


def frame(i, name, w=390, h=844, x=0, y=0, kind="FRAME", visible=True, fills=None, children=None):
    return {"id": i, "name": name, "type": kind, "visible": visible, "fills": fills or [],
            "absoluteBoundingBox": {"x": x, "y": y, "width": w, "height": h}, "children": children or []}


def section(i, name, kids, x=0, y=0, w=1400, h=1000):
    return {"id": i, "name": name, "type": "SECTION", "absoluteBoundingBox": {"x": x, "y": y, "width": w, "height": h},
            "children": kids}


def page(i, name, kids):
    return {"id": i, "name": name, "type": "CANVAS", "children": kids}


FILES = {
    "FAKEkeyAAA1": {"name": "Onboarding", "project": "101", "editorType": "figma", "lastModified": "2026-10-01T10:00:00Z",
                  "pages": [
                      page("0:1", "Cover", [frame("1:1", "Cover", 1440, 1024)]),
                      page("0:2", "-------", []),
                      page("0:3", "Screens", [
                          section("2:0", "Sign up", [
                              frame("2:1", "Welcome", x=40, y=80, fills=[paint("#5A78DC", "VariableID:1:1")],
                                    children=[frame("2:11", "Card", 300, 200, kind="RECTANGLE", fills=[paint("#EEEEFF", "VariableID:1:2")])]),
                              frame("2:2", "Email", x=470, y=80, fills=[paint("#5A78DC", "VariableID:1:1")],
                                    children=[frame("2:21", "Logo", 40, 40, kind="RECTANGLE", fills=[paint("#5A78DC")])]),
                              section("2:5", "Errors", [frame("2:6", "Email taken", x=940, y=120)], x=900, y=40, w=480, h=940),
                          ]),
                          frame("2:3", "Home", x=1500, y=80, fills=[paint("#FF0000")]),
                          frame("2:4", "Hidden draft", x=1950, y=80, visible=False),
                          frame("2:7", "Icons", 200, 120, x=1500, y=1000, kind="GROUP"),
                      ]),
                      page("0:4", "Archive v1", [frame("4:1", "Old home")]),
                  ]},
    "FAKEkeyBBB2": {"name": "Flows", "project": "101", "editorType": "figjam", "lastModified": "2026-09-20T09:00:00Z",
                  "pages": [page("0:1", "Page 1", [])]},
    "FAKEkeyCCC3": {"name": "Landing", "project": "102", "editorType": "figma", "lastModified": "2026-10-05T12:00:00Z",
                  "pages": [page("1:0", "Desktop", [
                      frame("3:1", "Landing long", 1920, 9000), frame("3:2", "Hero video", 1440, 900, x=2000),
                      frame("3:3", "Empty", 1440, 900, x=3600)])]},
}
VARIABLES = {"FAKEkeyAAA1": {"meta": {
    "variableCollections": {"VariableCollectionId:1:0": {
        "id": "VariableCollectionId:1:0", "name": "Colors", "key": "c0", "defaultModeId": "1:0",
        "modes": [{"modeId": "1:0", "name": "Light"}, {"modeId": "1:9", "name": "Dark"}],
        "variableIds": ["VariableID:1:1", "VariableID:1:2", "VariableID:1:3"]}},
    "variables": {
        "VariableID:1:1": {"id": "VariableID:1:1", "name": "color/brand", "key": "k11", "variableCollectionId": "VariableCollectionId:1:0",
                           "resolvedType": "COLOR", "scopes": ["ALL_SCOPES"], "codeSyntax": {"WEB": "var(--brand)"},
                           "valuesByMode": {"1:0": {"r": 90 / 255, "g": 120 / 255, "b": 220 / 255, "a": 1},
                                            "1:9": {"r": 0.5, "g": 0.6, "b": 1, "a": 1}}},
        "VariableID:1:2": {"id": "VariableID:1:2", "name": "color/bg", "key": "k12", "variableCollectionId": "VariableCollectionId:1:0",
                           "resolvedType": "COLOR", "scopes": ["ALL_SCOPES"], "codeSyntax": {},
                           "valuesByMode": {"1:0": {"r": 238 / 255, "g": 238 / 255, "b": 1, "a": 1},
                                            "1:9": {"type": "VARIABLE_ALIAS", "id": "VariableID:1:1"}}},
        "VariableID:1:3": {"id": "VariableID:1:3", "name": "space/m", "key": "k13", "variableCollectionId": "VariableCollectionId:1:0",
                           "resolvedType": "FLOAT", "scopes": ["GAP"], "codeSyntax": {},
                           "valuesByMode": {"1:0": 16, "1:9": 16}}}}}}
COMPONENTS = {}  # componentId → {name, componentSetId}; tests fill it
PROJECTS = [{"id": "101", "name": "Mobile App"}, {"id": "102", "name": "Website"}]


def _png(w, h, rgb):
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)  # noqa: E731
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def _node(key, nid):
    def find(n):
        if n.get("id") == nid:
            return n
        for c in n.get("children", []):
            r = find(c)
            if r:
                return r
    for p in FILES[key]["pages"]:
        r = find(p)
        if r:
            return r


def _depth(n, d):
    if d <= 0:
        return {k: v for k, v in n.items() if k != "children"}
    return dict(n, children=[_depth(c, d - 1) for c in n.get("children", [])])


class Handler(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        parts = u.path.strip("/").split("/")
        Handler.calls.append(u.path)
        if parts[0] == "img":  # rendered image download (no token, like Figma's S3 links)
            _, key, name = parts
            nid, ext = name.rsplit(".", 1)
            n = _node(key, nid.replace("-", ":"))
            if ext == "png":
                bb = n["absoluteBoundingBox"]
                return self._send(200, _png(max(1, int(bb["width"] / 20)), max(1, int(bb["height"] / 20)), (90, 120, 220)), "image/png")
            if ext == "svg":
                bb = n["absoluteBoundingBox"]
                ids = "ids" in q  # rendered with svg_include_node_id=true

                def draw(m):
                    hx = ["#%02X%02X%02X" % tuple(round(p["color"][k] * 255) for k in "rgb") for p in m.get("fills", [])]
                    inner = "".join(f'<rect width="10" height="10" fill="{h}"/>' for h in hx) + "".join(draw(c) for c in m.get("children", []))
                    return f'<g data-node-id="{m["id"]}">{inner}</g>' if ids else f"<g>{inner}</g>"
                svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{bb["width"]}" height="{bb["height"]}">'
                       f'{draw(n)}<text x="20" y="60" font-size="40">{n["name"]}</text></svg>')
                return self._send(200, svg.encode(), "image/svg+xml")
            return self._send(200, b"%PDF-1.4\n% fake\n%%EOF\n", "application/pdf")
        if self.headers.get("X-Figma-Token") != TOKEN:
            return self._send(403, {"status": 403, "err": "Invalid token"})
        if u.path == "/v1/me":
            return self._send(200, {"handle": "tester", "email": "tester@example.com"})
        if parts[:2] == ["v1", "teams"] and parts[3] == "projects":
            if parts[2] != TEAM_ID:
                return self._send(404, {"status": 404, "err": "Not found"})
            return self._send(200, {"name": "Example Team", "projects": PROJECTS})
        if parts[:2] == ["v1", "projects"]:
            files = [{"key": k, "name": f["name"], "last_modified": f["lastModified"], "thumbnail_url": ""}
                     for k, f in FILES.items() if f["project"] == parts[2]]
            return self._send(200, {"name": "", "files": files})
        if parts[:2] == ["v1", "files"] and parts[3:] == ["variables", "local"]:
            if parts[2] in VARIABLES:
                return self._send(200, dict(status=200, error=False, **VARIABLES[parts[2]]))
            return self._send(403, {"status": 403, "err": "Limited by Figma plan"})
        if parts[:2] == ["v1", "files"] and len(parts) == 4 and parts[3] == "meta":
            f = FILES[parts[2]]
            name = next(p["name"] for p in PROJECTS if p["id"] == f["project"])
            return self._send(200, {"file": {"name": f["name"], "folder_name": name, "editorType": f["editorType"]}})
        if parts[:2] == ["v1", "files"] and len(parts) == 3:
            f = FILES[parts[2]]
            doc = {"id": "0:0", "type": "DOCUMENT", "children": [_depth(p, int(q.get("depth", 99)) - 1) for p in f["pages"]]}
            return self._send(200, {"name": f["name"], "lastModified": f["lastModified"], "editorType": f["editorType"],
                                    "version": "1", "document": doc})
        if parts[:2] == ["v1", "files"] and parts[3] == "nodes":
            nodes = {i: {"document": _depth(_node(parts[2], i), int(q.get("depth", 99))), "components": COMPONENTS,
                         "componentSets": {}, "styles": {}} for i in q["ids"].split(",") if _node(parts[2], i)}
            return self._send(200, {"nodes": nodes})
        if parts[:2] == ["v1", "images"]:
            key, fmt = parts[2], q.get("format", "png")
            base = f"http://{self.headers['Host']}/img/{key}"
            imgs = {}
            for i in q["ids"].split(","):
                none = (fmt == "svg" and i in NO_SVG) or (fmt == "pdf" and i in NO_PDF)
                ids = "?ids=1" if q.get("svg_include_node_id") == "true" else ""
                imgs[i] = None if none else f"{base}/{i.replace(':', '-')}.{fmt}{ids}"
            return self._send(200, {"err": None, "images": imgs})
        return self._send(404, {"status": 404, "err": "Not found"})


def start():
    """Start the server in a thread; returns (server, base_url)."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"
