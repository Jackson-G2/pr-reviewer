#!/usr/bin/env python3
"""
PR Reviewer — Architecture-focused PR reviewer for large open-source pull requests.

Usage:
    python pr_reviewer.py <pr_url> [-o output.md] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ─── Data Types ──────────────────────────────────────────────────────────────

@dataclass
class PRInfo:
    number: int
    title: str
    author: str
    state: str
    created: str
    commits: int
    additions: int
    deletions: int
    changed_files: int
    base: str
    head: str
    body: str
    labels: list[str]
    repo_owner: str
    repo_name: str


@dataclass
class FileInfo:
    filename: str
    status: str
    additions: int
    deletions: int
    patch: str = ""


@dataclass
class ComponentGroup:
    name: str
    files: list[FileInfo] = field(default_factory=list)

    @property
    def total_additions(self) -> int:
        return sum(f.additions for f in self.files)

    @property
    def total_deletions(self) -> int:
        return sum(f.deletions for f in self.files)

    @property
    def file_count(self) -> int:
        return len(self.files)


@dataclass
class Issue:
    category: str  # BUG, DUPLICATION, INCONSISTENCY, TEST GAP, API RISK, FORCE CAST
    title: str
    file: str
    line: int | None
    description: str
    fix: str = ""


@dataclass
class ReviewFile:
    filename: str
    lines: int
    look_for: str
    depends_on: list[str] = field(default_factory=list)


# ─── GitHub API ──────────────────────────────────────────────────────────────

def fetch_json(url: str) -> Any:
    """Fetch JSON from GitHub API, handling control characters in patches."""
    req = urllib.request.Request(url, headers={"User-Agent": "pr-reviewer"})
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", raw)
    return json.loads(cleaned, strict=False)


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Extract owner, repo, number from GitHub PR URL."""
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if not m:
        print(f"Error: Invalid PR URL: {url}", file=sys.stderr)
        sys.exit(1)
    return m.group(1), m.group(2), int(m.group(3))


def fetch_pr_data(owner: str, repo: str, number: int) -> tuple[PRInfo, list[FileInfo], list[dict], list[dict]]:
    """Fetch all PR data from GitHub API."""
    base = f"https://api.github.com/repos/{owner}/{repo}"

    # PR metadata
    pr = fetch_json(f"{base}/pulls/{number}")

    # Files (paginate)
    all_files: list[dict] = []
    page = 1
    while True:
        batch = fetch_json(f"{base}/pulls/{number}/files?per_page=100&page={page}")
        if not isinstance(batch, list) or len(batch) == 0:
            break
        all_files.extend(batch)
        page += 1

    # Comments
    review_comments = fetch_json(f"{base}/pulls/{number}/comments")
    issue_comments = fetch_json(f"{base}/issues/{number}/comments")

    pr_info = PRInfo(
        number=number,
        title=pr["title"],
        author=pr["user"]["login"],
        state=pr["state"],
        created=pr["created_at"],
        commits=pr["commits"],
        additions=pr["additions"],
        deletions=pr["deletions"],
        changed_files=pr["changed_files"],
        base=pr["base"]["ref"],
        head=pr["head"]["ref"],
        body=pr.get("body", ""),
        labels=[l["name"] for l in pr.get("labels", [])],
        repo_owner=owner,
        repo_name=repo,
    )

    files = [
        FileInfo(
            filename=f["filename"],
            status=f["status"],
            additions=f["additions"],
            deletions=f["deletions"],
            patch=f.get("patch", ""),
        )
        for f in all_files
    ]

    return pr_info, files, review_comments, issue_comments


# ─── Architecture Knowledge ──────────────────────────────────────────────────

REPO_ARCHITECTURE: dict[str, dict[str, Any]] = {}

