"""Forge v8 citation verifier: online DOI verification with offline fallback.

Borrowed from zLanqing/codex-claude-academic-skills (CrossRef citation
verification) and bahayonghang/academic-writing-skills (provenance fields are
not proof). Every DOI found in the references is:

  1. format-checked against the DOI pattern;
  2. verified live against the CrossRef REST API
     (https://api.crossref.org/works/{doi}) when the network is reachable;
  3. marked `degraded` when the network is unavailable, so the team knows the
     verification did not actually run (never silently trusted).

Exit code: 0 = all DOIs verified or degraded (nothing failed);
           1 = at least one DOI failed live verification;
           2 = no DOI found.

Usage:
    python citation_verify.py --markdown paper.md --output-dir <dir>
    python citation_verify.py --references refs.txt --output-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9a-z]+")
CROSSREF_URL = "https://api.crossref.org/works/{doi}?mailto=forge.mathmodeling@example.com"
TIMEOUT = 8


def extract_dois(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for match in DOI_PATTERN.finditer(text):
        doi = match.group(0).rstrip(".,;)]}，。；）】")
        if doi not in seen:
            seen[doi] = None
    return list(seen)


def verify_online(doi: str) -> dict:
    url = CROSSREF_URL.format(doi=urllib.parse.quote(doi, safe="/"))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (forge math-modeling)"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                return {"doi": doi, "status": "failed", "reason": f"HTTP {response.status}"}
            payload = json.loads(response.read().decode("utf-8"))
            message = payload.get("message", {})
            title = (message.get("title") or [""])[0]
            if not title:
                return {"doi": doi, "status": "failed", "reason": "no title in CrossRef record"}
            return {"doi": doi, "status": "verified", "title": title[:200]}
    except urllib.error.HTTPError as exc:
        return {"doi": doi, "status": "failed", "reason": f"HTTP {exc.code}"}
    except Exception as exc:  # network / timeout / DNS
        return {"doi": doi, "status": "degraded", "reason": f"{type(exc).__name__}: {exc}"}


def run_verify(markdown_path: Path | None, references_path: Path | None) -> dict:
    if markdown_path is None and references_path is None:
        raise ValueError("Provide --markdown or --references")
    text = markdown_path.read_text(encoding="utf-8") if markdown_path else references_path.read_text(encoding="utf-8")
    dois = extract_dois(text)
    if not dois:
        return {
            "schema": "forge-citation-verify/v1",
            "doi_count": 0,
            "status": "no_doi",
            "results": [],
            "summary": "No DOI found in the references. Structure-only check: ensure each entry has author, title, source, year.",
        }

    results = [verify_online(doi) for doi in dois]
    verified = [r for r in results if r["status"] == "verified"]
    failed = [r for r in results if r["status"] == "failed"]
    degraded = [r for r in results if r["status"] == "degraded"]
    overall = "failed" if failed else ("verified" if verified and not degraded else "degraded")
    return {
        "schema": "forge-citation-verify/v1",
        "doi_count": len(dois),
        "status": overall,
        "results": results,
        "summary": (
            f"{len(verified)} verified, {len(failed)} failed, {len(degraded)} degraded "
            "(network unavailable)."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify reference DOIs against CrossRef.")
    parser.add_argument("--markdown", default=None, help="paper.md containing the references")
    parser.add_argument("--references", default=None, help="plain-text references file")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    md_path = Path(args.markdown) if args.markdown else None
    ref_path = Path(args.references) if args.references else None
    if md_path is None and ref_path is None:
        print("ERROR: provide --markdown or --references", file=sys.stderr)
        return 2

    result = run_verify(md_path, ref_path)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "citation_verify.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "doi_count": result["doi_count"],
                      "summary": result["summary"], "report": str(report.resolve())}, ensure_ascii=False))
    if result["status"] == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
