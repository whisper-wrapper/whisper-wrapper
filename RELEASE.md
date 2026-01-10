# Release Process

## 1) Update changelog
- Add release notes under `## [Unreleased]` in `CHANGELOG.md`.
- Move notes to a new version header once the version is finalized.

## 2) Bump version
- Use the version script to keep `src/meta.py` and `pyproject.toml` in sync:
  - `python scripts/bump_version.py --bump patch|minor|major`
  - or `python scripts/bump_version.py X.Y.Z`
- The script creates a git tag `vX.Y.Z` by default (use `--no-tag` to skip).

## 3) Build locally (optional)
- Build amd64:
  - `ARCH=amd64 ./build_deb.sh`
- Build arm64 (requires arm64 runner or host):
  - `ARCH=arm64 ./build_deb.sh`
- Artifacts are written to `dist/*.deb`.

## 4) Push and publish
- Push commits and tags:
  - `git push`
  - `git push --tags`

## 5) CI release (GitHub Actions)
- On tag `vX.Y.Z`, the release workflow builds and uploads `.deb` artifacts.
- To enable arm64 builds, set repository variable `ENABLE_ARM64=true` and
  ensure an ARM64 runner is available (or update the workflow `runs-on`).

## Notes
- CPU-only installs use `requirements-cpu.txt`.
- GPU builds include NVIDIA CUDA wheels from `requirements.txt`.
