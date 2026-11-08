# Contrat des pages du site Linga

Ce document fixe comment s'écrit une page du site. Le design (CSS, en-tête, pied, haut des pages) et le contenu des
pages sont faits séparément : une page de contenu n'utilise que les éléments décrits ici.

## Arborescence

| Chemin | Contenu |
|---|---|
| `build.py` | Assemble `src/pages/**/*.html` dans `_site/` (sans dépendance : Python 3 seul) |
| `src/layout.html` | Squelette commun : `<head>`, en-tête, pied de page |
| `src/pages/` | Une page par fichier, avec son en-tête (voir plus bas) |
| `assets/` | `css/linga.css`, `js/linga.js`, `fonts/`, `img/` (`logo/`, `icons.svg`) : copiés dans `_site/assets/` |
| `static/` | Fichiers copiés à la racine de `_site/` (favicons, `og-image.png` : image de partage 1200 × 630) |
| `_site/` | Le site construit (ignoré par git) |

`build.py` écrit aussi `_site/sitemap.xml` et `_site/robots.txt`, avec l'adresse publique du site (voir
« Construction »).

Adresses propres : `src/pages/cgu.html` donne `_site/cgu/index.html` (adresse `/cgu/`), `src/pages/aide/connexion.html`
donne `_site/aide/connexion/index.html`. `index.html` donne `_site/index.html`, `404.html` donne `_site/404.html`.

## Les pages