def load_repo_architecture(owner: str, repo: str) -> dict[str, Any] | None:
    """Load architecture knowledge for a repo if available."""
    key = f"{owner}/{repo}"
    if key in REPO_ARCHITECTURE:
        return REPO_ARCHITECTURE[key]

    # Try to load from repos/ directory
    repo_file = Path(__file__).parent / "repos" / f"{owner}_{repo}.yaml"
    if repo_file.exists():
        try:
            import yaml
            with open(repo_file) as f:
                data = yaml.safe_load(f)
            REPO_ARCHITECTURE[key] = data
            return data
        except ImportError:
            # yaml not available, try json
            json_file = repo_file.with_suffix(".json")
            if json_file.exists():
                with open(json_file) as f:
                    data = json.load(f)
                REPO_ARCHITECTURE[key] = data
                return data

    # Check for embedded architecture knowledge
    if key in EMBEDDED_ARCHITECTURE:
        REPO_ARCHITECTURE[key] = EMBEDDED_ARCHITECTURE[key]
        return EMBEDDED_ARCHITECTURE[key]

    return None


# Embedded architecture knowledge for known repos
EMBEDDED_ARCHITECTURE: dict[str, dict[str, Any]] = {
    "moreSwift/swift-cross-ui": {
        "name": "moreSwift/swift-cross-ui",
        "description": "SwiftUI-like cross-platform UI framework with pluggable backends",
        "directory_structure": {
            "Sources/SwiftCrossUI": "Core framework",
            "Sources/SwiftCrossUI/Backend": "Backend protocol definitions",
            "Sources/SwiftCrossUI/Backend/BackendFeatures": "~35+ small protocols for backend features",
            "Sources/SwiftCrossUI/Environment": "EnvironmentValues propagation",
            "Sources/SwiftCrossUI/Layout": "Two-phase measure/commit layout system",
            "Sources/SwiftCrossUI/State": "@State, @Binding, ObservableProperty",
            "Sources/SwiftCrossUI/ViewGraph": "ViewGraph, ViewGraphNode, AnyViewGraphNode",
            "Sources/SwiftCrossUI/Views": "All view types + Modifiers",
            "Sources/AppKitBackend": "macOS backend (NSView, NSCustomWindow)",
            "Sources/UIKitBackend": "iOS/tvOS/visionOS backend (UIView)",
            "Sources/GtkBackend": "Linux GTK4 backend",
            "Sources/Gtk3Backend": "Linux GTK3 backend (legacy)",
            "Sources/WinUIBackend": "Windows backend (WinUI3)",
            "Sources/DummyBackend": "In-memory backend for testing",
            "Sources/Gtk": "Swift bindings for GTK4",
            "Tests": "Swift Testing framework tests",
            "Examples": "Example apps",
        },
        "key_patterns": [
            {
                "name": "BackendFeatures protocol composition",
                "description": "New features add a protocol under BackendFeatures/, backends conform. FullAppBackend typealias updated.",
                "indicators": ["BackendFeatures/", "FullAppBackend.swift"],
            },
            {
                "name": "View lifecycle",
                "description": "children() → asWidget() → computeLayout() → commit(). commit() is where backend methods get called.",
                "indicators": ["ViewGraphNode.swift", "commit()"],
            },
            {
                "name": "Environment propagation",
                "description": "Features flow through EnvironmentValues (struct). View modifiers use EnvironmentModifier.",
                "indicators": ["EnvironmentValues.swift", "EnvironmentModifier"],
            },
            {
                "name": "State management",
                "description": "Custom Publisher/Cancellable (not Combine). @State uses StateImpl<Storage> with reference-type storage.",
                "indicators": ["State/", "Publisher", "Cancellable"],
            },
        ],
        "known_duplication": [
            {
                "pattern": "FocusStateManager",
                "description": "Each backend has its own FocusStateManager with identical [ObjectIdentifier: Set<FocusData>] pattern",
                "files": ["AppKitBackend+Focus.swift", "GtkBackend+Focus.swift", "WinUIBackend+Focus.swift"],
            },
        ],
        "testing": {
            "framework": "Swift Testing",
            "patterns": ["@Suite", "@Test", "#expect"],
            "backend": "DummyBackend",
        },
    },
    "moreSwift/swift-bundler": {
        "name": "moreSwift/swift-bundler",
        "description": "Xcode-independent tool for creating cross-platform Swift apps from Swift packages",
        "directory_structure": {
            "Sources/swift-bundler": "CLI entry point (thin wrapper)",
            "Sources/SwiftBundler": "Core library (~150+ files)",
            "Sources/SwiftBundler/Bundler": "Platform-specific bundler implementations",
            "Sources/SwiftBundler/Commands": "ArgumentParser subcommands",
            "Sources/SwiftBundler/Configuration": "TOML-based config with overlay/flattening",
            "Sources/SwiftBundlerBuilders": "Public builder API for subprojects",
            "Sources/SwiftBundlerRuntime": "Runtime library (hot reloading)",
            "Sources/SwiftBundlerMacrosPlugin": "Swift macro plugin for config",
            "Tests": "Swift Testing with fixtures",
        },
        "key_patterns": [
            {
                "name": "Bundler protocol",
                "description": "Static methods, no instances. Each platform is a static enum. BundlerChoice maps CLI to concrete type.",
                "indicators": ["Bundler.swift", "BundlerChoice"],
            },
            {
                "name": "Configuration system",
                "description": "TOML-based, format version 3. @Configuration(overlayable:) macro generates overlay/flattening.",
                "indicators": ["Configuration/", "@Configuration"],
            },
            {
                "name": "RichError pattern",
                "description": "Every utility defines ErrorMessage enum + typealias Error = RichError<ErrorMessage>. Typed throws throughout.",
                "indicators": ["RichError", "ErrorMessage"],
            },
        ],
        "testing": {
            "framework": "Swift Testing",
            "patterns": ["@Suite(.serialized)", "@Test", "withFixture()"],
        },
    },
    "stackotter/swift-macro-toolkit": {
        "name": "stackotter/swift-macro-toolkit",
        "description": "High-level abstraction over swift-syntax for Swift macro authors",
        "directory_structure": {
            "Sources/MacroToolkit": "Core library (~60 Swift files)",
            "Sources/MacroToolkitExamplePlugin": "Example macro implementations",
            "Tests": "Integration + unit tests",
        },
        "key_patterns": [
            {
                "name": "RepresentableBySyntax",
                "description": "Base protocol. All wrappers hold _syntax: UnderlyingSyntax.",
                "indicators": ["RepresentableBySyntax.swift"],
            },
            {
                "name": "Type wrappers",
                "description": "16 kinds (SimpleType, ArrayType, FunctionType, etc.) unified under Type enum + TypeProtocol.",
                "indicators": ["TypeProtocol.swift", "Type.swift"],
            },
            {
                "name": "Literal value extraction",
                "description": "LiteralProtocol with .value property. Handles hex, octal, binary, underscores, escape sequences.",
                "indicators": ["LiteralProtocol.swift"],
            },
        ],
        "testing": {
            "framework": "XCTest + swift-macro-testing",
            "patterns": ["assertMacro", "XCTestCase"],
        },
    },
}


