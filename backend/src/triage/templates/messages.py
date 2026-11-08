"""Server-side texts (email and link pages), in the owner's language. The web interface has its
own translations; these cover what is rendered without it."""

from typing import Any

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "email.subject": "Triage: {count} movie(s) to review",
        "email.intro": "Triage could not decide where these movies go. Choose a library for each one:",
        "email.leave": "Leave in the intake folder",
        "email.moveTo": "Move to {category}",
        "email.openApp": "Open the review queue",
        "email.footer": "Each link works once and expires on {date}.",
        "page.confirmTitle": "Move “{title}”?",
        "page.confirmMove": "Triage will move this movie to {category}.",
        "page.confirmLeave": "Triage will leave this movie in the intake folder and not propose it again.",
        "page.confirm": "Confirm",
        "page.doneTitle": "Done",
        "page.doneMove": "“{title}” is being moved to {category}.",
        "page.doneLeave": "“{title}” stays in the intake folder.",
        "page.goneTitle": "This link no longer works",
        "page.goneText": "It was already used, it expired, or the movie was decided in the app.",
        "page.badTitle": "Unknown choice",
        "page.badText": "This category no longer exists or has no library.",
        "page.openApp": "Open the review queue",
        "reason.no_categories": "No category is defined yet.",
        "reason.no_metadata": "No genre, keyword or company is known for this movie.",
        "reason.no_signal": "No category's rules matched.",
        "reason.low_confidence": "Confidence {confidence}, below the {threshold} threshold.",
        "reason.close_second": "Two categories are too close.",
        "reason.decisive_conflict": "Several decisive rules disagree.",
        "reason.ai_unavailable": "The AI could not answer.",
        "reason.ai_unsure": "The AI was not sure either.",
        "reason.category_without_folder": "The chosen category has no library yet.",
        "reason.corrected_before": "You corrected this movie before.",
    },
    "fr": {
        "email.subject": "Triage : {count} film(s) à trancher",
        "email.intro": "Triage n'a pas su où ranger ces films. Choisissez une bibliothèque pour chacun :",
        "email.leave": "Laisser dans le dossier d'entrée",
        "email.moveTo": "Déplacer vers {category}",
        "email.openApp": "Ouvrir la liste à trancher",
        "email.footer": "Chaque lien ne sert qu'une fois et expire le {date}.",
        "page.confirmTitle": "Déplacer « {title} » ?",
        "page.confirmMove": "Triage va déplacer ce film vers {category}.",
        "page.confirmLeave": "Triage va laisser ce film dans le dossier d'entrée et ne plus le proposer.",
        "page.confirm": "Confirmer",
        "page.doneTitle": "C'est fait",
        "page.doneMove": "« {title} » est en cours de déplacement vers {category}.",
        "page.doneLeave": "« {title} » reste dans le dossier d'entrée.",
        "page.goneTitle": "Ce lien ne fonctionne plus",
        "page.goneText": "Il a déjà servi, il a expiré, ou le film a été tranché dans l'application.",
        "page.badTitle": "Choix inconnu",
        "page.badText": "Cette catégorie n'existe plus ou n'a pas de bibliothèque.",
        "page.openApp": "Ouvrir la liste à trancher",
        "reason.no_categories": "Aucune catégorie n'est encore définie.",
        "reason.no_metadata": "Aucun genre, mot-clé ou société n'est connu pour ce film.",
        "reason.no_signal": "Les règles d'aucune catégorie ne correspondent.",
        "reason.low_confidence": "Confiance {confidence}, sous le seuil de {threshold}.",
        "reason.close_second": "Deux catégories sont trop proches.",
        "reason.decisive_conflict": "Plusieurs règles décisives se contredisent.",
        "reason.ai_unavailable": "L'IA n'a pas pu répondre.",
        "reason.ai_unsure": "L'IA n'était pas sûre non plus.",
        "reason.category_without_folder": "La catégorie choisie n'a pas encore de bibliothèque.",
        "reason.corrected_before": "Vous avez déjà corrigé ce film.",
    },
}


def text(locale: str, key: str, **values: Any) -> str:
    template = MESSAGES.get(locale, MESSAGES["en"]).get(key) or MESSAGES["en"].get(key, key)
    return template.format(**values)


def reason_text(locale: str, reason: dict[str, Any]) -> str:
    values = {
        k: f"{round(float(v) * 100)}%" if k in ("confidence", "threshold") else v
        for k, v in reason.items()
        if k != "code"
    }
    try:
        return text(locale, f"reason.{reason.get('code')}", **values)
    except (KeyError, ValueError):
        return str(reason.get("code"))
