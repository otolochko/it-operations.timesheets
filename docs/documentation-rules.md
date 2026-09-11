# Documentation Rules

How documentation in this repository is organized, written, and kept in sync with the code.

This file is the **standard**. It does not describe features — it describes where each kind of
information belongs, what each file may and may not contain, and what has to be updated when
code changes. If a change to the codebase does not fit any rule here, extend this file in the
same PR.

---

## 1. The documentation map

Documentation is split by **audience** and by **stability**. Nothing is duplicated between
layers; each fact has exactly one home, and everything else links to it.

| Layer | File(s) | Audience | Contains |
|---|---|---|---|
| Entry point (human) | [`README.md`](../README.md) | External reader, new contributor | What the product is, feature list, quick start, configuration table, API reference, deployment pointer |
| Entry point (agent) | [`AGENTS.md`](../AGENTS.md) | Any coding agent | Nothing but a pointer table into `CLAUDE.md` / `docs/claude/` plus cross-agent warnings |
| Navigation orchestrator | [`CLAUDE.md`](../CLAUDE.md) | Claude Code | "Where to read for X" table, invariants, run commands, env var table, known limitations |
| Topic files | [`docs/claude/*.md`](claude/) | Claude Code, maintainers | Deep detail per topic — architecture, conventions, features, clients, tasks, auth, logging, frontend |
| Operations | [`docs/deployment.md`](deployment.md) | Whoever deploys | VPS/systemd/nginx steps, env setup, upgrade procedure |
| Standard | `docs/documentation-rules.md` (this file) | Anyone writing docs | The rules below |
| Work artifacts | [`.claude/`](../.claude/) | Task-scoped | Audit reports, migration status, naming standards — see §7 |

### Hard boundaries

- `CLAUDE.md` is a **router**, not a manual. It stays short. If an explanation needs more than
  a table row or a three-line invariant, it belongs in `docs/claude/`.
- `AGENTS.md` never carries content of its own beyond the pointer table and rate-limit warnings.
  It must not become a second `CLAUDE.md`.
- `README.md` is the only file that markets the product. Topic files never contain badges,
  emoji headings, or promotional phrasing.
- `docs/claude/*.md` never contains deployment/hosting instructions — those live in
  `docs/deployment.md`.

---

## 2. Topic file ownership

Each topic file owns a fixed slice of knowledge. Write the fact where it is owned, then link.

| File | Owns | Does **not** own |
|---|---|---|
| `architecture.md` | `app/` directory tree, layering rule, request lifecycle, router registration, inbound rate-limit tiers, scheduler state files | Per-feature detail, client function signatures |
| `conventions.md` | Response contract, dry-run, timeouts, pagination pattern, error handling, dependency policy, outbound rate limiting | Directory layout, per-feature gotchas |
| `features.md` | One section per user-facing feature: purpose, router, service, frontend page, schemas, gotchas | Generic conventions, client signatures |
| `api-clients.md` | The HTTP clients in `app/core/` — function signatures, base URLs, auth modes, retry behaviour | Business logic, feature endpoints |
| `async-tasks.md` | Async task execution, scheduler jobs, watermark state machine, polling, failure recovery | Feature-specific task payloads |
| `frontend.md` | `frontend/src` tree, shared components, theme tokens, nav registration, API client usage | Backend anything |

If a new topic does not fit any row above, create a new `docs/claude/<topic>.md` **and** add it
to the tables in `CLAUDE.md`, `AGENTS.md`, and §2 of this file. A topic file that is not
reachable from `CLAUDE.md` does not exist.

---

## 3. Writing style

These rules make the docs cheap to scan and cheap to keep true.

1. **Terse, declarative present tense.** "Routers validate input via Pydantic schemas." Not
   "You should probably validate…".
2. **Every file opens with an H1 title and one sentence of scope.** No preamble, no changelog,
   no "In this document we will…".
