"""Ready-made category sets. A preset only seeds categories; everything stays editable
(Constitution II). Root folders are left for the owner to pick."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PresetRule:
    field: str
    operator: str
    value: str
    weight: int
    decisive: bool = False
    excludes: bool = False


@dataclass(frozen=True)
class PresetCategory:
    names: dict[str, str]
    descriptions: dict[str, str]
    is_fallback: bool = False
    rules: tuple[PresetRule, ...] = ()


@dataclass(frozen=True)
class Preset:
    key: str
    names: dict[str, str]
    descriptions: dict[str, str]
    categories: tuple[PresetCategory, ...] = field(default_factory=tuple)


ANIMATION_STUDIOS = (
    "Pixar",
    "Walt Disney Animation Studios",
    "DreamWorks Animation",
    "Studio Ghibli",
    "Illumination",
    "Blue Sky Studios",
    "Aardman",
    "Laika",
    "Sony Pictures Animation",
    "Toei Animation",
    "Cartoon Saloon",
)

# TMDB keywords of adult content ("contains": "sex" also catches "sex party", "sexuality"…)
ADULT_KEYWORDS = ("adult animation", "sex", "erotic", "nudity", "hentai", "gore", "rape")
# Age ratings for adults: US R / NC-17 (also what Radarr reports), French -16 / -18.
ADULT_RATINGS = ("R", "NC-17", "16", "18")

MOVIES_ANIMATION = Preset(
    key="movies-animation",
    names={"en": "Movies / Animation", "fr": "Films / Dessins animés"},
    descriptions={
        "en": "Animated films go to one library, everything else to another.",
        "fr": "Les films d'animation dans une bibliothèque, tout le reste dans une autre.",
    },
    categories=(
        PresetCategory(
            names={"en": "Animation", "fr": "Dessins animés"},
            descriptions={
                "en": (
                    "Animated feature films: cartoons, anime, stop-motion and computer animation, "
                    "mostly made for children and families."
                ),
                "fr": (
                    "Films d'animation : dessins animés, anime, stop-motion et images de synthèse, "
                    "surtout destinés aux enfants et aux familles."
                ),
            },
            rules=(
                PresetRule("genre", "is", "Animation", 60),
                PresetRule("keyword", "contains", "anime", 30),
                PresetRule("keyword", "contains", "stop motion", 30),
                PresetRule("keyword", "contains", "cartoon", 30),
                PresetRule("keyword", "is", "computer animation", 30),
                *(PresetRule("company", "contains", studio, 40) for studio in ANIMATION_STUDIOS),
                # horror and thrillers are never cartoons for the family, even when animated
                PresetRule("genre", "is", "Horror", 1, excludes=True),
                PresetRule("genre", "is", "Thriller", 1, excludes=True),
                # adult content and adult age ratings: the movie goes with the films
                *(PresetRule("keyword", "contains", word, 1, excludes=True) for word in ADULT_KEYWORDS),
                *(PresetRule("certification", "is", rating, 1, excludes=True) for rating in ADULT_RATINGS),
            ),
        ),
        PresetCategory(
            names={"en": "Movies", "fr": "Films"},
            descriptions={
                "en": "Live-action films of every genre, for adults and families.",
                "fr": "Films en prises de vue réelles de tous genres, pour adultes et familles.",
            },
            is_fallback=True,
            rules=(PresetRule("keyword", "contains", "live action", 40),),
        ),
    ),
)

PRESETS = {MOVIES_ANIMATION.key: MOVIES_ANIMATION}
