# Linga · site

Le site public de Linga : la page d'accueil, le centre d'aide, les conseils de sécurité et les pages légales (CGU, CGV,
politique de confidentialité, mentions légales, suppression du compte). Adresse prévue : https://linga.chat.

Du HTML et du CSS, un peu de JavaScript facultatif, et un petit script Python qui assemble les pages : ni framework, ni
dépendance, ni cookie, ni traceur. La police Bricolage Grotesque est servie par le site lui-même.

## Construire et voir le site en local

```sh
python3 build.py
python3 -m http.server 8090 --directory _site
```

Puis http://localhost:8090. `build.py` est strict : il échoue si un lien interne mène nulle part, si une ancre manque,
si une icône n'existe pas, si l'en-tête d'une page est incomplet ou si un avertissement reste (`--no-strict` pour un
essai seulement). La CI fait la même vérification. Il écrit aussi `sitemap.xml` (sans les brouillons) et `robots.txt`.

Options utiles : `--site-url` (adresse publique, `https://linga.chat` par défaut, pour les liens canoniques, Open Graph et
le sitemap) et `--root-path` (chemin de base, pour la page 404). La CI les prend dans la configuration de GitHub Pages.

## Écrire ou modifier une page

Tout est décrit dans [CONTRAT.md](CONTRAT.md) : l'en-tête de chaque page (`src/pages/…`), les layouts, les composants
et les icônes. En bref : une page de texte (légale ou d'aide) ne contient que des `<h2 id>`, des paragraphes, des
listes, des tableaux et quelques encadrés ; `build.py` ajoute le haut de page, le sommaire, l'en-tête et le pied.

## Publication

À chaque push sur `main`, GitHub Actions construit le site et le publie sur GitHub Pages
(`.github/workflows/pages.yml`). Les pull requests sont seulement construites, pour vérifier les liens. Tant que Pages
n'est pas activé pour le dépôt, le site est construit et vérifié, sans être publié (avertissement dans le résumé).

Sur le plan gratuit de GitHub, Pages ne publie que les dépôts publics. Pour l'activer, une fois :

```sh
gh repo edit Linga-Project/linga-site --visibility public --accept-visibility-change-consequences
gh api -X POST repos/Linga-Project/linga-site/pages -f build_type=workflow
gh workflow run pages.yml --repo Linga-Project/linga-site
```

Le site est alors en ligne sur https://linga-project.github.io/linga-site/. Pour garder le dépôt privé, Cloudflare Pages
peut publier le même site : projet relié à ce dépôt, commande de construction `python3 build.py`, dossier de sortie
`_site`, domaine `linga.chat`.

### Le domaine linga.chat

Chez Cloudflare (DNS du domaine), en « DNS only » (nuage gris) pour que GitHub obtienne lui-même le certificat :

| Type | Nom | Contenu |
|---|---|---|
| A | `linga.chat` | `185.199.108.153` |
| A | `linga.chat` | `185.199.109.153` |
| A | `linga.chat` | `185.199.110.153` |
| A | `linga.chat` | `185.199.111.153` |
| CNAME | `www` | `linga-project.github.io` |

Puis, dans les réglages du dépôt (Settings › Pages), donner `linga.chat` comme domaine personnalisé et cocher
« Enforce HTTPS » quand le certificat est prêt.

## Les pages légales

Ce sont des projets : chaque page légale porte le bandeau « Projet à faire valider par un juriste avant publication »
(`draft: true` dans son en-tête, qui ajoute aussi `noindex`), et les passages à compléter sont surlignés
(`<mark class="todo">`). Une fois un texte validé : compléter ses passages, retirer `draft: true`, mettre à jour
`updated`.

Les durées de conservation et le fonctionnement décrits viennent du backend (`backend/README.md`). Si le code change,
ces pages doivent changer aussi.
