---
name: pr-reviewer
description: "Architecture-focused PR reviewer for open-source Swift repos. Clones repo fresh, reads live code, produces structured review with issues and review order. Works for any PR size."
tags: [code-review, github, swift]
triggers:
  - "review PR"
  - "PR review"
  - "review pull request"
  - "architecture review"
---

# PR Reviewer

## Output Rules

- No praise, no hedging, no restating PR description
- No explanations of basic concepts
- Concrete issues with file:line references only
- Reads like tool output

## Workflow

### 1. Fetch PR

```bash
curl -s "https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
curl -s "https://api.github.com/repos/{owner}/{repo}/pulls/{number}/files?per_page=100"
curl -s "https://api.github.com/repos/{owner}/{repo}/pulls/{number}/comments"
curl -s "https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"
```

Parse JSON with `strict=False` — patches contain control chars.

### 2. Clone Repo

```bash
git clone --depth=1 https://github.com/{owner}/{repo}.git /tmp/{repo}
```

### 3. Read Context

For modified files:
- Read the current version on the base branch
- Read its imports/dependencies
- Read the protocol it conforms to

For new files (status=added):
- They don't exist on the base branch yet — read the patch content
- Read the files they import/depend on from the base branch
- Read the protocol they conform to from the base branch

For deleted files:
- Read the current version to understand what's being removed

### 4. Fetch Existing Review Comments

Fetch inline review comments (`/pulls/{n}/comments`) and general comments
(`/issues/{n}/comments`). If the owner has already reviewed:
- List each comment with its status (RESOLVED / ADDRESSED / PENDING)
- Note which files have pending feedback
- This prevents re-flagging issues the owner already raised

### 5. Analyze

For each file determine:
- Architectural layer
- Patterns followed or broken
- Consistency with rest of codebase
- What could go wrong

### 6. Output

For large PRs (200+ lines):
```
PR #{number}: {title}
{owner}/{repo} — {author}
+{additions} / -{deletions} across {files} files, {commits} commits

COMPONENT MAP
  {group} ({files} files, +{add} -{del}) — {percent}% of changes
    {status} +{add} -{del}  {filepath}

ARCHITECTURE
  {ASCII diagram of data flow}

  NEW TYPES:
    {NewType} ({kind})
      Purpose: {one line}
      File: {path}
      Used by: {consumers}

  MODIFIED:
    {ExistingType} — {what changed}
      File: {path}

EXISTING REVIEW FEEDBACK
  {file}:{line} — {comment summary} [{STATUS}]

ISSUES
  [{CATEGORY}] {title}
    File: {path}:{line}
    {what's wrong}
    {fix}

REVIEW ORDER
  1. {file} ({lines}L, ~{minutes}min) [CORE]
     Look for: {focus}
     Depends on: {deps}

  2. {file} ({lines}L, ~{minutes}min) [PERIPHERAL]
     Look for: {focus}

TOTAL ESTIMATED REVIEW TIME: {minutes} minutes
```

For small PRs (<200 lines):
```
PR #{number}: {title}
{owner}/{repo} — {author}
+{additions} / -{deletions} across {files} files

DIFF
  {file}:{lines}
  {before → after, or new code}

EXISTING REVIEW FEEDBACK
  {file}:{line} — {comment summary} [{STATUS}]

ISSUES
  [{CATEGORY}] {title}
    File: {path}:{line}
    {what's wrong}
    {fix}

VERDICT: {APPROVE / REQUEST CHANGES / NEEDS DISCUSSION}
  {one-line summary of recommendation}
```

Mark files as [CORE] (new types, integration points, architectural changes)
or [PERIPHERAL] (view updates, example changes, minor modifications).
Put all [CORE] files first in review order.

## Issue Categories

Only flag objective problems. No style opinions.

[BUG] — Incorrect logic, type safety, race conditions
[DUPLICATION] — Same pattern 3+ times
[INCONSISTENCY] — Different approaches to same problem
[TEST GAP] — Specific untested scenarios
[API RISK] — Public API hard to change later
[FORCE CAST] — Unguarded force casts (check if guarded first)

## Issue Severity

MUST FIX — Blocks merge. Bugs, crashes, data loss.
SHOULD FIX — Should address before merge. Missing tests, hardcoded values, premature API surface.
CONSIDER — Nice to have. Naming, minor restructuring, documentation.

## Verdicts (small PRs only)

APPROVE — No issues, or issues are all CONSIDER level.
REQUEST CHANGES — Has MUST FIX or SHOULD FIX issues.
NEEDS DISCUSSION — Design decision needed, not a clear fix.

## Reading Time

New code: ~30 lines/min. Modified: ~50 lines/min. Min per file: 0.5min.

---

## Repo: moreSwift/swift-cross-ui

SwiftUI-like cross-platform UI framework. Pluggable backends per platform.

### BackendFeatures Protocol System

Monolithic AppBackend split into ~35+ small protocols under `BackendFeatures`.
Each feature (Buttons, TextFields, etc.) has create/update/setValue methods.

