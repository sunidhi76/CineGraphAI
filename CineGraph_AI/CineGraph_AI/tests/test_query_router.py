from rag.query_router import route_question

def test_director_question():
    r=route_question('Who directed The Matrix?')
    assert r.category == 'director_lookup'
    assert 'Matrix' in r.parameters['name']

def test_actor_question():
    r=route_question('Which movies did Tom Hanks act in?')
    assert r.category == 'actor_lookup'
    assert 'Tom Hanks' in r.parameters['name']

def test_recommendation():
    r=route_question('Recommend movies related to The Matrix.')
    assert r.category == 'recommendations'


def test_director_lookup_uses_exact_movie_title():
    from rag.cypher_templates import TEMPLATES
    query = TEMPLATES["director_lookup"]
    assert "toLower(m.title) = toLower($name)" in query
    assert "p.name AS director" in query


def test_lowercase_home_recommendation_extracts_movie_title():
    r = route_question('recommend movies related to the matrix')
    assert r.category == 'recommendations'
    assert r.parameters['title'].lower() == 'the matrix'


def test_director_filmography_natural_phrasings():
    from rag.query_router import route_question
    for question in (
        'name the movies that Lily Wachowski directed',
        'what movies did Lily Wachowski direct',
        'films directed by Lily Wachowski',
    ):
        route = route_question(question)
        assert route.category == 'director_filmography'
        assert route.parameters['name'].lower() == 'lily wachowski'


def test_actor_filmography_alternate_wording():
    from rag.query_router import route_question
    route = route_question('what movies had Audrey Tautou acted in')
    assert route.category == 'actor_lookup'
    assert route.parameters['name'] == 'Audrey Tautou'


def test_producer_question():
    for q in ('Who produced Apollo 13?', 'who produced the movie apollo 13', 'Who were the producers of Apollo 13?'):
        r = route_question(q)
        assert r.category == 'producer_lookup'
        assert r.parameters['title'].lower() == 'apollo 13'


def test_reviewer_question():
    for q in ('Who reviewed Cloud Atlas?', 'who has reviewed cloud atlas', 'Who are the reviewers of Cloud Atlas?'):
        r = route_question(q)
        assert r.category == 'reviewer_lookup'
        assert r.parameters['title'].lower() == 'cloud atlas'


def test_producer_reviewer_templates_exist():
    from rag.cypher_templates import TEMPLATES
    assert '[:PRODUCED]' in TEMPLATES['producer_lookup']
    assert '[r:REVIEWED]' in TEMPLATES['reviewer_lookup']
    assert 'r.rating' in TEMPLATES['reviewer_lookup']


def _route(q):
    r = route_question(q)
    return r.category, r.parameters


def test_writer_questions():
    for q in ('Who wrote Cloud Atlas?', 'Who is the writer of Cloud Atlas?', 'who is writer of cloud atlas',
              'Who are the writers of Cloud Atlas?', 'Who wrote the screenplay for Cloud Atlas?'):
        cat, params = _route(q)
        assert cat == 'writer_lookup' and params['title'].lower() == 'cloud atlas'


def test_who_is_producer_of():
    for q in ('Who is the producer of Apollo 13?', 'who is producer of apollo 13', "Who's the producer of Apollo 13?"):
        cat, params = _route(q)
        assert cat == 'producer_lookup' and params['title'].lower() == 'apollo 13'


def test_review_wording_is_not_a_writing_credit():
    assert _route('Who wrote the review of Cloud Atlas?') == ('reviewer_lookup', {'title': 'Cloud Atlas'})


def test_reverse_questions():
    assert _route('Which movies did Joel Silver produce?') == ('producer_filmography', {'name': 'Joel Silver'})
    assert _route('Movies produced by Joel Silver') == ('producer_filmography', {'name': 'Joel Silver'})
    assert _route('What movies has Aaron Sorkin written?') == ('writer_filmography', {'name': 'Aaron Sorkin'})
    assert _route('Which movies did Lana Wachowski write?') == ('writer_filmography', {'name': 'Lana Wachowski'})
    assert _route('What movies did Jessica Thompson review?') == ('reviewer_filmography', {'name': 'Jessica Thompson'})
    assert _route('Movies reviewed by Jessica Thompson') == ('reviewer_filmography', {'name': 'Jessica Thompson'})


