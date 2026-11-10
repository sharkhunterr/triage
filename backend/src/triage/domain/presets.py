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
    addon: bool = False  # one more category beside the ones already there (no fallback of its own)


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
                PresetRule("keyword", "contains", "3d animation", 30),
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
            rules=(
                PresetRule("keyword", "contains", "live action", 40),
                # The Lion King (2019), Aladdin (2019)…: TMDB still lists "Animation" as a genre
                PresetRule("keyword", "is", "live action remake", 100, decisive=True),
            ),
        ),
    ),
)

# Shows and concerts: TMDB tags them by keywords (they share no genre of their own). A strong keyword is
# enough to move the movie; a weaker one (an opera, a ballet: often in films too) leaves it to review.
# A story genre rules them out: a drama about a singer has "concert" among its keywords, not a concert.
SHOWS = Preset(
    key="shows",
    names={"en": "Shows", "fr": "Spectacles"},
    descriptions={
        "en": "Adds a Shows category: stand-up, one-man shows, filmed theatre, opera, ballet and circus.",
        "fr": (
            "Ajoute une catégorie Spectacles : stand-up, one-man-shows, théâtre filmé, opéra, ballet "
            "et cirque."
        ),
    },
    addon=True,
    categories=(
        PresetCategory(
            names={"en": "Shows", "fr": "Spectacles"},
            descriptions={
                "en": (
                    "Recordings of live stage shows: stand-up comedy specials, one-man shows, filmed "
                    "theatre plays, opera, ballet, circus and magic shows. Not fiction films about "
                    "comedians or the stage."
                ),
                "fr": (
                    "Captations de spectacles sur scène : spectacles d'humour et de stand-up, "
                    "one-man-shows, théâtre filmé, opéra, ballet, cirque et magie. Pas les films de "
                    "fiction sur des humoristes ou la scène."
                ),
            },
            rules=(
                PresetRule("keyword", "contains", "comedy special", 90, decisive=True),
                PresetRule("keyword", "contains", "stand-up special", 90, decisive=True),
                PresetRule("keyword", "contains", "one-man show", 90, decisive=True),
                PresetRule("keyword", "contains", "one man show", 90, decisive=True),
                PresetRule("keyword", "contains", "one-woman show", 90, decisive=True),
                PresetRule("keyword", "contains", "one woman show", 90, decisive=True),
                PresetRule("keyword", "contains", "spectacle humoristique", 90, decisive=True),
                PresetRule("keyword", "contains", "filmed stand-up", 90, decisive=True),
                PresetRule("keyword", "contains", "filmed theater", 90, decisive=True),
                PresetRule("keyword", "contains", "filmed play", 90, decisive=True),
                PresetRule("keyword", "contains", "stand-up", 60),
                PresetRule("keyword", "contains", "humoriste", 50),
                PresetRule("keyword", "contains", "comedy show", 50),
                PresetRule("keyword", "contains", "sketch comedy", 40),
                PresetRule("keyword", "contains", "stage play", 50),
                PresetRule("keyword", "contains", "live performance", 30),
                PresetRule("keyword", "is", "humor", 20),
                PresetRule("keyword", "is", "opera", 40),
                PresetRule("keyword", "is", "ballet", 40),
                PresetRule("keyword", "contains", "circus", 30),
                PresetRule("keyword", "contains", "magic show", 50),
                # a story (about a comedian, a magician…), not a show on stage
                PresetRule("genre", "is", "Crime", 1, excludes=True),
                PresetRule("genre", "is", "Thriller", 1, excludes=True),
                PresetRule("genre", "is", "Horror", 1, excludes=True),
            ),
        ),
    ),
)

CONCERTS = Preset(
    key="concerts",
    names={"en": "Concerts", "fr": "Concerts"},
    descriptions={
        "en": "Adds a Concerts category: concert films and live recordings of tours and festivals.",
        "fr": "Ajoute une catégorie Concerts : films de concert, captations de tournées et de festivals.",
    },
    addon=True,
    categories=(
        PresetCategory(
            names={"en": "Concerts", "fr": "Concerts"},
            descriptions={
                "en": (
                    "Concert films: a band or a singer filmed live on stage, a tour or a festival. Not "
                    "biopics or fiction about musicians."
                ),
                "fr": (
                    "Films de concert : un groupe ou un artiste filmé en live sur scène, une tournée ou "
                    "un festival. Pas les biopics ni les fictions sur des musiciens."
                ),
            },
            rules=(
                PresetRule("keyword", "contains", "concert film", 90, decisive=True),
                PresetRule("keyword", "contains", "live concert", 90, decisive=True),
                PresetRule("keyword", "contains", "concert tour", 70),
                PresetRule("keyword", "contains", "music festival", 50),
                PresetRule("keyword", "is", "concert", 50),
                PresetRule("keyword", "contains", "live performance", 30),
                PresetRule("genre", "is", "Music", 20),
                # a story about musicians, not a concert
                PresetRule("keyword", "contains", "biography", 1, excludes=True),
                PresetRule("keyword", "contains", "biopic", 1, excludes=True),
                PresetRule("genre", "is", "Drama", 1, excludes=True),
                PresetRule("genre", "is", "Romance", 1, excludes=True),
            ),
        ),
    ),
)

PRESETS = {preset.key: preset for preset in (MOVIES_ANIMATION, SHOWS, CONCERTS)}
