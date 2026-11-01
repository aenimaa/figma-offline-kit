"""<workspace>/REPORT.md: one page a person can read later, rebuilt section by section as the job moves on.

Sections: settings (the decisions, in plain words), doctor, plan, pages, run, copies, tokens, close, and a dated log
with one line per step or decision and who made it. Never holds the token."""
import os
import re
import time

from .util import write_text

ORDER = ["summary", "log", "config", "doctor", "plan", "pages", "run", "copies", "tokens", "close"]  # log near the top
HEAD = {"en": ("# Figma backup report",
               "Written by figma-offline-kit: what happened (newest first), your settings, each step and its result. "
               "Edits here are overwritten."),
        "fa": ("# گزارش پشتیبان فیگما",
               "این فایل را figma-offline-kit می‌نویسد: آنچه اتفاق افتاد (تازه‌ترین بالا)، تنظیمات شما، هر قدم و نتیجه‌اش. "
               "ویرایش‌های اینجا بازنویسی می‌شوند.")}
_SECTION = re.compile(r"<!-- kit:(\w+) -->\n(.*?)<!-- /kit:\1 -->\n?", re.S)

# Who is acting, for the log: "start" while the guided start runs, "kit" in the background run, else a command.
ACTOR = {"who": None}
WHO = {"start": ("you, in Start", "شما، در Start"), "kit": ("the kit, in the background", "کیت، در پس‌زمینه"),
       None: ("command line or AI", "خط فرمان یا هوش مصنوعی")}


def _read(ws):
    if not os.path.exists(ws.report_path) and os.path.exists(ws.old_report_path):
        os.replace(ws.old_report_path, ws.report_path)  # before 1.2 the report lived in workstation/
    if not os.path.exists(ws.report_path):
        return {}
    with open(ws.report_path, encoding="utf-8") as f:
        return {m.group(1): m.group(2) for m in _SECTION.finditer(f.read())}


def _write(ws, parts):
    fa = _lang(ws) == "fa"
    title, intro = HEAD["fa" if fa else "en"]
    out = [title + "\n"]
    if fa:  # right-to-left in GitHub, VS Code and other Markdown previews (blank lines keep Markdown working inside)
        out.append('<div dir="rtl">\n')
    out.append(intro + "\n")
    for key in ORDER + sorted(set(parts) - set(ORDER)):
        if key in parts:
            out.append(f"<!-- kit:{key} -->\n{parts[key]}<!-- /kit:{key} -->\n")
    if fa:
        out.append("</div>\n")
    write_text(ws.report_path, "\n".join(out))


def update(ws, name, markdown):
    parts = _read(ws)
    # sections sit one level below the page title; shift only the new text (stored parts are already shifted)
    parts[name] = re.sub(r"^(#+) ", r"#\1 ", markdown.rstrip(), flags=re.M) + "\n"
    _write(ws, parts)


def _lang(ws):
    cfg = ws.config() or {}
    return cfg.get("language", "en")


lang_of = _lang  # the report's language (the settings' language)


LOG_TEXT = {
    "settings": ("Settings saved", "تنظیمات ذخیره شد"),
    "continued": ("Opened again with a new copy of the kit; settings kept", "با نسخهٔ تازهٔ کیت دوباره باز شد؛ تنظیمات همان ماند"),
    "language": ("Language: {lang}", "زبان: {lang}"),
    "token": ("Figma token added", "توکن فیگما اضافه شد"),
    "doctor_ok": ("Check: ready", "بررسی: آماده"),
    "doctor_no": ("Check: not ready ({items})", "بررسی: آماده نیست ({items})"),
    "scanned": ("Scanned Figma: {summary}", "فیگما خوانده شد: {summary}"),
    "pages": ("Pages confirmed: {pages} page(s) in {files} file(s)", "صفحه‌ها تأیید شد: {pages} صفحه در {files} فایل"),
    "run_start": ("Backup started", "پشتیبان‌گیری شروع شد"),
    "run_done": ("Backup finished: {screens} screens, {failed} failed", "پشتیبان‌گیری تمام شد: {screens} فریم، {failed} ناموفق"),
    "run_paused": ("Backup paused: {why}", "پشتیبان‌گیری متوقف شد: {why}"),
    "run_ended": ("Backup ended unexpectedly ({why}); resume continues it",
                  "پشتیبان‌گیری ناگهان تمام شد ({why})؛ ادامه دادن ممکن است"),
    "stop": ("Pause asked", "درخواست توقف"),
    "closed": ("Checked and packed: {checked} files checked, {problems} problems",
               "وارسی و آرشیو: {checked} فایل وارسی شد، {problems} مشکل"),
    "refresh": ("Changed in Figma, queued again: {names}", "در فیگما عوض شده و دوباره در صف است: {names}"),
}


