# `providers`

This directory is a leftover placeholder from an earlier architecture idea. It currently exists only as a historical artifact.

## Current intention

- New provider-facing code should go in `../inference/`, not here.
- This directory can either be removed later or kept temporarily as a breadcrumb during the transition.

## Adjacent directories to use instead

- `../inference/` for model-provider implementations and registries
- `../orchestration/` for model-role policy
- `../loop/` for provider-agnostic execution
