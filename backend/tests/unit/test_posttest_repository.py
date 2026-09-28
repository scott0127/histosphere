from concurrent.futures import ThreadPoolExecutor

from app.db.in_memory import InMemoryRepository
from app.db.supabase_repository import SupabaseRepository
from app.models.domain import SessionPosttest


def test_two_windows_cannot_silently_overwrite_a_saved_posttest():
    repository = InMemoryRepository()
    started = repository.create_posttest(SessionPosttest(session_id="session"))
    versions = [started.model_copy(update={"revision": 1, "engagement_answers": {"engagement_1": value}}) for value in (2, 5)]
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda record: repository.update_posttest(record, 0), versions))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    assert repository.get_posttest("session") == winners[0]
    resumed = repository.create_posttest(SessionPosttest(session_id="session"))
    assert resumed == winners[0]


def test_supabase_posttest_save_is_guarded_at_database_boundary(monkeypatch):
    repository = SupabaseRepository("http://example.invalid", "test-key")
    calls = []
    monkeypatch.setattr(repository, "_request", lambda *args, **kwargs: calls.append((args, kwargs)) or [])
    response = SessionPosttest(session_id="session", revision=5)
    try:
        assert repository.update_posttest(response, 4) is None
        args, kwargs = calls[0]
        assert args == ("PATCH", "session_posttests")
        assert kwargs["params"] == {"session_id": "eq.session", "revision": "eq.4", "stage": "neq.completed"}
    finally:
        repository.client.close()
