# Changelog - Kleber AI Python SDK

All notable changes to this project will be documented in this file.

## [0.2.1] - 2026-06-10
### Added
- Expanded test coverage for RAG API.
- Added `search` and `upload_document` aliases to `RAGAPI`.
### Fixed
- Fixed `RAGAPI.upload_file` to use `multipart/form-data` instead of JSON.
- Resolved deprecation warnings in `pyproject.toml`.

## [0.2.0] - 2026-06-09
### Added
- Standardized `pyproject.toml` for modern packaging.
- Consolidated `__version__` in `kleberai/__init__.py`.
- Added GitHub Action for automated testing and publication.
- Expanded API surface coverage (MCP, Deployments, System).

## [0.1.0] - 2026-05-15
### Added
- Initial release with basic Chat, Models, and Embeddings support.
