# daniel-site

Personal authority site for **Daniel Fox — Retail Music Behaviorist**.
Static, evergreen, zero content treadmill. Built on a lean SSG that mirrors the
Entuned brand-site conventions (so it's the same muscle memory).

Strategy of record: `../projects/personal-brand/SSOT.md`.

## Build

```bash
python3 build.py        # generates root-level .html from _src/
python3 -m http.server 8000   # preview at http://localhost:8000
```

Never edit the built root `.html` files — they're overwritten. Edit source in `_src/`.

## Structure

```
_src/
  layouts/base.html       ← HTML shell (head, schema slot, fonts, JS)
  partials/header.html    ← shared nav  (edit once, updates all pages)
  partials/footer.html    ← shared footer
  pages/<name>/
    config.json           ← title, meta_description, output, optional "schema"
    sections/*.html       ← body fragments, concatenated in filename order
styles.css                ← global stylesheet (gold-forward, Entuned-adjacent)
CNAME                     ← danielchristopherfox.com
build.py                  ← the generator (stdlib only, no deps)
```

Pages live at: `index.html` (home), `the-work.html`, `writing.html`,
`speaking.html`, `contact.html`.

## Wired values (filled 2026-05-31)

- YouTube: `https://www.youtube.com/@entuned` (channel ID `UCoYSpjqFPQTsaJGF90r7K2w`; homepage embeds uploads playlist `UUoYSpjqFPQTsaJGF90r7K2w` — auto-refreshes)
- LinkedIn: `https://www.linkedin.com/in/danielcfox/`
- Contact: `daniel@entuned.co`

No `REPLACE_` tokens remain. Before publishing, **verify asset counts** (videos published / finished, blog posts) before
any number is stated publicly — none are hard-coded into copy yet, by design.

## Deploy (when ready)

New GitHub repo → GitHub Pages, custom domain `danielchristopherfox.com`.
A deploy workflow that runs `python3 build.py` on push can be copied from the
brand-site repo's `.github/workflows/deploy.yml`. Point `speakwithdaniel.com`
at `/speaking` (301 or a thin landing that canonicals back here).