| Adresse | Source | Layout |
|---|---|---|
| `/` | `index.html` | `landing` |
| `/securite/` | `securite.html` | `page` |
| `/aide/` | `aide/index.html` | `page` |
| `/aide/connexion/` | `aide/connexion.html` | `help` |
| `/aide/verification/` | `aide/verification.html` | `help` |
| `/aide/signaler-bloquer/` | `aide/signaler-bloquer.html` | `help` |
| `/aide/abonnement/` | `aide/abonnement.html` | `help` |
| `/contact/` | `contact.html` | `page` |
| `/cgu/` | `cgu.html` | `legal` |
| `/cgv/` | `cgv.html` | `legal` |
| `/confidentialite/` | `confidentialite.html` | `legal` |
| `/mentions-legales/` | `mentions-legales.html` | `legal` |
| `/suppression-du-compte/` | `suppression-du-compte.html` | `legal` |
| `/conditions/` | `conditions.html` | `redirect` vers `/cgu/` (adresse déjà donnée par l'app) |
| `/404.html` | `404.html` | `page` |

## En-tête d'une page source

Un commentaire HTML en toute première ligne, une clé par ligne :

```html
<!--
title: Conditions générales d'utilisation
description: Les règles de Linga : qui peut l'utiliser, ce qui est interdit, la modération. (160 caractères au plus)
layout: legal
eyebrow: Informations légales
title_html: Conditions générales <span class="muted">d'utilisation</span>
lead: Une phrase sous le titre.
updated: 8 novembre 2026
draft: true
cta_label: Nos conseils de sécurité
cta_href: /securite/
redirect: /cgu/
-->
<h2 id="objet">Article 1 – Objet</h2>
<p>…</p>
```

- `title`, `description`, `layout` : obligatoires. Une clé inconnue (ou mal écrite : `Draft`, `drafts`) ou donnée deux
  fois fait échouer la construction.
- `description` : 160 caractères au plus.
- `eyebrow` : la pastille au-dessus du titre (layouts `page` et `legal` ; sur `help`, le fil d'Ariane la remplace).
- `title_html` : le titre affiché, si sa fin doit être grisée (`<span class="muted">`) ; sinon `title`.
- `lead` : la phrase sous le titre (layouts `page`, `legal`, `help`).
- `updated` : « Dernière mise à jour » (layouts `legal`, `help`).
- `draft: true` : bandeau « Projet à faire valider par un juriste avant publication » en tête du contenu, et
  `noindex` pour les moteurs de recherche. Seules valeurs admises : `true` ou `false` (sinon, erreur).
- `cta_label`, `cta_href` : un bouton sous le titre (layout `page`).
- `redirect` : seulement pour `layout: redirect`, le chemin du site vers lequel renvoyer (commence par `/`).

## Les liens

Toujours des chemins absolus depuis la racine du site, avec la barre finale : `/cgu/`, `/aide/connexion/`,
`/confidentialite/#durees`, `/assets/img/icons.svg#shield-check`. `build.py` les rend relatifs : le site marche à
n'importe quelle adresse (`https://linga.chat/` comme `https://linga-project.github.io/linga-site/`).
Liens externes : `https://…` ; e-mail : `mailto:aide@linga.chat`.

## Les layouts

- **legal** : `build.py` affiche le haut de page (pastille, titre, « Dernière mise à jour », et sur ces quatre
  documents seulement, les onglets CGU · CGV · Confidentialité · Mentions légales), puis deux colonnes : à gauche le sommaire, construit tout seul à partir des
  `<h2 id="…">` du corps ; à droite le corps, dans une carte. Le corps ne contient que du **texte** (voir plus bas).
- **help** : fil d'Ariane (Aide › titre) à la place de la pastille, haut de page, sommaire et carte de contenu comme `legal`, puis un encadré
  « Encore une question ? » ajouté par `build.py`. Le corps ne contient que du **texte**.
- **page** : haut de page rendu par `build.py` (pastille, titre, phrase, bouton facultatif) ; le corps est fait de
  **sections**.
- **landing** : le corps contient toute la page, sections comprises (l'accueil).
- **redirect** : page vide qui renvoie vers `redirect` (balise `meta refresh` et lien).

## Texte (layouts legal et help)

- Titres : `<h2 id="mot-cle">Article 1 – Objet</h2>` (id en minuscules, sans accent, mots reliés par des tirets ;
  unique dans la page), puis `<h3>`.
- `<p>`, `<ul>`, `<ol>`, `<strong>`, `<em>`, `<a href="…">`.
- Tableau : `<div class="table-wrap"><table><thead>…</thead><tbody>…</tbody></table></div>`, toujours avec un
  `<thead>` (un titre par colonne, sans `colspan`) et précédé d'un `<h2>` ou `<h3>`. `build.py` complète tout seul :
  nom de la zone (« Tableau : » + ce titre) pour le clavier et les lecteurs d'écran, et titre de colonne sur chaque
  cellule (`data-label`). Sur téléphone, un tableau de trois colonnes ou plus s'affiche en fiches empilées (la
  première cellule en titre, les autres précédées du titre de leur colonne) ; à deux colonnes, il tient dans la
  largeur. Ne rien écrire de tout cela à la main.
- Passage à compléter : `<mark class="todo">[à compléter : raison sociale]</mark>`.
  Sur les pages publiques (aide, contact, sécurité, accueil), pas de marque visible : une note
  `<!-- à compléter : … -->` (ou `à valider`, `à vérifier`), que `build.py` retire du site construit.
- Encadré : `<div class="callout"><p>…</p></div>` ; important : `<div class="callout callout--accent"><p>…</p></div>`.
- Définitions : `<dl class="definitions"><dt>Terme</dt><dd>Définition.</dd></dl>`.
- Étapes à suivre dans l'app : `<ol class="steps"><li>…</li></ol>`.
- Chemin dans l'app : `<span class="path">Réglages › Confidentialité › Télécharger mes données</span>` (texte seul,
  étapes séparées par « › ») : `build.py` ne laisse la ligne se couper qu'entre deux étapes.

## Sections (layouts page et landing)

- Section : `<section class="section" id="…"><div class="container">…</div></section>` ; plus serrée :
  `section section--tight`.
- En-tête de section : `<span class="eyebrow">Les bons réflexes</span>`, puis
  `<h2 class="display">Première ligne <span class="muted">deuxième ligne.</span></h2>`, puis `<p class="lead">…</p>`.
  Centré : ajouter `section__head--center` sur un `<div class="section__head">` qui les entoure.
- Deux colonnes (texte à gauche, contenu à droite) : `<div class="split"><div>…</div><div>…</div></div>`.
- Cartes : `<div class="cards cards--3">` (ou `cards--2`, `cards--4`) contenant des
  `<article class="card"><span class="card__icon"><svg class="icon" aria-hidden="true"><use href="/assets/img/icons.svg#shield-check"></use></svg></span><h3>Titre</h3><p>Texte.</p></article>`.
  Carte-lien : `<a class="card card--link" href="/aide/connexion/">…<span class="card__more">Lire l'article</span></a>`.
- Règles numérotées : `<ol class="rules"><li><p>…</p></li></ol>` (cartes au numéro coquelicot).
- Questions fréquentes : `<div class="faq"><details><summary>La question ?</summary><div class="faq__answer"><p>La réponse.</p></div></details></div>`.
- Liste à coches : `<ul class="checklist"><li>…</li></ul>`.
- Boutons : `<a class="button button--light" href="…">Libellé</a>` (blanc), `<a class="button button--ghost" href="…">`
  (contour), `<a class="button button--accent" href="…">` (coquelicot, texte noir).
- Pastille « Bientôt » (fonction pas encore disponible) : `<span class="tag">Bientôt</span>`, coquelicot, texte
  noir ; dans le coin d'une carte : `<span class="tag tag--corner">Bientôt</span>`. Un seul style sur tout le site.
- Badges des boutiques : `<span class="store">…</span>` dans `<div class="stores">`, volontairement d'aspect inactif
  (contour pointillé) tant que l'app n'est pas sortie ; ils deviendront des liens blancs avec les adresses des boutiques.
- Encadré de contact : `<div class="contact-card"><span class="card__icon">…</span><div><p class="contact-card__label">…</p><p class="contact-card__value">…</p></div></div>`.

## Icônes

Un seul fichier, `assets/img/icons.svg` : des symboles de 24 × 24, au trait (`stroke="currentColor"`, épaisseur 1,8,
bouts ronds). Noms disponibles :

`shield-check`, `map-pin`, `image`, `flag`, `bell`, `moon`, `lock`, `user`, `users`, `heart`, `message`, `mic`,
`calendar`, `pause`, `eye-off`, `check`, `x`, `plus`, `arrow-right`, `arrow-up-right`, `chevron-down`, `mail`,
`phone`, `smartphone`, `key`, `alert`, `help`, `sparkles`, `download`, `trash`, `file-text`, `globe`, `star`,
`camera`, `sliders`, `log-in`, `credit-card`, `clock`.

```html
<svg class="icon" aria-hidden="true"><use href="/assets/img/icons.svg#heart"></use></svg>
```

## Le ton

Français, tutoiement, sans emoji, phrases courtes. Écrire normalement l'espace avant « : ; ? ! » : `build.py` la rend
insécable (y compris dans `<strong>Important </strong>:`), et empêche « e-mail » et « Écris-nous » de se couper au trait d'union. Un chemin court (26 signes au plus,
« Profil › Vérification ») ne se coupe jamais. Pas de
photo de personne : des initiales à la place.

