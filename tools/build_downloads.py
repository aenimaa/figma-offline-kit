#!/usr/bin/env python3
"""Build the two double-click downloads that the site serves from downloads/:

  figma-offline-kit-windows.zip    Start.bat (CRLF)             + Read me first.html + Figma token.txt + app/ + guides/
  figma-offline-kit-macos.zip      Start.command (LF, mode 755) + Read me first.html + Figma token.txt + app/ + guides/

app/ holds kit.py, kit/, templates/, LICENSE and CHANGELOG.md; guides/ holds docs/*.md. AGENTS.md and the AI
stubs are left out: AI users work from the GitHub repo. The ZIPs have no top folder on purpose: Explorer's
"Extract All" and macOS Archive Utility already make one folder named after the ZIP, so a top folder inside would
give figma-offline-kit-windows/figma-offline-kit/. Figma token.txt is an empty, visible place for the token (Start
moves it into the workspace .env). The ZIPs are
byte-for-byte reproducible: fixed order, fixed dates (the release date in CHANGELOG.md), LF text.

    python tools/build_downloads.py            build into downloads/
    python tools/build_downloads.py --check    fail if downloads/ is out of date
"""
import argparse
import html
import os
import re
import sys
import tempfile
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "downloads")
TEXT = {".py", ".md", ".html", ".js", ".json", ".command", ".bat", ".txt", ""}
SITE = "https://aenimaa.github.io/figma-offline-kit/"
REPO_URL = "https://github.com/aenimaa/figma-offline-kit"
NAMES = {"windows": "figma-offline-kit-windows.zip", "macos": "figma-offline-kit-macos.zip"}


def version_and_date():
    sys.path.insert(0, REPO)
    from kit import VERSION
    with open(os.path.join(REPO, "CHANGELOG.md"), encoding="utf-8") as f:
        m = re.search(r"^## " + re.escape(VERSION) + r" \((\d{4})-(\d\d)-(\d\d)\)", f.read(), re.M)
    if not m:
        sys.exit(f"CHANGELOG.md has no '## {VERSION} (YYYY-MM-DD)' heading")
    return VERSION, tuple(int(x) for x in m.groups()) + (12, 0, 0)


def app_files():
    """(path in the ZIP, source path) for app/ and guides/, sorted."""
    out = [("app/kit.py", "kit.py"), ("app/LICENSE", "LICENSE"), ("app/CHANGELOG.md", "CHANGELOG.md")]
    for folder, ext in (("kit", ".py"), ("templates", "")):
        for name in sorted(os.listdir(os.path.join(REPO, folder))):
            if os.path.isfile(os.path.join(REPO, folder, name)) and name.endswith(ext) and not name.startswith("."):
                out.append((f"app/{folder}/{name}", f"{folder}/{name}"))
    for name in sorted(os.listdir(os.path.join(REPO, "docs"))):
        if name.endswith(".md"):
            out.append((f"guides/{name}", f"docs/{name}"))
    return out


def read_text(src, crlf=False):
    with open(os.path.join(REPO, src), "rb") as f:
        data = f.read().replace(b"\r\n", b"\n")
    return data.replace(b"\n", b"\r\n") if crlf else data


