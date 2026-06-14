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
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "_src")
PAGES = os.path.join(SRC, "pages")
LAYOUTS = os.path.join(SRC, "layouts")
LAYOUT = os.path.join(LAYOUTS, "base.html")
PARTIALS = os.path.join(SRC, "partials")

SITE_URL = "https://danielchristopherfox.com"

# Google Analytics 4 measurement ID (gtag.js). Injected into every page via the
# shared head partial ({{ga_id}}). Property: danielchristopherfox.com.
GA_MEASUREMENT_ID = "G-S2LCQFZ9SG"

# The owned tagline (commercial hook) and the canonical descriptor. The tagline
# is the schema "slogan"; the two together form LIFTABLE — one consistent block
# reused as the Person schema description and echoed in visible copy + meta so
# engines and models lock onto one entity. Builder-forward by design (researches /
# designs / builds), with "Music Behaviorist" + Entuned retained as the durable
# disambiguation anchors against the other musical Daniel Foxes.
SLOGAN = "Daniel Fox helps brands engineer music that sells."
LIFTABLE = (
    SLOGAN + " He researches how music moves people, designs the systems, and "
    "builds the music that puts it to work for brands. Known as the Music "
    "Behaviorist, he is the founder of Entuned."
)

# Shared structured-data blocks. Every note/essay re-used the same author and
# publisher Person; define them once and inject at render time so configs only
# carry the per-page fields (headline/description/about).
SCHEMA_AUTHOR = {
    "@type": "Person",
    "name": "Daniel Christopher Fox",
    "alternateName": "Daniel Fox",
    "jobTitle": ["Music Behaviorist", "Retail Music Behaviorist"],
    "slogan": SLOGAN,
    "url": SITE_URL,
    "description": LIFTABLE,
    "worksFor": {"@type": "Organization", "name": "Entuned", "url": "https://entuned.co"},
    "knowsAbout": [
        "How music affects customer behavior",
        "Music and behavior",
        "Retail music",
        "Music psychology",
        "Consumer behavior",
        "Store atmospherics",
        "Sensory marketing",
        "Generative music",
    ],
    # sameAs is the disambiguation override: "this Daniel Fox is these accounts,
    # and no others." speakwithdaniel.com is intentionally absent — it 301s into
    # this hub, so it is *this* entity, not a separate corroborating profile.
    # Add producer profiles / bylines here only once they link back (reciprocity).
    "sameAs": [
        "https://www.wikidata.org/wiki/Q140128155",
        "https://entuned.co",
        "https://www.youtube.com/@entuned",
        "https://www.linkedin.com/in/danielcfox/",
    ],
}
SCHEMA_PUBLISHER = {"@type": "Person", "name": "Daniel Christopher Fox"}


def build_schema(schema, canonical, date_published=None, date_modified=None):
    """Render a structured schema dict into a <script type="application/ld+json">
    block. `schema` is {type, headline, description, about:[...]}; author,
    publisher and mainEntityOfPage(=canonical) are injected from module constants,
    dates (ISO strings) from the page config's top-level date_published /
    date_modified. Output is compact (no spaces) to match the hand-written
    strings it replaces.
    """
    data = {
        "@context": "https://schema.org",
        "@type": schema["type"],
        "headline": schema["headline"],
        "description": schema["description"],
        "author": SCHEMA_AUTHOR,
        "publisher": SCHEMA_PUBLISHER,
        "mainEntityOfPage": canonical,
        "about": schema.get("about", []),
    }
    if date_published:
        data["datePublished"] = date_published
        data["dateModified"] = date_modified or date_published
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return f'<script type="application/ld+json">{payload}</script>'


def build_faq_schema(faq):
    """Render a FAQ list (config "faq": [{q, a}, ...]) into FAQPage JSON-LD.
    Answers are plain text (no markup) so the same source feeds both the
    machine-readable block here and the visible block in build_faq_html.
    """
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in faq
        ],
    }
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return f'<script type="application/ld+json">{payload}</script>'


def build_faq_html(faq):
    """Visible FAQ block from the same config "faq" list. Wrapped in .prose so it
    inherits the page's type scale; injected wherever a page places {{faq}}."""
    rows = "".join(
        f"<h3>{html.escape(item['q'])}</h3><p>{html.escape(item['a'])}</p>"
        for item in faq
    )
    return (
        '<section class="section faq-section"><div class="container">'
        '<div class="prose fade-up"><h2>Common questions</h2>'
        f"{rows}</div></div></section>"
    )


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


