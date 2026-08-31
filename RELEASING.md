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
- `backend/app/version.py`
- `scripts/upgrades/release.json`

Use the version sync helper to keep the machine-readable files aligned:

```bash
python scripts/update_version.py <version>
```

The changelog is the curated, human-readable release note and must still be
reviewed and edited by hand.

## Standard Release Flow

1. Update version metadata:

   ```bash
   python scripts/update_version.py <version>
   ```

2. Update `docs-site/docs/changelog.md`.

3. Build the frontend and documentation, then refresh the runtime checksum:

   ```bash
   npm run build --prefix frontend
   npm run build --prefix docs-site
   python scripts/prepare_release.py
   ```

4. Validate the release policy, payload, and tests:

   ```bash
   python scripts/validate_release.py \
     --previous-version <previous-version> \
     --base-ref v<previous-version>
   python scripts/prepare_release.py --check
   python -m pytest tests/upgrade tests/schema/test_line_item_schema_alignment.py -q
   ```

5. Commit the release metadata:

   ```bash
   git add VERSION \
     backend/app/version.py \
     backend/static \
     frontend/package.json frontend/package-lock.json frontend/src/version.ts \
     docs-site/package.json docs-site/package-lock.json \
     docs-site/docs/changelog.md \
     scripts/upgrades/release.json
   git commit -m "Release v<version>"
   git push databrickslabs main
   ```

6. Run the release-candidate workflow against `main`. Set `publish_tag=true`
   only when the workflow should create the final tag after all installation,
   upgrade, end-to-end, rollback, and re-upgrade gates pass:

   ```bash
   gh workflow run release-candidate.yml \
     --repo databrickslabs/lakemeter-oss \
     -f candidate_ref=main \
     -f previous_tag=v<previous-version> \
     -f publish_tag=true
   ```

7. The tag triggers `.github/workflows/release.yml`, which publishes the exact
   tested artifacts and generates the GitHub Release. Review the generated
   GitHub notes against the curated changelog before announcing the release.

## Version Bump Guidelines

- Patch (`v0.1.2`): application-only bug fixes, security maintenance, and
  documentation changes; no Lakebase data or schema changes.
- Minor (`v0.2.0`): releases that include declared data-only Lakebase updates
  and no schema migration.
- Major (`v1.0.0`): releases that include schema migrations or breaking
  database changes.

