"""Text for the guided start (`kit.py start`) in English and Persian.

Terminals on Windows don't lay out right-to-left text (no bidi), so the Persian lines are kept short and paths,
commands and other Latin terms go on lines of their own."""

LANGS = ("en", "fa")

MESSAGES = {
    "title": ("figma-offline-kit · guided start", "figma-offline-kit · راهنمای قدم‌به‌قدم"),
    "intro": ("Answer each question, or press Enter for the suggestion in [brackets]. Ctrl+C stops at any time.",
              "به هر سؤال جواب بدهید.\nبا Enter پیشنهاد داخل [ ] انتخاب می‌شود.\nبا Ctrl+C هر وقت خواستید متوقف کنید."),
    "fa_check": ("Persian check: is the line above readable, with joined letters in the right order?",
                 "Persian check: is the line above readable, with joined letters in the right order?"),
    "fa_sample": ("", "این یک خط آزمایشی فارسی است."),
    "fa_fallback": ("OK, English from here. The reports can still be read in any editor.",
                    "OK, English from here."),
    "step": ("Step {n} of {total} · {title}", "قدم {n} از {total} · {title}"),
    "t_setup": ("Setup", "تنظیمات"),
    "t_token": ("Figma token", "توکن فیگما"),
    "t_check": ("Check", "بررسی"),
    "t_scan": ("Scan Figma", "خواندن فیگما"),
    "t_pages": ("Pages", "صفحه‌ها"),
    "t_backup": ("Backup", "پشتیبان‌گیری"),
    "setup_intro": ("A few questions: your Figma team or file links, where to save the backup, and how to run it.",
                    "چند سؤال کوتاه:\nلینک تیم یا فایل‌ها، محل ذخیره و نحوهٔ اجرا."),
    "token_need": ("The kit needs a read-only Figma token. How to make one:",
                   "کیت یک توکن فیگما (فقط خواندنی) لازم دارد.\nروش ساختنش:"),
    "token_file": ("It goes in this file (after FIGMA_TOKEN=):", "جای توکن این فایل است (بعد از FIGMA_TOKEN=):"),
    "token_hidden_file": ("Finder hides files whose names start with a dot: use option 2 to open it.",
                          "فایندر فایل‌هایی را که اسمشان با نقطه شروع می‌شود پنهان می‌کند.\nبرای باز کردنش گزینهٔ ۲ را بزنید."),
    "token_menu": ("  1. Paste it here (hidden)\n  2. Open the token file in {editor}, paste it there and save\n  3. Later",
                   "  ۱. همین‌جا بچسبانید (دیده نمی‌شود)\n  ۲. فایل توکن در {editor} باز شود، آنجا بچسبانید و ذخیره کنید\n  ۳. بعداً"),
    "token_paste": ("Paste the token with right-click or Ctrl+V (Cmd+V on a Mac), then press Enter.\n"
                    "Nothing shows while you paste: that's normal.\nToken (hidden): ",
                    "توکن را با راست‌کلیک یا Ctrl+V بچسبانید\n(در مک Cmd+V) و Enter بزنید.\nموقع چسباندن چیزی دیده نمی‌شود؛ عادی است.\n> "),
    "token_saved": ("✔ Token saved in:", "✔ توکن ذخیره شد در:"),
    "token_empty": ("No token yet: nothing was pasted.", "هنوز توکنی نیست؛ چیزی چسبانده نشد."),
    "token_opened": ("Opened in {editor}. On its last line, paste the token right after FIGMA_TOKEN= "
                     "(no space), save (Ctrl+S, or Cmd+S on a Mac), close it, then press Enter here.",
                     "فایل در {editor} باز شد.\nدر خط آخرش، توکن را درست بعد از FIGMA_TOKEN= بچسبانید (بدون فاصله)،\nذخیره کنید (Ctrl+S) و ببندید. بعد اینجا Enter بزنید."),
    "token_open_failed": ("Couldn't open an editor. Open the file above yourself.",
                          "ویرایشگر باز نشد. فایل بالا را خودتان باز کنید."),
    "token_works": ("✔ The token works (signed in as {who}).", "✔ توکن کار می‌کند. حساب:\n  {who}"),
    "token_refused": ("✖ Figma refused this token ({status}): it is wrong, expired, or lacks the read scopes. "
                      "Make a new one and try again.",
                      "✖ فیگما این توکن را قبول نکرد ({status}).\nاشتباه است، منقضی شده یا دسترسی خواندن ندارد.\nیک توکن تازه بسازید و دوباره امتحان کنید."),
    "token_untested": ("! Couldn't reach Figma to test the token. The check step tries again.",
                       "! برای آزمودن توکن به فیگما وصل نشد.\nقدم بررسی دوباره امتحان می‌کند."),
    "token_later": ("Start again when the token is in place.", "وقتی توکن را گذاشتید، دوباره شروع کنید."),
    "choice": ("> [1] ", "> [۱] "),
    "doctor_en": ("", "جزئیات زیر انگلیسی است."),
    "doctor_fix": ("Fix the items under “You need to do” above, then start again.",
                   "موارد زیرِ «You need to do» را درست کنید و دوباره شروع کنید."),
    "scan_q": ("Scan Figma now to see what's there? It only reads", "الان فیگما خوانده شود؟ چیزی تغییر نمی‌کند"),
    "pages_ok_q": ("Back up the pages marked ✔? (n = choose file by file)",
                   "صفحه‌های ✔ پشتیبان بگیرند؟\n(n = فایل‌به‌فایل انتخاب کنید)"),
    "pages_undecided": ("✖ {n} pages are still undecided. Start again to choose them.",
                        "✖ هنوز {n} صفحه انتخاب نشده.\nدوباره شروع کنید و انتخابشان کنید."),
    "pages_done": ("Confirmed: {pages} pages · ≈ {screens} screens · ≈ {minutes} min",
                   "تأیید شد: {pages} صفحه · حدود {screens} فریم · حدود {minutes} دقیقه"),
    "running": ("The backup is running in the background. You can close this window; start again any time to see progress.",
                "پشتیبان‌گیری در پس‌زمینه در حال اجراست.\nمی‌توانید این پنجره را ببندید.\nهر وقت خواستید دوباره شروع کنید تا پیشرفت را ببینید."),
    "run_start_q": ("Start the backup now? It runs in the background and keeps going if you close this window",
                    "پشتیبان‌گیری شروع شود؟\nدر پس‌زمینه اجرا می‌شود و با بستن پنجره متوقف نمی‌شود"),
    "run_continue_q": ("Continue the backup now? It runs in the background and keeps going if you close this window",
                       "پشتیبان‌گیری ادامه پیدا کند؟\nدر پس‌زمینه اجرا می‌شود و با بستن پنجره متوقف نمی‌شود"),
    "close_q": ("All screens are exported. Check everything and pack the archives now?",
                "همهٔ فریم‌ها خروجی گرفته شدند.\nحالا همه‌چیز وارسی و آرشیو شود؟"),
    "drift_q": ("Look for files that changed in Figma since the backup?",
                "فایل‌هایی که بعد از پشتیبان‌گیری در فیگما عوض شده‌اند پیدا شوند؟"),
    "rerun_q": ("Export the changed files again now?", "از فایل‌های عوض‌شده دوباره خروجی گرفته شود؟"),
    "ready": ("Your backup is ready in:", "پشتیبان شما آماده است در:"),
    "coverage_q": ("Open the coverage page?", "صفحهٔ پوشش (COVERAGE) باز شود؟"),
    "copies": ("Local .fig copies are a separate step with Figma desktop. Guide:",
               "نسخه‌های محلی fig قدم جداگانه‌ای با فیگمای دسکتاپ است.\nراهنما:"),
    "stopped": ("Stopped. Start again any time: it picks up where you left off.",
                "متوقف شد.\nهر وقت دوباره شروع کنید، از همین‌جا ادامه می‌دهد."),
    "press_enter": ("Press Enter to close this window.", "برای بستن پنجره Enter بزنید."),
    "yes_no": ("[Y/n]", "[Y/n]"),
    "no_yes": ("[y/N]", "[y/N]"),
    "in_zip": ("This is running from inside the ZIP. Extract the ZIP first (right-click it → Extract All), "
               "then double-click Start in the new folder.",
               "این از داخل فایل ZIP اجرا شده.\nاول ZIP را از حالت فشرده دربیاورید\n(راست‌کلیک → Extract All)،\nبعد Start را در پوشهٔ تازه باز کنید."),
    "report_where": ("Everything is written down in:", "همه‌چیز در این فایل نوشته می‌شود:"),
    "ws_ready": ("✔ Settings saved. Backup folder:", "✔ تنظیمات ذخیره شد. پوشهٔ پشتیبان:"),
    "token_where": ("Where it is kept:", "جای نگه‌داری آن:"),
    "token_drop": ("Or put it in this file next to Start (after FIGMA_TOKEN= on its last line), save it, and choose 2:",
                   "یا آن را در این فایل کنار Start بگذارید (بعد از FIGMA_TOKEN= در خط آخر)، ذخیره کنید و ۲ را بزنید:"),
    "token_moved": ("✔ Token taken from “{name}” (that file is empty again) and saved in:",
                    "✔ توکن از «{name}» برداشته شد (آن فایل دوباره خالی است)\nو اینجا ذخیره شد:"),
    "scanning": ("Scanning Figma, about 1.5 s per call (a big team takes a few minutes)…",
                 "در حال خواندن فیگما…\nهر درخواست حدود ۱٫۵ ثانیه؛ تیم بزرگ چند دقیقه طول می‌کشد."),
    "found": ("Found: {summary}", "پیدا شد: {summary}"),
    "run_started": ("✔ The backup started. It runs in the background and keeps going when you close this window.\n"
                    "Double-click Start again any time to see progress, or to pause it.",
                    "✔ پشتیبان‌گیری شروع شد.\nدر پس‌زمینه اجرا می‌شود و با بستن این پنجره متوقف نمی‌شود.\n"
                    "هر وقت خواستید Start را دوباره باز کنید تا پیشرفت را ببینید یا متوقفش کنید."),
    "progress": ("Progress: {done} of {files} files · {screens} screens{failed}",
                 "پیشرفت: {done} از {files} فایل · {screens} فریم{failed}"),
    "failed_n": (" · {n} failed", " · {n} ناموفق"),
    "now": ("Now: {name}", "الان: {name}"),
    "pause_q": ("Pause the backup?", "پشتیبان‌گیری متوقف شود؟"),
    "paused": ("OK: it pauses after the current batch of screens. Double-click Start again to continue.",
               "باشد؛ بعد از دستهٔ فعلی فریم‌ها متوقف می‌شود.\nبرای ادامه، Start را دوباره باز کنید."),
    "need": ("You need to do:", "باید انجام بدهید:"),
    "still_ready": ("✔ Everything is still ready (Python, internet, token, Figma).",
                    "✔ همه‌چیز هنوز آماده است (پایتون، اینترنت، توکن، فیگما)."),
    "coverage_q2": ("Open the coverage page? It links to the gallery of every file",
                    "صفحهٔ پوشش باز شود؟ به گالری همهٔ فایل‌ها لینک دارد"),
    "folder_q": ("Open the backup folder?", "پوشهٔ پشتیبان باز شود؟"),
    "watch_intro": ("Progress shows here. Closing this window does NOT stop the backup.\n"
                    "Keys: P = pause · Enter = stop watching (the backup keeps going)",
                    "پیشرفت اینجا نشان داده می‌شود. بستن این پنجره پشتیبان‌گیری را متوقف نمی‌کند.\n"
                    "کلیدها: P = توقف · Enter = بستن نمایش (پشتیبان‌گیری ادامه دارد)"),
    "watch_line": ("{file} · PNG {png} · SVG {svg} · {elapsed} so far · {left}",
                   "{file} · PNG {png} · SVG {svg} · {elapsed} گذشته · {left}"),
    "left": ("≈ {min} min left", "حدود {min} دقیقه مانده"),
    "left_soon": ("almost done", "تقریباً تمام"),
    "waiting": ("waiting…", "در انتظار…"),
    "starting": ("starting…", "در حال شروع…"),
    "file_done": ("✔ {name}: {n} screens", "✔ {name}: {n} فریم"),
    "file_failed": ("✖ {name}: {error}", "✖ {name}: {error}"),
    "wait_network": ("! Can't reach Figma: check your internet or VPN. The backup waits and goes on by itself.",
                     "! به فیگما وصل نمی‌شود: اینترنت یا VPN را بررسی کنید. پشتیبان‌گیری صبر می‌کند و خودش ادامه می‌دهد."),
    "wait_server": ("! Figma had a problem. The backup waits and goes on by itself.",
                    "! فیگما مشکل داشت. پشتیبان‌گیری صبر می‌کند و خودش ادامه می‌دهد."),
    "wait_rate": ("! Figma asked the kit to slow down. It waits as long as Figma asks.",
                  "! فیگما خواست آهسته‌تر برود. به همان اندازه صبر می‌کند."),
    "wait_count": ("Trying again in {secs} s · R = retry now · P = pause",
                   "{secs} ثانیهٔ دیگر دوباره · R = همین حالا · P = توقف"),
    "wait_count_rate": ("Going on in {secs} s · P = pause", "{secs} ثانیهٔ دیگر ادامه · P = توقف"),
    "retrying": ("Retrying now…", "همین حالا دوباره…"),
    "found_backup": ("Found an existing backup in this folder ({what}).", "در این پوشه یک پشتیبان پیدا شد ({what})."),
    "found_what": ("{names} · {done} of {files} files done · {screens} screens", "{names} · {done} از {files} فایل تمام · {screens} فریم"),
    "found_none": ("set up for {src}, not scanned yet", "برای {src}، هنوز خوانده نشده"),
    "continue_q": ("Continue it, with its settings? (n = answer the questions again)",
                   "همان را با همان تنظیمات ادامه بدهیم؟ (n = سؤال‌ها از نو)"),
    "stalled": ("No new screen for {min} min: a stalled download is tried again by itself · P = pause",
                "{min} دقیقه فریم تازه‌ای نیامده: دانلودِ گیرکرده خودش دوباره امتحان می‌شود · P = توقف"),
    "pausing": ("Pausing after the current batch of screens…", "بعد از دستهٔ فعلی فریم‌ها متوقف می‌شود…"),
    "watch_left": ("OK. The backup keeps going in the background. Double-click Start again to watch it.",
                   "باشد. پشتیبان‌گیری در پس‌زمینه ادامه دارد. برای دیدنش Start را دوباره باز کنید."),
    "run_done": ("✔ Backup finished: {screens} screens, {failed} failed.",
                 "✔ پشتیبان‌گیری تمام شد: {screens} فریم، {failed} ناموفق."),
    "retry_failed_q": ("{n} file(s) failed. Retry them now?", "{n} فایل ناموفق بود. دوباره امتحان شود؟"),
    "run_stopped": ("The backup stopped unexpectedly. It continues where it left off.",
                    "پشتیبان‌گیری ناگهان متوقف شد. از همان‌جا ادامه می‌دهد."),
}