```
BaseAppBackend = Core & Containers & PassiveViews & Controls
FullAppBackend = BaseAppBackend & ~17 more (alerts, sheets, gestures, etc.)
```

New features add a protocol under `BackendFeatures/`. Some should be optional
(not in FullAppBackend) if not all backends can support them.

### View Lifecycle

```
children() → asWidget() → computeLayout() → commit()
```

`ViewGraphNode` manages this. `commit()` calls backend methods — force casts
happen here (`widget as! Backend2.Widget`).

### EnvironmentValues Propagation

Features flow through `EnvironmentValues` (struct with `[ObjectIdentifier: Any]`
storage). View modifiers use `EnvironmentModifier`. Flows top-down.

### State Management

Custom `Publisher`/`Cancellable` (not Combine). `@State` uses `StateImpl<Storage>`
with reference-type storage. `DynamicPropertyUpdater` discovers properties via
memory byte offset scanning.

### DummyBackend

In-memory backend for testing. Real widget class hierarchy (Button, TextField,
Container). Stores state without rendering. Tests use Swift Testing (@Suite,
@Test, #expect).

### Widget Types

AppKit=NSView, Gtk=UnsafeMutablePointer<GtkWidget>, WinUI=WinUI.FrameworkElement,
DummyBackend=custom classes. Type erasure via AnyViewGraphNode/AnyWidget.

### Directory Layout

```
Sources/
├── SwiftCrossUI/
│   ├── Backend/
│   │   ├── BackendFeatures/  # Feature protocols
│   │   ├── BaseAppBackend.swift
│   │   └── FullAppBackend.swift
│   ├── Environment/
│   ├── Layout/
│   ├── State/
│   ├── Values/
│   ├── ViewGraph/
│   └── Views/ & Views/Modifiers/
├── AppKitBackend/
├── UIKitBackend/
├── GtkBackend/
├── Gtk3Backend/
├── WinUIBackend/
├── DummyBackend/
├── Gtk/
└── GtkCodeGen/
```

### Common PR Types

- New backend feature (protocol + all backends)
- New view modifier
- Backend-specific implementation
- Layout fixes
- Platform bug fixes

---

## Repo: moreSwift/swift-bundler

Xcode-independent tool for cross-platform Swift app bundling.
macOS, Linux (AppImage/RPM), Windows (MSI), Android (APK).

### Bundler Protocol

Static methods, no instances. Each platform is a static enum:
`DarwinBundler`, `GenericLinuxBundler`, `AppImageBundler`, `RPMBundler`,
`GenericWindowsBundler`, `MSIBundler`, `APKBundler`.

`BundlerChoice` maps CLI to concrete type.

### Configuration System

TOML-based (`Bundler.toml`), format version 3.
`@Configuration(overlayable:)` macro generates overlay/flattening.
`ConfigurationFlattener` resolves platform/bundler/arch overrides.

### RichError Pattern

Every utility: `ErrorMessage` enum + `typealias Error = RichError<ErrorMessage>`.
Errors chain via `cause`. Typed throws throughout.

### Builder Protocol

`static func build(_ context: some BuilderContext) async throws -> BuilderResult`
Builders receive context via stdin JSON.

### Testing

Swift Testing `@Suite(.serialized)`. Fixture-based with `withFixture()`.
Integration tests for full create→bundle→run.

### Directory Layout

```
Sources/
├── swift-bundler/          # CLI entry
├── SwiftBundler/           # Core library
│   ├── Bundler/            # Platform bundlers
│   ├── Commands/           # CLI subcommands
│   ├── Configuration/      # TOML config system
│   └── Utility/
├── SwiftBundlerBuilders/   # Subproject builder API
├── SwiftBundlerRuntime/    # Hot reloading runtime
└── SwiftBundlerMacrosPlugin/
```

---

## Repo: stackotter/swift-macro-toolkit

High-level abstraction over swift-syntax for macro authors.

### RepresentableBySyntax

Base protocol. All wrappers hold `_syntax: UnderlyingSyntax`.
Users can always drop to raw swift-syntax API.

### Type Wrappers

16 kinds unified under `Type` enum + `TypeProtocol`:
SimpleType, ArrayType, FunctionType, OptionalType, MemberType, etc.

### Literal Extraction

`LiteralProtocol` with `.value`. Handles hex, octal, binary, underscores,
escape sequences, raw strings.

### DeclGroup Wrappers

`Struct`, `Enum`, `Class`, `Actor`, `Extension`, `Protocol` unified under
`DeclGroup` enum for exhaustive pattern matching.

### Diagnostics Builder

`DiagnosticBuilder(for:).message(...).severity(...).fixIt(...).build()`

### Testing

Integration via swift-macro-testing (Point-Free). Unit tests for wrappers.
Most common PR: swift-syntax version bumps.

### Directory Layout

```
Sources/
├── MacroToolkit/              # Core library
├── MacroToolkitExamplePlugin/ # Example macros
└── MacroToolkitExample/       # Test target
```
