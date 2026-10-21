from dataclasses import dataclass
import json
import re
from typing import Any

@dataclass(frozen=True)
class Route:
    category: str
    parameters: dict[str, str]
    confidence: float
    reason: str

# Categories the local LLM may pick when no keyword rule matched.
LLM_CATEGORIES = {
    "movie_lookup", "actor_lookup", "director_lookup", "cast_discovery",
    "director_filmography", "actor_collaborations", "shared_movie",
    "movie_relationships", "recommendations", "producer_lookup", "reviewer_lookup",
    "writer_lookup", "producer_filmography", "writer_filmography", "reviewer_filmography",
    "produced_check", "wrote_check", "reviewed_check", "directed_check", "acted_check",
}
PARAMS_BY_CATEGORY = {
    "movie_lookup": {"title"}, "actor_lookup": {"name"},
    "director_lookup": {"name"}, "cast_discovery": {"title"},
    "director_filmography": {"name"}, "actor_collaborations": {"name"},
    "shared_movie": {"person1", "person2"}, "movie_relationships": {"title"},
    "recommendations": {"title"}, "producer_lookup": {"title"},
    "reviewer_lookup": {"title"}, "writer_lookup": {"title"},
    "producer_filmography": {"name"}, "writer_filmography": {"name"},
    "reviewer_filmography": {"name"},
    "produced_check": {"person", "title"}, "wrote_check": {"person", "title"},
    "reviewed_check": {"person", "title"}, "directed_check": {"person", "title"},
    "acted_check": {"person", "title"},
    # --- added: question types that previously had no query at all ---
    "movies_between": {"start", "end"},
    "oldest_movies": set(), "newest_movies": set(),
    "list_movies": set(), "database_counts": set(), "top_actors": set(),
    "largest_casts": set(), "top_rated_movies": set(),
    "person_movie_count": {"name"}, "cast_size": {"title"},
    "movie_rating": {"title"},
    "actor_directors": {"name"}, "director_actors": {"name"},
    "actor_directors_overlap": set(), "person_movies_any": {"name"},
}
ALLOWED_CATEGORIES = set(PARAMS_BY_CATEGORY)

# Only the vague fall-through ("movie_lookup" guess / unsupported) is handed to the LLM.
_LLM_FALLTHROUGH_CONFIDENCE = 0.7

_WHO = r"(?:who(?:'s|\s+(?:is|are|was|were))\s+)?(?:the\s+|a\s+)?"
_AUX = r"(?:has\s+|have\s+|had\s+)?"
_FILM = r"(?:movies?|films?)"

# Yes/no questions -> (category, patterns with named groups person/title). Order matters:
# "reviewed" first so "Did X write a review of Y?" is not read as a writing credit.
_YES_NO_PATTERNS = [
    ("reviewed_check", [
        r"^(?:did|has|have|had)\s+(?P<person>.+?)\s+(?:review(?:ed)?|(?:write|written|wrote|leave|left|give|gave)\s+(?:a\s+|the\s+)?reviews?\s+(?:of|for|on))\s+(?P<title>.+)$",
        r"^(?:was|is|were|are)\s+(?P<title>.+?)\s+reviewed by\s+(?P<person>.+)$",
        r"^(?:is|was|are|were)\s+(?P<person>.+?)\s+(?:a|an|the|one of the)\s+reviewers?\s+(?:of|for|on)\s+(?P<title>.+)$",
    ]),
    ("produced_check", [
        r"^(?:did|has|have|had)\s+(?P<person>.+?)\s+produce[d]?\s+(?P<title>.+)$",
        r"^(?:was|is|were|are)\s+(?P<title>.+?)\s+produced by\s+(?P<person>.+)$",
        r"^(?:is|was|are|were)\s+(?P<person>.+?)\s+(?:a|an|the|one of the)\s+(?:executive\s+|co-)?producers?\s+(?:of|for|on)\s+(?P<title>.+)$",
    ]),
    ("wrote_check", [
        r"^(?:did|has|have|had)\s+(?P<person>.+?)\s+(?:write|written|wrote)\s+(?P<title>.+)$",
        r"^(?:was|is|were|are)\s+(?P<title>.+?)\s+written by\s+(?P<person>.+)$",
        r"^(?:is|was|are|were)\s+(?P<person>.+?)\s+(?:a|an|the|one of the)\s+(?:writers?|screenwriters?|scriptwriters?|authors?)\s+(?:of|for|on)\s+(?P<title>.+)$",
    ]),
    ("directed_check", [
        r"^(?:did|has|have|had)\s+(?P<person>.+?)\s+direct(?:ed)?\s+(?P<title>.+)$",
        r"^(?:was|is|were|are)\s+(?P<title>.+?)\s+directed by\s+(?P<person>.+)$",
        r"^(?:is|was|are|were)\s+(?P<person>.+?)\s+(?:a|an|the|one of the)\s+directors?\s+(?:of|for|on)\s+(?P<title>.+)$",
    ]),
    ("acted_check", [
        r"^(?:did|has|have|had)\s+(?P<person>.+?)\s+(?:act(?:ed)?|appear(?:ed)?|star(?:red)?)\s+(?:in|on)\s+(?P<title>.+)$",
        r"^(?:is|was|were|are)\s+(?P<person>.+?)\s+(?:in the cast of|part of the cast of|an actor in|an actress in|in)\s+(?P<title>.+)$",
    ]),
]

