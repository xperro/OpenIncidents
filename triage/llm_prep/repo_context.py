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
ALLOWED_NO_EXTENSION_FILENAMES = {
    "Dockerfile",
    "Makefile",
}
EXCLUDED_BASENAMES = {
    "mvnw",
    "mvnw.cmd",
    "gradlew",
    "gradlew.bat",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "go.sum",
    "cargo.lock",
    "composer.lock",
}
PATH_INCLUDE_HINTS = (
    "/internal/",
    "/src/",
    "/service/",
    "/services/",
    "/handler/",
    "/handlers/",
    "/repository/",
    "/repositories/",
    "/controller/",
    "/controllers/",
    "/api/",
    "/domain/",
    "/usecase/",
)
PATH_EXCLUDE_HINTS = (
    "/docs/",
    "/scripts/",
    "/ops/",
    "/infra/",
    "/.github/",
    "/node_modules/",
    "/vendor/",
    "/build/",
    "/dist/",
    "/target/",
    "/.mvn/",
)
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


def checkout_repo(
    cwd: str,
    repo_url: str,
    branch: str = "main",
    clone_url: str | None = None,
    fallback_clone_url: str | None = None,
) -> RepoSource:
    if not command_exists("git"):
        raise UserError("`git` is required to clone repositories for `llm-prep`.")
    repo_url = repo_url.strip()
    if not repo_url:
        raise UserError("`--repo-url` cannot be empty.")
    repo_name = infer_repo_name(repo_url)
    source_url = clone_url.strip() if clone_url else repo_url
    fallback_url = fallback_clone_url.strip() if fallback_clone_url else ""
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
            if fallback_url and fallback_url != source_url and is_git_auth_error(detail):
                retry_cmd = [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    branch,
                    fallback_url,
                    target_dir,
                ]
                retry = run_subprocess(retry_cmd, cwd=cwd)
                if retry.returncode == 0:
                    source_url = fallback_url
                else:
                    retry_detail = retry.stderr.strip() or retry.stdout.strip()
                    raise UserError(f"Failed to clone repo `{repo_url}`: {retry_detail}")
            else:
                raise UserError(f"Failed to clone repo `{repo_url}`: {detail}")
    else:
        # Keep cache usable for private repos by refreshing origin with the current source URL.
        set_origin = run_subprocess(["git", "-C", target_dir, "remote", "set-url", "origin", source_url], cwd=cwd)
        if set_origin.returncode != 0:
            detail = set_origin.stderr.strip() or set_origin.stdout.strip()
            raise UserError(f"Failed to update repo `{repo_url}`: {detail}")
        update_cmds = (
            ["git", "-C", target_dir, "fetch", "--depth", "1", "origin", branch],
            ["git", "-C", target_dir, "checkout", branch],
            ["git", "-C", target_dir, "pull", "--ff-only", "origin", branch],
        )
        for cmd in update_cmds:
            result = run_subprocess(cmd, cwd=cwd)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip()
                if fallback_url and fallback_url != source_url and is_git_auth_error(detail):
                    swap = run_subprocess(
                        ["git", "-C", target_dir, "remote", "set-url", "origin", fallback_url],
                        cwd=cwd,
                    )
                    if swap.returncode != 0:
                        swap_detail = swap.stderr.strip() or swap.stdout.strip()
                        raise UserError(f"Failed to update repo `{repo_url}`: {swap_detail}")
                    source_url = fallback_url
                    retried_ok = True
                    for retry_cmd in update_cmds:
                        retry = run_subprocess(retry_cmd, cwd=cwd)
                        if retry.returncode != 0:
                            retried_ok = False
                            retry_detail = retry.stderr.strip() or retry.stdout.strip()
                            raise UserError(f"Failed to update repo `{repo_url}`: {retry_detail}")
                    if retried_ok:
                        break
                else:
                    raise UserError(f"Failed to update repo `{repo_url}`: {detail}")

    return RepoSource(repo_name=repo_name, repo_dir=target_dir, repo_url=repo_url, branch=branch)