# ─── Analysis ────────────────────────────────────────────────────────────────

def group_files(files: list[FileInfo]) -> dict[str, ComponentGroup]:
    """Group files by component (top-level directory under Sources/Examples/Tests)."""
    groups: dict[str, ComponentGroup] = {}

    for f in files:
        parts = f.filename.split("/")
        if len(parts) >= 2 and parts[0] in ("Sources", "Examples", "Tests"):
            group_name = parts[1]
        elif len(parts) >= 2:
            group_name = parts[0]
        else:
            group_name = "root"

        if group_name not in groups:
            groups[group_name] = ComponentGroup(name=group_name)
        groups[group_name].files.append(f)

    return dict(sorted(groups.items()))


def detect_issues(files: list[FileInfo], architecture: dict[str, Any] | None) -> list[Issue]:
    """Detect concrete issues in the diff."""
    issues: list[Issue] = []

    for f in files:
        if not f.patch:
            continue

        lines = f.patch.split("\n")
        for i, line in enumerate(lines):
            # Force casts
            if "as!" in line and not line.strip().startswith("//"):
                # Check if it's guarded
                context_start = max(0, i - 5)
                context = "\n".join(lines[context_start:i])
                guarded = "as?" in context or "guard" in context or "if let" in context
                issues.append(Issue(
                    category="FORCE CAST",
                    title=f"Force cast in {f.filename}",
                    file=f.filename,
                    line=_estimate_line_number(lines, i),
                    description=line.strip(),
                    fix="Guard with as? or add precondition" if not guarded else "Guarded by preceding as? check",
                ))

            # Hash value comparison (known bug pattern)
            if "hashValue ==" in line or "== hashValue" in line:
                issues.append(Issue(
                    category="BUG",
                    title="Equality uses hashValue comparison",
                    file=f.filename,
                    line=_estimate_line_number(lines, i),
                    description="hashValue comparison causes false positives on collision",
                    fix="Compare underlying values directly",
                ))

    # Check for known duplication patterns if architecture is available
    if architecture and "known_duplication" in architecture:
        for dup in architecture["known_duplication"]:
            matching_files = [f.filename for f in files if any(
                pattern in f.filename for pattern in dup["files"]
            )]
            if len(matching_files) >= 2:
                issues.append(Issue(
                    category="DUPLICATION",
                    title=f"{dup['pattern']} pattern duplicated",
                    file=", ".join(matching_files),
                    line=None,
                    description=dup["description"],
                    fix=f"Extract to generic {dup['pattern']} in core module",
                ))

    return issues


