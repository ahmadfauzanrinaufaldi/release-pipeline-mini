# release-pipeline-mini

Pipeline rilis mini: API FastAPI, Docker, CI GitHub Actions. Tahap berikutnya: CD bertahap (Dev/UAT/Prod), rollback, Ansible, log deployment.

## Jalankan lokal

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements-dev.txt
    ruff check . && pytest -q
    uvicorn app.main:app --reload

## Docker

    APP_VERSION=0.1.0 docker compose up --build
    curl localhost:8000/health
    curl localhost:8000/version

## Status

- [x] Sesi 1: aplikasi, tes, Docker
- [x] Sesi 2: CI (lint, tes, build, smoke test)
- [x] Branch protection aktif
- [ ] Sesi 3: CD Dev/UAT/Prod, rollback
- [ ] Sesi 4: Ansible, changelog, log deployment CSV

## Catatan kegagalan dan perbaikan

(isi tiap kali pipeline gagal: apa yang rusak, cara membaca lognya, perbaikannya)