3. **Prefer tables and fenced code blocks over prose.** A signature, a directory tree, or a
   mapping is always a code block or table.
4. **Reference code by path, not by description.** Write `backend/app/core/jira_http.py`, in backticks.
   Add the symbol when it is the point: `work_date_from_jira_json(worklog_json)`.
5. **Link with relative markdown links**, with the link text in backticks — sibling topic files
   as ``[`async-tasks.md`](async-tasks.md)``, and from the repo root as
   ``[`docs/claude/features.md`](docs/claude/features.md)``. Never paste absolute local paths.
6. **Code examples are minimal and runnable in shape** — imports included, 3–12 lines, showing
   the pattern and nothing else. No invented APIs; copy the real call signature.
7. **Mark severity inline** where behaviour bites: a `**Gotchas**` bullet list, or a bold
   `**Never**` / `**Always**` sentence. No warning admonition blocks.
8. **No emoji outside `README.md`.**
9. **No dates, author names, version banners, or "last updated" lines** in any doc. Git carries
   that; hand-maintained timestamps rot.
10. **English only**, including in commit messages and code comments, regardless of the language
    the change was requested in.
11. **Horizontal rules (`---`) separate top-level sections** in long files (`features.md`,
    `architecture.md`); short files need none.
12. **Absolute claims must be verifiable.** If you write "all endpoints return X", either it is
    true of every endpoint or the sentence is rewritten with its exception named.

---

## 4. The invariants block

`CLAUDE.md` carries a numbered **Invariants** list — rules that hold across the entire codebase
with no exceptions. Rules for that list must be:

- **Universal** — true in every module, not "usually" true.
- **Checkable** — a reviewer can grep for a violation.
- **One line** — the detail lives in the topic file that owns it.

Anything conditional, per-feature, or advisory is not an invariant; it is a convention and
belongs in `conventions.md` or a feature's gotchas. Adding an invariant means every existing
violation is fixed in the same PR, or the rule is written narrower.

---

## 5. Templates

### 5.1 New feature — `docs/claude/features.md`

Append a section in the same order as its nav position, using exactly these fields. Omit a
field only when it does not exist (e.g. no backend router for a client-only page).

```markdown
---

## <Feature Name>

<One or two sentences: what it does for the user, and the shape of the operation
(sync / async task / scheduled).>

- **Router**: `backend/app/routers/<name>.py` — endpoints: `POST /<path>/`, … (note rate-limit tier if non-standard)
- **Service**: `backend/app/services/<name>_service.py` — key functions and what they validate
- **Frontend**: `frontend/src/app/<slug>/page.tsx`
- **Schemas**: `backend/app/schemas/<name>.py` — `RequestModel`, `ResponseModel`
- **Gotchas**:
  - <Non-obvious behaviour a future change would break.>
  - <API quirk, ordering constraint, or partial-failure semantics.>
```

**Gotchas are mandatory for any feature with non-obvious behaviour** — API quirks, sequential
processing, silent exclusions, cache scoping, dry-run asymmetries. This is the highest-value
content in the docs; a feature section with no gotchas asserts there are none.

### 5.2 New topic file — `docs/claude/<topic>.md`

```markdown
# <Topic Title>

<One sentence of scope: which modules/behaviour this file owns.>

## <Concept>

<Table or code block first, prose only where a table cannot carry it.>
```

Then register it in the `CLAUDE.md` "Where to read for X" table, the `AGENTS.md` quick links
table, and §2 above.

### 5.3 New env var

Add a row to the `CLAUDE.md` **Key env vars** table (`| Var | Purpose |`), and:

- add it to `.env.example` with a safe placeholder — never a real value;
- add its accessor to `backend/app/core/config.py` (all env access is centralized there);
- add it to the `README.md` configuration table if an operator must set it;
- mention it in `docs/deployment.md` if it is deployment-specific.

Never document a secret's value, and never hand-edit `.env`.

---

## 6. Update triggers — what to touch when

