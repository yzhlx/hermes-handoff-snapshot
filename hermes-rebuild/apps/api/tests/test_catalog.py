from fastapi.testclient import TestClient

from hermes_api.catalog import METHODS, SITUATIONS, get_method, get_situation, list_methods
from hermes_api.main import create_app
from hermes_api.settings import Settings


def test_catalog_has_five_actionable_methods_with_the_five_required_detail_parts():
    assert len(METHODS) == 5
    assert len({method.id for method in METHODS}) == 5
    for method in list_methods():
        assert method.problem.strip()
        assert method.situations
        assert len(method.steps) >= 4
        assert method.pitfalls
        assert method.content_version == 1


def test_all_nine_situations_map_to_existing_methods_or_free_learning():
    assert len(SITUATIONS) == 9
    ids = {method.id for method in METHODS}
    for situation in SITUATIONS:
        assert situation.reason.strip()
        assert set(situation.method_ids) <= ids
        assert situation.method_ids or situation.allow_free_learning
    assert get_situation("know-what-to-do").method_ids == ()


def test_lookup_returns_none_for_unknown_public_catalog_ids():
    assert get_method("missing") is None
    assert get_situation("missing") is None


def test_catalog_routes_serve_the_complete_public_content_and_unknown_ids_are_404(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'catalog.db'}"
    with TestClient(create_app(Settings(database_url=database_url, environment="test"))) as client:
        methods = client.get("/api/v1/learning-methods")
        situations = client.get("/api/v1/learning-situations")

        assert methods.status_code == situations.status_code == 200
        method_items = methods.json()["data"]["items"]
        situation_items = situations.json()["data"]["items"]
        assert len(method_items) == 5
        assert len(situation_items) == 9
        method_ids = {item["id"] for item in method_items}
        assert all(set(item["method_ids"]) <= method_ids for item in situation_items)
        assert client.get("/api/v1/learning-methods/unknown").status_code == 404
        assert client.get("/api/v1/learning-situations/unknown").status_code == 404
