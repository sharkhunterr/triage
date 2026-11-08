from httpx import AsyncClient

from tests.conftest import Env

ANIMATION = {
    "name": "Dessins Animés",
    "description": "Animated films for the family",
    "root_folder_path": "/media/animation/",
    "is_fallback": False,
    "rules": [
        {"field": "genre", "operator": "is", "value": "Animation", "weight": 60, "decisive": False},
        {"field": "company", "operator": "contains", "value": "Pixar", "weight": 40, "decisive": False},
    ],
}
FILMS = {"name": "Films", "description": "Everything else", "root_folder_path": "/media/films", "is_fallback": True, "rules": []}


async def test_create_list_update_delete(owner: AsyncClient):
    created = await owner.post("/api/v1/categories", json=ANIMATION)
    assert created.status_code == 201, created.text
    category = created.json()
    assert category["key"] == "dessins-animes"
    assert category["root_folder_path"] == "/media/animation"
    assert category["version"] == 1
    assert len(category["rules"]) == 2

    await owner.post("/api/v1/categories", json=FILMS)
    listed = (await owner.get("/api/v1/categories")).json()
    assert [c["name"] for c in listed] == ["Dessins Animés", "Films"]

    updated = await owner.put(f"/api/v1/categories/{category['id']}", json={**ANIMATION, "name": "Animation"})
    assert updated.status_code == 200
    assert (updated.json()["name"], updated.json()["version"], updated.json()["key"]) == ("Animation", 2, "dessins-animes")

    assert (await owner.delete(f"/api/v1/categories/{category['id']}")).status_code == 204
    assert [c["name"] for c in (await owner.get("/api/v1/categories")).json()] == ["Films"]


async def test_root_folder_must_exist_in_radarr_and_not_be_intake(owner: AsyncClient):
    unknown = await owner.post("/api/v1/categories", json={**ANIMATION, "root_folder_path": "/nowhere"})
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "unknown_root_folder"
    intake = await owner.post("/api/v1/categories", json={**ANIMATION, "root_folder_path": "/media/intake"})
    assert intake.status_code == 422
    assert intake.json()["error"]["code"] == "intake_folder"
    unset = await owner.post("/api/v1/categories", json={**ANIMATION, "root_folder_path": None})
    assert unset.status_code == 201


async def test_rules_are_validated(owner: AsyncClient):
    bad_field = {**ANIMATION, "rules": [{"field": "mood", "operator": "is", "value": "x", "weight": 10}]}
    assert (await owner.post("/api/v1/categories", json=bad_field)).status_code == 422
    bad_weight = {**ANIMATION, "rules": [{"field": "genre", "operator": "is", "value": "x", "weight": 500}]}
    assert (await owner.post("/api/v1/categories", json=bad_weight)).status_code == 422


async def test_a_single_fallback(owner: AsyncClient):
    first = (await owner.post("/api/v1/categories", json=FILMS)).json()
    second = (await owner.post("/api/v1/categories", json={**FILMS, "name": "Other"})).json()
    listed = {c["id"]: c for c in (await owner.get("/api/v1/categories")).json()}
    assert listed[second["id"]]["is_fallback"]
    assert not listed[first["id"]]["is_fallback"]


async def test_the_last_category_cannot_be_deleted(owner: AsyncClient):
    only = (await owner.post("/api/v1/categories", json=FILMS)).json()
    response = await owner.delete(f"/api/v1/categories/{only['id']}")
    assert response.status_code == 409


async def test_reorder(owner: AsyncClient):
    a = (await owner.post("/api/v1/categories", json=ANIMATION)).json()
    b = (await owner.post("/api/v1/categories", json=FILMS)).json()
    assert (await owner.post("/api/v1/categories/reorder", json={"ids": [b["id"], a["id"]]})).status_code == 204
    assert [c["id"] for c in (await owner.get("/api/v1/categories")).json()] == [b["id"], a["id"]]


async def test_names_are_unique(owner: AsyncClient):
    await owner.post("/api/v1/categories", json=FILMS)
    duplicate = await owner.post("/api/v1/categories", json={**FILMS, "is_fallback": False})
    assert duplicate.status_code == 409


async def test_root_folders_for_the_picker(owner: AsyncClient):
    folders = (await owner.get("/api/v1/radarr/root-folders")).json()
    assert {f["path"]: f["is_intake"] for f in folders} == {
        "/media/intake": True,
        "/media/films": False,
        "/media/animation": False,
    }


async def test_categories_need_the_owner(client: AsyncClient):
    assert (await client.get("/api/v1/categories")).status_code == 401


async def test_radarr_down_does_not_block_editing_descriptions(owner: AsyncClient, env: Env):
    created = (await owner.post("/api/v1/categories", json=ANIMATION)).json()
    assert env.fakes.radarr is not None
    env.fakes.radarr.down = True
    response = await owner.put(
        f"/api/v1/categories/{created['id']}", json={**ANIMATION, "description": "Cartoons"}
    )
    assert response.status_code == 200
