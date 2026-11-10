import httpx

from triage.adapters.wiki import WikiClient


def handler(request: httpx.Request) -> httpx.Response:
    params = dict(request.url.params)
    if request.url.host == "www.wikidata.org" and params.get("props") == "claims|sitelinks":
        claim = lambda qid: {"mainsnak": {"datavalue": {"value": {"id": qid}}}}  # noqa: E731
        entity = {
            "claims": {"P31": [claim("Q11424")], "P136": [claim("Q1"), claim("Q2")]},
            "sitelinks": {"frwiki": {"title": "A Star Is Born (film, 2018)"}, "enwiki": {"title": "x"}},
        }
        return httpx.Response(200, json={"entities": {"Q3286391": entity}})
    if request.url.host == "www.wikidata.org":
        assert params["ids"] == "Q1|Q2"  # "film" (Q11424) tells nothing: not even asked
        labels = {"Q1": "musical film", "Q2": "romantic drama"}
        return httpx.Response(
            200, json={"entities": {q: {"labels": {"en": {"value": v}}} for q, v in labels.items()}}
        )
    assert request.url.host == "fr.wikipedia.org"
    assert request.url.raw_path.endswith(b"/A_Star_Is_Born_%28film%2C_2018%29")
    assert "Triage/" in request.headers["User-Agent"]
    return httpx.Response(
        200,
        json={
            "extract": "A Star Is Born est un film musical américain réalisé par Bradley Cooper.",
            "content_urls": {"desktop": {"page": "https://fr.wikipedia.org/wiki/A_Star_Is_Born"}},
        },
    )


async def test_the_kind_of_work_and_the_article_in_the_tmdb_language():
    client = WikiClient(httpx.AsyncClient(transport=httpx.MockTransport(handler)), language="fr-FR")
    facts = await client.facts("Q3286391")
    assert facts.types == ("musical film", "romantic drama")
    assert facts.extract is not None and facts.extract.startswith("A Star Is Born est un film musical")
    assert facts.url == "https://fr.wikipedia.org/wiki/A_Star_Is_Born"
