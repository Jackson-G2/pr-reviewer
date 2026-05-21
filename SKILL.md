---
name: pr-reviewer
description: "Architecture-focused PR reviewer for large open-source Swift PRs. Teaches an agent how to dynamically analyze a PR by cloning the repo, reading live code, and producing structured reviews. No static architecture snapshots — the agent reads the actual codebase every time. No fluff output."
tags: [code-review, github, architecture, open-source, swift]
triggers:
  - "review PR"
  - "PR review"
  - "review pull request"
  - "architecture review"
  - "large PR"
  - "stackotter PR"
---

# PR Reviewer Skill

## What This Is

A methodology for reviewing large PRs (300+ lines) on open-source Swift repos.
The agent clones the repo fresh, reads the actual code, and produces a structured
architecture review. No static docs that go stale.

## Output Rules (NON-NEGOTIABLE)

- NO praise, NO hedging, NO restating the PR description
- NO explanations of basic concepts
- YES: concrete issues with file:line references
- YES: architecture diagrams (ASCII)
- YES: suggested review order with time estimates
- Reads like a tool generated it, not a person

## Workflow

### Step 1: Fetch PR Data

```bash
# PR metadata
curl -s "https://api.github.com/repos/{owner}/{repo}/pulls/{number}"

# Changed files (paginate if >100)
curl -s "https://api.github.com/repos/{owner}/{repo}/pulls/{number}/files?per_page=100"

# Review comments (inline)
curl -s "https://api.github.com/repos/{owner}/{repo}/pulls/{number}/comments"

# Discussion comments
curl -s "https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"
```

Parse with `strict=False` — GitHub patches contain control chars.

### Step 2: Clone the Repo

Clone to /tmp/{repo-name}. Read the ACTUAL code, not a cached summary.

```bash
git clone --depth=1 https://github.com/{owner}/{repo}.git /tmp/{repo-name}
```

### Step 3: Explore the Structure

Don't assume — read the actual directory layout:
```bash
find Sources -type f -name "*.swift" | head -100
```

Read key files to understand current architecture:
- Package.swift (dependencies, targets)
- Main module's directory structure
- Any protocols/typealiases that define the architecture

### Step 4: Read Context for Each Changed File

For every file in the PR diff:
1. Read the full current version of the file (not just the patch)
2. Read files it imports or depends on
3. Read the protocol it conforms to
4. Understand how it fits into the larger system

This is what makes agent reviews better than regex tools —
you understand the code, not just the diff.

### Step 5: Analyze

For each changed file, determine:
- What architectural layer it belongs to
- What patterns it follows or breaks
- Whether the approach is consistent with the rest of the codebase
- What could go wrong (bugs, maintenance burden, API surface)

### Step 6: Output Format

```
PR #{number}: {title}
{owner}/{repo} — {author}
+{additions} / -{deletions} across {files} files, {commits} commits

COMPONENT MAP
=============
  {group} ({files} files, +{add} -{del})
    {status} +{add} -{del}  {filepath}
  ...

ARCHITECTURE
============
  {ASCII diagram of what this PR adds/changes}

  {NewType} ({kind})
    Purpose: {one line}
    File: {path}
    Used by: {consumers}

  ...

ISSUES
======
  [{CATEGORY}] {title}
    File: {path}:{line}
    {what's wrong}
    {suggested fix}

  ...

REVIEW ORDER
============
  1. {file} ({lines}L, ~{minutes}min)
     Look for: {what to focus on}
     Depends on: {dependencies}
  ...

TOTAL ESTIMATED REVIEW TIME: {minutes} minutes
```

## Issue Categories

Only flag objectively problematic things. No style opinions.

**[BUG]** — Incorrect logic, type safety, race conditions
**[DUPLICATION]** — Same pattern 3+ times across files
**[INCONSISTENCY]** — Different approaches to same problem
**[TEST GAP]** — Specific untested scenarios
**[API RISK]** — Public API hard to change later
**[FORCE CAST]** — Unguarded force casts (check if guarded first)

## Repo-Specific Patterns

### moreSwift/swift-cross-ui

SwiftUI-like cross-platform UI framework. Users write SwiftUI-style
views; pluggable backends render them on each platform.

**Key architectural concepts:**

1. **BackendFeatures protocol system**
   The monolithic AppBackend was split into ~35+ small protocols under
   `BackendFeatures` namespace. Each feature (Buttons, TextFields, etc.)
   has its own protocol with create/update/setValue methods.
   `BaseAppBackend` = Core & Containers & PassiveViews & Controls.
   `FullAppBackend` adds ~17 more (alerts, sheets, gestures, etc.).
   When reviewing: check if new features should be optional (not all
   backends can support everything) or required in FullAppBackend.