def is_git_auth_error(detail: str) -> bool:
    lowered = detail.lower()
    markers = (
        "could not read username",
        "authentication failed",
        "access denied",
        "requested url returned error: 401",
        "requested url returned error: 403",
        "write access to repository not granted",
    )
    return any(marker in lowered for marker in markers)


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
        llm_input = incident.get("llm_input")
        evidence = llm_input.get("evidence") if isinstance(llm_input, dict) else []
        evidence_excerpt = ""
        if isinstance(evidence, list) and evidence:
            evidence_excerpt = str(evidence[0])[:1600]
        search_text = " ".join(
            [
                str(incident.get("incident_summary") or ""),
                str(incident.get("error_message") or ""),
                str(incident.get("stacktrace_excerpt") or ""),
                evidence_excerpt,
            ]
        )
        hints = extract_location_hints(search_text)
        terms = extract_query_terms(
            search_text
        )
        for hint in hints:
            file_path = str(hint.get("file_path") or "")
            if not file_path:
                continue
            basename = os.path.basename(file_path).lower()
            if basename and basename not in terms:
                terms.append(basename)
        matches: list[dict[str, Any]] = []
        for repo in repos:
            matches.extend(
                scan_repo_for_terms(
                    repo,
                    terms,
                    hints=hints,
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
    hints: list[dict[str, Any]] | None = None,
    max_files: int,
    max_snippet_lines: int,
    max_snippet_chars: int,
) -> list[dict[str, Any]]:
    if not terms and not hints:
        return []
    hints = hints or []
    candidates: list[dict[str, Any]] = []
    for root, dirnames, filenames in os.walk(repo.repo_dir):
        dirnames[:] = [name for name in dirnames if name not in {".git", "__pycache__", "node_modules", ".venv"}]
        for filename in filenames:
            lower_name = filename.lower()
            if lower_name in EXCLUDED_BASENAMES:
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext:
                if ext not in DEFAULT_EXTENSIONS:
                    continue
            elif filename not in ALLOWED_NO_EXTENSION_FILENAMES:
                continue
            path = os.path.join(root, filename)
            if os.path.getsize(path) > 600_000:
                continue
            relpath = os.path.relpath(path, repo.repo_dir)
            file_matches = first_file_match(path, terms) if terms else None
            hint_score, hinted_line = location_hint_score(relpath, hints)
            if not file_matches and hint_score <= 0:
                continue
            score = 0
            matched_term = ""
            line_number = hinted_line or 1
            if file_matches:
                base_score, base_line, base_term = file_matches
                score += base_score
                matched_term = base_term
                if not hinted_line:
                    line_number = base_line
            score += hint_score
            score += path_score_adjustment(relpath)
            ext = os.path.splitext(relpath)[1].lower()
            if ext == ".json" and hint_score <= 0:
                score -= 4
            snippet, line_start, line_end = extract_snippet(path, line_number, max_snippet_lines, max_snippet_chars)
            if not snippet.strip():
                continue
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


def path_score_adjustment(relpath: str) -> int:
    path = "/" + relpath.replace("\\", "/").lower()
    score = 0
    for hint in PATH_INCLUDE_HINTS:
        if hint in path:
            score += 3
    for hint in PATH_EXCLUDE_HINTS:
        if hint in path:
            score -= 2
    return score


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


def extract_location_hints(raw_text: str) -> list[dict[str, Any]]:
    text = str(raw_text or "")
    hints: list[dict[str, Any]] = []
    path_line_re = re.compile(
        r"(?P<path>[A-Za-z0-9_\-./]+?\.(?:go|py|java|kt|rb|php|cs|rs|cpp|c|h|hpp|js|ts|tsx)):(?P<line>\d+)"
    )
    for match in path_line_re.finditer(text):
        file_path = match.group("path").strip().lstrip("./")
        line_raw = match.group("line")
        try:
            line_number = int(line_raw)
        except ValueError:
            line_number = 0
        hints.append({"file_path": file_path, "line": line_number})
    seen = set()
    unique = []
    for hint in hints:
        key = (hint.get("file_path"), int(hint.get("line") or 0))
        if key in seen:
            continue
        seen.add(key)
        unique.append(hint)
    return unique[:6]


def location_hint_score(relpath: str, hints: list[dict[str, Any]]) -> tuple[int, int]:
    if not hints:
        return (0, 0)
    path = relpath.replace("\\", "/").lower()
    basename = os.path.basename(path)
    best_score = 0
    best_line = 0
    for hint in hints:
        file_path = str(hint.get("file_path") or "").replace("\\", "/").lower()
        if not file_path:
            continue
        hint_basename = os.path.basename(file_path)
        score = 0
        if path.endswith(file_path):
            score += 8
        elif basename == hint_basename and hint_basename:
            score += 5
        elif hint_basename and hint_basename in basename:
            score += 3
        if score > best_score:
            best_score = score
            best_line = int(hint.get("line") or 0)
    return (best_score, best_line)


def infer_repo_name(repo_url: str) -> str:
    tail = repo_url.rstrip("/").rsplit("/", 1)[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    if not tail:
        return "repo"
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", tail)
