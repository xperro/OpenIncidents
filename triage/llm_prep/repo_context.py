"""Repository checkout and lightweight snippet extraction for LLM preparation."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from typing import Any

from ..errors import UserError
from ..validation import command_exists, run_subprocess


DEFAULT_EXTENSIONS = {
    ".go",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".cs",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".sql",
    ".yaml",
    ".yml",
    ".json",
}
STOPWORDS = {
    "error",
    "errors",
    "warning",
    "critical",
    "failed",
    "failure",
    "panic",
    "exception",
    "timeout",
    "request",
    "service",
    "cloud",
    "gcp",
    "aws",
    "postgres",
}


@dataclass
class RepoSource:
    repo_name: str
    repo_dir: str
    repo_url: str = ""
    branch: str = ""


def checkout_repo(cwd: str, repo_url: str, branch: str = "main", clone_url: str | None = None) -> RepoSource:
    if not command_exists("git"):
        raise UserError("`git` is required to clone repositories for `llm-prep`.")
    repo_url = repo_url.strip()
    if not repo_url:
        raise UserError("`--repo-url` cannot be empty.")
    repo_name = infer_repo_name(repo_url)
    source_url = clone_url.strip() if clone_url else repo_url
    cache_root = os.path.join(cwd, ".triage", "cache", "repos")
    os.makedirs(cache_root, exist_ok=True)
    digest = hashlib.sha1(f"{repo_url}#{branch}".encode("utf-8")).hexdigest()[:10]
    target_dir = os.path.join(cache_root, f"{repo_name}-{digest}")

    if not os.path.isdir(os.path.join(target_dir, ".git")):
        clone_cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            branch,
            source_url,
            target_dir,
        ]
        clone = run_subprocess(clone_cmd, cwd=cwd)
        if clone.returncode != 0:
            detail = clone.stderr.strip() or clone.stdout.strip()
            raise UserError(f"Failed to clone repo `{repo_url}`: {detail}")
    else:
        for cmd in (
            ["git", "-C", target_dir, "fetch", "--depth", "1", "origin", branch],
            ["git", "-C", target_dir, "checkout", branch],
            ["git", "-C", target_dir, "pull", "--ff-only", "origin", branch],
        ):
            result = run_subprocess(cmd, cwd=cwd)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip()
                raise UserError(f"Failed to update repo `{repo_url}`: {detail}")

    return RepoSource(repo_name=repo_name, repo_dir=target_dir, repo_url=repo_url, branch=branch)


def local_repo(path: str) -> RepoSource:
    if not os.path.isabs(path):
        raise UserError("`--repo-path` must be an absolute path.")
    if not os.path.isdir(path):
        raise UserError(f"Repository path does not exist: {path}")
    name = os.path.basename(path.rstrip(os.sep)) or "local-repo"
    return RepoSource(repo_name=name, repo_dir=path)


def enrich_prepared_with_repo_context(
    prepared: dict[str, Any],
    repos: list[RepoSource],
    *,
    max_files_per_incident: int = 3,
    max_snippet_lines: int = 80,
    max_snippet_chars: int = 2400,
) -> dict[str, Any]:
    incidents = prepared.get("incidents")
    if not isinstance(incidents, list):
        return prepared
    for incident in incidents:
        if not isinstance(incident, dict):
            continue
        terms = extract_query_terms(
            " ".join(
                [
                    str(incident.get("incident_summary") or ""),
                    str(incident.get("error_message") or ""),
                    str(incident.get("stacktrace_excerpt") or ""),
                ]
            )
        )
        matches: list[dict[str, Any]] = []
        for repo in repos:
            matches.extend(
                scan_repo_for_terms(
                    repo,
                    terms,
                    max_files=max_files_per_incident,
                    max_snippet_lines=max_snippet_lines,
                    max_snippet_chars=max_snippet_chars,
                )
            )
        matches.sort(key=lambda item: (int(item.get("score", 0)), -int(item.get("line_start", 1))), reverse=True)
        incident["repo_context"] = matches[:max_files_per_incident]
        if incident["repo_context"]:
            incident["analysis_mode"] = "with_repo"
            llm_input = incident.get("llm_input")
            if isinstance(llm_input, dict):
                llm_input["repo_context"] = incident["repo_context"]
    return prepared


def scan_repo_for_terms(
    repo: RepoSource,
    terms: list[str],
    *,
    max_files: int,
    max_snippet_lines: int,
    max_snippet_chars: int,
) -> list[dict[str, Any]]:
    if not terms:
        return []
    candidates: list[dict[str, Any]] = []
    for root, dirnames, filenames in os.walk(repo.repo_dir):
        dirnames[:] = [name for name in dirnames if name not in {".git", "__pycache__", "node_modules", ".venv"}]
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext and ext not in DEFAULT_EXTENSIONS:
                continue
            path = os.path.join(root, filename)
            if os.path.getsize(path) > 600_000:
                continue
            relpath = os.path.relpath(path, repo.repo_dir)
            file_matches = first_file_match(path, terms)
            if not file_matches:
                continue
            score, line_number, matched_term = file_matches
            snippet, line_start, line_end = extract_snippet(path, line_number, max_snippet_lines, max_snippet_chars)
            candidates.append(
                {
                    "repo_name": repo.repo_name,
                    "repo_url": repo.repo_url,
                    "branch": repo.branch,
                    "file_path": relpath,
                    "line_start": line_start,
                    "line_end": line_end,
                    "match_term": matched_term,
                    "score": score,
                    "snippet": snippet,
                }
            )
            if len(candidates) >= max_files * 3:
                break
        if len(candidates) >= max_files * 3:
            break
    return candidates


def first_file_match(path: str, terms: list[str]) -> tuple[int, int, str] | None:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            lines = handle.readlines()
    except OSError:
        return None
    best: tuple[int, int, str] | None = None
    for idx, line in enumerate(lines, start=1):
        lower = line.lower()
        score = 0
        matched = ""
        for term in terms:
            if term in lower:
                score += 1
                matched = term if not matched else matched
        if score <= 0:
            continue
        if best is None or score > best[0]:
            best = (score, idx, matched)
    return best


def extract_snippet(path: str, line_number: int, max_lines: int, max_chars: int) -> tuple[str, int, int]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            lines = handle.readlines()
    except OSError:
        return ("", line_number, line_number)
    half = max(1, max_lines // 2)
    start = max(1, line_number - half)
    end = min(len(lines), start + max_lines - 1)
    if end - start + 1 < max_lines and start > 1:
        start = max(1, end - max_lines + 1)
    chunk = []
    for idx in range(start, end + 1):
        chunk.append(f"{idx:>6} | {lines[idx - 1].rstrip()}")
    text = "\n".join(chunk)
    if len(text) > max_chars:
        text = text[:max_chars]
    return (text, start, end)


def extract_query_terms(raw_text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_./:-]{2,}", raw_text.lower())
    weighted = []
    for token in tokens:
        clean = token.strip(".,:;()[]{}<>\"'")
        if len(clean) < 4:
            continue
        if clean in STOPWORDS:
            continue
        weighted.append(clean)
    seen = set()
    unique = []
    for token in weighted:
        if token in seen:
            continue
        seen.add(token)
        unique.append(token)
    return unique[:12]


def infer_repo_name(repo_url: str) -> str:
    tail = repo_url.rstrip("/").rsplit("/", 1)[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    if not tail:
        return "repo"
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", tail)