def test_yes_no_questions():
    cases = {
        'Did Joel Silver produce The Matrix?': 'produced_check',
        'Was The Matrix produced by Joel Silver?': 'produced_check',
        'Is Joel Silver the producer of The Matrix?': 'produced_check',
        'Did Joel Silver write The Matrix?': 'wrote_check',
        'Was The Matrix written by Joel Silver?': 'wrote_check',
        'Is Joel Silver the writer of The Matrix?': 'wrote_check',
        'Did Joel Silver review The Matrix?': 'reviewed_check',
        'Did Joel Silver write a review of The Matrix?': 'reviewed_check',
        'Was The Matrix reviewed by Joel Silver?': 'reviewed_check',
        'Did Joel Silver direct The Matrix?': 'directed_check',
        'Was The Matrix directed by Joel Silver?': 'directed_check',
        'Did Joel Silver act in The Matrix?': 'acted_check',
    }
    for q, expected in cases.items():
        cat, params = _route(q)
        assert cat == expected, q
        assert params == {'person': 'Joel Silver', 'title': 'The Matrix'}, q


def test_new_templates_exist_and_use_right_relationships():
    from rag.cypher_templates import TEMPLATES
    assert '[:WROTE]' in TEMPLATES['writer_lookup']
    assert '[:PRODUCED]' in TEMPLATES['producer_filmography']
    assert '[:WROTE]' in TEMPLATES['writer_filmography']
    assert '[r:REVIEWED]' in TEMPLATES['reviewer_filmography']
    for cat, rel in (('produced_check', 'PRODUCED'), ('wrote_check', 'WROTE'), ('reviewed_check', 'REVIEWED'),
                     ('directed_check', 'DIRECTED'), ('acted_check', 'ACTED_IN')):
        assert rel in TEMPLATES[cat] and '$person' in TEMPLATES[cat] and '$title' in TEMPLATES[cat]


def test_every_routable_category_has_a_template():
    from rag.cypher_templates import TEMPLATES
    from rag.query_router import ALLOWED_CATEGORIES
    assert ALLOWED_CATEGORIES <= set(TEMPLATES)


# ---- question-coverage regression tests (added) ----
COVERAGE_CASES = [
    ('List the actors of The Matrix', 'cast_discovery'),
    ('Who is in The Matrix?', 'cast_discovery'),
    ('Who starred in Apollo 13?', 'cast_discovery'),
    ('Which actors were in Cloud Atlas?', 'cast_discovery'),
    ('The Matrix cast', 'cast_discovery'),
    ('Cast members of The Matrix', 'cast_discovery'),
    ('Who acted in The Matrix', 'cast_discovery'),
    ('Tom Hanks movies', 'person_movies_any'),
    ('Movies starring Tom Hanks', 'actor_lookup'),
    ('What movies has Tom Hanks been in?', 'actor_lookup'),
    ('List the movies of Tom Hanks', 'person_movies_any'),
    ('Tom Hanks filmography', 'person_movies_any'),
    ('Which movies did Tom Hanks act in?', 'actor_lookup'),
    ('Who are the directors of Cloud Atlas?', 'director_lookup'),
    ('Who directed The Matrix?', 'director_lookup'),
    ('Who has Tom Hanks worked with?', 'actor_collaborations'),
    ('Who acted with Tom Hanks?', 'actor_collaborations'),
    ('Co-stars of Tom Hanks', 'actor_collaborations'),
    ('Movies with both Tom Hanks and Meg Ryan', 'shared_movie'),
    ('Did Tom Hanks and Meg Ryan work together?', 'shared_movie'),
    ('Which movies do Tom Hanks and Meg Ryan share?', 'shared_movie'),
    ('When was The Matrix released?', 'movie_lookup'),
    ('What is the tagline of The Matrix?', 'movie_lookup'),
    ('What is The Matrix about?', 'movie_lookup'),
    ('Who worked on The Matrix?', 'movie_relationships'),
    ('Everyone involved in Apollo 13', 'movie_relationships'),
    ('What rating did Jessica Thompson give Cloud Atlas?', 'reviewed_check'),
    ('What is the rating of Cloud Atlas?', 'movie_rating'),
    ('How many reviews does Cloud Atlas have?', 'movie_rating'),
    ('Movies released in 1999', 'movies_between'),
    ('Movies from the 90s', 'movies_between'),
    ('Which movies came out after 2000?', 'movies_between'),
    ('Movies between 1995 and 2000', 'movies_between'),
    ('What is the oldest movie?', 'oldest_movies'),
    ('What is the newest movie in the database?', 'newest_movies'),
    ('List all movies', 'list_movies'),
    ('How many movies are in the database?', 'database_counts'),
    ('How many people are there?', 'database_counts'),
    ('Which actor appeared in the most movies?', 'top_actors'),
    ('Who has acted in the most movies?', 'top_actors'),
    ('Which movie has the largest cast?', 'largest_casts'),
    ('How many movies did Tom Hanks act in?', 'person_movie_count'),
    ('How many actors are in The Matrix?', 'cast_size'),
    ('Which directors has Tom Hanks worked with?', 'actor_directors'),
    ('Which actors worked with director Lana Wachowski?', 'director_actors'),
    ('Which actors did Lana Wachowski direct?', 'director_actors'),
    ('Who both acted in and directed a movie?', 'actor_directors_overlap'),
    ('Movies of Lana Wachowski', 'person_movies_any'),
    ('Who produced and directed The Matrix?', 'movie_relationships'),
    ('List the cast and director of The Matrix', 'movie_relationships'),
    ('Highest rated movies', 'top_rated_movies'),
    ('Did Tom Hanks produce Apollo 13?', 'produced_check'),
    ('Recommend movies like The Matrix', 'recommendations'),
    ('Who wrote Cloud Atlas?', 'writer_lookup'),
    ('Who reviewed Cloud Atlas?', 'reviewer_lookup'),
    ('Movies that Joel Silver produced', 'producer_filmography'),
    ('Tell me a joke', 'unsupported'),
    ('What is the weather?', 'unsupported'),
]


