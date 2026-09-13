# Release checklist

Use this checklist when publishing a new orchestration revision. The public
repository defines the integration contract; the component repositories own
their binaries and application behavior.

## Pin the release inputs

- Record the exact Go API/TUI and C++ engine revisions.
- Build or select immutable container images for those revisions.
- Replace development tags with release tags or digests in the Kubernetes
  manifests.
- Confirm the PostgreSQL and base-image versions.
- Document any configuration or schema migration.

## Validate locally

```bash
python -m pytest tests/test_gitroll_manifests.py -v
pre-commit run --config .pre-commit/.pre-commit-config.yaml --all-files
docker compose config
DRY_RUN=true ./k8s/deploy.sh dev
DRY_RUN=true ./k8s/deploy.sh production
```

When all component source is available, build the Compose stack and verify the
health endpoints described in [the local integration guide](QUICKSTART.md).

## Rehearse operations

- Start the stack with newly generated development credentials.
- Verify PostgreSQL, the matching engine, and the API become healthy.
- Submit a representative request through the API and inspect the resulting
  application logs.
- Stop and restart the stack without deleting the database volume.
- Exercise any required schema migration and rollback.
- Confirm the Kubernetes overlay renders the same image versions and runtime
  settings as the tested Compose stack.

## Publish

- Open a pull request containing only the intended orchestration change.
- Require the pull-request checks to pass.
- Link any measured performance statement to the retained run described in
  [Performance testing](PERFORMANCE.md).
- Tag the merged orchestration revision only after the component revisions and
  images are fixed.

This repository does not automatically publish releases or deploy an
environment.
