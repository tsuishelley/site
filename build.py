#!/usr/bin/env python3
"""Generate the case study pages and the homepage lists from content/*.md.

One markdown file per project is the single source of truth: it produces the
case study page, its card in Selected work, and its row in the Index. Adding a
project means adding a file — no markup to copy.

    python3 build.py

Front matter keys:
    title     required, project name
    blurb     one line, used on the card and the index row
    card      image for the card and index thumbnail
    hero      full-width image at the top of the case study page
    gallery   comma-separated images for the index row's expanding carousel
              (falls back to `card` when it is not set)
    group     featured | index   (which homepage list it belongs to)
    order     sort position within that list
    draft     true = no page is generated and it is not linked anywhere
    role / company / timeline / scope   optional details row

Body: "## Label" starts a section, blank-line-separated paragraphs form its
copy, and "![caption](path)" drops in a full-width image.
"""

import html
import re
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
TEMPLATE = ROOT / "templates" / "project.html"
INDEX = ROOT / "index.html"


def parse(path):
    raw = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
    if not m:
        raise SystemExit(f"{path.name}: missing front matter")
    meta, body = {}, m.group(2).strip()
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    meta["slug"] = path.stem
    meta["gallery"] = [s.strip() for s in meta.get("gallery", "").split(",") if s.strip()]
    meta["draft"] = meta.get("draft", "false").lower() == "true"
    meta["order"] = int(meta.get("order", 999))
    return meta, body


def esc(s):
    return html.escape(s, quote=True)


def render_body(body):
    """Blocks -> sections and full-width images, matching project.css."""
    out, section, paras = [], None, []

    def flush():
        nonlocal section, paras
        if section is None and not paras:
            return
        copy = "\n".join(f"          <p>{esc(p)}</p>" for p in paras)
        out.append(
            '    <section class="project-section">\n'
            f'      <div class="project-section__label">{esc(section or "")}</div>\n'
            '      <div class="project-section__body">\n'
            f"{copy}\n"
            "      </div>\n"
            "    </section>"
        )
        section, paras = None, []

    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block:
            continue
        img = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", block, re.S)
        if img:
            flush()
            caption, src = img.group(1).strip(), img.group(2).strip()
            cap = (
                f'\n      <p class="project-image__caption">{esc(caption)}</p>'
                if caption
                else ""
            )
            out.append(
                '    <div class="project-image project-image--full">\n'
                f'      <img src="{esc(src)}" alt="{esc(caption)}" />{cap}\n'
                "    </div>"
            )
        elif block.startswith("## "):
            flush()
            section = block[3:].strip()
        else:
            paras.append(" ".join(block.split()))
    flush()
    return "\n\n".join(out)


def render_page(meta, body, template):
    hero = ""
    if meta.get("hero"):
        hero = (
            '    <div class="project-hero">\n'
            f'      <img src="{esc(meta["hero"])}" alt="{esc(meta["title"])}" class="project-hero__img" />\n'
            "    </div>\n"
        )

    fields = [(k.title(), meta[k]) for k in ("role", "company", "timeline", "scope") if meta.get(k)]
    details = ""
    if fields:
        rows = "\n".join(
            '      <div class="project-detail">\n'
            f'        <span class="project-detail__label">{esc(label)}</span>\n'
            f'        <span class="project-detail__value">{esc(value)}</span>\n'
            "      </div>"
            for label, value in fields
        )
        details = (
            '    <hr class="project-divider" />\n'
            '    <div class="project-details">\n'
            f"{rows}\n"
            "    </div>\n"
            '    <hr class="project-divider" />\n'
        )

    page = template
    for key, value in (
        ("title", esc(meta["title"])),
        ("hero", hero),
        ("details", details),
        ("body", render_body(body)),
    ):
        page = page.replace("{{" + key + "}}", value)
    return page


def featured_markup(items):
    out = []
    for m in items:
        img = (
            f'              <img class="feature__image" src="{esc(m["card"])}" alt="{esc(m["title"])}" />'
        )
        if m["draft"]:
            link = f'            <div class="feature__link">\n{img}\n            </div>'
        else:
            link = (
                f'            <a href="{m["slug"]}.html" class="feature__link">\n'
                f"{img}\n            </a>"
            )
        out.append(
            '          <article class="feature">\n'
            f"{link}\n"
            '            <div class="meta">\n'
            f'              <h2 class="meta__title">{esc(m["title"])}</h2>\n'
            f'              <p class="meta__desc">{esc(m["blurb"])}</p>\n'
            "            </div>\n"
            "          </article>"
        )
    return "\n".join(out)


