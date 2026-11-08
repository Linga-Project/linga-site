# Visages des captures de l'app

Les profils de démonstration de l'app n'ont pas de photo : l'app montre leur initiale. Pour les captures du site,
`captures.py` sert ces photos au test d'intégration de l'app, qui les affiche à la place des initiales. Elles ne
sont jamais publiées telles quelles : on ne les voit que dans les captures (`assets/img/app/`).

| Fichier | Personne de la démonstration | Où on la voit |
|---|---|---|
| `awa.jpg` | Awa, 28 ans | Découvrir, profil, « C'est réciproque », messages, conversation, accueil de l'app |
| `lea.jpg` | Léa | Messages |
| `maya.jpg` | Maya | Messages, accueil de l'app |
| `ines.jpg` | Inès | Messages, accueil de l'app |
| `nadia.jpg` | Nadia, 27 ans | Likes (le like du jour) |
| `sam.jpg` | Sam, 29 ans (la personne qui utilise l'app) | Mon profil, « C'est réciproque », vérification |

## Origine

Photos Unsplash (licence Unsplash : usage gratuit, y compris commercial, sans autorisation ni mention obligatoire),
choisies et validées par lot en novembre 2026 pour les maquettes de l'app (canevas « Maquettes Linga »), puis
recadrées ici en portrait 3:4, 720 × 960. Les noms des photographes et les pages d'origine n'ont pas été notés au
téléchargement : à retrouver et à ajouter ici.

## Avant d'en ajouter ou d'en changer

- Des personnes noires, la cible principale de Linga ; chaque nouveau lot est validé avant d'être téléchargé.
- Ces personnes ne sont pas des membres de Linga : le site le dit en bas de chaque page. Une photo de stock n'a pas
  d'autorisation du modèle pour un usage « rencontre » : pour une campagne ou les fiches des stores, préférer des
  photos avec autorisation écrite (modèles, proches) ou des visages générés.
- Un nouveau visage : le fichier ici, en minuscules et sans accent, puis le prénom dans `_visages` de
  `integration_test/captures_site_test.dart` (dépôt de l'app), puis `python3 captures.py --simulateur <UDID>`.