## Construction

```
python3 build.py                                    # strict : la moindre erreur ou le moindre avertissement arrête tout
python3 build.py --no-strict                        # essai : les avertissements n'arrêtent plus (jamais pour publier)
python3 build.py --site-url https://linga-project.github.io/linga-site --root-path /linga-site/
```

- Strict par défaut : description de plus de 160 caractères, `<h2>` sans id (absent du sommaire), id mal formé, clé
  d'en-tête inconnue, `draft` autre que `true`/`false`, fichier qui n'est pas en UTF-8 : rien n'est écrit.
- Contrôlé aussi : aucun `style=`, `<style>`, script en ligne, ni ressource chargée depuis un autre site (`src`,
  `<link href>`, `<use href>`… en `https://` ou `//`) : la CSP les bloquerait. Seuls les liens `<a href>` et la
  balise canonique peuvent viser un autre site.
- `--site-url` (ou `LINGA_SITE_URL`, défaut `https://linga.chat`) : adresse publique, utilisée pour les adresses
  canoniques, `og:url`, `og:image`, `sitemap.xml` et `robots.txt`. Tant que le site est servi par GitHub Pages sous
  `/linga-site/`, construire avec l'adresse GitHub ; `robots.txt` n'est lu par les robots qu'à la racine d'un hôte,
  donc il ne servira qu'une fois `linga.chat` branché.
