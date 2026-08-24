#!/usr/bin/env python3
"""
Analyse de volume de recherche de mots-clés — 100 % outils open source / gratuits.

Stack :
  - Google Trends  (via pytrends, licence MIT)  -> intérêt de recherche relatif (0-100)
  - Google Autocomplete / Suggest (endpoint public gratuit) -> expansion de mots-clés

POURQUOI PAS DE "VOLUME ABSOLU" EXACT ?
  Le volume mensuel absolu (ex. « 2 400 recherches/mois ») est une donnée
  propriétaire de Google (Keyword Planner). Aucun outil purement open source
  n'y donne accès. Ce script fournit donc la meilleure approximation possible
  avec des outils libres :
    1. l'intérêt RELATIF (Google Trends) — fiable pour comparer/prioriser ;
    2. une estimation de volume CALIBRÉE : on ancre l'échelle Google Trends sur
       un mot-clé dont on connaît le volume approximatif (--anchor / --anchor-vol),
       ce qui transforme l'intérêt relatif en estimation absolue grossière.

Usage :
  pip install -r seo/requirements.txt
  python seo/keyword_volume.py                       # géo BE, langue fr, mots-clés du fichier
  python seo/keyword_volume.py --geo BE --no-suggest  # sans expansion autocomplete
  python seo/keyword_volume.py --anchor "psychologue" --anchor-vol 18000  # estimation absolue

Sorties (dans seo/output/) :
  - keywords_trends.csv      : intérêt relatif moyen + estimation de volume par mot-clé
  - keywords_suggest.csv     : suggestions Autocomplete (idées de longue traîne)
  - RAPPORT-VOLUME.md        : rapport lisible classé par priorité

Remarque réseau : Google Trends et Autocomplete doivent être joignables depuis
la machine qui exécute le script (certains environnements CI/cloud les bloquent).
Lancez ce script depuis votre poste si l'accès est filtré.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

SEO_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SEO_DIR / "output"
KEYWORDS_FILE = SEO_DIR / "keywords.txt"


# --------------------------------------------------------------------------- #
# Lecture des mots-clés
# --------------------------------------------------------------------------- #
def load_seed_keywords(path: Path) -> list[str]:
    keywords: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line not in keywords:
            keywords.append(line)
    return keywords


# --------------------------------------------------------------------------- #
# Google Autocomplete / Suggest (gratuit, sans clé)
# --------------------------------------------------------------------------- #
def fetch_suggestions(keyword: str, hl: str, gl: str, session) -> list[str]:
    """Retourne les suggestions Google Autocomplete pour un mot-clé."""
    url = "https://suggestqueries.google.com/complete/search"
    params = {"client": "firefox", "hl": hl, "gl": gl, "q": keyword}
    try:
        resp = session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return list(data[1]) if len(data) > 1 else []
    except Exception as exc:  # noqa: BLE001
        print(f"  [suggest] échec pour « {keyword} » : {exc}", file=sys.stderr)
        return []


# --------------------------------------------------------------------------- #
# Google Trends (pytrends) — intérêt relatif
# --------------------------------------------------------------------------- #
def fetch_trends(keywords: list[str], geo: str, hl: str, timeframe: str) -> dict[str, float]:
    """
    Retourne {mot-clé: intérêt relatif moyen 0-100}.
    Google Trends compare au maximum 5 termes à la fois ; on traite par lots
    en ré-ancrant chaque lot sur un terme pivot commun pour garder une échelle
    cohérente entre les lots.
    """
    from pytrends.request import TrendReq

    pytrends = TrendReq(hl=f"{hl}-{geo}", tz=0, retries=3, backoff_factor=0.5)

    pivot = keywords[0]
    scores: dict[str, float] = {}

    # Termes restants traités par lots de 4 (+ pivot = 5 max par requête).
    rest = keywords[1:]
    batches = [rest[i : i + 4] for i in range(0, len(rest), 4)] or [[]]

    pivot_reference = None
    for bi, batch in enumerate(batches):
        terms = [pivot] + batch
        for attempt in range(3):
            try:
                pytrends.build_payload(terms, timeframe=timeframe, geo=geo)
                df = pytrends.interest_over_time()
                break
            except Exception as exc:  # noqa: BLE001
                wait = 2 ** attempt
                print(f"  [trends] lot {bi+1} tentative {attempt+1} échec ({exc}); "
                      f"nouvelle tentative dans {wait}s", file=sys.stderr)
                time.sleep(wait)
        else:
            print(f"  [trends] lot {bi+1} abandonné", file=sys.stderr)
            continue

        if df is None or df.empty:
            continue
        if "isPartial" in df.columns:
            df = df.drop(columns=["isPartial"])

        means = df.mean(numeric_only=True)
        pivot_mean = float(means.get(pivot, 0.0)) or 1e-9

        # On fige la valeur de référence du pivot au premier lot.
        if pivot_reference is None:
            pivot_reference = pivot_mean
            scores[pivot] = round(pivot_mean, 2)

        # Ré-échelonnage des termes du lot sur l'échelle du pivot de référence.
        scale = pivot_reference / pivot_mean
        for term in batch:
            scores[term] = round(float(means.get(term, 0.0)) * scale, 2)

        time.sleep(1)  # politesse / anti-rate-limit

    return scores


# --------------------------------------------------------------------------- #
# Estimation de volume absolu (calibrée sur un mot-clé d'ancrage)
# --------------------------------------------------------------------------- #
def estimate_volume(scores: dict[str, float], anchor: str | None,
                    anchor_vol: float | None) -> dict[str, int | None]:
    if not anchor or not anchor_vol or anchor not in scores or scores[anchor] <= 0:
        return {k: None for k in scores}
    ratio = anchor_vol / scores[anchor]
    return {k: int(round(v * ratio)) for k, v in scores.items()}


# --------------------------------------------------------------------------- #
# Écriture des sorties
# --------------------------------------------------------------------------- #
def write_trends_csv(scores, volumes, path: Path) -> None:
    rows = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mot-cle", "interet_relatif_0_100", "volume_estime_mensuel"])
        for kw, score in rows:
            w.writerow([kw, score, volumes.get(kw, "")])


def write_suggest_csv(suggestions: dict[str, list[str]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mot-cle-source", "suggestion"])
        for seed, sugg in suggestions.items():
            for s in sugg:
                w.writerow([seed, s])


def write_report(scores, volumes, suggestions, meta, path: Path) -> None:
    rows = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    lines = [
        "# Rapport de volume de recherche — psychologue-liurno",
        "",
        f"- **Région** : {meta['geo']}  |  **Langue** : {meta['hl']}  |  "
        f"**Période** : {meta['timeframe']}",
        "- **Sources** : Google Trends (pytrends, open source) + Google Autocomplete (gratuit)",
    ]
    if meta.get("anchor"):
        lines.append(f"- **Ancrage volume** : « {meta['anchor']} » ≈ "
                     f"{meta['anchor_vol']} rech./mois (calibration de l'estimation absolue)")
    else:
        lines.append("- **Volume absolu** : non calibré (lancez avec --anchor/--anchor-vol "
                     "pour une estimation chiffrée). La colonne ci-dessous reste en intérêt relatif.")
    lines += ["", "## Mots-clés classés par intérêt de recherche", "",
              "| # | Mot-clé | Intérêt relatif (0-100) | Volume estimé /mois |",
              "|---|---------|------------------------:|--------------------:|"]
    for i, (kw, score) in enumerate(rows, 1):
        vol = volumes.get(kw)
        vol_str = f"{vol:,}".replace(",", " ") if isinstance(vol, int) else "—"
        lines.append(f"| {i} | {kw} | {score} | {vol_str} |")

    lines += ["", "## Idées de longue traîne (Google Autocomplete)", ""]
    for seed, sugg in suggestions.items():
        if sugg:
            lines.append(f"- **{seed}** → {', '.join(sugg[:10])}")

    lines += [
        "",
        "## Notes méthodologiques",
        "",
        "- L'**intérêt relatif** (Google Trends) compare les mots-clés entre eux sur "
        "une échelle 0-100 ; il est fiable pour **prioriser**, pas pour donner un nombre absolu.",
        "- Le **volume estimé** n'est obtenu que par **calibration** sur un mot-clé d'ancrage "
        "dont on connaît le volume approximatif. C'est une approximation, pas une mesure exacte.",
        "- Pour des volumes absolus exacts : **Google Keyword Planner** (gratuit avec un compte "
        "Google Ads ; chiffres précis dès ~5 €/mois de budget actif). Ce n'est pas open source "
        "mais c'est la source officielle.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    p = argparse.ArgumentParser(description="Analyse open source de volume de mots-clés.")
    p.add_argument("--geo", default="BE", help="Code pays Google Trends (défaut: BE)")
    p.add_argument("--hl", default="fr", help="Langue (défaut: fr)")
    p.add_argument("--timeframe", default="today 12-m",
                   help="Période Google Trends (défaut: 'today 12-m')")
    p.add_argument("--keywords", default=str(KEYWORDS_FILE),
                   help="Fichier de mots-clés (défaut: seo/keywords.txt)")
    p.add_argument("--no-suggest", action="store_true",
                   help="Désactive l'expansion via Google Autocomplete")
    p.add_argument("--no-trends", action="store_true",
                   help="Désactive Google Trends (suggestions seulement)")
    p.add_argument("--anchor", default=None,
                   help="Mot-clé d'ancrage pour estimer un volume absolu")
    p.add_argument("--anchor-vol", type=float, default=None,
                   help="Volume mensuel approximatif du mot-clé d'ancrage")
    args = p.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    seeds = load_seed_keywords(Path(args.keywords))
    print(f"{len(seeds)} mots-clés semence chargés depuis {args.keywords}")

    # 1) Autocomplete
    suggestions: dict[str, list[str]] = {}
    if not args.no_suggest:
        import requests
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (SEO open-source keyword tool)"})
        print("Récupération des suggestions Google Autocomplete…")
        for kw in seeds:
            suggestions[kw] = fetch_suggestions(kw, args.hl, args.geo, session)
            time.sleep(0.3)
        write_suggest_csv(suggestions, OUTPUT_DIR / "keywords_suggest.csv")
        total = sum(len(v) for v in suggestions.values())
        print(f"  {total} suggestions écrites dans output/keywords_suggest.csv")

    # 2) Google Trends
    scores: dict[str, float] = {}
    volumes: dict[str, int | None] = {}
    if not args.no_trends:
        print("Interrogation de Google Trends (pytrends)…")
        scores = fetch_trends(seeds, args.geo, args.hl, args.timeframe)
        volumes = estimate_volume(scores, args.anchor, args.anchor_vol)
        write_trends_csv(scores, volumes, OUTPUT_DIR / "keywords_trends.csv")
        print(f"  {len(scores)} scores écrits dans output/keywords_trends.csv")

    # 3) Rapport
    meta = {"geo": args.geo, "hl": args.hl, "timeframe": args.timeframe,
            "anchor": args.anchor, "anchor_vol": args.anchor_vol}
    write_report(scores, volumes, suggestions, meta, OUTPUT_DIR / "RAPPORT-VOLUME.md")
    print(f"Rapport : {OUTPUT_DIR / 'RAPPORT-VOLUME.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
