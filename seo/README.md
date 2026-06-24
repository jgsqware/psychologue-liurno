# Analyse SEO — volume de recherche des mots-clés (outils open source)

Boîte à outils pour estimer le **volume de recherche** des mots-clés du site
**psychologue-liurno** (Céline Liurno, psychologue & sexologue à Clermont-sous-Huy /
Engis, province de Liège) en utilisant **le plus possible d'outils open source / gratuits**.

## Le constat important d'abord

Le **volume de recherche mensuel absolu** (« X recherches/mois ») est une donnée
**propriétaire de Google** (Google Keyword Planner). **Aucun outil 100 % open source
n'y donne accès directement.** Ce que l'open source permet réellement :

| Besoin | Outil open source / gratuit | Donne |
|--------|-----------------------------|-------|
| Comparer / prioriser des mots-clés | **Google Trends** via `pytrends` (MIT) | Intérêt **relatif** 0-100 |
| Découvrir des mots-clés (longue traîne) | **Google Autocomplete/Suggest** (endpoint gratuit) | Idées de requêtes réelles |
| Suivre les positions | **Serposcope** (open source, PHP) | Positions, pas le volume |
| Volume absolu **estimé** dans le navigateur | **Ubersuggest** ext. Chrome (gratuit, 40/j) / **Keywords Everywhere** | Volume estimé |
| Volume absolu **officiel** | **Google Keyword Planner** (gratuit, *non* open source) | Volume exact par tranches |

➡️ **Stratégie retenue** : `pytrends` + `Autocomplete` pour la partie open source,
avec une **calibration optionnelle** sur un volume connu pour produire une estimation
absolue. Pour des chiffres exacts, compléter avec Keyword Planner (voir plus bas).

## Installation

```bash
pip install -r seo/requirements.txt
```

## Utilisation

```bash
# Analyse par défaut : région Belgique (BE), langue fr, 12 derniers mois
python seo/keyword_volume.py

# Estimation de volume ABSOLU calibrée sur un mot-clé d'ancrage connu
# (ex. on sait que « psychologue » fait ~18 000 rech./mois en Belgique)
python seo/keyword_volume.py --anchor "psychologue" --anchor-vol 18000

# Cibler une autre zone (France) ou une autre période
python seo/keyword_volume.py --geo FR --timeframe "today 5-y"

# Suggestions Autocomplete uniquement (sans Google Trends)
python seo/keyword_volume.py --no-trends
```

### Sorties (dossier `seo/output/`)

- `keywords_trends.csv` — intérêt relatif (0-100) + volume estimé par mot-clé
- `keywords_suggest.csv` — suggestions Google Autocomplete (longue traîne)
- `RAPPORT-VOLUME.md` — rapport lisible, mots-clés classés par priorité

> ⚠️ **Réseau** : Google Trends et Autocomplete doivent être **joignables depuis la
> machine** qui exécute le script. Certains environnements cloud/CI les bloquent
> (c'est le cas de l'environnement où ce dépôt a été préparé). **Lancez le script
> depuis votre poste** pour obtenir les données.

## Les mots-clés analysés

Définis dans [`keywords.txt`](./keywords.txt) — services (psychologue, sexologue,
sexothérapie, thérapie de couple…) croisés avec la géographie locale (Engis, Huy,
Liège, Wallonie). Modifiez ce fichier pour ajouter/retirer des termes ; le script
enrichit automatiquement la liste avec les suggestions Google Autocomplete.

## Obtenir des volumes absolus EXACTS (complément non open source)

1. **Google Keyword Planner** — gratuit avec un compte Google Ads. Sans campagne
   active, les volumes s'affichent par tranches larges (ex. « 1 K – 10 K ») ;
   avec ~5 €/mois de budget actif, les chiffres deviennent précis. C'est la
   **source officielle**, à privilégier pour valider les estimations.
2. **Ubersuggest** (extension Chrome gratuite, 40 recherches/jour) ou
   **Keywords Everywhere** — affichent un volume estimé directement sous les
   résultats Google. Pratique pour un recoupement rapide.

## Méthodologie d'estimation absolue

L'intérêt Google Trends est **relatif**. Pour le convertir en volume :
on choisit un mot-clé d'ancrage dont on connaît le volume approximatif
(via Keyword Planner), et on applique le ratio à tous les autres termes.
C'est une **approximation** (l'échelle Trends est arrondie), utile pour
hiérarchiser, à confirmer ensuite sur Keyword Planner pour les termes décisifs.

Voir [`ESTIMATION-INITIALE.md`](./ESTIMATION-INITIALE.md) pour une première
estimation raisonnée (ordres de grandeur) en attendant l'exécution du script.