# The guided start is for people without an AI: friendlier defaults and wording than the AI interview.
PERSON = {
    "mode": {"default": "full"},
    "local_copies": {
        "default": "skip",
        "en": {"ask": "Also save real .fig copies with Figma desktop? You press Save for each file, later.",
               "help": "Figma allows about 40 a day. You can switch this on later.",
               "options": {"guided": "Yes, later: the kit opens each file in Figma desktop, you press Save local copy",
                           "skip": "Not now"}},
        "fa": {"ask": "نسخهٔ واقعی fig هم با فیگمای دسکتاپ ذخیره شود؟\nبعداً برای هر فایل خودتان Save می‌زنید.",
               "help": "فیگما روزی حدود ۴۰ تا اجازه می‌دهد. بعداً هم می‌شود روشنش کرد.",
               "options": {"guided": "بله، بعداً: کیت فایل را در فیگمای دسکتاپ باز می‌کند، شما Save local copy را می‌زنید",
                           "skip": "فعلاً نه"}}},
}

SUMMARY = {
    "en": "{files} in {projects} · {pages} · ≈ {screens} · ≈ {minutes} min · {size}",
    "fa": "{files} فایل در {projects} پروژه · {pages} صفحه · حدود {screens} فریم · حدود {minutes} دقیقه · {size}",
}


