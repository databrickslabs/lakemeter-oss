# Releasing Lakemeter OSS

Lakemeter uses Semantic Versioning (`vMAJOR.MINOR.PATCH`) for public releases.

## Version Sources

The release version is recorded in:

- `VERSION`
- `frontend/package.json`
- `frontend/package-lock.json`
- `docs-site/package.json`
- `docs-site/package-lock.json`
- `frontend/src/version.ts`
- `docs-site/docs/changelog.md`

Use the version sync helper to keep the machine-readable files aligned:

```bash
python scripts/update_version.py 0.1.0
```

The changelog should still be reviewed and edited by hand for human-readable release notes.

## Standard Release Flow

1. Update version metadata:

   ```bash
   python scripts/update_version.py <version>
   ```

2. Update `docs-site/docs/changelog.md`.

3. Run checks:

   ```bash
   python -m pytest tests/schema/test_line_item_schema_alignment.py -q
   (cd frontend && npm run build)
   (cd docs-site && npm run build)
   ```

4. Commit the release metadata:

   ```bash
   git add VERSION frontend/package.json frontend/package-lock.json docs-site/package.json docs-site/package-lock.json frontend/src/version.ts docs-site/docs/changelog.md backend/static
   git commit -m "Release v<version>"
   git push databrickslabs main
   ```

5. Create an annotated tag:

   ```bash
   git tag -a v<version> -m "Lakemeter OSS v<version>"
   git push databrickslabs v<version>
   ```

6. Create a GitHub Release:

   ```bash
   gh release create v<version> \
     --repo databrickslabs/lakemeter-oss \
     --title "Lakemeter OSS v<version>" \
     --notes-file <release-notes-file>
   ```

## Version Bump Guidelines

- Patch (`v0.1.1`): bug fixes, pricing data updates, documentation fixes.
- Minor (`v0.2.0`): new workload support, new user-facing features, installer improvements.
- Major (`v1.0.0`): stable API/installer contract or breaking changes.

