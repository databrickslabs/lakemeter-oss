from upgrader.payload import build_runtime_payload, referenced_assets


def create_repository(root):
    (root / "backend/app").mkdir(parents=True)
    (root / "backend/static/assets").mkdir(parents=True)
    (root / "backend/static/pricing").mkdir(parents=True)
    (root / "backend/app/main.py").write_text("app = object()")
    (root / "backend/static/index.html").write_text(
        '<script src="/assets/index-new.js"></script>'
        '<link href="/assets/index-new.css">'
    )
    (root / "backend/static/assets/index-new.js").write_text(
        'import("./lazy-new.js")'
    )
    (root / "backend/static/assets/lazy-new.js").write_text("export default 1")
    (root / "backend/static/assets/index-new.css").write_text("body {}")
    (root / "backend/static/assets/index-old.js").write_text("stale")
    (root / "backend/static/pricing/rates.json").write_text("{}")
    (root / "backend/static/pricing/rates.csv").write_text("stale")
    (root / "app.yaml").write_text("command: []")
    (root / "requirements.txt").write_text("fastapi")


def test_runtime_payload_includes_only_reachable_frontend_assets(tmp_path):
    repository = tmp_path / "repo"
    destination = tmp_path / "runtime"
    create_repository(repository)

    assert referenced_assets(repository / "backend/static") == {
        "index-new.js",
        "index-new.css",
        "lazy-new.js",
    }
    build_runtime_payload(repository, destination)

    assert (destination / "backend/static/assets/index-new.js").is_file()
    assert (destination / "backend/static/assets/lazy-new.js").is_file()
    assert not (destination / "backend/static/assets/index-old.js").exists()
    assert (destination / "backend/static/pricing/rates.json").is_file()
    assert not (destination / "backend/static/pricing/rates.csv").exists()

