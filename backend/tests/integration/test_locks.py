from httpx import AsyncClient

from tests.conftest import Env
from tests.helpers import ANIMATION_FOLDER, FILMS_FOLDER, seed_categories
from tests.integration.test_scans import doubtful, library, run_scan


async def page(owner: AsyncClient, scan: dict, tab: str = "gaps") -> dict:
    return (await owner.get(f"/api/v1/scans/{scan['id']}/page?tab={tab}")).json()


async def settle_gap(owner: AsyncClient, env: Env) -> dict:
    """Check the Films library and send its misplaced cartoon to Animation by hand."""
    scan = await run_scan(owner, env)
    (gap,) = (await page(owner, scan))["items"]
    animation = gap["target_category"]["id"]
    response = await owner.post(f"/api/v1/decisions/{gap['id']}/apply", json={"category_id": animation})
    assert response.status_code == 200, response.text
    await env.state.worker.tick()
    return gap


async def test_a_gap_settled_by_hand_locks_the_movie_and_a_check_leaves_it(owner: AsyncClient, env: Env):
    await seed_categories(env)
    library(env)
    gap = await settle_gap(owner, env)
    sheet = (await owner.get(f"/api/v1/decisions/{gap['id']}")).json()
    assert sheet["movie"]["lock"]["via"] == "check_gap"
    assert sheet["movie"]["lock"]["folder"] == ANIMATION_FOLDER

    # a check of its new library respecting locks says why it stays
    scan = await run_scan(owner, env, ANIMATION_FOLDER)
    assert scan["respect_locks"] is True
    in_place = await page(owner, scan, "in_place")
    locked = next(d for d in in_place["items"] if d["movie"]["title"] == "Spirited Away")
    assert {"code": "locked", "via": "check_gap"} in locked["reasons"]


async def test_a_doubt_left_in_place_is_locked_there(owner: AsyncClient, env: Env):
    await seed_categories(env)
    doubtful(env)
    scan = await run_scan(owner, env)
    (held,) = (await page(owner, scan, "held"))["items"]
    await owner.post(f"/api/v1/decisions/{held['id']}/apply", json={"target": "intake"})
    lock = (await owner.get(f"/api/v1/decisions/{held['id']}")).json()["movie"]["lock"]
    assert (lock["via"], lock["folder"]) == ("check_doubt", FILMS_FOLDER)
    again = await run_scan(owner, env)
    assert (await page(owner, again, "held"))["held"] == 0
    assert {"code": "locked", "via": "check_doubt"} in (await page(owner, again, "in_place"))["items"][0][
        "reasons"
    ]

    # ignoring locks, the same check finds the doubt again
    response = await owner.post(
        "/api/v1/scans", json={"root_folder_path": FILMS_FOLDER, "respect_locks": False}
    )
    await env.state.worker.tick()
    ignored = (await owner.get(f"/api/v1/scans/{response.json()['id']}")).json()
    assert (ignored["respect_locks"], ignored["waiting"]) == (False, 1)
    assert [d["movie"]["title"] for d in (await page(owner, ignored, "held"))["items"]] == ["Perfect Blue"]


async def test_proposals_applied_in_bulk_do_not_lock(owner: AsyncClient, env: Env):
    await seed_categories(env)
    library(env)
    scan = await run_scan(owner, env)
    await owner.post("/api/v1/decisions/apply-confident", json={"scan_id": scan["id"]})
    await env.state.worker.tick()
    (moved,) = (await owner.get(f"/api/v1/scans/{scan['id']}/results")).json()[1:]
    assert moved["status"] == "moved" and moved["movie"]["lock"] is None


async def test_a_choice_on_the_sheet_says_so_and_a_lock_can_be_removed(owner: AsyncClient, env: Env):
    await seed_categories(env)
    library(env)
    scan = await run_scan(owner, env)
    (gap,) = (await page(owner, scan))["items"]
    body = {"category_id": gap["target_category"]["id"], "via": "sheet"}
    await owner.post(f"/api/v1/decisions/{gap['id']}/apply", json=body)
    await env.state.worker.tick()
    sheet = (await owner.get(f"/api/v1/decisions/{gap['id']}")).json()
    assert sheet["movie"]["lock"]["via"] == "sheet"

    assert (await owner.delete(f"/api/v1/movies/{sheet['movie']['radarr_id']}/lock")).status_code == 204
    assert (await owner.get(f"/api/v1/decisions/{gap['id']}")).json()["movie"]["lock"] is None
    assert (await owner.delete("/api/v1/movies/999/lock")).status_code == 404


async def test_a_lock_holds_only_once_the_movie_is_in_its_library(owner: AsyncClient, env: Env):
    """Chosen but not moved yet: the lock shows nothing until the move is done."""
    await seed_categories(env)
    library(env)
    scan = await run_scan(owner, env)
    (gap,) = (await page(owner, scan))["items"]
    await owner.post(
        f"/api/v1/decisions/{gap['id']}/apply", json={"category_id": gap["target_category"]["id"]}
    )
    assert (await owner.get(f"/api/v1/decisions/{gap['id']}")).json()["movie"]["lock"] is None
    await env.state.worker.tick()
    assert (await owner.get(f"/api/v1/decisions/{gap['id']}")).json()["movie"]["lock"] is not None


async def test_correcting_and_undoing_from_the_sheet(owner: AsyncClient, env: Env):
    await seed_categories(env)
    library(env)
    gap = await settle_gap(owner, env)
    # undo in bulk: the choice is gone, and its lock with it
    response = await owner.post("/api/v1/decisions/revert", json={})
    assert response.json()["count"] == 1
    await env.state.worker.tick()
    assert (await owner.get(f"/api/v1/decisions/{gap['id']}")).json()["movie"]["lock"] is None
