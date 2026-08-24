# psyneupre

Site vitrine de Céline Liurno, psychologue & sexologue à Plainevaux (Neupré, Liège).

## Stack
Statique pur : un `index.html`, un `styles.css`. Aucun build, aucun framework, aucun
runtime. Servi par nginx:alpine sur node2 :8145. `seo/` est un outillage Python
autonome (pytrends), sans lien avec le site servi.

## Commandes
    python3 -m http.server 8000     # aperçu local
    ship psyneupre                  # déploie sur node2 (mode A · docker-context)
    ship psyneupre --checks-only    # sondes via l'edge, zéro deploy

## Ce qu'il faut savoir avant de coder
- 🔴 **Pas de build.** `Dockerfile` COPIE `index.html`/`styles.css` tels quels dans nginx.
  Introduire un bundler oblige à réécrire l'étage 1 du Dockerfile.
- 🔴 `absolute_redirect off` dans `nginx.conf` : sans lui, nginx émet des redirections
  `http://psyneupre.jgsquare.io:8145/…` (port interne, HTTP) derrière Caddy → page morte.
- 🔴 Le JSON-LD `MedicalBusiness` de `index.html` porte l'adresse, le téléphone et le mail
  **réels**. Ce sont des données métier : ne jamais les inventer ni les « corriger ».
- 🟡 `canonical` / `og:url` pointent `psy-plainevaux.be`, **qui ne résout pas**. À reprendre
  le jour où un domaine est acheté.
- 🟡 GitHub Pages est **désactivé** depuis 2026-08-24. Le seul front est node2, tailnet-only.
