# PR Reviewer

Architecture-focused PR reviewer for large open-source pull requests.

Given a PR URL, it fetches the full diff via GitHub's public API, analyzes the changes against known codebase architecture, and produces a structured review with:

- Component map (file groups + line counts)
- Architecture analysis (data flow, type relationships)
- Concrete issues (bugs, duplication, test gaps, API risks)
- Suggested review order with time estimates

No fluff. No praise. Reads like tool output.

## Install

```bash
git clone https://github.com/Jackson-G2/pr-reviewer.git
cd pr-reviewer
pip install -r requirements.txt
```

## Usage

```bash
# Review a PR
python pr_reviewer.py https://github.com/moreSwift/swift-cross-ui/pull/414

# Output to file
python pr_reviewer.py https://github.com/moreSwift/swift-cross-ui/pull/414 -o review.md

# JSON output (for piping to other tools)
python pr_reviewer.py https://github.com/moreSwift/swift-cross-ui/pull/414 --json
```

## Output Format

```
PR #414: Feat/focus chain+focus state
moreSwift/swift-cross-ui — MiaKoring
+2600 / -204 across 48 files, 48 commits

COMPONENT MAP
=============
  AppKitBackend (4 files, +301 -73)
  SwiftCrossUI (22 files, +579 -16)
  GtkBackend (2 files, +124 -5)
  ...

ARCHITECTURE
============
  FocusState<Value> (property wrapper)
    Purpose: Bidirectional focus state binding
    File: Sources/SwiftCrossUI/State/FocusState.swift
    Used by: View/focused(_:), FocusModifier

  FocusChainManager (protocol)
    Purpose: Tab-cycle management across backends
    File: Sources/SwiftCrossUI/Backend/FocusChainManager.swift
    Used by: NSCustomWindow, CustomWindow

ISSUES
======
  [BUG] FocusData equality uses hashValue comparison
    File: Sources/SwiftCrossUI/Values/FocusData.swift:35
    hashValue comparison causes false positives on collision
    Fix: Compare type and match directly

  [DUPLICATION] FocusStateManager copy-pasted 4 times
    Files: AppKitBackend+Focus.swift, GtkBackend+Focus.swift, WinUIBackend+Focus.swift, DummyBackend.swift
    Pattern: [ObjectIdentifier: Set<FocusData>], register(), handleFocusChange()
    Extract to: Generic FocusStateManager<Widget> in SwiftCrossUI core

REVIEW ORDER
============
  1. Focusability.swift (10L, ~0.5min)
     Look for: Enum cases, no concerns expected
     Depends on: nothing

  2. FocusData.swift (43L, ~1.5min)
     Look for: Equality implementation (known bug)
     Depends on: nothing

  ...

TOTAL ESTIMATED REVIEW TIME: 45 minutes
```

## Supported Repos

The tool has built-in architecture knowledge for:

| Repo | Description |
|------|-------------|
| moreSwift/swift-cross-ui | SwiftUI-like cross-platform UI framework |
| moreSwift/swift-bundler | Xcode-independent Swift app bundler |
| stackotter/swift-macro-toolkit | High-level swift-syntax abstraction for macros |
| stackotter/delta-client | Minecraft client written in Swift |

For other repos, it produces a generic review (component map + issue detection without architecture-specific analysis).

## Adding Repo Knowledge

To add support for a new repo, create a YAML file in `repos/`:

```yaml
# repos/owner_repo.yaml
name: owner/repo
description: What this repo does

architecture:
  directory_structure: |
    Sources/
    ├── Module1/           # Description
    ├── Module2/           # Description
    ...

  key_patterns:
    - name: Pattern Name
      description: What to watch for
      files: ["path/to/relevant/files"]

  common_issues:
    - category: DUPLICATION
      description: Known duplication hot spot
      files: ["path/to/duplicated/code"]

testing:
  framework: "Swift Testing"
  patterns: ["@Suite", "@Test", "#expect"]
  backend: "DummyBackend"  # if applicable
```

## How It Works

1. **Fetch**: Calls GitHub API (public, no auth) to get PR metadata, file diffs, and comments
2. **Map**: Groups files by component, counts additions/deletions per group
3. **Analyze**: Cross-references changes against repo-specific architecture knowledge
4. **Flag**: Identifies concrete issues (bugs, duplication, test gaps, API risks, force casts)
5. **Order**: Generates dependency-sorted review order with reading time estimates
6. **Output**: Produces structured, no-fluff review

## Contributing

This tool is designed for reviewing PRs on stackotter's repos, but contributions welcome:

- Add repo knowledge for other projects
- Improve issue detection heuristics
- Add new output formats
- Fix bugs

## License

MIT
