#!/usr/bin/env python3
"""Generatore statico del sito CriticalPrep.

Nessuna dipendenza: solo la libreria standard di Python 3.8+.

    python3 build.py            # genera il sito in public/
    python3 build.py --strict   # come sopra, ma fallisce se restano segnaposto [..]
    python3 build.py --serve    # genera e serve public/ su http://localhost:8000

Struttura:
    config.json               valori globali (dominio, email, prezzi, titolare...)
    content/strings.json      testi dell'interfaccia (menu, piè di pagina...) per lingua
    content/faq.json          domande frequenti (pagina Supporto)
    content/changelog.json    novità per versione (pagina Novità/Changelog)
    content/<lang>/*.html     pagine; content/<lang>/guides/*.html guide
    templates/layout.html     unico layout condiviso
    static/                   CSS, immagini, appcast.xml, robots.txt... copiati in public/

Sintassi nei file di contenuto:
    {{c.chiave}}     valore da config.json (con escape HTML)
    {{t.chiave}}     testo da strings.json nella lingua della pagina
    {{u.chiave}}     URL della pagina con quella `key` nella lingua corrente
    {{page.title}}   campi della front matter della pagina
    {{lang}}         codice lingua
    {{{blocco}}}     blocco HTML generato (faq_list, guides_list, changelog_list...)
"""

import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
OUT = ROOT / "public"
LANGS = ["it", "en"]
DEFAULT_LANG = "it"

PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]")
VAR_RE = re.compile(r"\{\{\{\s*([\w.-]+)\s*\}\}\}|\{\{\s*([\w.-]+)\s*\}\}")

warnings = set()


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def localize(value, lang):
    if isinstance(value, dict) and set(value) <= set(LANGS) and value:
        return value.get(lang, value.get(DEFAULT_LANG))
    return value


def parse_page(path):
    text = path.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        text = body
    for required in ("key", "title"):
        if required not in meta:
            sys.exit(f"ERRORE: {path} non ha '{required}' nella front matter")
    meta.setdefault("slug", "")
    meta.setdefault("description", "")
    meta.setdefault("order", "100")
    meta["body"] = text
    meta["source"] = path
    return meta


class Renderer:
    def __init__(self, config, strings, lang, urls, raw, page=None):
        self.config = config
        self.strings = strings
        self.lang = lang
        self.urls = urls
        self.raw = raw
        self.page = page or {}

    def lookup(self, name, where):
        if name == "lang":
            return self.lang
        ns, _, key = name.partition(".")
        table = {"c": self.config, "t": self.strings.get(self.lang, {}),
                 "u": self.urls.get(self.lang, {}), "page": self.page}.get(ns)
        if table is None or key not in table:
            sys.exit(f"ERRORE: variabile sconosciuta {{{{{name}}}}} in {where}")
        value = localize(table[key], self.lang)
        if ns == "c" and isinstance(value, str) and PLACEHOLDER_RE.search(value):
            warnings.add(f"config.{key} = {value}")
        return str(value)

    def render(self, src, where):
        def sub(m):
            raw_name, name = m.group(1), m.group(2)
            if raw_name:
                if raw_name not in self.raw:
                    sys.exit(f"ERRORE: blocco sconosciuto {{{{{{{raw_name}}}}}}} in {where}")
                return self.raw[raw_name]
            value = self.lookup(name, where)
            # i testi di strings.json sono HTML fidato e possono contenere {{...}}
            if name.startswith("t."):
                return self.render(value, where)
            return html.escape(value, quote=True)
        return VAR_RE.sub(sub, src)


TEXT_NODE_RE = re.compile(r">([^<]+)<")


def highlight_placeholders(doc):
    """Evidenzia i segnaposto [..] rimasti nel testo visibile (non negli attributi né in <head>)."""
    head, sep, body = doc.partition("<body")
    if not sep:
        return doc
    def text(m):
        return ">" + PLACEHOLDER_RE.sub(lambda p: f'<span class="ph">{p.group(0)}</span>', m.group(1)) + "<"
    return head + sep + TEXT_NODE_RE.sub(text, body)


def page_url(lang, slug):
    slug = slug.strip("/")
    return f"/{lang}/" + (f"{slug}/" if slug else "")


