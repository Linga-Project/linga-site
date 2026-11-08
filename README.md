# Linga · site

Le site public de Linga : la page d'accueil, le centre d'aide, les conseils de sécurité et les pages légales (CGU, CGV,
politique de confidentialité, mentions légales, suppression du compte). Adresse prévue : https://linga.chat.

Du HTML et du CSS, un peu de JavaScript facultatif, et un petit script Python qui assemble les pages : ni framework, ni
dépendance, ni cookie, ni traceur. La police Bricolage Grotesque est servie par le site lui-même.

## Construire et voir le site en local

```sh
python3 build.py
python3 -m http.server 8090 --bind 127.0.0.1 --directory _site
```

Puis http://localhost:8090. `build.py` est strict : il échoue si un lien interne mène nulle part, si une ancre manque,
si une icône n'existe pas, si l'en-tête d'une page est incomplet ou si un avertissement reste (`--no-strict` pour un
essai seulement). La CI fait la même vérification. Il écrit aussi `sitemap.xml` (sans les brouillons) et `robots.txt`.

Options utiles : `--site-url` (adresse publique, `https://linga.chat` par défaut, pour les liens canoniques, Open Graph et
le sitemap) et `--root-path` (chemin de base, pour la page 404). Les valeurs par défaut sont celles de
https://linga.chat, servi par Cloudflare.

## Captures d'écran de l'app

Les téléphones de l'accueil et les images des articles d'aide sont de vraies captures de l'app, prises dans le
simulateur iOS par `captures.py` : le test d'intégration `integration_test/captures_site_test.dart` de l'app
(dépôt voisin, `../app`) l'ouvre en démonstration et va d'écran en écran. Pour les refaire, après un changement
d'écran dans l'app (macOS, Xcode, Flutter et `cwebp` : `brew install webp`) :

```sh
xcrun simctl list devices | grep Booted           # l'UDID du simulateur, démarré (un iPhone Pro Max)
python3 captures.py --simulateur <UDID>
```

Le script fige la barre d'état (« 09:41 » sur un simulateur en français), fait les captures, puis écrit trois tailles de chaque écran utilisé dans
`assets/img/app/` (WebP). À la fin, `flutter test` désinstalle l'app du simulateur : relancer `flutter run` pour la
retrouver. Le détail est dans [CONTRAT.md](CONTRAT.md#captures-décran-de-lapp).

## Écrire ou modifier une page

Tout est décrit dans [CONTRAT.md](CONTRAT.md) : l'en-tête de chaque page (`src/pages/…`), les layouts, les composants
et les icônes. En bref : une page de texte (légale ou d'aide) ne contient que des `<h2 id>`, des paragraphes, des
listes, des tableaux et quelques encadrés ; `build.py` ajoute le haut de page, le sommaire, l'en-tête et le pied.

## Publication

Le site est publié par **Cloudflare** (Workers & Pages), relié à ce dépôt : à chaque push sur `main`, Cloudflare
lance `npx wrangler deploy`, qui lit [wrangler.jsonc](wrangler.jsonc) : il construit le site (`python3 build.py`),
puis envoie le dossier `_site` comme fichiers statiques (sans script). Une adresse inconnue reçoit la page 404 ;
`/cgu` mène à `/cgu/`.

Réglages du projet dans Cloudflare (Workers & Pages › le Worker › Settings › Build) :

| Réglage | Valeur |
|---|---|
| Nom du Worker | `linga-site`, le même que `name` dans `wrangler.jsonc` |
| Commande de construction | aucune (ou `python3 build.py`, sans effet de plus) |
| Commande de déploiement | `npx wrangler deploy` |
| Branche | `main` |

Le domaine `linga.chat` se branche dans le même Worker : Settings › Domains & Routes › Add › Custom domain, puis
`linga.chat` et `www.linga.chat`. Le domaine étant chez Cloudflare, les enregistrements DNS et le certificat sont
créés tout seuls. L'API reste à part, sur `api.linga.chat`.

GitHub Actions (`.github/workflows/site.yml`) construit le site à chaque push et pull request, pour vérifier les
liens, les images et les en-têtes ; il ne publie rien.

## Les pages légales

Ce sont des projets : chaque page légale porte le bandeau « Projet à faire valider par un juriste avant publication »
(`draft: true` dans son en-tête, qui ajoute aussi `noindex`), et les passages à compléter sont surlignés
(`<mark class="todo">`). Une fois un texte validé : compléter ses passages, retirer `draft: true`, mettre à jour
`updated`.

Les durées de conservation et le fonctionnement décrits viennent du backend (`backend/README.md`). Si le code change,
ces pages doivent changer aussi.