def test_question_coverage_routes():
    wrong = []
    for question, expected in COVERAGE_CASES:
        got = route_question(question).category
        if got != expected:
            wrong.append((question, got, expected))
    assert not wrong, wrong


def test_list_actors_of_movie_extracts_title():
    for q in ('List the actors of The Matrix', 'Who is in The Matrix?', 'Who starred in The Matrix?', 'The Matrix cast'):
        r = route_question(q)
        assert r.category == 'cast_discovery' and r.parameters == {'title': 'The Matrix'}, q


def test_two_person_parameters():
    r = route_question('Movies with both Tom Hanks and Meg Ryan')
    assert r.category == 'shared_movie'
    assert r.parameters == {'person1': 'Tom Hanks', 'person2': 'Meg Ryan'}
    r = route_question('Did Tom Hanks and Meg Ryan work together?')
    assert r.parameters == {'person1': 'Tom Hanks', 'person2': 'Meg Ryan'}


def test_year_ranges():
    assert route_question('Movies released in 1999').parameters == {'start': '1999', 'end': '1999'}
    assert route_question('Movies from the 90s').parameters == {'start': '1990', 'end': '1999'}
    assert route_question('Movies after 2000').parameters == {'start': '2001', 'end': '9999'}
    assert route_question('Movies before 1995').parameters == {'start': '0', 'end': '1994'}






def test_every_category_has_template_and_all_params_are_supplied():
    import re
    from rag.cypher_templates import TEMPLATES
    from rag.query_router import PARAMS_BY_CATEGORY
    assert set(PARAMS_BY_CATEGORY) <= set(TEMPLATES)
    for cat, params in PARAMS_BY_CATEGORY.items():
        used = set(re.findall(r'\$(\w+)', TEMPLATES[cat])) - {'limit'}
        assert used <= params, (cat, used, params)


def test_vague_question_still_falls_through_to_llm():
    assert route_question('Tell me about the movie Heat').confidence <= 0.7
    assert route_question('What is the weather?').category == 'unsupported'


def test_unsupported_topics_are_not_misrouted():
    for q in ('When was Tom Hanks born?', 'Was Tom Hanks born in 1956?', 'Who does Jessica Thompson follow?',
              'What role did Tom Hanks play in Apollo 13?', 'Who played Neo?', 'How old is Tom Hanks?'):
        assert route_question(q).category == 'unsupported', q
    assert route_question('Who played in The Matrix?').category == 'cast_discovery'


def test_non_actor_rankings_are_not_answered_with_actor_ranking():
    assert route_question('Who directed the most movies?').category == 'unsupported'
    assert route_question('Which actor appeared in the most movies?').category == 'top_actors'
