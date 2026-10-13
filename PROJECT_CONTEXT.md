# Project context

Source of truth: this Git repository, published as `mastarai2024-del/feishu-bitable-browser-skill`.

The installable unit is `skills/feishu-bitable-browser/`. It contains the entry point, agent metadata, conditional references, a private runtime bootstrap, and bounded browser/matching helpers. The root installer copies only that unit.

The default runtime belongs outside Git in the current user's private cache. `FEISHU_SKILL_RUNTIME` overrides that location for isolated checks. Authentication profiles and business data are not project assets.

Development: create a task branch and worktree under ignored `.worktrees/`; keep ongoing local state in ignored `PRIVATE_STATUS.md`. Run `python -m unittest discover -s tests -v` using the pinned private runtime. All checked-in fixtures are synthetic. Runtime installation and local fixture tests are not real Feishu end-to-end acceptance.

Publication: review the exact staged file set for credentials/company data, run the focused checks, commit the accepted task version, integrate into a clean main, then push only when publication was explicitly requested. Verify the public tree and a fresh clone. Retain a recoverable local source until that succeeds.