def _estimate_line_number(lines: list[str], patch_line_index: int) -> int | None:
    """Estimate the actual file line number from a patch line index."""
    file_line = 0
    for i, line in enumerate(lines):
        if i == patch_line_index:
            return file_line if file_line > 0 else None
        if line.startswith("@@"):
            # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
            m = re.search(r"\+(\d+)", line)
            if m:
                file_line = int(m.group(1)) - 1
        elif line.startswith("-"):
            continue  # Removed line, don't increment
        elif not line.startswith("\\"):
            file_line += 1
    return None


def generate_review_order(files: list[FileInfo]) -> list[ReviewFile]:
    """Generate dependency-sorted review order."""
    review_files: list[ReviewFile] = []

    # Sort: types before consumers, protocols before implementations, core before backends
    def sort_key(f: FileInfo) -> tuple[int, str]:
        path = f.filename
        # Priority order
        if "Values/" in path or "Values\\" in path:
            return (0, path)
        if "Backend/BackendFeatures/" in path:
            return (1, path)
        if "State/" in path:
            return (2, path)
        if "Backend/" in path and "BackendFeatures" not in path:
            return (3, path)
        if "Environment/" in path:
            return (4, path)
        if "ViewGraph/" in path:
            return (5, path)
        if "Views/Modifiers/" in path:
            return (6, path)
        if "Views/" in path:
            return (7, path)
        if "Layout/" in path:
            return (8, path)
        if "AppKitBackend/" in path:
            return (9, path)
        if "GtkBackend/" in path or "Gtk/" in path:
            return (10, path)
        if "WinUIBackend/" in path:
            return (11, path)
        if "UIKitBackend/" in path:
            return (12, path)
        if "DummyBackend/" in path:
            return (13, path)
        if "Tests/" in path:
            return (14, path)
        if "Examples/" in path:
            return (15, path)
        return (16, path)

    sorted_files = sorted(files, key=sort_key)

    for f in sorted_files:
        lines_changed = f.additions + f.deletions
        # Reading time: ~30 lines/min for new code, ~50 lines/min for modifications
        if f.status == "added":
            minutes = max(0.5, lines_changed / 30)
        else:
            minutes = max(0.5, lines_changed / 50)

        # Determine what to look for based on file type
        look_for = _determine_look_for(f)

        # Determine dependencies
        depends_on = _determine_dependencies(f, sorted_files)

        review_files.append(ReviewFile(
            filename=f.filename,
            lines=lines_changed,
            look_for=look_for,
            depends_on=depends_on,
        ))

    return review_files