def index_panel(m):
    """The row's drawer: a horizontal carousel of the project's images.

    `inert` and aria-hidden keep the collapsed contents out of the tab order
    and the accessibility tree; the toggle script clears them on open.
    """
    shots = m["gallery"] or ([m["card"]] if m.get("card") else [])
    if not shots:
        return ""
    tiles = "\n".join(
        f'                  <img class="index__shot" src="{esc(src)}" alt="" loading="lazy" />'
        for src in shots
    )
    more = (
        f'\n                <a class="index__more" href="{m["slug"]}.html">Read the case study</a>'
        if not m["draft"]
        else ""
    )
    return (
        f'            <div class="index__panel" id="panel-{esc(m["slug"])}" inert aria-hidden="true">\n'
        '              <div class="index__panel-inner">\n'
        '                <div class="index__carousel">\n'
        f"{tiles}\n"
        "                </div>"
        f"{more}\n"
        "              </div>\n"
        "            </div>\n"
    )


def index_markup(items):
    out = []
    for i, m in enumerate(items, 1):
        panel = index_panel(m)
        # nothing to show -> a plain span, so the row keeps its shape without
        # pretending to be a control that does nothing when clicked or tabbed to
        control = (
            '\n              <button type="button" class="pill-btn index__toggle"'
            f' aria-expanded="false" aria-controls="panel-{esc(m["slug"])}">Expand</button>'
            if panel
            else '\n              <span class="pill-btn pill-btn--inert">Expand</span>'
        )
        out.append(
            '          <li class="index__item">\n'
            '            <div class="index__row">\n'
            f'              <span class="index__num">{i:02d}</span>\n'
            '              <div class="index__info">\n'
            f'                <h3 class="index__title">{esc(m["title"])}</h3>\n'
            f'                <p class="index__desc">{esc(m["blurb"])}</p>\n'
            "              </div>"
            f"{control}\n"
            "            </div>\n"
            f"{panel}"
            "          </li>"
        )
    return "\n".join(out)


def splice(page, name, markup):
    start, end = f"<!-- build:{name} -->", f"<!-- /build:{name} -->"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(page):
        raise SystemExit(f"index.html: missing {start} … {end} markers")
    return pat.sub(lambda _: f"{start}\n{markup}\n{' ' * 8}{end}", page)


def main():
    template = TEMPLATE.read_text()
    projects = [parse(p) for p in sorted(CONTENT.glob("*.md"))]

    built = 0
    for meta, body in projects:
        page = ROOT / f"{meta['slug']}.html"
        if meta["draft"]:
            # only ever removes a page this script would itself generate
            if page.name != "index.html" and page.exists():
                page.unlink()
                print(f"removed stale page: {page.name}")
            continue
        page.write_text(render_page(meta, body, template))
        built += 1

    def group(name):
        return sorted(
            (m for m, _ in projects if m.get("group") == name),
            key=lambda m: (m["order"], m["title"]),
        )

    featured, indexed = group("featured"), group("index")

    page = INDEX.read_text()
    page = splice(page, "featured", featured_markup(featured))
    page = splice(
        page,
        "index",
        f'        <h2 class="s-title">Index<sup class="s-title__count">{len(indexed)}</sup></h2>\n'
        '        <ul class="index__list">\n'
        f"{index_markup(indexed)}\n"
        "        </ul>",
    )
    INDEX.write_text(page)

    page_text = INDEX.read_text()
    todos = page_text.count("TODO")
    lorem = page_text.lower().count("lorem ipsum")
    if todos:
        print(f"warning: index.html still contains {todos} TODO placeholder(s)")
    if lorem:
        print(f"warning: index.html still contains {lorem} lorem ipsum placeholder(s)")

    drafts = [m["slug"] for m, _ in projects if m["draft"]]
    print(f"{built} case study page(s) built; {len(featured)} featured, {len(indexed)} indexed")
    if drafts:
        print("drafts (no page, not linked): " + ", ".join(drafts))


if __name__ == "__main__":
    main()
