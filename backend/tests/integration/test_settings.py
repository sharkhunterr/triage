import json

from httpx import AsyncClient

from tests.conftest import Env
from tests.fakes.ollama import FakeOllama


async def test_secrets_are_write_only(owner: AsyncClient):
    settings = (await owner.get("/api/v1/settings")).json()
    assert settings["radarr"]["api_key"] == {"set": True}
    assert settings["tmdb"]["api_key"] == {"set": False}

    response = await owner.patch("/api/v1/settings", json={"tmdb": {"api_key": "tmdb-secret-123"}})
    assert response.status_code == 200
    assert "tmdb-secret-123" not in response.text
    assert (await owner.get("/api/v1/settings")).json()["tmdb"]["api_key"] == {"set": True}
    assert "tmdb-secret-123" not in (await owner.get("/api/v1/settings")).text


async def test_absent_secrets_are_kept_and_empty_ones_cleared(owner: AsyncClient):
    await owner.patch("/api/v1/settings", json={"radarr": {"url": "http://radarr.lan:7878"}})
    assert (await owner.get("/api/v1/settings")).json()["radarr"]["api_key"] == {"set": True}
    await owner.patch("/api/v1/settings", json={"radarr": {"api_key": ""}})
    assert (await owner.get("/api/v1/settings")).json()["radarr"]["api_key"] == {"set": False}


async def test_intake_folders_must_exist_in_radarr(owner: AsyncClient):
    bad = await owner.patch("/api/v1/settings", json={"radarr": {"intake_root_folders": ["/nowhere"]}})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "unknown_root_folder"
    ok = await owner.patch("/api/v1/settings", json={"radarr": {"intake_root_folders": ["/media/intake/"]}})
    assert ok.json()["radarr"]["intake_root_folders"] == ["/media/intake"]


async def test_values_are_validated(owner: AsyncClient):
    response = await owner.patch("/api/v1/settings", json={"sorting": {"threshold": 3}})
    assert response.status_code == 422
    mode = await owner.patch("/api/v1/settings", json={"sorting": {"mode": "automatic"}})
    assert mode.json()["sorting"]["mode"] == "automatic"


async def test_connection_tests(owner: AsyncClient, env: Env):
    ok = (await owner.post("/api/v1/settings/test/radarr", json={})).json()
    assert ok["ok"] and ok["detail"] == "Radarr 6.2.1"
    assert env.fakes.radarr is not None
    env.fakes.radarr.down = True
    down = (await owner.post("/api/v1/settings/test/radarr", json={})).json()
    assert not down["ok"]
    env.fakes.ollama = None
    missing = (await owner.post("/api/v1/settings/test/ollama", json={})).json()
    assert missing == {"ok": False, "detail": "not_configured", "latency_ms": 0}


async def test_a_connection_test_can_use_unsaved_values(owner: AsyncClient, env: Env):
    seen = []

    def factory(settings):
        seen.append(settings.radarr.url)
        return env.fakes.factory(settings)

    env.state.adapter_factory = factory
    await owner.post("/api/v1/settings/test/radarr", json={"radarr": {"url": "http://new-radarr:7878"}})
    assert seen[-1] == "http://new-radarr:7878"
    assert (await owner.get("/api/v1/settings")).json()["radarr"]["url"] == "http://radarr.test"


async def test_ollama_models_for_the_picker(owner: AsyncClient, env: Env):
    env.fakes.ollama = FakeOllama()
    assert (await owner.get("/api/v1/ollama/models")).json() == ["mistral:7b", "qwen3:8b"]


async def test_webhook_secret_is_shown_once(owner: AsyncClient):
    response = await owner.post("/api/v1/settings/webhook-secret")
    secret = response.json()["secret"]
    assert len(secret) >= 32
    settings = await owner.get("/api/v1/settings")
    assert secret not in settings.text
    assert settings.json()["seerr"]["webhook_secret"] == {"set": True}
    assert json.loads(settings.text)["webhook_url"].endswith("/api/v1/webhooks/seerr")


async def test_the_setup_wizard_runs_once_and_can_be_reopened(owner: AsyncClient):
    assert (await owner.get("/api/v1/settings")).json()["wizard_completed"] is False
    done = await owner.patch("/api/v1/settings", json={"wizard_completed": True})
    assert done.json()["wizard_completed"] is True
    reopened = await owner.patch("/api/v1/settings", json={"wizard_completed": False})
    assert reopened.json()["wizard_completed"] is False
