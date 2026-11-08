#!/usr/bin/env python3
"""Construit le site Linga : src/pages/**/*.html -> _site/ (Python 3 seul, aucune dépendance).

Usage :
    python3 build.py                        construit _site/ ; échoue au moindre problème, avertissements compris
    python3 build.py --no-strict            les avertissements (description trop longue, <h2> sans id…) n'arrêtent
                                            plus la construction (essais seulement, jamais pour publier)
    python3 build.py --allow-missing-links  liens vers des pages ou ancres absentes : simple avertissement
    python3 build.py --include-underscore   construit aussi les fichiers dont le nom commence par _ (essais)
    python3 build.py --root-path /linga/
        préfixe des liens de 404.html, la seule page servie à n'importe quelle adresse : « / » (défaut) pour
        https://linga.chat, « /linga/ » pour un site servi dans un sous-dossier
    python3 build.py --site-url https://exemple.org/linga
        adresse publique du site, sans barre finale (défaut : https://linga.chat, ou LINGA_SITE_URL) : adresses
        canoniques, og:url, og:image, sitemap.xml et robots.txt

Le format des pages est décrit dans CONTRAT.md.
"""

from __future__ import annotations

import argparse
import datetime
import html
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGES = ROOT / "src" / "pages"
LAYOUT = ROOT / "src" / "layout.html"
ASSETS = ROOT / "assets"
STATIC = ROOT / "static"
OUT = ROOT / "_site"
ICONS = ASSETS / "img" / "icons.svg"

SITE_URL = "https://linga.chat"  # remplacé par --site-url
OG_IMAGE = "og-image.png"  # dans static/, 1200 × 630, opaque
OG_IMAGE_ALT = "Linga, l'app de rencontre : des rencontres qui se tiennent"
LAYOUTS = {"landing", "page", "legal", "help", "redirect"}
REQUIRED = ("title", "description", "layout")
KNOWN_KEYS = {
    "title", "description", "layout", "eyebrow", "title_html", "lead", "updated", "draft",
    "cta_label", "cta_href", "redirect",
}
DRAFT_TEXT = "Projet à faire valider par un juriste avant publication."

# Onglets des pages légales (layout legal).
LEGAL_TABS = [
    ("/cgu/", "CGU"),
    ("/cgv/", "CGV"),
    ("/confidentialite/", "Confidentialité"),
    ("/mentions-legales/", "Mentions légales"),
]

CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; base-uri 'none'; form-action 'none'"
)


class BuildError(Exception):
    pass


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def icon(name: str, cls: str = "icon") -> str:
    return f'<svg class="{cls}" aria-hidden="true"><use href="/assets/img/icons.svg#{name}"></use></svg>'


# ---------------------------------------------------------------------------------------------------------------
# Lecture des pages


class Page:
    def __init__(self, src: Path, meta: dict, body: str):
        self.src = src
        self.rel = src.relative_to(PAGES).as_posix()
        self.meta = meta
        self.body = body
        self.layout = meta["layout"]
        self.draft = meta.get("draft", "false").strip().lower() == "true"
        self.url, self.out = self._address()
        self.html = ""
        self.ids: set = set()

    def _address(self):
        rel = self.rel
        if rel == "index.html":
            return "/", "index.html"
        if rel == "404.html":
            return "/404.html", "404.html"
        stem = rel[: -len(".html")]
        if stem.endswith("/index"):
            stem = stem[: -len("/index")]
        return f"/{stem}/", f"{stem}/index.html"

    @property
    def depth(self) -> int:
        return self.out.count("/")

    @property
    def indexable(self) -> bool:
        return not self.draft and self.layout != "redirect" and self.url != "/404.html"


