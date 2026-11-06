# Repo and environment

## Repo
- Local: `C:\Users\satis\microburbs-hackathon-demos` (Windows 11; Git Bash and PowerShell; Python 3.14).
- Remotes: `origin` = https://github.com/Microburbs/microburbs-hackathon-demos (the organisers' demo repo - do NOT push there); `mine` = https://github.com/satishpoks/microburbs-rent-task (**PUBLIC**, created 2026-11-06 from the whole folder, `main` tracks `mine/main`).
- Because it is public: never commit the API key, `.env`, private day-of files, or cached API responses. `.gitignore` covers `.env`, `.env.*` (except `.env.example`), `rents/data/`, `rents/cache/`.
- Scan before the public push found no secrets in history. `.env` was never opened by Claude.
- Layout: `CLAUDE.md` (project instructions), `rents/fetcher.py`, `rents/test_fetcher.py`, `rents/docs/{README.md,PLAN.md,openapi.json}`, `rents/wiki/` (this wiki), demos: `fastapi-property-report`, `nextjs-suburb-map`, `python-quickstart`, `streamlit-property-explorer`.
- Env vars (`.env.example`): `MICROBURBS_API_KEY`, `MICROBURBS_API_BASE=https://api-ht.microburbs.com.au`.
- Git state when this wiki was written: first push done (commit with CLAUDE.md, README, openapi.json, .gitignore). The fetcher, tests, README/CLAUDE.md edits and this wiki were written afterwards; commit/push them (ask the user) so they are safe.
- User-level AGENTS.md says to run `graphify update .` after modifying code files in a session; not run so far.

## Python environment
- Installed: requests, httpx, pytest. **pandas MISSING**. lightgbm, xgboost, shap, scikit-learn, python-dotenv: not checked (fetcher works without dotenv).
- Do `pip install pandas lightgbm scikit-learn shap xgboost` BEFORE the competition if the network allows.
- Run tests: `cd rents && python -m pytest -q` (19 pass; pytest-asyncio deprecation warnings are harmless).

## Windows gotchas
- Console encoding is cp1252: printing non-ASCII from the spec (e.g. arrows) raises UnicodeEncodeError. Use `sys.stdout.reconfigure(encoding='ascii', errors='replace')` or write to files with `encoding='utf-8'`. `python -I` ignores PYTHONIOENCODING.
- Read JSON with `encoding='utf-8'`.
- Git warns about LF->CRLF; harmless.
- Scratchpad for temporary files: the session's scratchpad dir (not inside the repo).

## Tools/connectors notes
- Claude-in-Chrome extension was "not connected" (needs extension installed/enabled, logged into claude.ai, Chrome restart). Not needed now: the spec is saved locally.
- GitHub MCP server failed to connect (auth header); use the `gh` CLI (logged in as `satishpoks`).
