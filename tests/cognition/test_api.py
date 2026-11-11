"""Authenticated API integration smoke, no production deployment claims."""
import pytest
from tiny_experts.source_studio.app import create_app
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path):
    c=TestClient(create_app(tmp_path/'state',token='x'*32))
    return c,{'Authorization':'Bearer '+'x'*32}

def test_cognitive_api_auth_and_goal_state(client):
    c,auth=client
    assert c.get('/api/cognition/readiness').status_code==401
    assert c.get('/api/cognition/readiness',headers=auth).json()['cognition']['learned_planning_policy'] is False
    g=c.post('/api/cognition/goals',headers=auth,json={'title':'Check numerical result','success':['Correct computed answer']})
    assert g.status_code==200,g.text
    goal_id=g.json()['id']
    assert c.get('/api/cognition/goals/'+goal_id,headers=auth).json()['success']==['Correct computed answer']
    s=c.post('/api/cognition/observe',headers=auth,json={'scope':'session-test','snapshot':{'page':'homepage'},'expected_version':0})
    assert s.status_code==200
    assert c.get('/api/cognition/state',headers=auth,params={'scope':'session-test'}).json()['snapshot']['page']=='homepage'
    bad=c.post('/api/cognition/observe',headers=auth,json={'scope':'session-test','snapshot':{'page':'other'},'expected_version':0})
    assert bad.status_code==400
    options=[{'id':'a','metrics':{'quality':0.85},'allowed':True,'evidence_ids':[]},
             {'id':'b','metrics':{'quality':0.5},'allowed':True,'evidence_ids':[]}]
    r=c.post('/api/cognition/compare',headers=auth,json={'goal_id':goal_id,'options':options,'weights':{'quality':1}})
    assert r.status_code==200 and r.json()['selected']=='a'

def test_definition_api_no_silent_approval(client):
    c,auth=client
    r=c.get('/api/cognition/definitions',headers=auth,params={'concept_id':'concept.thermodynamics'})
    assert r.status_code==200 and r.json()==[]
    s=c.post('/api/cognition/definitions',headers=auth,json={'concept_id':'concept.thermodynamics',
        'wording':'Not a supported definition without evidence', 'scope':'Testing', 'evidence_ids':[]})
    assert s.status_code==400