# Person -> movies (reverse) questions.
_REVERSE_PATTERNS = [
    ("reviewer_filmography", [
        _FILM + r"\s+(?:that|which)\s+(.+?)\s+" + _AUX + r"reviewed\b",
        _FILM + r"\s+(?:did|has|have|had)\s+(.+?)\s+review(?:ed)?\b",
        _FILM + r"\s+(?:was |were |are |is )?reviewed by\s+(.+)$",
        r"what\s+(?:did|has|have|had)\s+(.+?)\s+review(?:ed)?\b",
        r"reviews?\s+(?:written\s+)?by\s+(.+)$",
    ]),
    ("producer_filmography", [
        _FILM + r"\s+(?:that|which)\s+(.+?)\s+" + _AUX + r"produced\b",
        _FILM + r"\s+(?:did|has|have|had)\s+(.+?)\s+produce[d]?\b",
        _FILM + r"\s+(?:was |were |are |is )?produced by\s+(.+)$",
        r"what\s+(?:did|has|have|had)\s+(.+?)\s+produce[d]?\b",
    ]),
    ("writer_filmography", [
        _FILM + r"\s+(?:that|which)\s+(.+?)\s+" + _AUX + r"(?:wrote|written)\b",
        _FILM + r"\s+(?:did|has|have|had)\s+(.+?)\s+(?:write|written|wrote)\b",
        _FILM + r"\s+(?:was |were |are |is )?written by\s+(.+)$",
        r"what\s+(?:did|has|have|had)\s+(.+?)\s+(?:write|written|wrote)\b",
    ]),
]


_NOUN = r"(?:cast|actors?|actresses|directors?|producers?|writers?|screenwriters?)"
_NAME_STOPWORDS = {"action", "comedy", "drama", "horror", "new", "old", "best", "good", "top", "all",
                   "romantic", "sci-fi", "the", "these", "those", "some", "any", "my", "your", "which", "what"}
_DECADES = {"fifties": 1950, "sixties": 1960, "seventies": 1970, "eighties": 1980,
            "nineties": 1990, "noughties": 2000, "aughts": 2000}
_ROLE_WORDS = r"(?:produced|wrote|directed|acted in|starred in)"


def _clean_entity(value: str) -> str:
    value = re.sub(r"^(?:the movie|the film|movie|film)\s+", "", value.strip(), flags=re.I)
    value = re.sub(r"[?!.\"'`]+$", "", value).strip()
    value = re.sub(r"\s+(?:together|please|in the database|in the graph|in the dataset)$", "", value, flags=re.I)
    value = re.sub(r"'s$", "", value).strip()
    return re.sub(r"\s+", " ", value)