def plan_summary(t, lang="en"):
    from .util import plural, size_text
    size = size_text(t.get("mb_est", t["gb_est"] * 1024))
    if lang == "fa":
        return fa_digits(SUMMARY["fa"].format(
            files=t["files"], projects=t["projects"], pages=t["pages"], screens=t["screens_est"],
            minutes=t["minutes_est"], size=size.replace("≈ ", "حدود ").replace("MB", "مگابایت").replace("GB", "گیگابایت")))
    return SUMMARY["en"].format(files=plural(t["files"], "file"), projects=plural(t["projects"], "project"),
                                pages=plural(t["pages"], "page"), screens=plural(t["screens_est"], "screen"),
                                minutes=t["minutes_est"], size=size)

# Persian text for the interview questions (kit/interview.py), shown by the guided start.
QUESTIONS_FA = {
    "workspace": {"ask": "پشتیبان در کدام پوشه ذخیره شود؟",
                  "help": "درایوی با فضای کافی انتخاب کنید؛ یک تیم کامل ممکن است ۱۰ گیگابایت یا بیشتر بشود."},
    "team": {"ask": "از چه چیزی پشتیبان گرفته شود؟\nلینک تیم، یا لینک یک یا چند فایل (با کاما جدا کنید).",
             "help": "کل تیم: آدرس تیم در فیگما\n  …/files/team/1234567890/…\nفایل‌ها: آدرس هر فایل\n  …/design/<key>/…"},
    "mode": {"ask": "پشتیبان‌گیری چطور اجرا شود؟",
             "options": {"full": "کامل: همه با هم تا آخر", "project": "پروژه‌به‌پروژه: بعد از هر پروژه مکث",
                         "file": "فایل‌به‌فایل: بعد از هر فایل مکث"}},
    "pages": {"ask": "از کدام صفحه‌های هر فایل خروجی گرفته شود؟",
              "options": {"all-except-archive": "همه به‌جز صفحه‌های آرشیو", "named": "فقط صفحه‌هایی که اسمشان را می‌دهم",
                          "pick": "بعد از برنامه‌ریزی، خودم برای هر فایل انتخاب می‌کنم"}},
    "page_names": {"ask": "اسم صفحه‌ها؟ (با کاما جدا کنید، دقیقاً همان اسم)", "help": "مثلاً: Ready for dev, Shipped"},
    "archive_words": {"ask": "کدام کلمه‌ها یعنی صفحهٔ آرشیو؟ (با کاما جدا کنید)",
                      "help": "صفحه‌ای که اسمش یکی از این کلمه‌ها را دارد در گزارش می‌آید ولی خروجی نمی‌گیرد."},
    "formats": {"ask": "فرمت فریم‌ها؟", "help": "اگر فیگما SVG نسازد، خودکار PDF گرفته می‌شود.",
                "options": {"png": "تصویر PNG", "svg": "وکتور SVG (متن، متن می‌ماند)"}},
    "addons": {"ask": "کدام امکانات اضافه؟ (شماره‌ها را با کاما جدا کنید)",
               "options": {"coverage": "صفحهٔ پوشش: پشتیبان چه چیزهایی دارد",
                           "drift": "تغییرات: کدام فایل‌ها بعداً در فیگما عوض شده‌اند",
                           "archives": "آرشیو: یک فایل فشرده برای هر پروژه",
                           "tokens": "توکن‌های طراحی: متغیرها به‌صورت CSS/SCSS",
                           "handoff": "تحویل به برنامه‌نویس: کد و مشخصات (فیگمای دسکتاپ لازم است)"}},
    "local_copies": {"ask": "نسخهٔ محلی (fig / jam / deck) از فیگمای دسکتاپ؟",
                     "help": "فیگما روزی حدود ۴۰ تا اجازه می‌دهد؛ تیم بزرگ چند روز طول می‌کشد.",
                     "options": {"auto": "خودکار: هوش مصنوعی ذخیره می‌کند (کنترل دسکتاپ لازم است)",
                                 "guided": "راهنمایی‌شده: فایل باز می‌شود، خودم Save می‌زنم",
                                 "skip": "نه، لازم نیست"}},
    "archive_format": {"ask": "فرمت آرشیو؟",
                       "options": {"zip": "zip (همه‌جا باز می‌شود)", "7z": "7z (کوچک‌تر، 7-Zip لازم است)",
                                   "rar": "rar (WinRAR لازم است)"}},
    "language": {"ask": "زبان گزارش‌ها و پیام‌ها؟", "options": {"en": "English", "fa": "فارسی"}},
}


FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_digits(value):
    """Persian digits for numbers shown in Persian text (typed answers accept both)."""
    return str(value).translate(FA_DIGITS)


def num(value, lang):
    return fa_digits(value) if lang == "fa" else str(value)


def t(key, lang="en", **kw):
    en, fa = MESSAGES[key]
    text = fa if lang == "fa" and fa else en
    if lang == "fa":  # numbers in Persian text get Persian digits; names and paths stay as they are
        kw = {k: fa_digits(v) if isinstance(v, (int, float)) else v for k, v in kw.items()}
    return text.format(**kw) if kw else text


def question(q, lang="en"):
    """(ask, help, [option labels]) for an interview question in the chosen language."""
    if lang != "fa":
        return q["ask"], q.get("help"), [o["label"] for o in q.get("options", [])]
    fa = QUESTIONS_FA.get(q["id"], {})
    labels = [fa.get("options", {}).get(o["value"], o["label"]) for o in q.get("options", [])]
    return fa.get("ask", q["ask"]), fa.get("help", q.get("help")), labels


def person_question(q, lang="en"):
    """The question as the guided start asks it: PERSON's default, options and wording where it has them."""
    p = PERSON.get(q["id"])
    if not p:
        return q
    q = dict(q, default=p.get("default", q["default"]))
    words = p.get(lang) or p.get("en")
    if words:
        q["options"] = [dict(o, label=words["options"][o["value"]]) for o in q["options"] if o["value"] in words["options"]]
        q["ask"], q["help"] = words["ask"], words.get("help")
        q["_translated"] = True
    return q


YES = {"y", "yes", "بله", "ب", "آره", "اره"}
NO = {"n", "no", "نه", "ن", "خیر"}
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize(raw):
    """Lower-case, trimmed, with Persian / Arabic digits turned into 0-9."""
    return raw.strip().translate(PERSIAN_DIGITS).lower()
