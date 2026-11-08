from httpx import AsyncClient

from tests.conftest import PASSWORD, Env


async def test_setup_creates_the_owner_and_signs_in(client: AsyncClient):
    assert (await client.get("/api/v1/setup/status")).json() == {"needs_setup": True}
    response = await client.post(
        "/api/v1/setup", json={"username": "owner", "password": PASSWORD, "locale": "fr"}
    )
    assert response.status_code == 204
    assert "httponly" in response.headers["set-cookie"].lower()
    assert (await client.get("/api/v1/setup/status")).json() == {"needs_setup": False}
    assert (await client.get("/api/v1/auth/me")).json() == {"username": "owner", "locale": "fr"}
    # TMDB follows the owner's language from the start
    assert (await client.get("/api/v1/settings")).json()["tmdb"]["language"] == "fr-FR"


async def test_setup_is_refused_once_an_owner_exists(owner: AsyncClient):
    response = await owner.post("/api/v1/setup", json={"username": "intruder", "password": PASSWORD})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_set_up"


async def test_protected_routes_need_a_session(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_login_logout(owner: AsyncClient):
    assert (await owner.post("/api/v1/auth/logout")).status_code == 204
    owner.cookies.clear()
    assert (await owner.get("/api/v1/auth/me")).status_code == 401
    bad = await owner.post("/api/v1/auth/login", json={"username": "owner", "password": "wrong-password"})
    assert bad.status_code == 401
    good = await owner.post("/api/v1/auth/login", json={"username": "owner", "password": PASSWORD})
    assert good.status_code == 204
    assert (await owner.get("/api/v1/auth/me")).status_code == 200


async def test_writes_need_the_csrf_header(owner: AsyncClient):
    response = await owner.put("/api/v1/auth/me/locale", json={"locale": "fr"}, headers={"X-Triage-CSRF": ""})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf"


async def test_login_is_throttled(owner: AsyncClient):
    owner.cookies.clear()
    for _ in range(5):
        await owner.post("/api/v1/auth/login", json={"username": "owner", "password": "wrong-password"})
    response = await owner.post("/api/v1/auth/login", json={"username": "owner", "password": PASSWORD})
    assert response.status_code == 429


async def test_sessions_expire_after_thirty_idle_days(owner: AsyncClient, env: Env):
    env.clock.advance(days=31)
    assert (await owner.get("/api/v1/auth/me")).status_code == 401


async def test_healthz_is_public(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