def _extract_after(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return _clean_entity(match.group(1))
    return ""


def _first_match(text: str, patterns: list[str]):
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match
    return None


def _year_range(text: str) -> tuple[int, int] | None:
    """Turn 'in 1999', 'the 90s', 'after 2000', 'between 1990 and 2000' into (start, end)."""
    t = text.lower()
    m = re.search(r"\b(?:between|from)\s+(\d{4})\s+(?:and|to|-|–|until|through)\s+(\d{4})\b", t) \
        or re.search(r"\b(\d{4})\s*(?:-|–|to)\s*(\d{4})\b", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return min(a, b), max(a, b)
    for word, year in _DECADES.items():
        if re.search(rf"\b{word}\b", t):
            return year, year + 9
    m = re.search(r"\b'?(\d{4}|\d{2})'?s\b", t)
    if m:
        raw = m.group(1)
        if len(raw) == 4 and raw.endswith("0"):
            return int(raw), int(raw) + 9
        if len(raw) == 2 and raw.endswith("0"):
            year = 1900 + int(raw) if int(raw) >= 30 else 2000 + int(raw)
            return year, year + 9
    m = re.search(r"\b(after|since|later than|newer than)\s+(?:the\s+year\s+)?(\d{4})\b", t)
    if m:
        year = int(m.group(2))
        return (year + 1 if m.group(1) == "after" else year), 9999
    m = re.search(r"\b(before|prior to|earlier than|older than|until|by|up to)\s+(?:the\s+year\s+)?(\d{4})\b", t)
    if m:
        year = int(m.group(2))
        return 0, (year - 1 if m.group(1) in ("before", "prior to", "earlier than", "older than") else year)
    m = re.search(r"\b(1[89]\d{2}|20\d{2})\b", t)
    if m:
        return int(m.group(1)), int(m.group(1))
    return None


def _route(category: str, params: dict[str, str], confidence: float, reason: str) -> Route:
    return Route(category, params, confidence, reason)


def _global_route(q: str, lq: str) -> Route | None:
    """Questions about the whole database that mention no specific movie or person."""
    n = re.sub(r"[?!.\s]+$", "", lq)

    if re.search(r"^(?:how many|what(?:'s| is) the (?:total )?(?:number|count) of|(?:total )?(?:number|count) of|count (?:of )?(?:all )?(?:the )?)\s*"
                 r"(?:all\s+)?(?:the\s+)?(?:movies?|films?|people|persons?|actors?|actresses|directors?|producers?|writers?|reviewers?|reviews?|ratings?|nodes)"
                 r"(?:\s+(?:are\s+|do\s+we\s+have\s+|have\s+we\s+got\s+)?(?:there\s+)?(?:in\s+(?:the\s+)?(?:database|graph|dataset|total)|total|overall|available))?$", n) \
            or n in ("how many movies are there", "how many movies", "how many people are there"):
        return _route("database_counts", {}, .93, "Detected a database count question.")

    if re.search(r"^(?:list|show|give me|name|display|what are)\s+(?:me\s+)?(?:all|every|each)\s+(?:of\s+)?(?:the\s+)?(?:movies?|films?)(?:\s+(?:in|from)\s+(?:the\s+)?(?:database|graph|dataset))?$", n) \
            or re.search(r"^(?:which|what)\s+(?:movies?|films?)\s+(?:are\s+there|do\s+you\s+have|are\s+available|are\s+in\s+(?:the\s+)?(?:database|graph|dataset))$", n) \
            or n in ("all movies", "all films", "list movies", "list all movies"):
        return _route("list_movies", {}, .93, "Detected a list-all-movies request.")

    if re.search(r"\b(?:most\s+(?:movies?|films?)|most\s+(?:prolific|active|appearances|credits)|(?:highest|largest|biggest)\s+number\s+of\s+(?:movies?|films?)|top\s+(?:actors?|directors?))", n) \
            and not re.search(r"\b(?:did|does)\s+[a-z]+\s+[a-z]+\s+(?:act|direct)", n):
        if re.search(r"\b(?:direct\w*|produc\w*|writ\w*|wrote|review\w*)\b", n):
            return _route("unsupported", {}, .2, "Only actor rankings are supported.")
        return _route("top_actors", {}, .9, "Detected a most-prolific-actor question.")

    if re.search(r"\b(?:largest|biggest|most|highest|greatest)\s+(?:cast|number of (?:actors|cast members)|actors)\b", n) \
            and re.search(r"\b(?:movie|film)s?\b", n):
        return _route("largest_casts", {}, .9, "Detected a largest-cast question.")

    if re.search(r"\b(?:highest|best|top|most)[\s-]+(?:rated|reviewed|reviews)\b.*\b(?:movies?|films?)\b|\b(?:movies?|films?)\b.*\b(?:highest|best)[\s-]+rated\b|\bhighest rating\b", n):
        return _route("top_rated_movies", {}, .9, "Detected a top-rated-movies question.")

    if re.search(r"^(?:what|which)(?:\s+is|\s+are|'s)?\s+(?:the\s+)?(?:oldest|earliest|first)\s+(?:movies?|films?)(?:\s+in\s+.*)?$|^(?:oldest|earliest)\s+(?:movies?|films?)$", n):
        return _route("oldest_movies", {}, .9, "Detected an oldest-movie question.")
    if re.search(r"^(?:what|which)(?:\s+is|\s+are|'s)?\s+(?:the\s+)?(?:newest|latest|most recent|last)\s+(?:movies?|films?)(?:\s+in\s+.*)?$|^(?:newest|latest)\s+(?:movies?|films?)$", n):
        return _route("newest_movies", {}, .9, "Detected a newest-movie question.")
    return None


def route_question(question: str) -> Route:
    """Deterministic router: maps natural phrasings onto allow-listed Cypher templates."""
    q = re.sub(r"[?!.\s]+$", "", re.sub(r"\s+", " ", question.strip()))
    lq = q.lower()
    if not q:
        return Route("unsupported", {}, 0.0, "Empty question.")

    if "recommend" in lq or "similar" in lq or "related to" in lq:
        title = _extract_after(q, [
            r"related to\s+(.+)$", r"similar to\s+(.+)$",
            r"recommend(?:\s+me)?\s+(?:some\s+)?movies?\s+(?:like|similar to|related to)\s+(.+)$",
            r"recommend(?:\s+me)?\s+(?:movies?\s+)?(?:for|based on)\s+(.+)$",
        ]) or _extract_after(q, [r"(?:recommend|similar)\s+(.+)$"])
        return _route("recommendations", {"title": title}, .88, "Detected a recommendation request.")

    # Topics the graph queries do not cover (birth dates, character roles, follow links, ages).
    if re.search(r"\b(?:born|birth|birthday|how old|follow(?:s|ed|ing|ers?)?|roles?|characters?|played|plays|portray\w*|voiced)\b", lq) \
            and not re.search(r"\bwho\s+(?:played|plays|acted|starred)\s+in\b", lq):
        return _route("unsupported", {}, .2, "This question type is not supported by the connected graph queries.")

    # ---- whole-database questions (counts, rankings, lists) ----
    route = _global_route(q, lq)
    if route:
        return route

    # ---- how many actors are in X / how many movies did X act in ----
    title = _extract_after(q, [
        r"how many\s+(?:actors?|actresses|people|persons|cast members?|stars)\s+(?:are |were |is |was )?(?:there\s+)?(?:in|acted in|appeared in|starred in)\s+(.+)$",
        r"(?:size|number)\s+of\s+(?:the\s+)?cast\s+(?:of|in|for)\s+(.+)$",
    ])
    if title:
        return _route("cast_size", {"title": title}, .9, "Detected a cast-size question.")
    name = _extract_after(q, [
        r"how many\s+(?:movies?|films?)\s+(?:has|have|had|did|does|is|was)\s+(.+?)\s+(?:act(?:ed)?|appear(?:ed)?|star(?:red)?|been|direct(?:ed)?|produce[d]?|writ(?:e|ten)|wrote|worked|review(?:ed)?)\b",
        r"how many\s+(?:movies?|films?)\s+(?:has|have|had|did|does|is|was)\s+(.+?)\s*$",
        r"(?:number|count)\s+of\s+(?:movies?|films?)\s+(?:that\s+)?(.+?)\s+(?:acted|appeared|starred|directed|produced|wrote|has|have|had)\b",
    ])
    if name:
        return _route("person_movie_count", {"name": name}, .9, "Detected a per-person movie count.")

    # ---- two people together (movies shared / worked together) ----
    two = _first_match(q, [
        r"(?:movies?|films?)\s+(?:with|featuring|starring)\s+both\s+(?P<a>.+?)\s+and\s+(?P<b>.+)$",
        r"(?:movies?|films?)\s+(?:with|featuring|starring)\s+(?P<a>.+?)\s+and\s+(?P<b>.+)$",
        r"(?:shared|common)\s+(?:movies?|films?)\s+(?:of|between|for)\s+(?P<a>.+?)\s+and\s+(?P<b>.+)$",
        r"(?:movies?|films?)\s+(?:shared\s+)?between\s+(?P<a>.+?)\s+and\s+(?P<b>.+)$",
        r"(?:did|do|does|have|has|had)\s+(?P<a>.+?)\s+and\s+(?P<b>.+?)\s+(?:ever\s+)?(?:work(?:ed)?|act(?:ed)?|appear(?:ed)?|star(?:red)?|collaborat\w*)\s+(?:together|with each other|in the same (?:movie|film)|in (?:a|any|one) (?:movie|film) together)",
        r"(?:which|what)\s+(?:movies?|films?)\s+(?:do|did|have|has)\s+(?P<a>.+?)\s+and\s+(?P<b>.+?)\s+(?:share|have in common|both\s+\w+(?:\s+in)?|(?:act|appear|star|work)\w*\s+(?:in\s+)?together)",
        r"(?:movies?|films?)\s+(?:that\s+)?(?P<a>.+?)\s+and\s+(?P<b>.+?)\s+(?:both\s+)?(?:acted|appeared|starred|worked)\s+(?:in|on)",
        r"^(?P<a>.+?)\s+and\s+(?P<b>.+?)\s+(?:work(?:ed)?|act(?:ed)?|star(?:red)?|appear(?:ed)?)\s+together",
    ])
    if two:
        a, b = _clean_entity(two.group("a")), _clean_entity(two.group("b"))
        a = re.sub(r"^both\s+", "", a, flags=re.I)
        if a and b and not (re.fullmatch(r"\d{4}", a) and re.fullmatch(r"\d{4}", b)):
            return _route("shared_movie", {"person1": a, "person2": b}, .92, "Detected a two-person shared-movie question.")

    # ---- movies by release year ----
    if re.search(r"\b(?:movies?|films?)\b", lq) and not re.search(
            r"\b(?:did|does|has|have|had|by|with|starring|featuring|directed|acted|appeared|produced|wrote|written|reviewed|similar|like)\b", lq):
        rng = _year_range(q)
        if rng:
            return _route("movies_between", {"start": str(rng[0]), "end": str(rng[1])}, .9, "Detected a release-year filter.")

    # ---- ratings ----
    two = _first_match(q, [
        r"what\s+(?:rating|score|stars?)\s+(?:did|has|have|had)\s+(?P<person>.+?)\s+(?:give|gave|assign(?:ed)?|leave|left)\s+(?:to\s+)?(?P<title>.+)$",
        r"how\s+(?:did|does|has)\s+(?P<person>.+?)\s+(?:rate|review)\s+(?P<title>.+)$",
    ])
    if two:
        return _route("reviewed_check", {"person": _clean_entity(two.group("person")), "title": _clean_entity(two.group("title"))},
                      .92, "Detected a rating-given-by-person question.")
    title = _extract_after(q, [
        r"(?:average\s+|overall\s+)?(?:ratings?|scores?)\s+(?:of|for|on)\s+(.+)$",
        r"how many\s+(?:reviews?|ratings?)\s+(?:does|did|has|have)\s+(.+?)(?:\s+(?:have|get|got|received?|had))?$",
        r"how\s+(?:is|was|are)\s+(.+?)\s+rated",
        r"how\s+(?:well|highly)\s+(?:is|was)\s+(.+?)\s+(?:rated|reviewed)",
        r"what\s+(?:is|was)\s+(.+?)\s+rated",
        r"how many\s+(?:reviews?|ratings?)\s+(?:of|for)\s+(.+?)(?:\s+(?:are there|exist))?$",
    ])
    if title:
        return _route("movie_rating", {"title": title}, .9, "Detected a movie rating question.")

    # ---- combined credit questions: "who produced and directed X", "cast and director of X" ----
    title = _extract_after(q, [
        rf"who\s+{_ROLE_WORDS}(?:\s*,\s*{_ROLE_WORDS})*(?:\s*,)?\s+(?:and|&)\s+{_ROLE_WORDS}\s+(.+)$",
        rf"\b{_NOUN}(?:\s*,\s*(?:the\s+)?{_NOUN})*\s*,?\s*(?:and|&)\s+(?:the\s+)?{_NOUN}\s+(?:of|for|in|on)\s+(.+)$",
        r"who\s+(?:all\s+)?(?:worked|works)\s+(?:on|in)\s+(.+)$",
        r"who(?:\s+all)?\s+(?:is|was|are|were)\s+involved\s+(?:in|with|on)\s+(.+)$",
        r"(?:everyone|everybody|people|persons?|anyone|all the people)\s+(?:who\s+(?:was\s+|were\s+)?)?(?:involved|worked)\s+(?:in|on|with)\s+(.+)$",
        r"(?:crew|full credits|credits)\s+(?:of|for)\s+(.+)$",
        r"who\s+made\s+(.+)$",
    ])
    if title:
        return _route("movie_relationships", {"title": title}, .9, "Detected a combined/crew credits question.")

    # ---- cross-role: directors an actor worked with, actors a director worked with, actor-directors ----
    if re.search(r"\b(?:acted|appeared|starred)\s+in\s+and\s+directed\b|\b(?:directed\s+and\s+acted|acted\s+and\s+directed|directed\s+and\s+starred)\b"
                 r"|\bactors?\s+(?:who|that)\s+(?:are\s+)?(?:also|later)\s+(?:directed|directors?)\b|\bdirectors?\s+(?:who|that)\s+(?:are\s+)?(?:also|later)\s+(?:acted|act|actors?)\b"
                 r"|\bactors?\s+(?:who\s+are\s+)?(?:also\s+)?directors?\b|\bactor[- ]directors?\b", lq):
        return _route("actor_directors_overlap", {}, .9, "Detected an actor-who-also-directed question.")
    name = _extract_after(q, [
        r"(?:which|what|who)\s+directors?\s+(?:has|have|had|did|does)\s+(.+?)\s+(?:work(?:ed)?|collaborat\w*)\s+with",
        r"directors?\s+(?:who|that)\s+(?:has\s+|have\s+)?(?:worked|collaborated)\s+with\s+(.+)$",
        r"directors?\s+(?:of|for)\s+(?:all\s+)?(?:the\s+)?(?:movies|films)\s+(?:that\s+)?(.+?)\s+(?:acted|appeared|starred)\s+in",
        r"(?:which|what|who)\s+directors?\s+(?:has|have|had|did|does)\s+(.+?)\s+(?:act(?:ed)?|appear(?:ed)?|star(?:red)?)\s+(?:for|under|with)",
    ])
    if name:
        return _route("actor_directors", {"name": name}, .9, "Detected a directors-an-actor-worked-with question.")
    name = _extract_after(q, [
        r"actors?\s+(?:who\s+|that\s+)?(?:has\s+|have\s+)?(?:worked|collaborated)\s+with\s+(?:the\s+)?director\s+(.+)$",
        r"actors?\s+(?:who\s+(?:were|was|have been)\s+)?directed\s+by\s+(.+)$",
        r"(?:which|what|who)\s+actors?\s+(?:has|have|had|did|does)\s+(?:the\s+)?(?:director\s+)?(.+?)\s+direct(?:ed)?\s*$",
        r"(?:which|what|who)\s+actors?\s+(?:has|have|had|did)\s+(?:the\s+)?director\s+(.+?)\s+(?:work(?:ed)?|collaborat\w*)\s+with",
        r"(?:which|what|who)\s+actors?\s+(?:worked|collaborated)\s+with\s+(?:the\s+)?director\s+(.+)$",
    ])
    if name:
        return _route("director_actors", {"name": name}, .9, "Detected an actors-of-a-director question.")

    # ---- yes/no questions ----
    for category, patterns in _YES_NO_PATTERNS:
        for pattern in patterns:
            match = re.search(pattern, q, re.I)
            if match:
                person, title = _clean_entity(match.group("person")), _clean_entity(match.group("title"))
                if person and title:
                    return _route(category, {"person": person, "title": title}, .93, "Detected a yes/no relationship question.")

    # ---- person -> movies they reviewed / produced / wrote ----
    for category, patterns in _REVERSE_PATTERNS:
        name = _extract_after(q, patterns)
        if name:
            return _route(category, {"name": name}, .91, "Detected a person's reviewed/produced/written movies request.")

    # ---- movie -> reviewer(s). Checked first so "who wrote the review of X" is not read as a writing credit ----
    reviewer_title = _extract_after(q, [
        r"who\s+" + _AUX + r"reviewed\s+(.+)$",
        _WHO + r"reviewers?\s+(?:of|for|on)\s+(.+)$",
        r"(?:who\s+(?:wrote|gave|left)\s+)?(?:the\s+)?reviews?\s+(?:of|for|on)\s+(.+)$",
        r"(.+?)\s+was reviewed by\b",
    ])
    if reviewer_title:
        return _route("reviewer_lookup", {"title": reviewer_title}, .92, "Detected a movie reviewer lookup.")

    producer_title = _extract_after(q, [
        r"who\s+" + _AUX + r"produced\s+(.+)$",
        _WHO + r"(?:executive\s+|co-)?producers?\s+(?:of|for|on)\s+(.+)$",
        r"(.+?)\s+was produced by\b",
    ])
    if producer_title:
        return _route("producer_lookup", {"title": producer_title}, .92, "Detected a movie producer lookup.")

    writer_title = _extract_after(q, [
        r"who\s+" + _AUX + r"(?:wrote|written)\s+the\s+(?:screenplay|script|story|book)\s+(?:of|for|to|on)\s+(.+)$",
        r"who\s+" + _AUX + r"(?:wrote|written)\s+(.+)$",
        _WHO + r"(?:writers?|screenwriters?|scriptwriters?|authors?)\s+(?:of|for|on)\s+(.+)$",
        r"(.+?)\s+was written by\b",
    ])
    if writer_title:
        return _route("writer_lookup", {"title": writer_title}, .92, "Detected a movie writer lookup.")

    # ---- director filmography (person -> movies) ----
    director_name = _extract_after(q, [
        r"(?:movies|films)\s+(?:that|which)\s+(.+?)\s+(?:directed|directs)",
        r"(?:what|which|name the|list the)?\s*(?:movies|films)\s+(?:did|has|have|had)\s+(.+?)\s+direct(?:ed)?\b",
        r"(?:movies|films)\s+directed by\s+(.+)$",
        r"what did\s+(.+?)\s+direct",
        r"filmography of director\s+(.+)$",
        r"(?:directed by)\s+(.+)$",
    ])
    if director_name:
        return _route("director_filmography", {"name": director_name}, .91, "Detected a director filmography request.")

    # ---- movie -> director(s) ----
    movie_title = _extract_after(q, [
        r"who\s+(?:has\s+)?directed\s+(.+)$",
        r"(?:who(?:'s|\s+(?:is|are|was|were))\s+)?(?:the\s+)?directors?\s+(?:of|for|on)\s+(.+)$",
        r"(.+?)\s+was directed by\b",
    ])
    if movie_title:
        return _route("director_lookup", {"name": movie_title}, .92, "Detected a movie director lookup.")

    # ---- co-stars ----
    name = _extract_after(q, [
        r"who\s+(?:has|have|had|did|does)\s+(.+?)\s+(?:work(?:ed)?|act(?:ed)?|appear(?:ed)?|star(?:red)?|collaborat\w*)\s+(?:with|alongside|opposite)",
        r"who\s+(?:acted|worked|appeared|starred|collaborated)\s+(?:with|alongside|opposite)\s+(.+)$",
        r"(?:which|what)\s+(?:actors?|people|persons)\s+(?:has|have|had|did|does)\s+(.+?)\s+(?:work(?:ed)?|act(?:ed)?|collaborat\w*|appear(?:ed)?)\s+(?:with|alongside)",
        r"(?:actors?|people|persons)\s+(?:who\s+|that\s+)?(?:has\s+|have\s+)?(?:worked|acted|appeared|starred|collaborated)\s+(?:with|alongside)\s+(.+)$",
        r"(?:co-?stars?|costars?|collaborators?)\s+(?:of|for)\s+(.+)$",
        r"^(.+?)'s\s+(?:co-?stars?|collaborators?)$",
        r"collaborat\w*\s+(?:of|with)\s+(.+)$",
    ])
    if name:
        return _route("actor_collaborations", {"name": name}, .9, "Detected an actor collaboration request.")

    # ---- cast of a movie ----
    cast_title = _extract_after(q, [
        r"(?:cast|actors?|actresses|cast members?|stars|starring)\s+(?:of|in|for|from)\s+(.+)$",
        r"who\s+(?:all\s+)?(?:acted|starred|stars|appeared|performed|played)\s+in\s+(.+)$",
        r"who\s+(?:all\s+)?(?:is|are|was|were)\s+in\s+(?:the\s+(?:movie|film)\s+)?(.+)$",
        r"(?:which|what)\s+(?:actors?|actresses|people|persons)\s+(?:acted|appeared|starred|were|was|are|is)\s+in\s+(.+)$",
        r"^(.+?)\s+cast(?:\s+members?|\s+list)?$",
        r"^cast\s+(.+)$",
    ])
    if cast_title:
        return _route("cast_discovery", {"title": cast_title}, .9, "Detected a cast request.")

    # ---- person -> movies (acting credits) ----
    actor_patterns = [
        r"(?:which|what|name the|list the)?\s*(?:movies|films)\s+(?:did|has|have|had)\s+(.+?)\s+(?:act(?:ed|ing)?|appear(?:ed|ing)?|star(?:red|ring)?)\s+(?:in|on)",
        r"(?:which|what|name the|list the)?\s*(?:movies|films)\s+(?:did|has|have|had)\s+(.+?)\s+(?:act(?:ed|ing)?|appear(?:ed|ing)?|star(?:red|ring)?)\b",
        r"(?:which|what)\s+(?:movies?|films?)\s+(?:has|have|had|did|does|is|was)\s+(.+?)\s+(?:been\s+)?(?:in|featured in)\s*$",
        r"(?:movies?|films?)\s+(?:starring|featuring|with)\s+(.+)$",
        r"(?:movies?|films?)\s+(?:that\s+)?(.+?)\s+(?:has\s+)?(?:been in|is in|was in|acted in|appeared in|starred in)\b",
    ]
    name = _extract_after(q, actor_patterns)
    if name:
        return _route("actor_lookup", {"name": name}, .9, "Detected an actor filmography request.")

    # ---- person -> movies in any role ----
    name = _extract_after(q, [
        r"filmography(?:\s+of|\s+for)?\s+(.+)$",
        r"(?:list|show|give me|name|tell me)?\s*(?:all\s+)?(?:the\s+)?(?:movies?|films?)\s+(?:of|by|for|involving)\s+(.+)$",
        r"^(.+?)'s\s+(?:movies?|films?|filmography)$",
        r"(?:movies?|films?)\s+(?:that\s+)?(.+?)\s+(?:worked on|was involved in|were involved in|has worked on|has been involved in)\b",
    ])
    if name:
        return _route("person_movies_any", {"name": name}, .88, "Detected a person's movies (any role) request.")
    m = re.match(r"^(?P<n>[A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){1,3})\s+(?:movies|films|filmography)\??$", q)
    if m and m.group("n").split()[0].lower() not in _NAME_STOPWORDS:
        return _route("person_movies_any", {"name": m.group("n")}, .85, "Detected a '<person> movies' request.")

    # ---- movie facts ----
    title = _extract_after(q, [
        r"(?:when|what year|which year)\s+(?:was|did|is)\s+(.+?)\s+(?:released|come out|came out|made|released)",
        r"(?:release\s*(?:year|date)|year)\s+of\s+(.+)$",
        r"(?:tagline|slogan)\s+(?:of|for)\s+(.+)$",
        r"what(?:'s|\s+is|\s+was)\s+(.+?)\s+about$",
        r"(?:plot|summary|description|synopsis)\s+of\s+(.+)$",
        r"(?:details|info|information)\s+(?:of|about|on)\s+(.+)$",
    ])
    if title:
        return _route("movie_lookup", {"title": title}, .9, "Detected a movie-facts question.")

    relationship_title = _extract_after(q, [
        r"connections? (?:exist )?(?:for|in|to)\s+(.+)$",
        r"relationships? (?:for|in|to)\s+(.+)$",
    ])
    if relationship_title:
        return _route("movie_relationships", {"title": relationship_title}, .82, "Detected graph relationship exploration.")

    title = _extract_after(q, [r"(?:about|movie|film)\s+(.+)$"])
    if title or "movie" in lq or "film" in lq:
        return _route("movie_lookup", {"title": title or _clean_entity(q)}, .65, "General movie lookup.")
    return _route("unsupported", {}, .2, "No supported graph question pattern matched.")


def route_question_with_llm(question: str, model: str, host: str) -> Route:
    """Use Ollama to classify intent, but only permit allow-listed Cypher templates.

    The LLM never writes or executes Cypher. If Ollama or validation fails, use
    deterministic routing so the app remains usable without changing the UI.
    """
    fallback = route_question(question)
    # Every keyword rule is unambiguous; only the vague "general movie lookup" guess or an
    # unsupported question is passed to the LLM, so a small local model can't misroute them.
    if fallback.confidence > _LLM_FALLTHROUGH_CONFIDENCE:
        return fallback
    try:
        from ollama import Client
        client = Client(host=host)
        categories = ", ".join(sorted(LLM_CATEGORIES))
        prompt = (
            "Classify this movie-graph question and extract the entity name(s). "
            f"Allowed categories: {categories}. Return only JSON with keys category, parameters, confidence. "
            "Parameter values must be strings. Categories: actor_lookup=movies an actor acted in; "
            "director_filmography=movies a director directed; director_lookup=who directed a movie; "
            "cast_discovery=actors in a movie; actor_collaborations=actors who worked with a person; "
            "shared_movie=movies shared by two people; recommendations=similar/related movies; "
            "producer_lookup=who produced a movie; reviewer_lookup=who reviewed a movie; writer_lookup=who wrote a movie; "
            "producer_filmography/writer_filmography/reviewer_filmography=movies a person produced/wrote/reviewed (parameter name); "
            "produced_check/wrote_check/reviewed_check/directed_check/acted_check=yes/no question about whether a person did that for a movie (parameters person and title); "
            "movie_relationships=people/relationships connected to a movie; movie_lookup=general movie facts. "
            "Never invent entities. Examples: 'Which movies did Tom Hanks act in?' -> "
            '{"category":"actor_lookup","parameters":{"name":"Tom Hanks"},"confidence":0.98}; '
            "'name the movies that Lily Wachowski directed' -> "
            '{"category":"director_filmography","parameters":{"name":"Lily Wachowski"},"confidence":0.98}; '
            "'what movies had Audrey Tautou acted in' -> "
            '{"category":"actor_lookup","parameters":{"name":"Audrey Tautou"},"confidence":0.98}; '
            "'Who directed The Matrix?' -> "
            '{"category":"director_lookup","parameters":{"name":"The Matrix"},"confidence":0.98}; '
            "'Who produced Apollo 13?' -> "
            '{"category":"producer_lookup","parameters":{"title":"Apollo 13"},"confidence":0.98}; '
            "'Who reviewed Cloud Atlas?' -> "
            '{"category":"reviewer_lookup","parameters":{"title":"Cloud Atlas"},"confidence":0.98}; '
            "'Did Tom Hanks produce Apollo 13?' -> "
            '{"category":"produced_check","parameters":{"person":"Tom Hanks","title":"Apollo 13"},"confidence":0.98}.\n'
            f"Question: {question}"
        )
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": "You are a strict intent classifier. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={"temperature": 0, "num_predict": 180},
        )
        content = response.message.content if response.message else ""
        data: dict[str, Any] = json.loads(content or "{}")
        category = str(data.get("category", "unsupported")).strip()
        if category not in LLM_CATEGORIES:
            return fallback
        raw_params = data.get("parameters", {})
        if not isinstance(raw_params, dict):
            return fallback
        required = PARAMS_BY_CATEGORY[category]
        params: dict[str, str] = {}
        for key in required:
            value = raw_params.get(key)
            if isinstance(value, str) and _clean_entity(value):
                params[key] = _clean_entity(value)
        if set(params) != required:
            return fallback
        confidence = float(data.get("confidence", 0.8))
        if confidence < 0.45:
            return fallback
        return Route(category, params, min(1.0, max(0.0, confidence)),
                     "Interpreted by local Ollama; retrieval uses an allow-listed safe Cypher template.")
    except Exception:
        return fallback