def _determine_look_for(f: FileInfo) -> str:
    """Determine what to focus on when reviewing a file."""
    path = f.filename

    if "BackendFeatures/" in path:
        return "Protocol methods, conformance requirements"
    if "State/" in path:
        return "Property wrapper implementation, storage pattern"
    if "Environment/" in path:
        return "Environment key definition, propagation mechanism"
    if "ViewGraph/" in path:
        return "Integration point, force casts, lifecycle hooks"
    if "Views/Modifiers/" in path:
        return "Modifier implementation, environment usage"
    if "Backend+Focus" in path or "Focus" in path.lower():
        return "Focus state management, observer pattern"
    if "Tests/" in path:
        return "Test coverage, edge cases, assertions"
    if "Examples/" in path:
        return "Usage patterns, API ergonomics"
    if f.status == "added":
        return "New type/protocol, API surface, integration points"
    return "Changes to existing behavior, regression risk"


def _determine_dependencies(f: FileInfo, all_files: list[FileInfo]) -> list[str]:
    """Determine which other files this file depends on."""
    deps: list[str] = []
    path = f.filename

    # Backend implementations depend on core types
    if any(backend in path for backend in ["AppKitBackend/", "GtkBackend/", "WinUIBackend/", "UIKitBackend/"]):
        for other in all_files:
            if "SwiftCrossUI/" in other.filename and other.filename != path:
                if any(core in other.filename for core in ["Backend/", "State/", "Values/", "Environment/"]):
                    deps.append(other.filename)

    # Modifiers depend on state/environment
    if "Views/Modifiers/" in path:
        for other in all_files:
            if "State/" in other.filename or "Environment/" in other.filename:
                deps.append(other.filename)

    # Tests depend on everything
    if "Tests/" in path:
        for other in all_files:
            if "Tests/" not in other.filename:
                deps.append(other.filename)

    return deps[:5]  # Limit to top 5 dependencies


# ─── Output Formatting ───────────────────────────────────────────────────────