Documentation updates ship **in the same commit or PR as the code change**. A PR that adds a
feature and no docs is incomplete.

| Code change | Docs that must change |
|---|---|
| New feature (router + service + page) | `features.md` section; `frontend.md` tree + nav; `README.md` feature bullet; `architecture.md` only if the tree gains a `core/` module |
| New endpoint on an existing feature | That feature's `features.md` bullet; `README.md` API reference if it is publicly relevant |
| New `backend/app/core/` module | `architecture.md` directory tree (with its one-line purpose); a topic file if it introduces a pattern |
| New/changed HTTP client function | `api-clients.md` signatures |
| New env var | See §5.3 |
| New Python package import | `backend/requirements.txt` in the same change; pin per `conventions.md` |
| New shared frontend component | `frontend.md` component list |
| New nav item | `frontend/src/components/NavSidebar.tsx` (single source of truth), then `frontend.md` |
| New async task or scheduler job | `async-tasks.md`; scheduler state details in `architecture.md` |
| New rule that holds everywhere | `CLAUDE.md` invariants, per §4 |
| Changed response shape, dry-run, or pagination behaviour | `conventions.md` |
| Known bug or accepted limitation | `CLAUDE.md` **Known limitations** |
| Removed feature | Delete its `features.md` section, `README.md` bullet, nav item, and every inbound link |

**Deletion is part of the job.** A stale section is worse than a missing one: it is read as true.

---

## 7. Work artifacts vs. documentation

`.claude/` holds task-scoped material with a different lifecycle from `docs/`:

- one-off audit output and status trackers;
- external standards a feature validates against.

Rules:

- Anything that stays true after the task ends and that a future change must respect gets
  promoted into `docs/claude/` and the artifact deleted or reduced to a pointer.
- A durable standard referenced by code is cited by path from the relevant `features.md` gotcha,
  so a reader can find it.
- Never treat `.claude/` as documentation of record; it is not in the `CLAUDE.md` routing table
  and agents are not directed to read it by default.

Never hand-edit, and never document as editable: `.env`, runtime-managed logs, or state files.

---

## 8. README rules

`README.md` is the only reader-facing document and the only one with presentation polish.
It keeps this order:

1. Centered title block, tagline, badges, section jump links.
2. **Features** — grouped by domain, one bold-lead bullet per feature.
3. **Architecture** — Mermaid diagram plus a short layer description.
4. **Quick Start** — backend, frontend, env.
5. **Configuration** — env var tables.
6. **API Reference** — endpoints grouped by feature.
7. **Project Structure** — trimmed tree.
8. **Deployment** — summary plus a link to `docs/deployment.md`.

Constraints:

- Feature bullets describe **user-visible capability**, never file paths or internal function
  names. Internals belong in `docs/claude/`.
- Mermaid edge labels use the quoted form (`A -->|"label"| B`) so pipes and special characters
  in labels don't break rendering.
- Every count stated in prose must match the code at the time of writing, or be phrased without
  the number.
- The section jump links, the section list above, and the actual headings stay in sync.

---

## 9. Review checklist

Before marking documentation work complete:

- [ ] Every fact lives in the one file that owns it (§2) — no copy between layers.
- [ ] Every new topic file is reachable from `CLAUDE.md` and `AGENTS.md`.
- [ ] Every code path mentioned exists — paths, module names, and function signatures verified
      against the tree, not from memory.
- [ ] Feature sections use the §5.1 field order and carry gotchas.
- [ ] New env vars appear in `config.py`, `.env.example`, and the `CLAUDE.md` table.
- [ ] No secrets, real tokens, real account IDs, or customer data anywhere.
- [ ] No emoji, dates, or "last updated" lines outside `README.md`.
- [ ] Removed behaviour has its documentation removed, including inbound links.
- [ ] Relative links resolve from the file they are written in.
- [ ] Absolute claims ("every endpoint…", "never…") are actually true.
