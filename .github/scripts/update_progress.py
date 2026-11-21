#!/usr/bin/env python3
"""Aktualizuje issue "Postep modulow" tabela postepu prac.

Zlicza issues przypisane do modulu - przez prefiks w tytule `[<nazwa>] ...`
albo etykiete `module:<nazwa>` (otwarte i zamkniete, bez pull requestow i bez
issues z etykieta `epic`) i wpisuje tabele do tresci issue o tytule
PROGRESS_TITLE. Jesli takie issue nie istnieje, zostaje utworzone.
Niczego nie commituje, wiec dziala przy chronionej galezi main.

Uzycie (w GitHub Actions):
    GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python3 update_progress.py

Podglad lokalny bez zapisu (plik JSON w formacie odpowiedzi /issues):
    PROGRESS_FAKE_JSON=issues.json GITHUB_REPOSITORY=owner/repo python3 update_progress.py
"""

import json
import os
import re
import sys
import urllib.request

# Kolejnosc = kierunek zaleznosci. Moduly spoza listy trafiaja na koniec.
MODULES = ["core", "attacks", "board", "movegen", "eval", "search", "uci", "app"]
LABEL_PREFIX = "module:"
TITLE_PREFIX = re.compile(r"^\s*\[([A-Za-z0-9_-]+)\]")
SKIP_LABELS = {"epic"}
BAR_WIDTH = 20
PROGRESS_TITLE = "Postęp modułów"
API = "https://api.github.com"


def api(method: str, path: str, token: str, data: dict | None = None):
    req = urllib.request.Request(
        f"{API}{path}",
        method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        })
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def fetch_issues(repo: str, token: str) -> list[dict]:
    issues, page = [], 1
    while True:
        batch = api("GET", f"/repos/{repo}/issues?state=all&per_page=100&page={page}", token)
        issues += batch
        if len(batch) < 100:
            return issues
        page += 1


def count(issues: list[dict]) -> dict[str, list[int]]:
    stats: dict[str, list[int]] = {m: [0, 0] for m in MODULES}  # [zamkniete, wszystkie]
    for issue in issues:
        if "pull_request" in issue:
            continue
        labels = {l["name"] for l in issue["labels"]}
        if labels & SKIP_LABELS:
            continue
        modules = {l[len(LABEL_PREFIX):] for l in labels if l.startswith(LABEL_PREFIX)}
        if m := TITLE_PREFIX.match(issue.get("title", "")):
            modules.add(m.group(1).lower())
        for module in modules:
            s = stats.setdefault(module, [0, 0])
            s[1] += 1
            s[0] += issue["state"] == "closed"
    return stats


def bar(done: int, total: int) -> str:
    filled = round(BAR_WIDTH * done / total) if total else 0
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def row(link: str, done: int, total: int) -> str:
    pct = f"{100 * done // total}%" if total else "-"
    return f"| {link} | {bar(done, total)} | {pct} | {done} / {total} |"


def render(stats: dict[str, list[int]], repo: str) -> str:
    base = f"https://github.com/{repo}/issues"
    lines = [
        "Jedynym kamieniem milowym jest **działający silnik**. Postęp liczony jest z issues "
        "z prefiksem [moduł] w tytule.",
        "",
        "| Moduł | Postęp | % | Zamknięte / wszystkie |",
        "| ----- | ------ | - | --------------------- |",
    ]
    for name, (done, total) in stats.items():
        link = f"[{name}]({base}?q=is%3Aissue+%22%5B{name}%5D%22+in%3Atitle)"
        lines.append(row(link, done, total))
    done = sum(s[0] for s in stats.values())
    total = sum(s[1] for s in stats.values())
    lines.append(row("**Działający silnik**", done, total))
    lines += ["", "_Aktualizowane automatycznie przez .github/workflows/progress.yml "
              "- nie edytuj ręcznie._"]
    return "\n".join(lines)


def main() -> int:
    repo = os.environ["GITHUB_REPOSITORY"]
    fake = os.environ.get("PROGRESS_FAKE_JSON")
    if fake:
        with open(fake, encoding="utf-8") as f:
            print(render(count(json.load(f)), repo))
        return 0

    token = os.environ["GITHUB_TOKEN"]
    issues = fetch_issues(repo, token)
    body = render(count(issues), repo)

    target = next((i for i in issues if "pull_request" not in i
                   and i["title"] == PROGRESS_TITLE and i["state"] == "open"), None)
    if target is None:
        created = api("POST", f"/repos/{repo}/issues", token,
                      {"title": PROGRESS_TITLE, "body": body})
        print(f"Utworzono issue #{created['number']} - przypnij je w zakladce Issues.")
    elif (target.get("body") or "").strip() != body.strip():
        api("PATCH", f"/repos/{repo}/issues/{target['number']}", token, {"body": body})
        print(f"Zaktualizowano issue #{target['number']}.")
    else:
        print("Bez zmian.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
