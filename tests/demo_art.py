"""Draw the made-up "Bloom" app screens used by the fake Figma server and the demo gallery.

Each screen is a small HTML page rendered to PNG with headless Chrome (fresh profile) into tests/demo_assets/.
Run once after changing a design: python -m tests.demo_art   (needs Google Chrome)"""
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "demo_assets")
BRAND, BG, INK, MUT, LINE = "#5A78DC", "#EEEEFF", "#1B1F2A", "#667085", "#E4E7EF"
CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
          "google-chrome", "chromium"]

BASE = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{{w}}px;height:{{h}}px;overflow:hidden;font-family:"Segoe UI",system-ui,sans-serif;color:{INK};background:#fff}}
.status{{height:44px;display:flex;justify-content:space-between;align-items:center;padding:0 24px;font-size:14px;font-weight:600}}
.btn{{display:block;text-align:center;background:{BRAND};color:#fff;border-radius:14px;padding:16px;font-weight:600;font-size:16px}}
.btn.ghost{{background:transparent;color:{BRAND};border:1.5px solid {LINE}}}
.field{{border:1.5px solid {LINE};border-radius:12px;padding:14px 16px;font-size:15px;color:{MUT}}}
.label{{font-size:13px;font-weight:600;margin:0 0 8px;color:{INK}}}
.leaf{{width:120px;height:120px;border-radius:50%;background:{BG};display:flex;align-items:center;justify-content:center}}
</style></head><body>{{body}}</body></html>"""

LEAF = f'<svg width="64" height="64" viewBox="0 0 64 64"><path d="M32 58C32 36 40 20 56 8 38 10 18 22 14 40c-2 9 4 16 12 16" fill="{BRAND}"/><path d="M32 58C30 44 24 34 12 26" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/></svg>'
STATUS = '<div class="status"><span>9:41</span><span>●●● ▮</span></div>'


def plant(name, note, hue):
    return (f'<div style="display:flex;gap:14px;align-items:center;padding:14px;border:1px solid {LINE};border-radius:16px;margin-bottom:12px">'
            f'<div style="width:56px;height:56px;border-radius:14px;background:{hue};display:flex;align-items:center;justify-content:center">'
            f'{LEAF.replace("64", "34", 2)}</div><div style="flex:1"><div style="font-weight:600;font-size:16px">{name}</div>'
            f'<div style="color:{MUT};font-size:13px;margin-top:2px">{note}</div></div><div style="color:{MUT};font-size:20px">›</div></div>')


SCREENS = {
    "1-1": (1440, 1024, f"""<div style="height:100%;background:linear-gradient(135deg,{BRAND},#8FA6F0);color:#fff;padding:120px;display:flex;flex-direction:column;justify-content:space-between">
      <div style="display:flex;align-items:center;gap:20px">{LEAF.replace(f'fill="{BRAND}"', 'fill="#fff"').replace('stroke="#fff"', f'stroke="{BRAND}"')}<span style="font-size:40px;font-weight:700">Bloom</span></div>
      <div><div style="font-size:120px;font-weight:700;line-height:1">Onboarding</div><div style="font-size:36px;opacity:.85;margin-top:24px">Sign-up flow · v2</div></div>
      <div style="display:flex;gap:16px"><span style="background:#fff;color:{BRAND};padding:12px 24px;border-radius:99px;font-size:22px;font-weight:600">✓ Ready for dev</span>
      <span style="border:2px solid rgba(255,255,255,.7);padding:10px 24px;border-radius:99px;font-size:22px">Mobile · iOS & Android</span></div></div>"""),
    "2-1": (390, 844, f"""{STATUS}<div style="padding:40px 28px;display:flex;flex-direction:column;height:800px">
      <div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:28px">
      <div class="leaf" style="width:180px;height:180px">{LEAF.replace('width="64" height="64"', 'width="96" height="96"')}</div>
      <div style="font-size:30px;font-weight:700;line-height:1.2">Grow happier plants</div>
      <div style="color:{MUT};font-size:16px;line-height:1.5">Watering reminders, light tips and a<br>diary for every plant in your home.</div></div>
      <a class="btn">Get started</a><a class="btn ghost" style="margin-top:12px">I already have an account</a></div>"""),
    "2-2": (390, 844, f"""{STATUS}<div style="padding:24px 28px"><div style="font-size:22px;color:{MUT}">‹</div>
      <div style="font-size:28px;font-weight:700;margin:28px 0 8px">What's your email?</div>
      <div style="color:{MUT};font-size:15px;margin-bottom:32px">We'll send your plant reminders there.</div>
      <div class="label">Email</div><div class="field" style="color:{INK}">sam@example.com</div>
      <div style="margin-top:420px"><a class="btn">Continue</a></div></div>"""),
    "2-6": (390, 844, f"""{STATUS}<div style="padding:24px 28px"><div style="font-size:22px;color:{MUT}">‹</div>
      <div style="font-size:28px;font-weight:700;margin:28px 0 8px">What's your email?</div>
      <div style="color:{MUT};font-size:15px;margin-bottom:32px">We'll send your plant reminders there.</div>
      <div class="label">Email</div><div class="field" style="color:{INK};border-color:#D92D20">sam@example.com</div>
      <div style="color:#B42318;font-size:14px;margin-top:8px">⚠ This email already has an account. <u>Log in instead</u></div>
      <div style="margin-top:390px"><a class="btn" style="opacity:.45">Continue</a></div></div>"""),
    "2-3": (390, 844, f"""{STATUS}<div style="padding:16px 24px"><div style="display:flex;justify-content:space-between;align-items:center">
      <div><div style="color:{MUT};font-size:14px">Good morning, Sam</div><div style="font-size:26px;font-weight:700">Your plants</div></div>
      <div style="width:44px;height:44px;border-radius:50%;background:{BG};position:relative"><span style="position:absolute;top:2px;right:2px;width:12px;height:12px;border-radius:50%;background:#FF0000"></span></div></div>
      <div style="background:{BRAND};color:#fff;border-radius:18px;padding:18px;margin:20px 0">
      <div style="font-size:13px;opacity:.85">Today</div><div style="font-size:19px;font-weight:600;margin-top:4px">3 plants need water</div>
      <div style="display:flex;gap:6px;margin-top:14px">{''.join('<span style="flex:1;height:6px;border-radius:3px;background:rgba(255,255,255,%s)"></span>' % o for o in ('1', '1', '.35', '.35', '.35'))}</div></div>
      {plant('Monstera', 'Water today · bright, indirect light', '#E3F1E6')}{plant('Snake plant', 'Water in 6 days', '#F3EEDF')}
      {plant('Pothos', 'Water today · trim soon', '#E6EBFA')}{plant('Fiddle leaf fig', 'Water today', '#F6E7E4')}
      <div style="position:absolute;left:0;right:0;bottom:0;height:84px;border-top:1px solid {LINE};display:flex;justify-content:space-around;align-items:center;font-size:12px;color:{MUT}">
      <span style="color:{BRAND};font-weight:600">● Home</span><span>○ Diary</span><span>○ Explore</span><span>○ Me</span></div></div>"""),
    "2-7": (200, 120, f"""<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:14px;height:100%">{''.join(
        f'<div style="background:{BG};border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px;color:{BRAND}">{c}</div>'
        for c in ['💧', '☀️', '🌱', '✂️', '📅', '🔔'])}</div>"""),
    "3-1": (1440, 4200, f"""<div style="padding:28px 120px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid {LINE}">
      <div style="display:flex;align-items:center;gap:12px">{LEAF.replace('width="64" height="64"', 'width="36" height="36"')}<b style="font-size:24px">Bloom</b></div>
      <div style="display:flex;gap:40px;color:{MUT};font-size:17px"><span>Features</span><span>Plants</span><span>Pricing</span><a class="btn" style="padding:10px 22px;font-size:16px">Get the app</a></div></div>
      <div style="padding:160px 120px;display:grid;grid-template-columns:1.1fr 1fr;gap:80px;align-items:center">
      <div><div style="font-size:84px;font-weight:700;line-height:1.05">Every plant,<br>happy and<br>watered.</div>
      <div style="color:{MUT};font-size:24px;margin:32px 0 44px;line-height:1.5">Reminders that fit each plant, light tips<br>for every room, and a diary to see them grow.</div>
      <a class="btn" style="display:inline-block;padding:20px 40px;font-size:20px">Download for free</a></div>
      <div style="height:640px;border-radius:40px;background:linear-gradient(160deg,{BG},#DCE3FB);display:flex;align-items:center;justify-content:center">{LEAF.replace('width="64" height="64"', 'width="260" height="260"')}</div></div>
      <div style="padding:80px 120px;display:grid;grid-template-columns:repeat(3,1fr);gap:32px">{''.join(
        f'<div style="border:1px solid {LINE};border-radius:24px;padding:40px"><div style="font-size:44px">{i}</div><div style="font-size:26px;font-weight:600;margin:20px 0 10px">{t}</div><div style="color:{MUT};font-size:18px;line-height:1.5">{d}</div></div>'
        for i, t, d in (('💧', 'Smart reminders', 'Each plant gets its own rhythm, adjusted for the season.'),
                        ('☀️', 'Light finder', 'Point your phone at a window and see which plants will love it.'),
                        ('📓', 'Plant diary', 'Photos and notes on one timeline, so you see what works.')))}</div>
      <div style="margin:120px;border-radius:40px;background:{BRAND};color:#fff;padding:120px;text-align:center">
      <div style="font-size:64px;font-weight:700">Loved by 40,000 plant people</div><div style="font-size:24px;opacity:.85;margin-top:20px">★★★★★ 4.8 on the App Store</div></div>
      <div style="padding:60px 120px;display:grid;grid-template-columns:repeat(2,1fr);gap:32px">{''.join(
        f'<div style="background:{BG};border-radius:24px;padding:48px;font-size:22px;line-height:1.6">“{q}”<div style="color:{MUT};font-size:18px;margin-top:20px">{n}</div></div>'
        for q, n in (('My fiddle leaf finally stopped dropping leaves.', 'Ana, Lisbon'), ('The only reminder app I never mute.', 'Kai, Osaka'),
                     ('I check the light finder before buying any plant now.', 'Mo, Toronto'), ('Simple, calm and actually useful.', 'Lea, Berlin')))}</div>
      <div style="margin:120px;padding-top:60px;border-top:1px solid {LINE};display:flex;justify-content:space-between;color:{MUT};font-size:18px"><span>© Bloom (a made-up app)</span><span>Privacy · Terms · Contact</span></div>"""),
    "3-2": (1440, 900, f"""<div style="height:100%;background:#0F1424;color:#fff;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:28px">
      <div style="width:120px;height:120px;border-radius:50%;background:rgba(255,255,255,.12);display:flex;align-items:center;justify-content:center;font-size:48px">▶</div>
      <div style="font-size:48px;font-weight:700">See Bloom in 60 seconds</div><div style="opacity:.7;font-size:22px">Hero video · autoplay, muted</div></div>"""),
    "3-3": (1440, 900, '<div style="height:100%;background:#fff"></div>'),
}


def chrome():
    for c in CHROME:
        if os.path.exists(c) or shutil.which(c):
            return shutil.which(c) or c
    raise SystemExit("Google Chrome not found")


def main():
    os.makedirs(OUT, exist_ok=True)
    exe, tmp = chrome(), tempfile.mkdtemp()
    try:
        for nid, (w, h, body) in SCREENS.items():
            page = os.path.join(tmp, nid + ".html")
            html = BASE.replace("{w}", str(w)).replace("{h}", str(h)).replace("{{", "{").replace("}}", "}").replace("{body}", body)
            with open(page, "w", encoding="utf-8") as f:
                f.write(html.replace("<body>", '<body style="position:relative">'))
            subprocess.run([exe, "--headless=new", "--disable-gpu", f"--user-data-dir={os.path.join(tmp, 'profile')}",
                            "--hide-scrollbars", "--force-device-scale-factor=1", f"--window-size={w},{h}",
                            f"--screenshot={os.path.join(OUT, nid + '.png')}", "file:///" + page.replace(os.sep, "/")],
                           check=True, capture_output=True)
            print("drew", nid, w, "x", h)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
