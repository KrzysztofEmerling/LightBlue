#!/usr/bin/env python3
"""Aktualizuje tabele postepu modulow w pliku Markdown.

Zlicza issues przypisane do modulu - przez prefiks w tytule `[<nazwa>] ...`
albo etykiete `module:<nazwa>` (otwarte i zamkniete, bez pull requestow i bez
issues z etykieta `epic`) i wstawia tabele miedzy znacznikami:

    <!-- progress:start -->
    <!-- progress:end -->

Uzycie (w GitHub Actions):
    GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python3 update_progress.py PLAN_PROJEKTU.md

Test lokalny bez API (plik JSON w formacie odpowiedzi /issues):
    PROGRESS_FAKE_JSON=issues.json GITHUB_REPOSITORY=owner/repo python3 update_progress.py plik.md
"""

import json
import os
import re
import sys
import urllib.request

# Kolejnosc = kierunek zaleznosci. Etykiety module:* spoza listy trafiaja na koniec.
MODULES = ["core", "attacks", "board", "movegen", "eval", "search", "uci", "app"]
LABEL_PREFIX = "module:"
TITLE_PREFIX = re.compile(r"^\s*\[([A-Za-z0-9_-]+)\]")
SKIP_LABELS = {"epic"}
BAR_WIDTH = 20
START, END = "<!-- progress:start -->", "<!-- progress:end -->"


def fetch_issues(repo: str, token: str) -> list[dict]:
    issues, page = [], 1
    while True:
        url = f"https://api.github.com/repos/{repo}/issues?state=all&per_page=100&page={page}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(req) as resp:
            batch = json.load(resp)
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
    return "`" + "█" * filled + "░" * (BAR_WIDTH - filled) + "`"


def row(name: str, link: str, done: int, total: int) -> str:
    pct = f"{100 * done // total}%" if total else "-"
    return f"| {link} | {bar(done, total)} | {pct} | {done} / {total} |"


def render(stats: dict[str, list[int]], repo: str) -> str:
    base = f"https://github.com/{repo}/issues"
    lines = ["| Moduł | Postęp | % | Zamknięte / wszystkie |",
             "| ----- | ------ | - | --------------------- |"]
    for name, (done, total) in stats.items():
        link = f"[`{name}`]({base}?q=is%3Aissue+%22%5B{name}%5D%22+in%3Atitle)"
        lines.append(row(name, link, done, total))
    done = sum(s[0] for s in stats.values())
    total = sum(s[1] for s in stats.values())
    lines.append(row("razem", "**Działający silnik**", done, total))
    return "\n".join(lines)


def main() -> int:
    path = sys.argv[1]
    repo = os.environ["GITHUB_REPOSITORY"]
    fake = os.environ.get("PROGRESS_FAKE_JSON")
    if fake:
        with open(fake, encoding="utf-8") as f:
            issues = json.load(f)
    else:
        issues = fetch_issues(repo, os.environ["GITHUB_TOKEN"])

    table = render(count(issues), repo)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        print(f"Brak znacznikow {START} / {END} w {path}", file=sys.stderr)
        return 1
    new = pattern.sub(lambda _: f"{START}\n{table}\n{END}", text)
    if new != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        print("Zaktualizowano tabele postepu.")
    else:
        print("Bez zmian.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
