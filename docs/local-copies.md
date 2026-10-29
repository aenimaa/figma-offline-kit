# Local copies (.fig / .jam / .deck / .make)

A local copy is the whole file as Figma desktop saves it with **Save local copy**. It can be opened again with Figma → Import, or dragged into Figma. Figma has no API for this, so the kit keeps a checklist and either the AI (automatic) or the user (guided) does the saving.

| Command | What it does |
|---|---|
| `python kit.py copies` | the checklist: number, project, file, state, and today's count |
| `python kit.py copies next` | the next file to save, and how long to wait before opening it (JSON) |
| `python kit.py copies open <n>` | opens file `<n>` in Figma desktop and prints where to save it |
| `python kit.py copies check` | ticks off every copy on disk; files saved to the inbox or Downloads are moved into place |
| `python kit.py copies watch` | keeps checking until every opened file is saved (guided mode) |
| `python kit.py copies skip <n> --reason "view only"` | for files that can't be saved (no edit access, for example) |

**Pacing:** at most ≈ 40 copies a day and ≥ 60 s between files. Faster, and Figma shows a bot check ("verify you are not a bot"). `copies open` refuses until it's safe; don't use `--force` to rush.

## Guided (the user saves)
1. `python kit.py copies open <n>`. Figma desktop opens the file.
2. Tell the user: in Figma press **Ctrl+/** (**Cmd+/** on a Mac), type *Save local copy*, press Enter, wait for the image download to finish, and save the file to the folder the command printed. Saving to Downloads or `<workspace>/temp/incoming` also works: the kit moves it.
3. `python kit.py copies watch` ticks it off as soon as the file appears. Then the next file.

## Automatic (the AI saves, with desktop control)
Do one file at a time, in the foreground (background desktop control has been unreliable).

**Before the first file:** take a screenshot and write down the open Figma tabs. Those tabs belong to the user: never close them.

For each file:
1. `python kit.py copies next`. If `wait_seconds` > 0, wait; if it is -1, stop for today.
2. `python kit.py copies open <n>`. Wait ≈ 15 s, then screenshot. A freshly opened tab needs that long before shortcuts work.
3. Press **Esc**, then **Ctrl+/** (Cmd+/). Wait 2–3 s for Quick actions. Click the row **Save local copy…** (it is often already under Recents; typing into the panel can switch it into a component search, so prefer clicking). In a **Make** file Quick actions doesn't open: use the main menu (Figma logo, top-left) → File → Save local copy….
4. A toast shows "Downloading images… n / N". Wait until it's done (small files ≈ 20 s, big ones several minutes; poll every 30–60 s). Never click **Save partial file**.
5. The system Save dialog opens. Wait 2 s, click the **File name** box, select all, type the full target path from step 2, then **zoom in to check the box** before pressing Enter: the first typing is sometimes dropped. Retype if it's wrong.
6. `python kit.py copies check`. It must report the file; if not, look at the dialog and retry once.
7. Close the tab with Ctrl+W (Cmd+W) **only if you opened it**, while it is the active tab, after checking its full title.

**Seen on Figma desktop 126 (October 2026):** Quick actions opens with Ctrl+/ and typing *Save local copy* shows one result; click it. A 36 MB file with 67 images took ≈ 5 min to download (the counter stalls, then jumps). The Save dialog opens in the last folder used with the file name already selected: click the box, select all, type the full path, zoom to check, Enter. Saving works in Design or Dev Mode.

**Rules**
- Read coordinates from a fresh screenshot every time; screen sizes change between days and monitors. If screenshots show only wallpaper, Figma may be on another monitor: switch displays.
- Never edit the canvas: no typing there, no dragging, no deleting. A click on the canvas selects a frame; press Esc before any shortcut.
- Sign in, upgrade, share, accept terms, **Verify / CAPTCHA**, Publish: stop and tell the user. Don't click.
- On Windows an invisible text-input overlay can swallow keystrokes. If typing does nothing, click the target element first.
- Anything unexpected: screenshot, Esc, retry once, then `python kit.py copies skip <n> --reason "<what happened>"` and move on.
