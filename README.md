# pr-reviewer

Agent skill for reviewing PRs on open-source Swift repos.

## Setup

Drop `SKILL.md` into your agent's skill directory.

```
# Hermes
cp SKILL.md ~/.hermes/skills/pr-reviewer/SKILL.md

# Cursor
cp SKILL.md .cursorrules

# Claude / other
paste SKILL.md into system prompt
```

## Usage

```
review PR https://github.com/moreSwift/swift-cross-ui/pull/414
```

## What You Get

```
PR #414: Feat/focus chain+focus state
moreSwift/swift-cross-ui — MiaKoring
+2600 / -204 across 48 files, 48 commits

COMPONENT MAP
  AppKitBackend (4 files, +301 -73)
  SwiftCrossUI (22 files, +579 -16)
  ...

ARCHITECTURE
  FocusState<Value> (property wrapper)
    Purpose: Bidirectional focus state binding
    File: Sources/SwiftCrossUI/State/FocusState.swift

ISSUES
  [BUG] Equality uses hashValue comparison
    File: Sources/SwiftCrossUI/Values/FocusData.swift:35

  [DUPLICATION] FocusStateManager copy-pasted 4 times
    Files: AppKitBackend+Focus.swift, GtkBackend+Focus.swift, ...

REVIEW ORDER
  1. FocusData.swift (43L, ~1min)
  2. FocusState.swift (115L, ~2min)
  ...

TOTAL ESTIMATED REVIEW TIME: 45 minutes
```

## Supported Repos

| Repo | Knowledge |
|------|-----------|
| moreSwift/swift-cross-ui | Full architecture |
| moreSwift/swift-bundler | Full architecture |
| stackotter/swift-macro-toolkit | Full architecture |
| Other repos | Generic review |

## Adding Repos

Add a section to SKILL.md under "Repo-Specific Patterns". Include:
- What the repo does (one line)
- Key architectural concepts (stable patterns, not file snapshots)
- Directory structure (general layout)

Don't include file contents — they go stale. The agent reads live code.

## License

MIT
