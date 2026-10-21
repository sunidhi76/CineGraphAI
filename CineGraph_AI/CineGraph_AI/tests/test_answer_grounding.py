from rag.answer_generator import AnswerGenerator

def test_empty_evidence_is_grounded():
    obj=AnswerGenerator.__new__(AnswerGenerator)
    result=obj.answer('Who directed X?', [])
    assert 'could not find relevant evidence' in result.lower()
