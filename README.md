# PR Reviewer Skill

A methodology for reviewing large PRs (300+ lines) on open-source Swift repos.

This is not a script. It's a skill you load into an AI agent (Hermes, Cursor, Claude, etc.) that teaches it how to review PRs by reading the actual code — not pattern-matching regex.

## What It Does

Given a PR URL, the agent will:

1. Fetch the PR diff via GitHub's public API
2. Clone the repo and read the actual current source files
3. Understand context by reading neighboring code and dependencies
4. Produce a structured architecture review with:
   - Component map (file groups + line counts)
   - Architecture analysis (what the PR adds/changes)
   - Concrete issues (bugs, duplication, test gaps — with file:line)
   - Suggested review order with time estimates

No fluff. No praise. Reads like tool output.

## How to Use

### Option 1: Load as an Agent Skill

Copy `SKILL.md` into your agent's skill directory:

```bash
# Hermes
cp SKILL.md ~/.hermes/skills/pr-reviewer/SKILL.md

# Cursor (as a rule)
cp SKILL.md .cursorrules

# Claude (paste into system prompt)
cat SKILL.md
```

Then ask your agent: "Review PR https://github.com/moreSwift/swift-cross-ui/pull/414"

### Option 2: Use as a Prompt Template

Copy the contents of `SKILL.md` and paste it into any LLM chat with the PR URL.

### Option 3: GitHub Action (Coming Soon)

A GitHub Action that automatically reviews PRs when they're opened.

## Supported Repos

Built-in knowledge for:

| Repo | Description |
|------|-------------|
| moreSwift/swift-cross-ui | SwiftUI-like cross-platform UI framework |
| moreSwift/swift-bundler | Xcode-independent Swift app bundler |
| stackotter/swift-macro-toolkit | High-level swift-syntax abstraction for macros |

For other repos, the agent produces a generic review (component map + issue detection) without repo-specific architecture analysis.

## How It Works

The skill teaches the agent a methodology, not a database:

1. **Clone fresh every time** — no stale cached knowledge
2. **Read the actual code** — understand context, not just diffs
3. **Follow architectural patterns** — know how each repo is structured
4. **Flag concrete issues** — bugs, duplication, test gaps, API risks
5. **Output structured reviews** — no fluff, no opinions

The agent always works with live code. Architecture knowledge is about stable patterns (how BackendFeatures works, how the View lifecycle flows), not snapshots of specific files.

## Adding New Repos

To add support for a new repo, add a section to SKILL.md under "Repo-Specific Patterns" with:

1. **What the repo does** (one paragraph)
2. **Key architectural concepts** (the stable patterns that don't change often)
3. **Directory structure** (the general layout)
4. **Common PR types** (what kinds of changes come in)

Don't include specific file contents — those go stale. Include patterns and concepts.

## License

MIT
