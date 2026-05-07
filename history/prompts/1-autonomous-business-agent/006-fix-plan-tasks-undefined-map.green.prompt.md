---
name: Fix PlanReview tasks undefined map error
description: Guard plan.tasks with ?? [] to prevent TypeError when field is absent from API response
type: green
stage: green
date: 2026-05-07
surface: agent
model: claude-sonnet-4-6
feature: 1-autonomous-business-agent
branch: 1-autonomous-business-agent
user: Rubaiya-Kamal
command: fix runtime TypeError in PlanReview.tsx
labels: ["bug-fix", "frontend", "plan-review", "defensive-guard"]
links:
  spec: specs/1-autonomous-business-agent/spec.md
  ticket: null
  adr: null
  pr: null
---

## Prompt

> Unhandled Runtime Error
> TypeError: Cannot read properties of undefined (reading 'map')
> Source: src\components\PlanReview.tsx (75:21) @ map
>   75 |         {plan.tasks.map((t) => (

## Response

Fixed by adding a null-coalescing guard on `plan.tasks`.

### Root cause

`plan` was non-null (passed the `if (!plan)` guard) but `plan.tasks` was `undefined`, causing `.map()` to throw.

### File changed

- `frontend/src/components/PlanReview.tsx` line 75 — changed `plan.tasks.map(...)` to `(plan.tasks ?? []).map(...)`

### Why tasks could be undefined

The backend `get_plan` always populates `tasks`, but a response shape mismatch (e.g., stale cached response, API version skew, or unexpected error path returning a partial object) can omit the field. The defensive `?? []` renders an empty list rather than crashing.

## Outcome

Runtime crash eliminated. PlanReview renders correctly whether tasks is a populated array or absent.
