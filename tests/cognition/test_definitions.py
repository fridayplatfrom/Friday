from tiny_experts.knowledge_core import KnowledgeCore,CoreError,AccessDenied
from tiny_experts.cognition import DefinitionLibrary
import pytest

@pytest.fixture
def db(tmp_path):
    with KnowledgeCore(tmp_path/'core',curator=True,actor='reviewer') as c:
        c.bootstrap();yield c,DefinitionLibrary(c)

def source(core,key,wording):
    rev=core.import_text(key,key,wording,rights={'store':True,'retrieve':True},
            license_note='Original synthetic fixture',concepts=['concept.thermodynamics'])
    seg=core.edges(rev['revision_id'],relation='segment_of',reverse=True)[0]['src']
    return rev['revision_id'],seg

def test_two_book_definition_retains_exact_sources_and_review(db):
    c,d=db
    a,aa=source(c,'book-a','Entropy is an extensive state variable in the specified context.')
    b,bb=source(c,'book-b','The thermodynamic entropy depends on the state and is measured in J/K.')
    definition=d.propose('concept.thermodynamics','In the applicable thermodynamic setting, entropy is a state quantity.',
          evidence_ids=[aa,bb],scope='Macroscopic equilibrium thermodynamics')
    with pytest.raises(AccessDenied):d.get(definition)
    with pytest.raises(CoreError,match='reviewed'):d.review(definition,accept=True,note='Reviewed the scientific scope')
    c.review(a,decision='accepted',note='Source reviewed');c.review(b,decision='accepted',note='Source reviewed')
    d.review(definition,accept=True,note='Meaning and limitations reviewed')
    entries=d.for_concept('concept.thermodynamics')
    assert entries[0]['independent_book_count']==2
    assert {ref['source_title'] for ref in entries[0]['references']}=={'book-a','book-b'}
    assert entries[0]['reviewer']=='reviewer'

def test_withdrawal_removes_definition_not_just_search_results(db):
    c,d=db
    a,aa=source(c,'book-a','Entropy is a state variable for thermodynamic systems.')
    c.review(a,decision='accepted',note='Fixture review')
    definition=d.propose('concept.thermodynamics','A context-specific thermodynamic state property.',
                          evidence_ids=[aa],scope='Equilibrium')
    d.review(definition,accept=True,note='Scientific review')
    assert len(d.for_concept('concept.thermodynamics'))==1
    c.withdraw_source(a,reason='Source access withdrawn')
    assert d.for_concept('concept.thermodynamics')==[]
    with pytest.raises(AccessDenied):d.get(definition)

def test_reject_definition_and_tenant_scope(db):
    c,d=db
    a,aa=source(c,'book','Entropy relates heat and reversible transfer.')
    definition=d.propose('concept.thermodynamics','Unreviewed text',evidence_ids=[aa],scope='Draft')
    d.review(definition,accept=False,note='Incorrect interpretation')
    assert d.for_concept('concept.thermodynamics')==[]
    with pytest.raises(CoreError):d.review(definition,accept=True,note='Cannot change decision')
    with KnowledgeCore(c.root,tenant='another',curator=False) as other:
        other_d=DefinitionLibrary(other)
        with pytest.raises(CoreError):other_d.get(definition,include_unreviewed=True)
