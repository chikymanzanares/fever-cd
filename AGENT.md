# Agent Usage Guide

## Objective
Define how AI agents are used in this repository while keeping engineering quality and ownership.

## Principles
- Human review is mandatory for every agent-generated change.
- No changes are accepted without relevant tests.
- Public API contract changes require explicit approval.
- Keep changes small, reversible, and easy to reason about.

## Standard Agent Workflow
1. Define scope, context, and acceptance criteria.
2. Request implementation with clear constraints.
3. Review diff for architecture and code quality.
4. Run tests and validate runtime behavior.
5. Refine and merge only when quality gates pass.

## What We Ask Agents To Do
- Implement scoped features aligned with current architecture.
- Add unit/integration tests when behavior changes; use `make test-e2e` for real-stack E2E.
- Improve logging, observability, and error handling.
- Propose clear trade-offs when multiple options exist.

## What We Avoid
- Large refactors without a plan.
- Introducing dependencies without justification.
- Bypassing repository conventions.
- Merging unverified code.

## Quality Checklist Before Accepting Changes
- [ ] Architecture remains consistent (`domain`, `application`, `infrastructure`, `api`, `worker`)
- [ ] Tests are added/updated and passing
- [ ] Error handling and logs are actionable
- [ ] Performance and reliability impact are acceptable
- [ ] No unintended API contract regressions

## Preferred Test Commands
- `make test-unit`
- `make test-integration`
- `make test-e2e` (shell E2E: full stack + sync + `/search`)
- `make test-e2e VERBOSE=1`
- `make test-all`

## Notes
- **E2E** is only `make test-e2e` (shell against the real stack).
- E2E should start from a clean database state and leave it clean after execution (`make test-e2e` does this).
- Real-stack E2E is preferred for critical flows (API + Celery + Redis + Postgres).
