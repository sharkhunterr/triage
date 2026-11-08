from httpx import AsyncClient


async def test_presets_are_listed(owner: AsyncClient):
    presets = (await owner.get("/api/v1/presets")).json()
    assert [p["key"] for p in presets] == ["movies-animation"]
    assert len(presets[0]["categories"]) == 2


async def test_apply_movies_animation_in_french(owner: AsyncClient):
    await owner.put("/api/v1/auth/me/locale", json={"locale": "fr"})
    response = await owner.post("/api/v1/presets/movies-animation/apply")
    assert response.status_code == 201
    categories = (await owner.get("/api/v1/categories")).json()
    assert [c["name"] for c in categories] == ["Dessins animés", "Films"]
    animation, films = categories
    assert animation["root_folder_path"] is None and films["root_folder_path"] is None
    assert films["is_fallback"] and not animation["is_fallback"]
    fields = {r["field"] for r in animation["rules"]}
    assert fields == {"genre", "keyword", "company", "certification"}
    assert any(r["value"] == "Studio Ghibli" for r in animation["rules"])
    assert animation["description"]


async def test_applying_twice_does_not_duplicate_names(owner: AsyncClient):
    await owner.post("/api/v1/presets/movies-animation/apply")
    await owner.post("/api/v1/presets/movies-animation/apply")
    names = [c["name"] for c in (await owner.get("/api/v1/categories")).json()]
    assert len(names) == len(set(names))


async def test_unknown_preset(owner: AsyncClient):
    assert (await owner.post("/api/v1/presets/nope/apply")).status_code == 404
