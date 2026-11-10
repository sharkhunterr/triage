from httpx import AsyncClient


async def test_presets_are_listed(owner: AsyncClient):
    presets = (await owner.get("/api/v1/presets")).json()
    assert [p["key"] for p in presets] == ["movies-animation", "shows", "concerts"]
    assert len(presets[0]["categories"]) == 2
    assert [p["addon"] for p in presets] == [False, True, True]


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
    assert fields == {"genre", "keyword", "company", "certification", "wikidata"}
    assert any(r["value"] == "Studio Ghibli" for r in animation["rules"])
    assert animation["description"]


async def test_applying_twice_does_not_duplicate_names(owner: AsyncClient):
    await owner.post("/api/v1/presets/movies-animation/apply")
    await owner.post("/api/v1/presets/movies-animation/apply")
    names = [c["name"] for c in (await owner.get("/api/v1/categories")).json()]
    assert len(names) == len(set(names))


async def test_unknown_preset(owner: AsyncClient):
    assert (await owner.post("/api/v1/presets/nope/apply")).status_code == 404


async def test_shows_and_concerts_add_one_category_each(owner: AsyncClient):
    """Shows and Concerts each add one category beside Movies / Animation — never a second fallback."""
    await owner.put("/api/v1/auth/me/locale", json={"locale": "fr"})
    await owner.post("/api/v1/presets/movies-animation/apply")
    for key in ("shows", "concerts"):
        assert (await owner.post(f"/api/v1/presets/{key}/apply")).status_code == 201
    categories = (await owner.get("/api/v1/categories")).json()
    assert [c["name"] for c in categories] == ["Dessins animés", "Films", "Spectacles", "Concerts"]
    assert [c["name"] for c in categories if c["is_fallback"]] == ["Films"]
    shows = next(c for c in categories if c["name"] == "Spectacles")
    assert any(r["value"] == "comedy special" and r["decisive"] for r in shows["rules"])


async def test_complete_adds_the_rules_a_preset_gained_and_nothing_else(owner: AsyncClient):
    """A category made from an older preset gets the rules added since; the owner's own changes stay."""
    await owner.put("/api/v1/auth/me/locale", json={"locale": "fr"})
    await owner.post("/api/v1/presets/shows/apply")
    (shows,) = (await owner.get("/api/v1/categories")).json()
    kept = [r for r in shows["rules"] if "woman" not in r["value"]]
    body = {**shows, "description": "Mes spectacles", "rules": kept}
    assert (await owner.put(f"/api/v1/categories/{shows['id']}", json=body)).status_code == 200
    presets = {p["key"]: p for p in (await owner.get("/api/v1/presets")).json()}
    assert presets["shows"]["missing_rules"] == 2
    assert presets["concerts"]["missing_rules"] == 0  # not made yet: nothing to complete

    assert (await owner.post("/api/v1/presets/shows/complete")).json() == {"added": 2}
    (after,) = (await owner.get("/api/v1/categories")).json()
    assert after["description"] == "Mes spectacles"
    assert any(r["value"] == "one-woman show" and r["decisive"] for r in after["rules"])
    assert len(after["rules"]) == len(shows["rules"])
    assert (await owner.post("/api/v1/presets/shows/complete")).json() == {"added": 0}
