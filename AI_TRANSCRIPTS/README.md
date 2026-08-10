# AI transcripts

The brief asks for transcripts where conversational AI was used, and notes that for a
coding agent "a quick mention in your commit messages or PR description of how you used
it is great too".

Both are here:

- **[development-log.md](development-log.md)** — a session-by-session account of how the
  work was actually driven: what I asked for, what the agent produced, what I rejected,
  and the points where it changed direction.
- **The git history**, which is the more reliable record. Every commit message states
  what the agent contributed and, where relevant, what it got wrong. `git log` reads as
  the narrative of the build.

## Tooling

Claude Code (Opus 5), VS Code extension, 2026-08-10. Roughly three hours.

## A note on what is not here

Two things are deliberately omitted.

**Private preparation.** Part of the session was spent researching the role and company.
That is interview preparation rather than work on the exercise, and it is not in this
public repository.

**The raw session log.** Claude Code keeps a machine-readable log of each session. I
wrote an exporter for it, but the harness blocks programmatic reads of its own session
files, so the log here is written rather than dumped. It can be exported on request.