2. **View lifecycle: children → asWidget → computeLayout → commit**
   `ViewGraphNode` manages this cycle. `commit()` is where backend
   methods get called — force casts happen here. When reviewing new
   view modifiers or backend features, trace through this lifecycle.

3. **EnvironmentValues propagation**
   Features flow through EnvironmentValues (a struct with
   [ObjectIdentifier: Any] storage). View modifiers use
   `EnvironmentModifier` to create modified copies. Environment
   flows top-down. When reviewing: check if data should flow through
   environment vs. being stored on the widget directly.

4. **State management**
   Custom Publisher/Cancellable (not Combine). `@State` uses
   `StateImpl<Storage>` with reference-type storage that persists
   across view recomputations. `DynamicPropertyUpdater` discovers
   properties via memory byte offset scanning.

5. **DummyBackend for testing**
   In-memory backend with real widget class hierarchy (Button,
   TextField, Container, etc.). Stores state without rendering.
   Tests use Swift Testing (@Suite, @Test, #expect). When reviewing:
   check if new features have DummyBackend support and tests.

6. **Backend widget types**
   AppKit=NSView, Gtk=UnsafeMutablePointer<GtkWidget>,
   WinUI=WinUI.FrameworkElement, DummyBackend=custom class hierarchy.
   Type erasure via AnyViewGraphNode/AnyWidget prevents backend
   generics from leaking into user code.

7. **Code generation**
   gyb templates generate TupleView1..10, ViewBuilder, SceneBuilder.
   GTK bindings partially generated by GtkCodeGen.

**Directory structure (verify by reading actual code):**
```
Sources/
├── SwiftCrossUI/           # Core framework
│   ├── Backend/
│   │   ├── BackendFeatures/ # Feature protocols
│   │   ├── BaseAppBackend.swift
│   │   └── FullAppBackend.swift
│   ├── Environment/
│   ├── Layout/
│   ├── State/
│   ├── Values/
│   ├── ViewGraph/
│   └── Views/
│       └── Modifiers/
├── AppKitBackend/
├── UIKitBackend/
├── GtkBackend/
├── Gtk3Backend/
├── WinUIBackend/
├── DummyBackend/
├── Gtk/                    # GTK4 Swift bindings
└── GtkCodeGen/
```

### moreSwift/swift-bundler

Xcode-independent tool for creating cross-platform Swift apps from
Swift packages. Supports macOS, Linux, Windows, Android.

**Key architectural concepts:**

1. **Bundler protocol (static methods, no instances)**
   Each platform is a static enum (DarwinBundler, GenericLinuxBundler,
   etc.). BundlerChoice maps CLI selection to concrete type.
   When reviewing: check if new bundlers follow the static enum pattern.

2. **Configuration system (TOML with overlays)**
   Format version 3. @Configuration(overlayable:) macro generates
   overlay/flattening boilerplate. ConfigurationFlattener resolves
   platform/bundler/arch-specific overrides. When reviewing: check
   if new config fields use the macro system correctly.

3. **RichError pattern**
   Every utility defines ErrorMessage enum + typealias Error =
   RichError<ErrorMessage>. Errors form chains via cause. Typed
   throws throughout. When reviewing: check error handling follows
   this pattern.

4. **Builder protocol for subprojects**
   static func build(_ context: some BuilderContext) async throws
   Builders receive context via stdin JSON.

5. **Testing**
   Swift Testing (@Suite(.serialized)), fixture-based with
   withFixture() helper. Integration tests for full create→bundle→run.

### stackotter/swift-macro-toolkit

High-level abstraction over swift-syntax for Swift macro authors.

**Key architectural concepts:**

1. **RepresentableBySyntax base protocol**
   All wrappers hold _syntax: UnderlyingSyntax. Users can always
   drop down to raw swift-syntax API.

2. **Type wrappers (16 kinds)**
   Unified under Type enum + TypeProtocol. Covers SimpleType,
   ArrayType, FunctionType, OptionalType, etc.

3. **Literal value extraction**
   LiteralProtocol with .value property. Handles hex, octal, binary,
   underscores, escape sequences, raw strings.

4. **DeclGroup wrappers**
   Struct, Enum, Class, Actor, Extension, Protocol unified under
   DeclGroup enum for exhaustive pattern matching.

5. **Diagnostics builder**
   Fluent DiagnosticBuilder(for:).message(...).severity(...).build()

6. **Testing**
   Integration via swift-macro-testing (Point-Free), unit tests
   for wrappers. swift-syntax version bumps are most common PR type.

## Reading Time Estimates

- New code: ~30 lines/minute
- Modified code: ~50 lines/minute
- Minimum per file: 0.5 minutes
