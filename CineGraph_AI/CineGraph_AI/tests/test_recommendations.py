from rag.recommendation_engine import _explain

def test_recommendation_explanation():
    assert '2 shared actors' in _explain({'sharedActors':2,'sharedDirectors':0})
    assert '1 shared director' in _explain({'sharedActors':0,'sharedDirectors':1})
