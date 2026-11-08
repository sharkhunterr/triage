from httpx import AsyncClient

from tests.conftest import Env

APPROVED = {"notification_type": "MEDIA_AUTO_APPROVED", "media": {"media_type": "movie", "tmdbId": "862"}}


async def _secret(owner: AsyncClient) -> str:
    return (await owner.post("/api/v1/settings/webhook-secret")).json()["secret"]


async def test_an_approved_movie_wakes_the_worker(owner: AsyncClient, env: Env):
    secret = await _secret(owner)
    env.state.worker.next_poll_at = None
    owner.cookies.clear()
    response = await owner.post("/api/v1/webhooks/seerr", json=APPROVED, headers={"Authorization": secret})
    assert response.status_code == 202
    assert env.state.worker.next_poll_at is not None
    manual = {**APPROVED, "notification_type": "MEDIA_APPROVED"}
    assert (
        await owner.post("/api/v1/webhooks/seerr", json=manual, headers={"Authorization": secret})
    ).status_code == 202


async def test_the_secret_is_required(owner: AsyncClient, env: Env):
    secret = await _secret(owner)
    owner.cookies.clear()
    assert (await owner.post("/api/v1/webhooks/seerr", json=APPROVED)).status_code == 401
    wrong = await owner.post("/api/v1/webhooks/seerr", json=APPROVED, headers={"Authorization": secret + "x"})
    assert wrong.status_code == 401


async def test_without_a_configured_secret_nothing_is_accepted(client: AsyncClient):
    response = await client.post("/api/v1/webhooks/seerr", json=APPROVED, headers={"Authorization": ""})
    assert response.status_code == 401


async def test_other_notifications_are_ignored(owner: AsyncClient, env: Env):
    secret = await _secret(owner)
    env.state.worker.next_poll_at = None
    headers = {"Authorization": secret}
    test = await owner.post(
        "/api/v1/webhooks/seerr", json={"notification_type": "TEST_NOTIFICATION"}, headers=headers
    )
    assert test.status_code == 204
    tv = {"notification_type": "MEDIA_APPROVED", "media": {"media_type": "tv"}}
    assert (await owner.post("/api/v1/webhooks/seerr", json=tv, headers=headers)).status_code == 204
    assert env.state.worker.next_poll_at is None
