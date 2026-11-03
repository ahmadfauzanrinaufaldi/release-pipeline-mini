#!/usr/bin/env python3
"""Export deployment history of a GitHub repo to a CSV file.

Reads the workflow runs named "CD" and "Rollback" through the GitHub REST API,
looks at the deploy jobs inside each run, and writes one CSV row per job that
actually ran (skipped jobs are left out).

Usage:
    python scripts/export_deploy_log.py ahmadfauzanrinaufaldi/release-pipeline-mini
    python scripts/export_deploy_log.py OWNER/REPO --out data/deploy_log.csv

Public repos need no token (60 API calls per hour). To raise the limit, set
the GITHUB_TOKEN environment variable.
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
WORKFLOWS = {"CD", "Rollback"}
DEPLOY_JOBS = {"deploy-dev": "dev", "deploy-uat": "uat", "deploy-prod": "prod"}
ROLLBACK_TITLE = re.compile(r"^Rollback (\S+) to (\S+)$")

COLUMNS = [
    "kind", "environment", "version", "result", "started_at", "completed_at",
    "duration_s", "gap_since_uat_s", "commit_sha", "actor", "event", "run_id", "run_url",
]


def get(path):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "deploy-log-exporter"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        sys.exit(f"GitHub API error {err.code} for {path}: {err.reason}")
    except urllib.error.URLError as err:
        sys.exit(f"Cannot reach GitHub API: {err.reason}")


def parse_time(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ") if value else None


def seconds(start, end):
    return int((end - start).total_seconds()) if start and end else ""


def fetch_runs(repo):
    runs, page = [], 1
    while True:
        data = get(f"/repos/{repo}/actions/runs?per_page=100&page={page}")
        batch = data.get("workflow_runs", [])
        runs.extend(batch)
        if len(batch) < 100:
            return runs
        page += 1


def version_of(run):
    branch = run.get("head_branch") or ""
    if re.match(r"^v\d", branch):
        return branch
    return "sha-" + run["head_sha"][:7]


def rows_for_run(repo, run):
    jobs = get(f"/repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100").get("jobs", [])
    uat_done = None
    for job in jobs:
        if job["name"] == "deploy-uat" and job.get("conclusion") == "success":
            uat_done = parse_time(job.get("completed_at"))

    rows = []
    for job in jobs:
        if job.get("conclusion") in (None, "skipped", "cancelled"):
            continue
        started = parse_time(job.get("started_at"))
        completed = parse_time(job.get("completed_at"))
        gap = ""
        if run["name"] == "Rollback" and job["name"] == "rollback":
            match = ROLLBACK_TITLE.match(run.get("display_title", ""))
            kind, env, version = "rollback", (match.group(1) if match else "unknown"), (
                match.group(2) if match else "unknown")
        elif job["name"] in DEPLOY_JOBS:
            kind, env, version = "deploy", DEPLOY_JOBS[job["name"]], version_of(run)
            if env == "prod" and uat_done and started:
                gap = seconds(uat_done, started)
        else:
            continue
        rows.append({
            "kind": kind, "environment": env, "version": version,
            "result": job["conclusion"],
            "started_at": job.get("started_at", ""), "completed_at": job.get("completed_at", ""),
            "duration_s": seconds(started, completed), "gap_since_uat_s": gap,
            "commit_sha": run["head_sha"][:7],
            "actor": (run.get("actor") or {}).get("login", ""),
            "event": run["event"], "run_id": run["id"], "run_url": run["html_url"],
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", help="OWNER/REPO")
    parser.add_argument("--out", default="deploy_log.csv")
    args = parser.parse_args()

    rows = []
    for run in fetch_runs(args.repo):
        if run["name"] in WORKFLOWS:
            rows.extend(rows_for_run(args.repo, run))
    rows.sort(key=lambda r: r["started_at"])

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