def format_review_markdown(
    pr: PRInfo,
    groups: dict[str, ComponentGroup],
    issues: list[Issue],
    review_order: list[ReviewFile],
    architecture: dict[str, Any] | None,
    all_files: list[FileInfo] | None = None,
) -> str:
    """Format the review as Markdown."""
    lines: list[str] = []

    # Header
    lines.append(f"PR #{pr.number}: {pr.title}")
    lines.append(f"{pr.repo_owner}/{pr.repo_name} — {pr.author}")
    lines.append(f"+{pr.additions} / -{pr.deletions} across {pr.changed_files} files, {pr.commits} commits")
    lines.append("")

    # Component Map
    lines.append("COMPONENT MAP")
    lines.append("=" * 13)
    for name, group in groups.items():
        lines.append(f"  {name} ({group.file_count} files, +{group.total_additions} -{group.total_deletions})")
        for f in group.files:
            lines.append(f"    {f.status:10s} +{f.additions:4d} -{f.deletions:4d}  {f.filename}")
    lines.append("")

    # Architecture (if available)
    if architecture:
        lines.append("ARCHITECTURE")
        lines.append("=" * 11)

        # Show directory structure
        if "directory_structure" in architecture:
            lines.append("Structure:")
            for path, desc in architecture["directory_structure"].items():
                lines.append(f"  {path:<40s} # {desc}")
            lines.append("")

        # Show key patterns being used
        if "key_patterns" in architecture:
            used_patterns = []
            for pattern in architecture["key_patterns"]:
                for indicator in pattern.get("indicators", []):
                    if any(indicator in f.filename for f in (all_files or [])):
                        used_patterns.append(pattern)
                        break

            if used_patterns:
                lines.append("Patterns in use:")
                for pattern in used_patterns:
                    lines.append(f"  {pattern['name']}")
                    lines.append(f"    {pattern['description']}")
                lines.append("")

    # Issues
    if issues:
        lines.append("ISSUES")
        lines.append("=" * 6)
        for issue in issues:
            lines.append(f"  [{issue.category}] {issue.title}")
            if issue.line:
                lines.append(f"    File: {issue.file}:{issue.line}")
            else:
                lines.append(f"    File: {issue.file}")
            lines.append(f"    {issue.description}")
            if issue.fix:
                lines.append(f"    Fix: {issue.fix}")
            lines.append("")
    else:
        lines.append("ISSUES")
        lines.append("=" * 6)
        lines.append("  No concrete issues detected.")
        lines.append("")

    # Review Order
    lines.append("REVIEW ORDER")
    lines.append("=" * 12)
    total_minutes = 0.0
    for i, rf in enumerate(review_order, 1):
        minutes = max(0.5, rf.lines / (30 if "added" in rf.filename else 50))
        total_minutes += minutes
        lines.append(f"  {i}. {rf.filename} ({rf.lines}L, ~{minutes:.0f}min)")
        lines.append(f"     Look for: {rf.look_for}")
        if rf.depends_on:
            lines.append(f"     Depends on: {', '.join(rf.depends_on[:3])}")
        lines.append("")

    lines.append(f"TOTAL ESTIMATED REVIEW TIME: {total_minutes:.0f} minutes")

    return "\n".join(lines)


def format_review_json(
    pr: PRInfo,
    groups: dict[str, ComponentGroup],
    issues: list[Issue],
    review_order: list[ReviewFile],
) -> str:
    """Format the review as JSON."""
    data = {
        "pr": {
            "number": pr.number,
            "title": pr.title,
            "author": pr.author,
            "repo": f"{pr.repo_owner}/{pr.repo_name}",
            "additions": pr.additions,
            "deletions": pr.deletions,
            "files": pr.changed_files,
            "commits": pr.commits,
        },
        "components": {
            name: {
                "files": group.file_count,
                "additions": group.total_additions,
                "deletions": group.total_deletions,
            }
            for name, group in groups.items()
        },
        "issues": [
            {
                "category": issue.category,
                "title": issue.title,
                "file": issue.file,
                "line": issue.line,
                "description": issue.description,
                "fix": issue.fix,
            }
            for issue in issues
        ],
        "review_order": [
            {
                "file": rf.filename,
                "lines": rf.lines,
                "look_for": rf.look_for,
                "depends_on": rf.depends_on,
            }
            for rf in review_order
        ],
    }
    return json.dumps(data, indent=2)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Architecture-focused PR reviewer for large open-source pull requests."
    )
    parser.add_argument("pr_url", help="GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)")
    parser.add_argument("-o", "--output", help="Output file path (default: stdout)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Parse PR URL
    owner, repo, number = parse_pr_url(args.pr_url)

    # Fetch data
    print(f"Fetching PR #{number} from {owner}/{repo}...", file=sys.stderr)
    pr, files, review_comments, issue_comments = fetch_pr_data(owner, repo, number)

    # Load architecture knowledge
    architecture = load_repo_architecture(owner, repo)

    # Analyze
    groups = group_files(files)
    issues = detect_issues(files, architecture)
    review_order = generate_review_order(files)

    # Format output
    if args.json:
        output = format_review_json(pr, groups, issues, review_order)
    else:
        output = format_review_markdown(pr, groups, issues, review_order, architecture, files)

    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Review written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
