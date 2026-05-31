#!/usr/bin/env python3
"""
daniel-site — lean static site generator.

Mirrors the conventions of the Entuned brand-site SSG (separate repo) so the
mental model is identical, but with none of the blog-renderer / og-image / data-viz
machinery. Pure stdlib, no dependencies.

How it works:
  1. Edit source in _src/  (layout, partials, pages/<name>/config.json + sections/)
  2. Run `python3 build.py`
  3. Built HTML appears at the repo root

Never edit the built root-level .html files directly — they are overwritten on build.
"""

import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "_src")
PAGES = os.path.join(SRC, "pages")
LAYOUT = os.path.join(SRC, "layouts", "base.html")
PARTIALS = os.path.join(SRC, "partials")

SITE_URL = "https://danielchristopherfox.com"


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def load_partial(name):
    p = os.path.join(PARTIALS, name)
    return read(p) if os.path.exists(p) else ""


def build_sections(page_dir):
    """Concatenate sections/*.html in filename order. Fragments only — no doctype."""
    sec_dir = os.path.join(page_dir, "sections")
    if not os.path.isdir(sec_dir):
        return ""
    parts = []
    for fname in sorted(os.listdir(sec_dir)):
        if fname.endswith(".html"):
            parts.append(read(os.path.join(sec_dir, fname)))
    return "\n".join(parts)


def render_page(page_dir, base, header, footer):
    cfg_path = os.path.join(page_dir, "config.json")
    if not os.path.exists(cfg_path):
        return None
    cfg = json.loads(read(cfg_path))

    output = cfg["output"]
    out_path = os.path.join(ROOT, output)

    # Path-traversal guard: output must stay inside the repo root.
    if not os.path.abspath(out_path).startswith(ROOT):
        raise ValueError(f"Refusing to write outside repo root: {output}")

    # Redirect stub (meta-refresh), skips the full layout.
    if "redirect_to" in cfg:
        dest = html.escape(cfg["redirect_to"], quote=True)
        stub = (
            "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta http-equiv=\"refresh\" content=\"0; url={dest}\">"
            "<meta name=\"robots\" content=\"noindex\">"
            f"<link rel=\"canonical\" href=\"{dest}\"></head>"
            f"<body>Redirecting to <a href=\"{dest}\">{dest}</a>.</body></html>"
        )
        write(out_path, stub)
        return output

    depth = output.count("/")
    nav_prefix = "../" * depth
    canonical = f"{SITE_URL}/{output}".replace("/index.html", "/")

    content = build_sections(page_dir)
    schema = cfg.get("schema", "")

    page = base
    page = page.replace("{{title}}", html.escape(cfg.get("title", ""), quote=True))
    page = page.replace(
        "{{meta_description}}",
        html.escape(cfg.get("meta_description", ""), quote=True),
    )
    page = page.replace("{{canonical}}", html.escape(canonical, quote=True))
    page = page.replace("{{robots}}", cfg.get("robots", "index, follow"))
    page = page.replace("{{schema}}", schema)
    page = page.replace("{{header}}", header)
    page = page.replace("{{footer}}", footer)
    page = page.replace("{{content}}", content)
    # nav_prefix LAST — header/footer partials and content may contain it too.
    page = page.replace("{{nav_prefix}}", nav_prefix)

    write(out_path, page)
    return output


def main():
    if not os.path.exists(LAYOUT):
        print("ERROR: missing _src/layouts/base.html", file=sys.stderr)
        sys.exit(1)

    base = read(LAYOUT)
    header = load_partial("header.html")
    footer = load_partial("footer.html")

    built = []
    for name in sorted(os.listdir(PAGES)):
        page_dir = os.path.join(PAGES, name)
        if not os.path.isdir(page_dir):
            continue
        out = render_page(page_dir, base, header, footer)
        if out:
            built.append(out)

    print(f"Built {len(built)} pages:")
    for o in built:
        print(f"  - {o}")


if __name__ == "__main__":
    main()
