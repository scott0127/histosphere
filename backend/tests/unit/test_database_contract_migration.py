from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "supabase" / "migrations" / "202609040001_database_contract_alignment.sql"


def test_database_contract_migration_is_additive_and_enforces_runtime_assumptions():
    sql = MIGRATION.read_text(encoding="utf-8")
    normalized = " ".join(sql.lower().split())

    assert "delete from" not in normalized
    assert "on delete restrict" in normalized
    assert "create unique index if not exists uq_task_attempts_session" in normalized
    assert "create unique index if not exists uq_conversations_session" in normalized
    assert "experiment_sessions_participant_id_fkey" in normalized

    expected_rows = (
        ("no_ebl_no_roleplay", "false", "false", "generic", "standard"),
        ("ebl_no_roleplay", "true", "false", "generic", "scaffold"),
        ("no_ebl_roleplay", "false", "true", "persona", "standard"),
        ("ebl_roleplay", "true", "true", "persona", "scaffold"),
    )
    for key, ebl, roleplay, agent, policy in expected_rows:
        expected_mapping = (
            f"condition_key = '{key}' "
            f"and ebl_enabled = {ebl} "
            f"and roleplay_enabled = {roleplay} "
            f"and agent_mode = '{agent}' "
            f"and response_policy = '{policy}'"
        )
        assert expected_mapping in normalized
