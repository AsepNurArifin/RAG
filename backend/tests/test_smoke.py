"""
Smoke Test — EnterpriseMind AI.

Memverifikasi bahwa konfigurasi dasar dan entry point aplikasi bisa dimuat
tanpa memerlukan layanan eksternal (DB, Milvus, Temporal, dsb).
"""


def test_settings_load():
    from app.core.config import settings

    assert settings.APP_ENV in ("development", "staging", "production")
    assert settings.EMBEDDING_DIMENSIONS == 1024
    assert settings.TEMPORAL_HOST != ""


def test_groq_key_required_present_in_config():
    from app.core.config import settings

    # Minimal field exist (nilai aktual bisa kosong di CI, dicek oleh config __post_init__)
    assert hasattr(settings, "GROQ_API_KEY")


def test_main_app_importable():
    from app.main import app

    assert app is not None
    paths = [r.path for r in app.routes]
    assert any("/api/auth" in p for p in paths)
    assert any("/api/query" in p for p in paths)


def test_graph_buildable_imports():
    # Memverifikasi tidak ada circular import pada pipeline graph
    import app.agents.orchestrator  # noqa: F401
    import app.agents.verifier  # noqa: F401
    import app.agents.executor  # noqa: F401
    import app.graph.build_graph  # noqa: F401
