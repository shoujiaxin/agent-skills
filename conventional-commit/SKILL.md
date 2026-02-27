---
name: conventional-commit
description: Create git commits with messages that strictly follow the Conventional Commits specification. Use this skill whenever the user asks to commit changes, make a commit, save progress to git, or says things like "commit this", "commit my changes", "git commit", "/commit", or any variation of creating a git commit. Also use when the user asks to write a commit message or format a commit message. This skill ensures commit messages are well-structured, concise, and follow project conventions.
---

# Conventional Commit

Create git commits with messages that follow the Conventional Commits specification (v1.0.0), enforcing a 50-character title limit and consistent casing.

## Commit message format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

The **title** (first line) is `<type>[optional scope]: <description>` and must be at most 50 characters total. This limit exists because git tooling (GitHub, `git log --oneline`, etc.) truncates longer titles, making them harder to scan.

## Step 1: Gather context

Before generating the commit message, collect two pieces of information in parallel:

1. **Staged changes**: Run `git diff --staged` (and `git diff --staged --stat` for a file-level overview). If nothing is staged, check `git status` and inform the user that there are no staged changes — do not commit unstaged work without the user's explicit direction.

2. **Recent commit history**: Run `git log --oneline --no-decorate -20` to see the project's existing commit style. Pay attention to:
   - Whether descriptions start with a capital letter or lowercase
   - Whether scopes are used and what they look like
   - The typical level of detail

## Step 2: Determine the commit type

Choose the type that best describes the **primary intent** of the change. When a commit touches multiple concerns, pick the dominant one — a commit should ideally do one thing.

| Type       | When to use                                                |
| ---------- | ---------------------------------------------------------- |
| `feat`     | A new feature or capability for the user                   |
| `fix`      | A bug fix                                                  |
| `docs`     | Documentation-only changes                                 |
| `style`    | Formatting, whitespace, semicolons — no logic change       |
| `refactor` | Code restructuring that doesn't fix a bug or add a feature |
| `perf`     | A performance improvement                                  |
| `test`     | Adding or correcting tests                                 |
| `build`    | Changes to build system or external dependencies           |
| `ci`       | CI configuration and scripts                               |
| `chore`    | Maintenance tasks that don't fit the above                 |

## Step 3: Decide on scope (optional)

A scope is a noun in parentheses that narrows what part of the codebase the commit affects. Use a scope when the project already uses them consistently or when it genuinely helps disambiguate. Don't force a scope if the change is broad or the project doesn't use them.

**Example:** `fix(parser): handle escaped quotes` — the scope `parser` tells you which module is affected.

## Step 4: Write the description

The description is the short summary after the colon and space. It should:

- Use the **imperative mood** ("add", "fix", "remove" — not "added", "fixes", "removed"), as if completing the sentence "This commit will ..."
- Be specific enough to distinguish this commit from similar ones
- Not end with a period

### Case style

Check the recent commit history from Step 1. If the project has a clear pattern (e.g., all descriptions start lowercase, or all start capitalized), follow that pattern. If there is no clear pattern or no history, **default to lowercase**.

### 50-character title limit

The entire title — type, scope, colon, space, and description — must fit within 50 characters. This is a hard limit. If the message is too long:

1. Shorten the description — cut filler words, use more concise phrasing
2. Remove the scope if it's not essential
3. Move details to the body instead of cramming them into the title

**Examples of good titles:**

```
feat(auth): add JWT token refresh        (36 chars)
fix: resolve null pointer in parser      (39 chars)
docs: update API reference for v2        (37 chars)
refactor: extract validation helpers     (40 chars)
feat!: drop support for Node 14          (35 chars)
```

**Examples of titles that are too long:**

```
feat(authentication): add JWT token refresh mechanism    (55 chars — trim)
fix(database): resolve connection pool timeout issues    (55 chars — trim)
```

## Step 5: Add body and footers if needed

For simple changes, the title alone is enough. Add a body when:

- The **why** isn't obvious from the title
- There are important details about the approach
- The change has side effects worth noting

Separate the body from the title with a blank line. Wrap lines at 72 characters.

### Breaking changes

If the commit introduces a breaking change, signal it in **both** places:

1. Add `!` before the colon: `feat!: remove deprecated API`
2. Add a `BREAKING CHANGE:` footer explaining what breaks and how to migrate

### Other footers

Use git-trailer format for footers like `Refs:`, `Reviewed-by:`, `Co-authored-by:`, etc. Separate each footer token with `:<space>` or `<space>#`.

## Step 6: Create the commit

Once the message is ready, create the commit using `git commit`. Pass the message via a heredoc to preserve formatting:

```bash
git commit -m "$(cat <<'EOF'
<title line>

<optional body>

<optional footers>
EOF
)"
```

After the commit succeeds, run `git log --oneline -1` to confirm and show the user the result.

## Quick reference

```
<type>       := feat | fix | docs | style | refactor | perf | test | build | ci | chore
<scope>      := ( <noun> )                          [optional]
<breaking>   := !                                   [optional, before colon]
<title>      := <type>[<scope>][<breaking>]: <desc>  [max 50 chars]
<body>       := free-form, wrapped at 72 chars       [optional]
<footer>     := <token>: <value>                     [optional, one or more]
```