def render_page(page_dir, header, footer, head_meta):
    cfg_path = os.path.join(page_dir, "config.json")
    if not os.path.exists(cfg_path):
        return None
    cfg = json.loads(read(cfg_path))

    # Per-page layout override (defaults to base.html). Lets a page like the
    # home "Light" one-pager use its own shell, CSS and scripts.
    layout_name = cfg.get("layout", "base.html")
    base = read(os.path.join(LAYOUTS, layout_name))

    output = cfg["output"]
    out_path = os.path.join(ROOT, output)

    # Path-traversal guard: output must stay inside the repo root.
    if not os.path.abspath(out_path).startswith(ROOT):
        raise ValueError(f"Refusing to write outside repo root: {output}")

    # Redirect stub (meta-refresh), skips the full layout. Returns None so the
    # stub stays out of the sitemap (it's noindex; listing it would contradict
    # the robots directive).
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
        print(f"  - {output} (redirect -> {cfg['redirect_to']})")
        return None

    depth = output.count("/")
    nav_prefix = "../" * depth
    canonical = f"{SITE_URL}/{output}".replace("/index.html", "/")

    content = build_sections(page_dir)

    # Polymorphic schema: a dict is structured data we render here (notes/essays);
    # a str is a verbatim <script> block (the home Person schema); absent -> none.
    raw_schema = cfg.get("schema", "")
    if isinstance(raw_schema, dict):
        schema = build_schema(
            raw_schema, canonical,
            cfg.get("date_published"), cfg.get("date_modified"),
        )
    else:
        schema = raw_schema

    # Optional FAQ: appends FAQPage JSON-LD to the schema and exposes a visible
    # block via the {{faq}} token. Single source of truth is config "faq".
    faq = cfg.get("faq")
    faq_html = ""
    if faq:
        schema += build_faq_schema(faq)
        faq_html = build_faq_html(faq)

    # og:type — "article" for dated/Article pages, "website" otherwise. Lets
    # notes/essays/spokes/pillar present as articles with no per-config edits.
    og_type = cfg.get("og_type") or (
        "article"
        if isinstance(raw_schema, dict) and raw_schema.get("type") == "Article"
        else "website"
    )

    page = base
    # Inject the shared <head> partial first so its {{title}}/{{canonical}}/etc.
    # tokens get filled by the substitutions below. {{og_image}} is the one token
    # unique to the partial; fill it from SITE_URL here.
    page = page.replace("{{head_meta}}", head_meta)
    page = page.replace("{{og_image}}", html.escape(f"{SITE_URL}/og-default.png", quote=True))
    page = page.replace("{{ga_id}}", GA_MEASUREMENT_ID)
    page = page.replace("{{title}}", html.escape(cfg.get("title", ""), quote=True))
    page = page.replace(
        "{{meta_description}}",
        html.escape(cfg.get("meta_description", ""), quote=True),
    )
    page = page.replace("{{canonical}}", html.escape(canonical, quote=True))
    page = page.replace("{{robots}}", cfg.get("robots", "index, follow"))
    page = page.replace("{{og_type}}", og_type)
    page = page.replace("{{schema}}", schema)
    page = page.replace("{{header}}", header)
    page = page.replace("{{footer}}", footer)
    page = page.replace("{{content}}", content)
    page = page.replace("{{faq}}", faq_html)
    # Visible date label, available to content (so it must come after {{content}}).
    # "Updated" once the page has been revised, "Published" until then.
    dp, dm = cfg.get("date_published"), cfg.get("date_modified")
    if dp:
        shown = dm if (dm and dm != dp) else dp
        verb = "Updated" if (dm and dm != dp) else "Published"
        label = f"{verb} {date.fromisoformat(shown).strftime('%B %Y')}"
    else:
        label = ""
    page = page.replace("{{updated_display}}", label)
    # nav_prefix LAST — header/footer partials and content may contain it too.
    page = page.replace("{{nav_prefix}}", nav_prefix)

    write(out_path, page)
    # A page can opt out of the sitemap while still building and staying
    # reachable by direct URL (e.g. published but intentionally delisted until
    # an embedded video goes live). Returning None keeps it out of the sitemap.
    if not cfg.get("in_sitemap", True):
        print(f"  - {output} (built, excluded from sitemap)")
        return None
    return output


def write_sitemap(outputs):
    """Emit sitemap.xml listing every built page (apex URLs)."""
    locs = []
    for o in outputs:
        loc = f"{SITE_URL}/{o}".replace("/index.html", "/")
        locs.append(f"  <url><loc>{loc}</loc></url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(locs)
        + "\n</urlset>\n"
    )
    write(os.path.join(ROOT, "sitemap.xml"), xml)


def write_robots():
    write(
        os.path.join(ROOT, "robots.txt"),
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n",
    )


def write_llms():
    """Emit /llms.txt — a plain, machine-parsable summary of who this is and what
    the site covers. Reinforces the entity layer for model crawlers. Curated (not
    auto-listed) so it states what matters; the sitemap carries the full list."""
    body = "\n".join([
        "# Daniel Fox — the Music Behaviorist",
        "",
        f"> {LIFTABLE}",
        "",
        "## Who",
        "- Name: Daniel Christopher Fox (Daniel Fox)",
        "- Title: the Music Behaviorist — music producer and behavioral researcher",
        "- Company: founder of Entuned (https://entuned.co), a retail audio company",
        "- Field: how music shapes buying and behavior, grounded in peer-reviewed research",
        "- Not to be confused with other musicians named Daniel Fox or Christopher Fox.",
        "",
        "## Primary pages",
        f"- {SITE_URL}/ — home",
        f"- {SITE_URL}/about.html — about",
        f"- {SITE_URL}/store-music-and-customer-behavior.html — field guide: store music and customer behavior",
        f"- {SITE_URL}/writing.html — research notes and essays",
        f"- {SITE_URL}/speaking.html — speaking",
        f"- {SITE_URL}/the-work.html — the work",
        f"- {SITE_URL}/contact.html — contact",
        "",
        f"Full page list: {SITE_URL}/sitemap.xml",
        "",
    ])
    write(os.path.join(ROOT, "llms.txt"), body)


def main():
    if not os.path.exists(LAYOUT):
        print("ERROR: missing _src/layouts/base.html", file=sys.stderr)
        sys.exit(1)

    header = load_partial("header.html")
    footer = load_partial("footer.html")
    head_meta = load_partial("head.html")

    built = []
    for name in sorted(os.listdir(PAGES)):
        page_dir = os.path.join(PAGES, name)
        if not os.path.isdir(page_dir):
            continue
        out = render_page(page_dir, header, footer, head_meta)
        if out:
            built.append(out)

    write_sitemap(built)
    write_robots()
    write_llms()

    print(f"Built {len(built)} pages:")
    for o in built:
        print(f"  - {o}")
    print("  + sitemap.xml, robots.txt, llms.txt")


if __name__ == "__main__":
    main()
