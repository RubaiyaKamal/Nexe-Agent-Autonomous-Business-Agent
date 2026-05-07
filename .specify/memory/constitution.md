# Project Constitution: Nexe Agent — Autonomous Business Agent

**Created**: 2026-05-04  
**Owner**: Rubaiya-Kamal

---

## Purpose

Build an AI-powered Autonomous Business Agent that accepts high-level business goals in natural language, decomposes them into ordered task plans, reasons through multi-step execution, and produces immutable, auditable execution logs.

## Core Principles

1. **Transparency First** — Every agent decision must be logged with reasoning. No silent operations.
2. **Operator Control** — Humans remain in the loop. Execution requires confirmation unless explicitly opted out.
3. **Smallest Viable Change** — Each implementation step should be the minimum needed to move forward.
4. **Auditability** — Logs are immutable. Once written, a log entry cannot be altered or deleted.
5. **Fail Loud** — Failures are surfaced immediately. No silent swallowing of errors.

## Code Quality

- All requirements must have testable acceptance criteria before implementation begins.
- No hardcoded secrets or tokens — use environment variables.
- Prefer composable, single-responsibility units over monolithic implementations.

## Testing Standards

- Every functional requirement must have at least one corresponding test.
- Execution log integrity must be covered by automated audit tests.

## Security

- Destructive operations always require an explicit operator confirmation gate.
- All inputs from external sources must be validated before processing.
- Authentication is required for all operator-facing operations.

## Architecture

- Spec → Plan → Tasks → Implementation → Review order must be followed.
- ADRs required for: data model decisions, AI model integration choices, auth strategy, log storage strategy.