def parse_page(path: Path) -> Page:
    name = path.relative_to(ROOT).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise BuildError(f"{name} : fichier non UTF-8 (octet illisible en position {error.start}) : réenregistre-le en UTF-8")
    if not text.startswith("<!--"):
        raise BuildError(f"{name} : la page doit commencer par son en-tête (<!-- … -->), voir CONTRAT.md")
    end = text.find("-->")
    if end < 0:
        raise BuildError(f"{name} : en-tête non refermé (--> manquant)")
    meta: dict = {}
    for number, line in enumerate(text[4:end].splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            raise BuildError(f"{name}, en-tête ligne {number} : « {line} » n'est pas de la forme « clé: valeur »")
        key, value = line.split(":", 1)
        key = key.strip()
        if key not in KNOWN_KEYS:
            raise BuildError(
                f"{name}, en-tête ligne {number} : clé inconnue « {key} » (attendu : {', '.join(sorted(KNOWN_KEYS))})"
            )
        if key in meta:
            raise BuildError(f"{name}, en-tête ligne {number} : clé « {key} » donnée deux fois")
        meta[key] = value.strip()
    missing = [k for k in REQUIRED if not meta.get(k)]
    if missing:
        raise BuildError(f"{name} : clé d'en-tête obligatoire absente : {', '.join(missing)}")
    if meta["layout"] not in LAYOUTS:
        raise BuildError(
            f"{name} : layout inconnu « {meta['layout']} » (attendu : {', '.join(sorted(LAYOUTS))})"
        )
    if meta["layout"] == "redirect" and not meta.get("redirect"):
        raise BuildError(f"{name} : layout redirect sans clé « redirect »")
    if "redirect" in meta and meta["layout"] != "redirect":
        raise BuildError(f"{name} : la clé « redirect » ne sert qu'au layout redirect")
    if meta.get("redirect") and not (meta["redirect"].startswith("/") and not meta["redirect"].startswith("//")):
        raise BuildError(f"{name} : redirect « {meta['redirect']} » : un chemin du site est attendu (/cgu/), pas une adresse externe")
    if "draft" in meta and meta["draft"].lower() not in ("true", "false"):
        raise BuildError(f"{name} : draft « {meta['draft']} » : écrire draft: true ou draft: false")
    if len(meta["description"]) > 160:
        warn(f"{name} : description de {len(meta['description'])} caractères (160 au plus conseillé)")
    return Page(path, meta, text[end + 3:].lstrip("\n"))


# ---------------------------------------------------------------------------------------------------------------
# Hauts de page et corps selon le layout

H2_RE = re.compile(r"<h2\b([^>]*)>(.*?)</h2>", re.S | re.I)
ID_ATTR_RE = re.compile(r'\sid="([^"]*)"')
TAG_RE = re.compile(r"<[^>]+>")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def strip_tags(fragment: str) -> str:
    return " ".join(TAG_RE.sub("", fragment).split())


def headings(page: Page):
    """Les <h2 id> du corps, dans l'ordre : [(id, texte)]. Échoue sur un id en double."""
    found, seen = [], set()
    for attrs, inner in H2_RE.findall(page.body):
        m = ID_ATTR_RE.search(" " + attrs)
        if not m:
            if page.layout in ("legal", "help"):
                warn(f"{page.rel} : <h2> sans id, absent du sommaire : « {strip_tags(inner)} »")
            continue
        hid = m.group(1)
        if hid in seen:
            raise BuildError(f"{page.rel} : id de <h2> en double : « {hid} »")
        if not SLUG_RE.match(hid):
            warn(f"{page.rel} : id « {hid} » : minuscules sans accent et tirets attendus")
        seen.add(hid)
        found.append((hid, strip_tags(inner)))
    return found


def eyebrow(text: str) -> str:
    return f'<span class="eyebrow">{text}</span>' if text else ""


# Le fil de Linga : le monogramme du logo (l et i reliés par le bas, point coquelicot), tracé d'un seul trait.
# Décoratif ; linga.js n'y touche pas, la CSS le dessine (stroke-dashoffset) puis fait tomber le point.
FIL_SVG = (
    '<svg class="fil fil--head" viewBox="-14 -168 102 200" aria-hidden="true" focusable="false">'
    '<path class="fil__trait" d="M14 -148 V-34 A23 23 0 0 0 60 -34 V-100" pathLength="1"></path>'
    '<circle class="fil__point" cx="60" cy="-134" r="16"></circle></svg>'
)


def title_html(page: Page) -> str:
    return page.meta.get("title_html") or esc(page.meta["title"])


def draft_banner(page: Page) -> str:
    if not page.draft:
        return ""
    return f'<div class="draft-banner" role="note">{icon("alert")}<p>{DRAFT_TEXT}</p></div>'


def toc_html(items) -> tuple:
    """Sommaire pour grand écran (colonne collante) et pour mobile (dépliable)."""
    if not items:
        return "", ""
    links = "".join(f'<li><a href="#{hid}">{esc(text)}</a></li>' for hid, text in items)
    # Une seule des deux colonnes est affichée à la fois (display: none sur l'autre) ; noms distincts quand même,
    # pour que deux repères <nav> ne portent jamais le même nom.
    aside = (
        '<div class="doc__aside"><nav class="toc" aria-label="Sommaire">'
        f'<p class="toc__title">Sommaire</p><ol class="toc__list">{links}</ol></nav></div>'
    )
    mobile = (
        '<details class="toc-mobile"><summary>Sommaire</summary>'
        f'<nav aria-label="Sommaire de la page"><ol class="toc__list">{links}</ol></nav></details>'
    )
    return aside, mobile


def updated_html(page: Page) -> str:
    updated = page.meta.get("updated")
    if not updated:
        return ""
    return f'<p class="doc-hero__updated">{icon("file-text")}<span>Dernière mise à jour : {esc(updated)}</span></p>'


def render_legal_or_help(page: Page) -> str:
    items = headings(page)
    aside, mobile = toc_html(items)
    is_help = page.layout == "help"
    hero = [f'<section class="doc-hero theme-noir">{FIL_SVG}<div class="container">']
    if is_help:
        hero.append(
            '<nav class="breadcrumb" aria-label="Fil d\'Ariane"><ol>'
            '<li><a href="/aide/">Aide</a></li>'
            f'<li><span aria-current="page">{esc(page.meta["title"])}</span></li></ol></nav>'
        )
    if not is_help:  # sur l'aide, le fil d'Ariane situe déjà la page : pas de pastille en plus
        hero.append(eyebrow(page.meta.get("eyebrow", "Informations légales")))
    hero.append(f'<h1 class="display display--page">{title_html(page)}</h1>')
    if page.meta.get("lead"):
        hero.append(f'<p class="lead">{page.meta["lead"]}</p>')
    meta_row = updated_html(page)
    if any(url == page.url for url, _ in LEGAL_TABS):
        current = ' aria-current="page"'
        tabs = "".join(
            f'<a href="{url}"{current if url == page.url else ""}>{label}</a>' for url, label in LEGAL_TABS
        )
        meta_row += f'<nav class="tabs" aria-label="Documents légaux">{tabs}</nav>'
    if meta_row:
        hero.append(f'<div class="doc-hero__meta">{meta_row}</div>')
    hero.append("</div></section>")

    help_box = ""
    if is_help:
        help_box = (
            '<aside class="help-more" aria-labelledby="encore-une-question">'
            f'<span class="card__icon">{icon("message")}</span>'
            '<div><h2 class="help-more__title" id="encore-une-question">Encore une question ?</h2>'
            "<p>On te répond par e-mail, en français.</p></div>"
            '<div class="help-more__actions"><a class="button button--light" href="/contact/">Nous contacter</a>'
            '<a class="button button--ghost" href="/aide/">Toute l\'aide</a></div></aside>'
        )
    grid = "doc" + ("" if aside else " doc--single")
    body = (
        f'<div class="container {grid}">{aside}<div class="doc__main">{mobile}'
        f'<article class="doc__card prose">{draft_banner(page)}{enhance_tables(page)}</article>{help_box}</div></div>'
    )
    return "".join(hero) + f'<div class="doc-wrap theme-papier">{body}</div>'


TABLE_WRAP_RE = re.compile(r'<div class="table-wrap">(\s*<table\b.*?</table>\s*)</div>', re.S | re.I)
THEAD_RE = re.compile(r"<thead\b.*?</thead>", re.S | re.I)
TBODY_RE = re.compile(r"<tbody\b.*?</tbody>", re.S | re.I)
TH_RE = re.compile(r"<th\b[^>]*>(.*?)</th>", re.S | re.I)
TR_RE = re.compile(r"<tr\b[^>]*>.*?</tr>", re.S | re.I)
CELL_OPEN_RE = re.compile(r"<(td|th)\b([^>]*)>", re.I)
HEADING_RE = re.compile(r"<h[23]\b[^>]*>(.*?)</h[23]>", re.S | re.I)


def plain(fragment: str) -> str:
    """Texte brut d'un fragment HTML, prêt à être remis dans un attribut."""
    return esc(html.unescape(strip_tags(fragment)))


def enhance_tables(page: Page) -> str:
    """Chaque <div class="table-wrap"> du corps devient une zone nommée, atteignable au clavier quand elle défile
    (tabindex, rôle region, nom tiré du titre qui précède ; linga.js retire le tabindex si rien ne défile), et
    chaque cellule reçoit le titre de sa colonne (data-label) : sous 640 px, un tableau de trois colonnes ou plus
    s'affiche en fiches empilées au lieu de défiler de côté (table-wrap--stack)."""
    body = page.body

    def sub(match):
        table = match.group(1)
        thead = THEAD_RE.search(table)
        labels = [plain(cell) for cell in TH_RE.findall(thead.group(0))] if thead else []
        if labels and "colspan" not in table.lower():
            def label_row(row):
                index = iter(range(10_000))

                def label_cell(cell):
                    i = next(index)
                    if "data-label=" in cell.group(2) or i >= len(labels):
                        return cell.group(0)
                    return f'<{cell.group(1)} data-label="{labels[i]}"{cell.group(2)}>'

                return CELL_OPEN_RE.sub(label_cell, row.group(0))

            table = TBODY_RE.sub(lambda tb: TR_RE.sub(label_row, tb.group(0)), table)
        elif labels:
            warn(f"{page.rel} : tableau avec colspan : pas d'affichage en fiches sur mobile")
        before = HEADING_RE.findall(body, 0, match.start())
        name = f"Tableau : {plain(before[-1])}" if before else "Tableau"
        stack = " table-wrap--stack" if len(labels) >= 3 else ""
        return (
            f'<div class="table-wrap{stack}" tabindex="0" role="region" aria-label="{name}">{table}</div>'
        )

    return TABLE_WRAP_RE.sub(sub, body)


# Notes internes (« <!-- à compléter : … --> », « à valider », « à vérifier », « à retirer ») : gardées dans src/,
# jamais publiées.
NOTE_COMMENT_RE = re.compile(r"[ \t]*<!--\s*[àÀ] (?:compléter|valider|vérifier|retirer)\b.*?-->", re.S)

PATH_RE = re.compile(r'<span class="path">([^<]*)</span>')


def segment_paths(document: str) -> str:
    """Chemin dans l'app : la ligne ne se coupe qu'entre deux étapes, et la suite commence par « › »."""

    def sub(match):
        steps = [s.strip() for s in match.group(1).replace("&rsaquo;", "›").split("›") if s.strip()]
        if len(steps) < 2:
            return match.group(0)
        if len(" › ".join(steps)) <= 26:
            # Chemin court (« Profil › Vérification ») : jamais coupé, il tient même à 320 px.
            return f'<span class="path"><span class="nowrap">{f"{NBSP}›{NBSP}".join(steps)}</span></span>'
        parts = [f'<span class="nowrap">{steps[0]}</span>']
        parts += [f'<span class="nowrap">›{NBSP}{step}</span>' for step in steps[1:]]
        return f'<span class="path">{" ".join(parts)}</span>'

    return PATH_RE.sub(sub, document)


def render_page(page: Page) -> str:
    m = page.meta
    parts = [f'<section class="page-hero theme-noir">{FIL_SVG}<div class="container">']
    parts.append(eyebrow(m.get("eyebrow", "")))
    parts.append(f'<h1 class="display display--page">{title_html(page)}</h1>')
    if m.get("lead"):
        parts.append(f'<p class="lead">{m["lead"]}</p>')
    if m.get("cta_label") and m.get("cta_href"):
        parts.append(
            f'<p class="page-hero__cta"><a class="button button--light" href="{esc(m["cta_href"])}">'
            f'{esc(m["cta_label"])}</a></p>'
        )
    elif m.get("cta_label") or m.get("cta_href"):
        warn(f"{page.rel} : cta_label et cta_href vont ensemble (bouton ignoré)")
    parts.append("</div></section>")
    headings(page)  # vérifie les id en double
    if page.draft:
        parts.append(f'<div class="container">{draft_banner(page)}</div>')
    parts.append(page.body)
    return "".join(parts)


def render_main(page: Page) -> str:
    if page.layout == "landing":
        headings(page)
        return (f'<div class="container">{draft_banner(page)}</div>' if page.draft else "") + page.body
    if page.layout == "page":
        return render_page(page)
    return render_legal_or_help(page)


# ---------------------------------------------------------------------------------------------------------------
# Assemblage

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
DATA_NAV_RE = re.compile(r'\sdata-nav="([^"]*)"')


def head_meta(page: Page) -> dict:
    m = page.meta
    if page.layout == "landing":
        full = f"Linga · {m['title']}"
    else:
        full = f"{m['title']} · Linga"
    canonical = f"{SITE_URL}{page.url}"
    robots = '<meta name="robots" content="noindex">' if not page.indexable else ""
    is_404 = page.url == "/404.html"
    canonical_tag = f'<link rel="canonical" href="{canonical}">' if not is_404 else ""
    og_url = f'<meta property="og:url" content="{canonical}">' if not is_404 else ""
    og_image = "\n".join([
        f'<meta property="og:image" content="{SITE_URL}/{OG_IMAGE}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{esc(OG_IMAGE_ALT)}">',
        '<meta name="twitter:card" content="summary_large_image">',
    ])
    return {
        "title": esc(full),
        "og_title": esc(m["title"] if page.layout != "landing" else full),
        "description": esc(m["description"]),
        "canonical": canonical_tag,
        "og_url": og_url,
        "og_image": og_image,
        "robots": robots,
        "body_class": f"layout-{page.layout}",
        "csp": CSP,
        "year": str(datetime.date.today().year),
        "main": render_main(page),
    }


def fill(template: str, values: dict, where: str) -> str:
    def sub(match):
        key = match.group(1)
        if key not in values:
            raise BuildError(f"{where} : emplacement inconnu {{{{ {key} }}}} dans src/layout.html")
        return values[key]

    return PLACEHOLDER_RE.sub(sub, template)


def mark_nav(document: str, url: str) -> str:
    def sub(match):
        target = match.group(1)
        if target == url:
            return ' aria-current="page"'
        if target != "/" and url.startswith(target):
            return ' aria-current="true"'
        return ""

    return DATA_NAV_RE.sub(sub, document)


def render_redirect(page: Page) -> str:
    target = page.meta["redirect"]
    title = esc(page.meta["title"])
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>{title} · Linga</title>
<link rel="canonical" href="{SITE_URL}{esc(target)}">
<meta http-equiv="refresh" content="0; url=@@REDIRECT@@">
<meta name="theme-color" content="#141414">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/css/linga.css">
</head>
<body class="layout-redirect">
<main class="redirect">
<img class="redirect__logo" src="/assets/img/logo/linga-logo-negatif.svg" alt="Linga" width="120" height="60">
<p>Cette page a changé d'adresse.</p>
<p><a class="button button--light" href="{esc(target)}">{title}</a></p>
</main>
</body>
</html>
"""


# ---------------------------------------------------------------------------------------------------------------
# Typographie française : espace insécable dans le texte seulement

# Une balise s'arrête au premier « > » hors guillemets : un « > » dans la valeur d'un attribut ne la coupe pas.
TAG_BODY = r"""(?:[^<>"']|"[^"]*"|'[^']*')*"""
SPLIT_RE = re.compile(r"(<!--.*?-->|<!?[a-zA-Z/]" + TAG_BODY + r">)", re.S)
SKIP_TAGS = {"script", "style", "code", "pre", "textarea", "kbd", "samp"}
TAGNAME_RE = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9]+)")
# « e-mail » et « Écris-nous » ne se coupent pas au trait d'union (« par e- / mail », « Écris- / nous »)
EMAIL_WORD_RE = re.compile(r"(?<![\w-])([eE]-mails?|[ÉéEe]cris-nous)(?![\w-])")
# « <strong>Important </strong>: » : l'espace avant la ponctuation est dans l'élément en ligne qui se ferme
INLINE_CLOSE_SPACE_RE = re.compile(r"[ \t\r\n]+((?:</(?:strong|em|b|i|a|span|mark|small)>)+)([:;?!»])")
NBSP = " "


def french_spacing(document: str) -> str:
    document = INLINE_CLOSE_SPACE_RE.sub(NBSP + r"\1\2", document)
    out, skip, in_title = [], 0, False
    for chunk in SPLIT_RE.split(document):
        if not chunk:
            continue
        if chunk.startswith("<") and len(chunk) > 1 and (chunk[1].isalpha() or chunk[1] in "/!"):
            m = TAGNAME_RE.match(chunk)
            if m and m.group(2).lower() in SKIP_TAGS and not chunk.endswith("/>"):
                skip += -1 if m.group(1) else 1
                skip = max(skip, 0)
            if m and m.group(2).lower() == "title":
                in_title = not m.group(1)
            out.append(chunk)
            continue
        if skip == 0:
            chunk = re.sub(r"[ \t\r\n]+([:;?!»])", NBSP + r"\1", chunk)
            chunk = re.sub(r"«[ \t\r\n]+", "«" + NBSP, chunk)
            if not in_title:
                chunk = EMAIL_WORD_RE.sub(r'<span class="nowrap">\1</span>', chunk)
        out.append(chunk)
    return "".join(out)


# ---------------------------------------------------------------------------------------------------------------
# Liens : vérification puis passage en relatif

TAG_ONLY_RE = re.compile(r"<[a-zA-Z]" + TAG_BODY + r">")
LINK_ATTR_RE = re.compile(r'(\s(?:href|src)=")([^"]*)(")')
# srcset="/a-300.webp 300w, /a-600.webp 600w" : une liste d'adresses, chacune suivie de sa largeur
SRCSET_ATTR_RE = re.compile(r'(\ssrcset=")([^"]*)(")')
ANY_ID_RE = re.compile(r"<[a-zA-Z]" + TAG_BODY.replace(")*", ")*?") + r'\sid="([^"]+)"')
# Ressource chargée par le navigateur depuis un autre site : bloquée par la CSP, donc refusée au build.
EXTERNAL_ATTR_RE = re.compile(r"""\s(src|href|srcset|poster|data|action|xlink:href)\s*=\s*["']?\s*(?:[a-z][a-z0-9+.-]*:)?//""", re.I)
IMG_TAG_RE = re.compile(r"<img\b" + TAG_BODY + r">", re.I)


def srcset_urls(value: str):
    return [candidate.split()[0] for candidate in value.split(",") if candidate.strip()]


def links_of(document: str):
    for tag in TAG_ONLY_RE.findall(document):
        for m in LINK_ATTR_RE.finditer(tag):
            yield m.group(2)
        for m in SRCSET_ATTR_RE.finditer(tag):
            yield from srcset_urls(m.group(2))


def check_images(page: Page, document: str):
    """Chaque <img> : un alt (vide si l'image ne fait que décorer), width et height (place réservée avant le
    chargement, rien ne saute), et sizes avec srcset."""
    problems = []
    for tag in IMG_TAG_RE.findall(document):
        src = re.search(r'\ssrc="([^"]*)"', tag)
        name = src.group(1) if src else tag[:60]
        missing = [a for a in ("alt", "width", "height") if not re.search(rf'\s{a}="[^"]*"', tag)]
        if re.search(r"\ssrcset=", tag) and not re.search(r"\ssizes=", tag):
            missing.append("sizes")
        if missing:
            problems.append(f"{name} (sans {', '.join(missing)})")
        for attr in ("width", "height"):
            value = re.search(rf'\s{attr}="([^"]*)"', tag)
            if value and not value.group(1).isdigit():
                problems.append(f"{name} ({attr}=\"{value.group(1)}\" : un nombre de pixels)")
    if problems:
        raise BuildError(f"{page.rel} : <img> incomplète : {'; '.join(problems)}")


def check_csp(page: Page, document: str):
    problems = []
    for tag in TAG_ONLY_RE.findall(document):
        if re.search(r'\sstyle\s*=', tag):
            problems.append("attribut style=")
        if re.search(r"\son[a-z]+\s*=", tag, re.I):
            problems.append("attribut on…= (script en ligne)")
        if re.match(r"<style\b", tag, re.I):
            problems.append("balise <style>")
        if re.match(r"<script\b", tag, re.I) and " src=" not in tag:
            problems.append("<script> en ligne")
        name = TAGNAME_RE.match(tag).group(2).lower()
        external = EXTERNAL_ATTR_RE.search(tag)
        if external and name != "a" and not (name == "link" and re.search(r'\srel="canonical"', tag)):
            problems.append(f"ressource externe (<{name} {external.group(1)}=…>)")
        # srcset : chaque adresse de la liste, pas seulement la première
        for m in SRCSET_ATTR_RE.finditer(tag):
            if any(re.match(r"(?:[a-z][a-z0-9+.-]*:)?//", url, re.I) for url in srcset_urls(m.group(2))):
                problems.append(f"ressource externe (<{name} srcset=…>)")
    if problems:
        raise BuildError(
            f"{page.rel} : interdit par la CSP (aucun style ni script en ligne, aucune ressource d'un autre site) : "
            f"{', '.join(sorted(set(problems)))}"
        )


def check_links(pages, icons: set, allow_missing: bool) -> int:
    by_url = {p.url: p for p in pages}
    errors, warnings = [], 0
    for page in pages:
        found = set(links_of(page.html))
        if page.layout == "redirect":
            found.add(page.meta["redirect"])  # dans content="…" de la balise refresh
        for link in sorted(found):
            if not link or link.startswith(("http://", "https://", "mailto:", "tel:", "data:", "//")):
                continue
            if link.startswith("#"):
                path, frag = page.url, link[1:]
            elif link.startswith("/"):
                path, _, frag = link.partition("#")
            else:
                errors.append((False, f"{page.rel} : lien relatif « {link} » : écrire un chemin absolu (/cgu/)"))
                continue
            if path.startswith("/assets/"):
                file = ASSETS / path[len("/assets/"):]
                if not file.is_file():
                    errors.append((False, f"{page.rel} : fichier introuvable « {path} »"))
                elif file.stat().st_size == 0:
                    errors.append((False, f"{page.rel} : fichier vide « {path} »"))
                elif path == "/assets/img/icons.svg":
                    if not frag:
                        errors.append((False, f"{page.rel} : icône sans nom (« {link} »)"))
                    elif frag not in icons:
                        errors.append((False, f"{page.rel} : icône inconnue « {frag} » (absente de icons.svg)"))
                continue
            if path in by_url:
                target = by_url[path]
                if frag and frag not in target.ids:
                    errors.append((
                        target is not page,  # une ancre absente de la page elle-même ne dépend de personne d'autre
                        f"{page.rel} : ancre introuvable « {link} » (pas d'id « {frag} » dans {target.rel})",
                    ))
                continue
            if path in ("/sitemap.xml",) or (path.count("/") == 1 and (STATIC / path[1:]).is_file()):
                continue
            if not path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
                errors.append((True, f"{page.rel} : « {link} » : il manque la barre finale ({path}/)"))
                continue
            errors.append((True, f"{page.rel} : lien vers une page qui n'existe pas : « {link} »"))
    fatal = 0
    grouped: dict = {}
    for missing_kind, message in errors:
        page_name, _, detail = message.partition(" : ")
        grouped.setdefault((missing_kind, detail), []).append(page_name)
    for (missing_kind, detail), where in grouped.items():
        names = ", ".join(where) if len(where) <= 3 else f"{len(where)} pages ({', '.join(where[:3])}…)"
        message = f"{names} : {detail}"
        if missing_kind and allow_missing:
            warn(message, blocking=False)
            warnings += 1
        else:
            print(f"ERREUR  {message}", file=sys.stderr)
            fatal += 1
    return fatal


def relativize(document: str, page: Page, root_path: str) -> str:
    if page.url == "/404.html":
        prefix = root_path.rstrip("/") + "/"
    else:
        prefix = "../" * page.depth

    def fix_attr(m):
        value = m.group(2)
        if not value.startswith("/") or value.startswith("//"):
            return m.group(0)
        rel = prefix + value[1:]
        if rel == "" or rel.startswith("#"):
            rel = "./" + rel
        return m.group(1) + rel + m.group(3)

    def fix_url(value: str) -> str:
        if not value.startswith("/") or value.startswith("//"):
            return value
        return prefix + value[1:]

    def fix_srcset(m):
        candidates = []
        for candidate in m.group(2).split(","):
            parts = candidate.split()
            if parts:
                candidates.append(" ".join([fix_url(parts[0])] + parts[1:]))
        return m.group(1) + ", ".join(candidates) + m.group(3)

    def fix_tag(m):
        return SRCSET_ATTR_RE.sub(fix_srcset, LINK_ATTR_RE.sub(fix_attr, m.group(0)))

    return TAG_ONLY_RE.sub(fix_tag, document)


# ---------------------------------------------------------------------------------------------------------------

WARNINGS = []
BLOCKING = []


def warn(message: str, blocking: bool = True):
    """Avertissement ; « blocking » : fait échouer la construction, sauf avec --no-strict."""
    WARNINGS.append(message)
    if blocking:
        BLOCKING.append(message)
    print(f"attention  {message}", file=sys.stderr)


def collect_sources(include_underscore: bool):
    sources = []
    for path in sorted(PAGES.rglob("*.html")):
        parts = path.relative_to(PAGES).parts
        if any(p.startswith("_") for p in parts) and not include_underscore:
            continue
        if any(p.startswith(".") for p in parts):
            continue
        sources.append(path)
    return sources


def build(args) -> int:
    global SITE_URL
    SITE_URL = (args.site_url.strip() or "https://linga.chat").rstrip("/")  # vide (CI sans Pages) : défaut
    if not re.match(r"^https://[^/\s]+(/[^\s]*)?$", SITE_URL):
        raise BuildError(f"--site-url « {args.site_url} » : adresse https:// attendue (https://linga.chat)")
    if not (STATIC / OG_IMAGE).is_file():
        raise BuildError(f"static/{OG_IMAGE} introuvable (image de partage, 1200 × 630)")
    if not LAYOUT.is_file():
        raise BuildError("src/layout.html introuvable")
    layout = LAYOUT.read_text(encoding="utf-8")
    icons = set(re.findall(r'<symbol[^>]*\sid="([^"]+)"', ICONS.read_text(encoding="utf-8"))) if ICONS.is_file() else set()

    pages = [parse_page(p) for p in collect_sources(args.include_underscore)]
    urls = {}
    for page in pages:
        if page.url in urls:
            raise BuildError(f"{page.rel} et {urls[page.url]} donnent la même adresse {page.url}")
        urls[page.url] = page.rel

    for page in pages:
        if page.layout == "redirect":
            document = render_redirect(page)
        else:
            document = fill(layout, head_meta(page), page.rel)
            document = mark_nav(document, page.url)
        document = NOTE_COMMENT_RE.sub("", document)
        document = french_spacing(segment_paths(document))
        check_csp(page, document)
        check_images(page, document)
        ids = ANY_ID_RE.findall(document)
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise BuildError(f"{page.rel} : id en double dans la page : {', '.join(dupes)}")
        page.ids = set(ids)
        page.html = document

    fatal = check_links(pages, icons, args.allow_missing_links)
    if fatal:
        raise BuildError(f"{fatal} erreur(s) de lien : rien n'a été écrit")
    if BLOCKING and args.strict:
        raise BuildError(
            f"{len(BLOCKING)} avertissement(s) ci-dessus : rien n'a été écrit (--no-strict pour un essai)"
        )

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ASSETS, OUT / "assets", ignore=shutil.ignore_patterns(".DS_Store"))
    if STATIC.is_dir():
        for item in STATIC.iterdir():
            if item.name == ".DS_Store":
                continue
            if item.is_dir():
                shutil.copytree(item, OUT / item.name, ignore=shutil.ignore_patterns(".DS_Store"))
            else:
                shutil.copy2(item, OUT / item.name)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    root_path = args.root_path if args.root_path.startswith("/") else "/" + args.root_path
    for page in pages:
        document = page.html
        if page.layout == "redirect":
            target = page.meta["redirect"]
            rel = ("../" * page.depth) + target.lstrip("/") or "./"
            if rel.startswith("#"):
                rel = "./" + rel
            document = document.replace("@@REDIRECT@@", esc(rel))
        document = relativize(document, page, root_path)
        dest = OUT / page.out
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(document, encoding="utf-8")

    indexable = sorted((p for p in pages if p.indexable), key=lambda p: (p.url != "/", p.url))
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{SITE_URL}{p.url}</loc></url>" for p in indexable]
    sitemap.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    # Les robots ne lisent robots.txt qu'à la racine de l'hôte : utile une fois le site servi à https://linga.chat/.
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
    )

    drafts = sum(1 for p in pages if p.draft)
    print(
        f"_site/ : {len(pages)} page(s) ({drafts} brouillon(s)), {len(indexable)} dans sitemap.xml"
        + (f", {len(WARNINGS)} avertissement(s)" if WARNINGS else "")
    )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Construit le site Linga dans _site/.")
    parser.add_argument("--allow-missing-links", action="store_true",
                        help="pages ou ancres manquantes : avertir sans échouer")
    parser.add_argument("--include-underscore", action="store_true",
                        help="construire aussi les fichiers dont le nom commence par _")
    parser.add_argument("--root-path", default=os.environ.get("LINGA_ROOT_PATH", "/"),
                        help="adresse de la racine du site, pour les liens de 404.html (défaut : /)")
    parser.add_argument("--site-url", default=os.environ.get("LINGA_SITE_URL", "https://linga.chat"),
                        help="adresse publique du site, sans barre finale (défaut : https://linga.chat)")
    parser.add_argument("--no-strict", dest="strict", action="store_false",
                        help="les avertissements n'arrêtent pas la construction (essais seulement)")
    args = parser.parse_args(argv)
    try:
        return build(args)
    except BuildError as error:
        print(f"ERREUR  {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
