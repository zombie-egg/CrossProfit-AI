import sqlite3

from scripts.migrate_sqlite import migrate


def test_legacy_database_migration_is_idempotent_and_preserves_connections(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("CREATE TABLE promotion_activities (id INTEGER PRIMARY KEY)")
        db.execute("CREATE TABLE analysis_results (id INTEGER PRIMARY KEY)")
        db.execute("CREATE TABLE platform_connections (id INTEGER PRIMARY KEY, platform TEXT, status TEXT)")
        db.execute("INSERT INTO platform_connections VALUES (1, 'taobao', 'credentials_saved')")
        db.execute("INSERT INTO platform_connections VALUES (2, 'amazon', 'credentials_saved')")
    migrate(path)
    migrate(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT status FROM platform_connections WHERE id=1").fetchone()[0] == "deprecated"
        assert db.execute("SELECT status FROM platform_connections WHERE id=2").fetchone()[0] == "credentials_saved"
        assert [row[1] for row in db.execute("PRAGMA table_info(products)")].count("category") == 1