def main():
    strict = "--strict" in sys.argv
    config = load_json(ROOT / "config.json")
    config.pop("_readme", None)
    strings = load_json(CONTENT / "strings.json")
    faq = load_json(CONTENT / "faq.json")
    changelog = load_json(CONTENT / "changelog.json")
    layout = (ROOT / "templates" / "layout.html").read_text(encoding="utf-8")

    pages = {lang: [] for lang in LANGS}
    for lang in LANGS:
        for path in sorted((CONTENT / lang).rglob("*.html")):
            meta = parse_page(path)
            meta["section"] = path.parent.name if path.parent != CONTENT / lang else ""
            pages[lang].append(meta)

    urls = {lang: {p["key"]: page_url(lang, p["slug"]) for p in pages[lang]} for lang in LANGS}
    for lang in LANGS:
        other = [l for l in LANGS if l != lang][0]
        missing = set(urls[other]) - set(urls[lang])
        if missing:
            print(f"ATTENZIONE: pagine senza traduzione in '{lang}': {', '.join(sorted(missing))}")

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)

    sitemap = []
    for lang in LANGS:
        t = strings[lang]

        def r(src, where, page=None, raw=None):
            return Renderer(config, strings, lang, urls, raw or {}, page).render(src, where)

        # ---- blocchi generati -------------------------------------------------
        faq_html = []
        for item in faq["items"]:
            q = r(localize(item["q"], lang), "faq.json")
            a = r(localize(item["a"], lang), "faq.json")
            faq_html.append(f'<details class="faq" id="{item["id"]}"><summary>{q}</summary>'
                            f'<div class="faq-body">{a}</div></details>')

        guides = sorted([p for p in pages[lang] if p["section"] == "guides"],
                        key=lambda p: (int(p["order"]), p["title"]))
        if guides:
            guides_html = '<ul class="card-list">' + "".join(
                f'<li><a class="card-link" href="{urls[lang][g["key"]]}"><strong>{html.escape(g["title"])}</strong>'
                f'<span>{html.escape(g["description"])}</span></a></li>' for g in guides) + "</ul>"
        else:
            guides_html = f'<p class="empty">{html.escape(t["guides_empty"])}</p>'

        entries = changelog.get("entries", [])
        if entries:
            parts = []
            for e in entries:
                notes = "".join(f"<li>{r(n, 'changelog.json')}</li>" for n in localize(e["notes"], lang))
                parts.append(f'<article class="release" id="v{html.escape(e["version"])}">'
                             f'<h2>{html.escape(t["version"])} {html.escape(e["version"])}</h2>'
                             f'<p class="meta"><time datetime="{html.escape(e["date"])}">{html.escape(e["date"])}</time></p>'
                             f"<ul>{notes}</ul></article>")
            changelog_html = "".join(parts)
        else:
            changelog_html = f'<p class="empty">{html.escape(t["changelog_empty"])}</p>'

        blocks = {"faq_list": "".join(faq_html), "guides_list": guides_html,
                  "changelog_list": changelog_html}

        # ---- pagine -----------------------------------------------------------
        for p in pages[lang]:
            where = str(p["source"].relative_to(ROOT))
            body = r(p["body"], where, page=p, raw=blocks)
            key = p["key"]

            def nav_link(k, label):
                cur = ' aria-current="page"' if k == key else ""
                return f'<li><a href="{urls[lang][k]}"{cur}>{html.escape(label)}</a></li>'

            nav = "".join(nav_link(k, t["nav_" + k]) for k in t["nav_order"])
            footer_links = "".join(nav_link(k, t["nav_" + k]) for k in t["footer_order"])

            alternates, switch = [], []
            for l in LANGS:
                href = urls[l].get(key, urls[l]["home"])
                alternates.append(f'<link rel="alternate" hreflang="{l}" href="{config["site_url"]}{href}">')
                if l == lang:
                    switch.append(f'<li><span aria-current="true" lang="{l}">{l.upper()}</span></li>')
                else:
                    switch.append(f'<li><a href="{href}" hreflang="{l}" lang="{l}" '
                                  f'aria-label="{html.escape(strings[l]["lang_switch_label"])}">{l.upper()}</a></li>')
            alternates.append(f'<link rel="alternate" hreflang="x-default" href="{config["site_url"]}/">')

            breadcrumb = ""
            if p["section"] == "guides":
                breadcrumb = (f'<nav class="breadcrumb" aria-label="{html.escape(t["breadcrumb_label"])}">'
                              f'<a href="{urls[lang]["guides"]}">← {html.escape(t["nav_guides"])}</a></nav>')

            raw = {"content": breadcrumb + body, "nav": nav, "footer_links": footer_links,
                   "alternates": "\n  ".join(alternates), "lang_switch": "".join(switch)}
            full = highlight_placeholders(r(layout, "templates/layout.html", page=p, raw=raw))
            dest = OUT / urls[lang][key].strip("/") / "index.html"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(full, encoding="utf-8")
            sitemap.append(urls[lang][key])

    # ---- radice: reindirizzamento per lingua ----------------------------------
    root_tpl = (ROOT / "templates" / "root.html").read_text(encoding="utf-8")
    (OUT / "index.html").write_text(
        Renderer(config, strings, DEFAULT_LANG, urls, {}).render(root_tpl, "templates/root.html"),
        encoding="utf-8")
    nf_tpl = (ROOT / "templates" / "404.html").read_text(encoding="utf-8")
    (OUT / "404.html").write_text(
        Renderer(config, strings, DEFAULT_LANG, urls, {}).render(nf_tpl, "templates/404.html"),
        encoding="utf-8")

    # ---- file statici con variabili (appcast, robots, CNAME...) --------------
    for name in ("appcast.xml", "robots.txt", "CNAME", "_headers", "_redirects"):
        f = OUT / name
        if f.exists():
            f.write_text(Renderer(config, strings, "en", urls, {}).render(
                f.read_text(encoding="utf-8"), f"static/{name}"), encoding="utf-8")

    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{config['site_url']}{u}</loc></url>" for u in sitemap]
    sm.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")

    total = sum(len(v) for v in pages.values())
    print(f"OK: {total} pagine generate in {OUT.relative_to(ROOT)}/")
    if warnings:
        print(f"\nSegnaposto ancora da compilare in config.json ({len(warnings)}):")
        for w in sorted(warnings):
            print("  -", w)
        if strict:
            sys.exit(1)

    if "--serve" in sys.argv:
        import functools
        import http.server
        port = int(os.environ.get("PORT", "8000"))
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        print(f"\nServo {OUT} su http://localhost:{port}  (Ctrl+C per uscire)")
        http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()


if __name__ == "__main__":
    main()
