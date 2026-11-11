"""Cognitive orchestration invariants and integration with shared rights/registry."""
import pytest
from tiny_experts.knowledge_core import KnowledgeCore,CoreError,AccessDenied
from tiny_experts.cognition import CognitiveEngine

@pytest.fixture
def setup(tmp_path):
    with KnowledgeCore(tmp_path/'core',curator=True,actor='reviewer') as core:
        core.bootstrap()
        yield core,CognitiveEngine(core)

def ready(core,alias='compute.demo',permissions=('local_compute',)):
    cid=core.declare_capability(alias,name='Demonstration',task='calculate',implemented=True,
        lifecycle='implemented',permissions=permissions,input_fields=('value',))
    core.bind(cid,lambda inp:{'computed':inp['value']*2})
    return cid

def goal(c):return c.goal('Double an input',success=['Verify that the computed output is twice the input'])

def test_goal_and_state_persist_and_optimistic_version(setup):
    core,c=setup
    g=goal(c)
    assert c.get_goal(g)['success']
    assert c.observe('browser:session',{'url':'https://example.org/'},expected_version=0)==1
    with pytest.raises(CoreError,match='conflict'):c.observe('browser:session',{'url':'https://evil.example/'},expected_version=0)
    assert c.state('browser:session')['snapshot']['url']=='https://example.org/'
    assert c.history(goal_id=g)[0]['kind']=='goal_created'
    with KnowledgeCore(core.root,curator=True) as reopened:
        other=CognitiveEngine(reopened)
        assert other.state('browser:session')['version']==1
        assert other.get_goal(g)['title']=='Double an input'

def test_json_limits_nan_and_goal_validation(setup):
    _,c=setup
    with pytest.raises(CoreError):c.goal('bad',success=[])
    with pytest.raises(CoreError):c.goal('bad',success=['test'],budget={'max_steps':0})
    with pytest.raises(CoreError):c.observe('scope',{'x':float('nan')})
    with pytest.raises(CoreError):c.observe('scope',{'x':'a'*64000})

def test_comparator_is_order_invariant_and_abstains(setup):
    _,c=setup;g=goal(c)
    a={'id':'option-a','metrics':{'quality':.9,'efficiency':.5},'allowed':True,'evidence_ids':[]}
    b={'id':'option-b','metrics':{'quality':.6,'efficiency':.9},'allowed':True,'evidence_ids':[]}
    weights={'quality':3,'efficiency':1}
    assert c.compare(g,[a,b],weights=weights)['selected']=='option-a'
    assert c.compare(g,[b,a],weights=weights)['selected']=='option-a'
    assert c.compare(g,[a,b],weights=weights,minimum_margin=.5)['status']=='ambiguous'
    assert c.compare(g,[a,b],weights=weights,minimum_score=.95)['status']=='below_minimum_quality'
    assert c.compare(g,[{**a,'allowed':False},{**b,'allowed':False}],weights=weights)['status']=='no_acceptable_option'
    with pytest.raises(CoreError):c.compare(g,[a,a],weights=weights)
    with pytest.raises(CoreError):c.compare(g,[a,{**b,'metrics':{'quality':float('nan'),'efficiency':.1}}],weights=weights)

def test_comparator_rejects_withdrawn_evidence(setup):
    core,c=setup;g=goal(c)
    s=core.import_text('q','Question','Entropy measures a physical quantity.',rights={'store':True,'retrieve':True},
                license_note='Synthetic data')
    sid=core.edges(s['revision_id'],relation='segment_of',reverse=True)[0]['src']
    item={'id':'a','metrics':{'quality':1.0},'allowed':True,'evidence_ids':[sid]}
    other={'id':'b','metrics':{'quality':0.5},'allowed':True,'evidence_ids':[]}
    assert c.compare(g,[item,other],weights={'quality':1})['selected']=='a'
    core.withdraw_source(s['revision_id'],reason='Retired for test')
    with pytest.raises((CoreError,AccessDenied)):c.compare(g,[item,other],weights={'quality':1})

def test_plan_execute_and_no_unverified_dependency_progress(setup):
    core,c=setup; cap=ready(core);g=goal(c)
    steps=[{'id':'step1','capability':cap,'inputs':{'value':7},'depends_on':[]},
           {'id':'step2','capability':cap,'inputs':{'value':8},'depends_on':['step1']}]
    plan=c.plan(g,steps)
    assert plan['safe_to_auto_execute']
    assert c.execute_plan(plan)['status']=='incomplete'
    good=c.execute_plan(plan,verify=lambda s,out:out['result']['computed']==s['inputs']['value']*2)
    assert good['status']=='verified' and len(good['trace'])==2
    assert c.history(goal_id=g)[0]['kind']=='step_executed'
    with pytest.raises(CoreError):c.plan(g,[{'id':'x','capability':cap,'inputs':{},'depends_on':[]}])
    with pytest.raises(CoreError):c.plan(g,[{'id':'x','capability':cap,'inputs':{'value':2},'depends_on':['missing']}])

def test_sensitive_requires_approval_and_exact_inputs(setup):
    core,c=setup
    cap=ready(core,alias='browser.demo',permissions=('local_compute','browser_submit'))
    g=goal(c)
    step=[{'id':'submit','capability':cap,'inputs':{'value':3}}]
    with pytest.raises(AccessDenied):c.plan(g,step)
    plan=c.plan(g,step,permissions=('local_compute','browser_submit'))
    assert plan['safe_to_auto_execute'] is False
    with pytest.raises(AccessDenied):c.execute_plan(plan,permissions=('local_compute','browser_submit'),verify=lambda *_:True)
    token=core.approve_action(cap,{'value':3})
    out=c.execute_plan(plan,permissions=('local_compute','browser_submit'),approvals={'submit':token},verify=lambda *_:True)
    assert out['status']=='verified'
    with pytest.raises(AccessDenied):c.execute_plan(plan,permissions=('local_compute','browser_submit'),approvals={'submit':token},verify=lambda *_:True)

def test_skill_review_and_tenant_isolation(setup):
    core,c=setup;cap=ready(core);g=goal(c)
    steps=[{'id':'a','capability':cap,'inputs':{'value':5}}]
    skill=c.register_skill('Multiply',steps,validation_reference='passed-fixture:123')
    assert c.skill(skill)['name']=='Multiply'
    with KnowledgeCore(core.root,curator=False,tenant='other') as secondary:
        d=CognitiveEngine(secondary)
        with pytest.raises(CoreError):d.skill(skill)
        with pytest.raises(CoreError):d.get_goal(g)
        with pytest.raises(CoreError):d.retire_skill(skill)
    c.retire_skill(skill)
    with pytest.raises(CoreError):c.skill(skill)

def test_model_free_capability_router_only_ready_and_allowed(setup):
    core,c=setup;ready(core)
    choices=c.capability_choices(task='calculate')
    assert len(choices)==1 and choices[0]['permitted']
    assert c.capability_choices(task='unknown')==[]
