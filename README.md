# 17-0: Build Your Perfect Football Season

Anthony's Final Project for **Code in Place** — June 2026

Can you go 17-0? Draft players and schemes to build the best team in the NFL simulation verse, then chase a perfect season against elite opponents from **1999–2025**.

Build a dream NFL roster from real stats, draft offense and defense, and play for **17–0**. Available as a **free web game** and a **Python console app**.

## Play Free Online (Web Game)

**https://architexstudio.github.io/Code_in_Place_Project/**

### Enable GitHub Pages (one-time)

1. The repository must be **public** (required for free GitHub Pages hosting)
2. Go to **Settings → Pages → Build and deployment**
3. Set **Source** to **GitHub Actions** (not “Deploy from a branch”)
4. Every push to `main` runs `.github/workflows/pages.yml`, rebuilds NFL data, and deploys `docs/`

### Play locally in your browser

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_nfl_data.py    # first run: downloads nflverse data
cd docs
python -m http.server 8080
```

Open **http://localhost:8080**

## Web Game Flow

1. **Draft offense (7 picks)** — Spin a team (equal probability per franchise), then choose from every loaded QB/RB/WR/TE season on that roster (1999–2025) with regular-season stats. Roster: **1 QB · 1 RB · 3 WR · 1 TE · 1 OL unit**.
2. **OL pick** — Spin a year (equal probability per season with data), choose from the **top 3** offensive-line team units for that year.
3. **Pick defense** — Choose **4-3** or **3-4**, spin a year, select a **top-3** defensive team unit (#1 = best D that year).
4. **17-0 quest** — Simulate a 17-game regular season. Wins use Elo-style probability from roster rating vs opponent; schedule order is shuffled each run.

## Console Version

```bash
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Console flow

1. **Year spin** — Random season (1999–2025) with **2 free re-spins**
2. **Offense draft** — Top 5 at QB, RB, WR (×2), TE + best O-line team for that year
3. **Defense draft** — 3-4 or 4-3, then top 3 matching defenses
4. **Simulation** — Quarter-by-quarter scoring with MVP

## Requirements

- **Python 3.10+** (required by [nflreadpy](https://github.com/nflverse/nflreadpy))
- Internet on first data build (downloads NFL stats from nflverse)

## Run Tests

```bash
pip install -r requirements-dev.txt
PYTHONPATH=. pytest tests/ -v
```

## Project Structure

```
.github/workflows/pages.yml   # GitHub Pages CI: build data + deploy docs/
docs/
  index.html                  # Web game UI
  app.js                      # Web game logic (draft, sim, probability)
  nfl_data.json               # Generated NFL data (CI rebuilds on deploy)
  .nojekyll                   # Serve static files without Jekyll
scripts/
  build_nfl_data.py           # Build web data from nflreadpy (1999–2025)
main.py                       # Console entry point
src/                          # Python rankings, draft, simulation
tests/
  test_rankings.py
```

## Data Source

Stats from [nflreadpy](https://nflreadpy.nflverse.com/) / nflverse (1999–2025):

- Player stats aggregated by team-season (traded players appear per team)
- All rostered skill-position players per team-season in web data
- Top 3 O-line units and top 3 defenses per year
- Defensive scheme inferred from play-by-play personnel

## Deployment (GitHub Actions)

The **Deploy GitHub Pages** workflow:

1. Caches pip and nflverse downloads for faster rebuilds
2. Runs `python scripts/build_nfl_data.py` (1999–2025) — outputs `nfl_data.json` and compressed `nfl_data.json.gz`
3. Uploads the `docs/` folder as a Pages artifact
4. Deploys to the `github-pages` environment

Trigger manually from **Actions → Deploy GitHub Pages → Run workflow**, or push to `main`.

## Performance (multi-user)

GitHub Pages serves static files from a CDN — each player runs the game in their own browser with no shared server load. Optimizations:

- **~294 KB compressed data** (`nfl_data.json.gz`) instead of ~1.9 MB raw JSON on first load
- **Browser Cache API** stores parsed rosters locally for instant return visits
- **Indexed lookups** for team/position draft queries (no full-array scans during picks)
- **Preloaded fonts and scripts** for faster first paint

Live game: **https://architexstudio.github.io/Code_in_Place_Project/**

## Code in Place Submission

- **Title:** 17-0: Build Your Perfect Football Season
- **Published link:** https://github.com/ArchitexStudio/Code_in_Place_Project
- **Live demo:** https://architexstudio.github.io/Code_in_Place_Project/
- **Thumbnail:** Screenshot of draft board + field depth chart or final 17-0 screen
- **YouTube (optional):** Screen recording of web draft → season simulation

## Concepts Used

Variables, strings, lists, dictionaries, functions, modules, user input, randomness, probability, file/data loading, and browser UI with fetch/API-style JSON data.