def read_me_first(os_name, version):
    win = os_name == "windows"
    start = "Start.bat" if win else "Start.command"
    env = r"C:\Users\<you>\figma-backup\workstation\.env" if win else "/Users/<you>/figma-backup/workstation/.env"
    blocked_en = ("" if win else
                  "<p class=note>macOS may block <b>Start.command</b> the first time, because it came from the internet. "
                  "Open <b>System Settings → Privacy &amp; Security</b>, scroll down and click <b>Open Anyway</b>. "
                  "Or right-click the file → <b>Open</b>.</p>")
    blocked_fa = ("" if win else
                  "<p class=note>ممکن است مک بار اول <b dir=ltr>Start.command</b> را باز نکند، چون از اینترنت آمده. "
                  "<b>System Settings → Privacy &amp; Security</b> را باز کنید، پایین بروید و <b>Open Anyway</b> را بزنید. "
                  "یا روی فایل راست‌کلیک کنید و <b>Open</b> را بزنید.</p>")
    smart_en = ('<p class=note><b>Before you unzip</b>, to skip Windows’ warnings: right-click the ZIP → <b>Properties</b> → tick <b>Unblock</b> → <b>OK</b>. Otherwise Windows asks “Open File – Security Warning: the publisher could not be verified. Are you sure you want to run this software?”: click <b>Run</b>. If it shows “Windows protected your PC”, click <b>More info → Run anyway</b>. If Start says “Extract the ZIP first”, right-click the ZIP → <b>Extract All…</b> and use the new folder.</p>'
                if win else "")
    smart_fa = ('<p class=note><b>قبل از باز کردن ZIP</b>، برای اینکه ویندوز هشدار ندهد: روی ZIP راست\u200cکلیک کنید ← <b>Properties</b> ← تیک <b>Unblock</b> ← <b>OK</b>. وگرنه ویندوز می\u200cپرسد «Open File – Security Warning … Are you sure you want to run this software?»؛ دکمهٔ <b>Run</b> را بزنید. اگر «Windows protected your PC» آمد، <b>More info</b> و بعد <b>Run anyway</b>. اگر Start گفت «Extract the ZIP first»، روی ZIP راست\u200cکلیک کنید ← <b>Extract All…</b> و از پوشهٔ تازه استفاده کنید.</p><p class=note>ترمینال ویندوز فارسی را برعکس و جدا\u200cجدا نشان می\u200cدهد، برای همین پنجرهٔ Start در ویندوز انگلیسی است؛ اگر فارسی را انتخاب کنید، گزارش (REPORT.md) و صفحه\u200cها فارسی می\u200cشوند.</p>'
                if win else "")
    py_en = ("If Python is missing, Start.bat offers to install it with winget (Windows’ own installer) and asks first."
             if win else "If Python is missing, Start.command offers to install it (with Homebrew, or the python.org "
             "installer) and asks first.")
    py_fa = ("اگر پایتون نصب نباشد، Start.bat پیشنهاد می‌دهد آن را با winget (نصب‌کنندهٔ خود ویندوز) نصب کند؛ اول از شما می‌پرسد."
             if win else "اگر پایتون نصب نباشد، Start.command پیشنهاد می‌دهد نصبش کند (با Homebrew یا نصب‌کنندهٔ python.org)؛ اول از شما می‌پرسد.")
    hidden_en = "" if win else " Finder hides files that start with a dot; the guided start opens it in TextEdit for you."
    hidden_fa = "" if win else " فایندر فایل‌هایی را که با نقطه شروع می‌شوند پنهان می‌کند؛ راهنما خودش آن را در TextEdit باز می‌کند."
    e = html.escape
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>figma-offline-kit: read me first</title>
<style>
  :root {{ --bg:#fff; --fg:#1d2330; --muted:#5b6475; --line:#e3e6ee; --accent:#2457c9; --box:#f4f6fb; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#14171e; --fg:#e8ebf2; --muted:#a3abbb; --line:#2c323e; --accent:#7ea2ff; --box:#1c212b; }} }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.6 system-ui, -apple-system, "Segoe UI", Tahoma, sans-serif; }}
  main {{ max-width:720px; margin:0 auto; padding:32px 16px 48px; }}
  section + section {{ border-top:1px solid var(--line); margin-top:32px; padding-top:24px; }}
  h1 {{ font-size:24px; margin:0 0 4px; }} h2 {{ font-size:18px; margin:24px 0 8px; }}
  p, li {{ margin:6px 0; }} ol {{ padding-inline-start:22px; }}
  code {{ background:var(--box); border:1px solid var(--line); border-radius:6px; padding:1px 6px; font-size:14px; overflow-wrap:anywhere; }}
  .sub {{ color:var(--muted); margin:0; }} .note {{ background:var(--box); border-radius:8px; padding:8px 12px; }}
  a {{ color:var(--accent); }} [dir=rtl] {{ font-family:Tahoma, "Segoe UI", system-ui, sans-serif; }}
  nav {{ text-align:end; font-size:14px; }}
</style>
</head>
<body>
<main>
<nav><a href="#fa">فارسی</a></nav>
<section lang="en">
  <h1>figma-offline-kit {e(version)}</h1>
  <p class="sub">Back up your Figma team to this computer, and keep working when Figma or the internet is down.</p>
  <h2>Start in three steps</h2>
  <ol>
    <li><b>Python 3.10 or newer</b> must be installed: the kit runs on it (free, from python.org). {e(py_en)}</li>
    <li><b>Double-click <code>{start}</code></b>. It asks your language (فارسی / English), then walks you through every step and picks up where you left off.</li>
    <li><b>Your Figma token:</b> make a read-only token in Figma (<a href="guides/figma-token.md">how</a>). Then either paste it into <b><code>Figma token.txt</code></b> in this folder and save, or let Start ask you for it (hidden). Start keeps it in<br><code>{e(env)}</code><br>(or <code>workstation/.env</code> inside the backup folder you chose) and empties <code>Figma token.txt</code> again.{e(hidden_en)}</li>
  </ol>
  {blocked_en}{smart_en}
  <h2>What’s in this folder</h2>
  <p><code>{start}</code> starts the kit. <code>Figma token.txt</code> is where you can paste your token. <code>REPORT.md</code> in your backup folder records every setting, step and decision. <code>app/</code> is the kit itself: no need to open it. <code>guides/</code> has the guides (token, local copies, design tokens, handoff, FAQ, troubleshooting). Commands in the guides, like <code>python kit.py status</code>, run inside <code>app/</code>.</p>
  <h2>With an AI assistant?</h2>
  <p>Use the full repository instead: <a href="{REPO_URL}">{REPO_URL}</a>. It has <code>AGENTS.md</code>, the instructions your AI app reads.</p>
  <p class="sub"><a href="{SITE}">Website and live demo</a> · MIT license (<code>app/LICENSE</code>)</p>
</section>
<section lang="fa" dir="rtl" id="fa">
  <h1>figma-offline-kit {e(version)}</h1>
  <p class="sub">از تیم فیگمای خود روی همین کامپیوتر نسخهٔ پشتیبان بگیرید تا وقتی فیگما یا اینترنت قطع است، کارتان متوقف نشود.</p>
  <h2>شروع در سه قدم</h2>
  <ol>
    <li><b>پایتون ۳٫۱۰ یا جدیدتر</b> باید نصب باشد؛ کیت با آن کار می‌کند (رایگان، از python.org). {e(py_fa)}</li>
    <li><b>روی <code dir="ltr">{start}</code> دوبار کلیک کنید.</b> اول زبان را می‌پرسد (فارسی / English)، بعد قدم‌به‌قدم همراهتان است و از همان جایی که مانده‌اید ادامه می‌دهد.</li>
    <li><b>توکن فیگما:</b> در فیگما یک توکن فقط‌خواندنی بسازید (<a href="guides/figma-token.md">روش</a>). بعد یا آن را در فایل <b><code dir="ltr">Figma token.txt</code></b> همین پوشه بچسبانید و ذخیره کنید، یا بگذارید Start از شما بپرسد (دیده نمی‌شود). Start آن را اینجا نگه می‌دارد:<br><code dir="ltr">{e(env)}</code><br>(یا <code dir="ltr">workstation/.env</code> داخل پوشهٔ پشتیبانی که انتخاب کرده‌اید) و <code dir="ltr">Figma token.txt</code> را دوباره خالی می‌کند.{e(hidden_fa)}</li>
  </ol>
  {blocked_fa}{smart_fa}
  <h2>در این پوشه چه هست</h2>
  <p><code dir="ltr">{start}</code> کیت را شروع می‌کند. <code dir="ltr">Figma token.txt</code> جایی است که می‌توانید توکن را بچسبانید. فایل <code dir="ltr">REPORT.md</code> در پوشهٔ پشتیبان همهٔ تنظیمات، قدم‌ها و تصمیم‌ها را ثبت می‌کند. <code>app/</code> خود کیت است و لازم نیست بازش کنید. <code>guides/</code> راهنماها را دارد (توکن، نسخهٔ محلی، توکن‌های طراحی، تحویل به برنامه‌نویس، پرسش‌ها، رفع اشکال). دستورهای راهنماها، مثل <code dir="ltr">python kit.py status</code>، داخل <code>app/</code> اجرا می‌شوند.</p>
  <h2>با دستیار هوش مصنوعی؟</h2>
  <p>به‌جای این بسته، مخزن کامل را بگیرید: <a href="{REPO_URL}" dir="ltr">{REPO_URL}</a>. فایل <code>AGENTS.md</code> در آن است که برنامهٔ هوش مصنوعی می‌خواند.</p>
  <p class="sub"><a href="{SITE}">وب‌سایت و نمونهٔ زنده</a> · مجوز MIT (<code dir="ltr">app/LICENSE</code>)</p>
</section>
</main>
</body>
</html>
"""


def entries(os_name, version):
    """(path in the ZIP, bytes, unix mode) for one download, in a fixed order."""
    win = os_name == "windows"
    start = ("Start.bat", read_text("start.bat", crlf=True), 0o644) if win else \
            ("Start.command", read_text("start.command"), 0o755)
    sys.path.insert(0, REPO)
    from kit.workspace import TOKEN_FILE, TOKEN_FILE_TEMPLATE
    token = TOKEN_FILE_TEMPLATE.encode("utf-8")
    out = [start, ("Read me first.html", read_me_first(os_name, version).encode("utf-8"), 0o644),
           (TOKEN_FILE, token.replace(b"\n", b"\r\n") if win else token, 0o644)]
    for arc, src in app_files():
        ext = os.path.splitext(src)[1]
        if ext in TEXT:
            data = read_text(src)
        else:
            with open(os.path.join(REPO, src), "rb") as f:
                data = f.read()
        out.append((arc, data, 0o644))
    return out


def write_zip(path, items, date):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        dirs = sorted({a.rsplit("/", 1)[0] + "/" for a, _, _ in items if "/" in a})
        for d in dirs:
            zi = zipfile.ZipInfo(d, date)
            zi.create_system = 3
            zi.external_attr = (0o40755 << 16) | 0x10
            z.writestr(zi, b"")
        for arc, data, mode in items:
            zi = zipfile.ZipInfo(arc, date)
            zi.create_system = 3  # Unix, so macOS keeps the mode bits (755 for Start.command)
            zi.external_attr = (0o100000 | mode) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
    os.replace(tmp, path)
    return path


def _bytes(path):
    with open(path, "rb") as f:
        return f.read()


def build(out_dir=OUT):
    version, date = version_and_date()
    return [write_zip(os.path.join(out_dir, NAMES[o]), entries(o, version), date) for o in ("windows", "macos")]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build downloads/figma-offline-kit-{windows,macos}.zip")
    ap.add_argument("--out", default=OUT, help="output folder (default: downloads/)")
    ap.add_argument("--check", action="store_true", help="fail if the ZIPs in --out differ from a fresh build")
    a = ap.parse_args(argv)
    if a.check:
        with tempfile.TemporaryDirectory() as tmp:
            stale = []
            for fresh in build(tmp):
                old = os.path.join(a.out, os.path.basename(fresh))
                if not os.path.exists(old) or _bytes(old) != _bytes(fresh):
                    stale.append(os.path.basename(fresh))
        print("downloads are current" if not stale else "out of date: " + ", ".join(stale)
              + " (run python tools/build_downloads.py)")
        return 1 if stale else 0
    for p in build(a.out):
        with zipfile.ZipFile(p) as z:
            n = len([i for i in z.infolist() if not i.is_dir()])
        print(f"{os.path.relpath(p, REPO)}: {n} files, {os.path.getsize(p) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