def log(ws, text, who=None, **kw):
    """Add one dated line to the Log section: what happened and who did it. `text` is a LOG_TEXT key or plain
    text. Never pass the token."""
    if not ws or not ws.exists():
        return
    parts = _read(ws)
    lang = _lang(ws)
    if text in LOG_TEXT:
        if lang == "fa":  # Persian digits for counts in Persian lines
            from .i18n import fa_digits
            kw = {k: fa_digits(v) if isinstance(v, (int, float)) else v for k, v in kw.items()}
        text = LOG_TEXT[text][1 if lang == "fa" else 0].format(**kw)
    actor = WHO.get(who if who is not None else ACTOR["who"], WHO[None])[1 if lang == "fa" else 0]
    lines = (parts.get("log") or "").rstrip("\n").split("\n")
    head = lines[0] if lines and lines[0].startswith("## ") else "## " + ("گزارش کارها" if lang == "fa" else "Log")
    entries = [ln for ln in lines[1:] if ln.startswith("- ")]
    entries.insert(0, f"- {time.strftime('%Y-%m-%d %H:%M')} · {text} ({actor})")  # newest first
    parts["log"] = head + "\n\n" + "\n".join(entries) + "\n"
    _write(ws, parts)


CONFIG_TEXT = {
    "title": ("Settings: your decisions", "تنظیمات: تصمیم‌های شما"),
    "folder": ("Backup folder", "پوشهٔ پشتیبان"),
    "source": ("What is backed up", "از چه چیزی پشتیبان گرفته می‌شود"),
    "team": ("the whole team {id}", "کل تیم {id}"),
    "files": ("{n} file(s) by link: {keys}", "{n} فایل با لینک: {keys}"),
    "mode": ("How it runs", "نحوهٔ اجرا"),
    "full": ("all in one go, to the end", "همه با هم تا آخر"),
    "project": ("pause after each project", "مکث بعد از هر پروژه"),
    "file": ("pause after each file", "مکث بعد از هر فایل"),
    "pages": ("Pages", "صفحه‌ها"),
    "all-except-archive": ("all except archive pages (names with: {words})", "همه به‌جز صفحه‌های آرشیو (اسم‌های دارای: {words})"),
    "named": ("only these: {names}", "فقط این‌ها: {names}"),
    "pick": ("you pick them per file after the scan", "بعد از خواندن فیگما، برای هر فایل خودتان انتخاب می‌کنید"),
    "formats": ("Screen formats", "فرمت فریم‌ها"),
    "extras": ("Extras", "امکانات اضافه"),
    "none": ("none", "هیچ"),
    "coverage": ("coverage page", "صفحهٔ پوشش"), "drift": ("drift check", "بررسی تغییرات"),
    "archives": ("archives ({fmt})", "آرشیو ({fmt})"), "tokens": ("design tokens", "توکن‌های طراحی"),
    "handoff": ("dev handoff", "تحویل به برنامه‌نویس"),
    "copies": ("Local .fig copies", "نسخهٔ محلی fig"),
    "auto": ("automatic, by an AI with desktop control", "خودکار، با هوش مصنوعیِ دارای کنترل دسکتاپ"),
    "guided": ("guided: you press Save local copy for each file", "راهنمایی‌شده: برای هر فایل خودتان Save local copy را می‌زنید"),
    "skip": ("skipped", "نه"),
    "language": ("Language", "زبان"),
    "token": ("Figma token", "توکن فیگما"),
    "token_where": ("kept in {path} (never written here)", "در {path} (هرگز اینجا نوشته نمی‌شود)"),
}


def config_md(cfg, env_path=None):
    """The interview answers as plain decisions, in the chosen language."""
    fa = cfg.get("language") == "fa"

    def T(key, **kw):
        return CONFIG_TEXT[key][1 if fa else 0].format(**kw)

    p = cfg["pages"]
    pages = T(p["rule"], words=", ".join(p["archive_words"]), names=", ".join(p["names"]))
    extras = [T(k, fmt=cfg["archive_format"]) for k, v in cfg["addons"].items() if v] or [T("none")]
    source = (T("team", id=cfg["team"]["id"]) if cfg["team"]["id"] else
              T("files", n=len(cfg.get("files", [])), keys=", ".join(cfg.get("files", []))))
    sep = "، " if fa else ", "
    rows = [(T("folder"), cfg["workspace"]), (T("source"), source), (T("mode"), T(cfg["mode"])), (T("pages"), pages),
            (T("formats"), sep.join(x.upper() for x in cfg["formats"])), (T("extras"), sep.join(extras)),
            (T("copies"), T(cfg["local_copies"])), (T("language"), "فارسی" if fa else "English")]
    if env_path:
        rows.append((T("token"), T("token_where", path=env_path)))
    return f"# {T('title')}\n\n" + "\n".join(f"- **{k}:** {v}" for k, v in rows) + "\n"
