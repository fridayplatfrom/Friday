"""Source Studio and controlled automatic-training integration tests."""
import io
import tempfile
from pathlib import Path
import unittest

from tiny_experts.knowledge_services import EnhancedCore
from tiny_experts.knowledge_core.store import CoreError, AccessDenied
from tiny_experts.source_studio import TrainingDirector
from tiny_experts.source_studio.app import create_app
from fastapi.testclient import TestClient

TEXTS=[
 "Thermodynamic entropy: The state function captures reversible heat exchange over temperature.",
 "Thermodynamic entropy: This concept tracks reversible energy transfer per unit temperature.",
 "Thermodynamic entropy: The quantity is measured in joules per kelvin for a thermodynamic system."
]

class DirectorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.core=EnhancedCore(self.temp.name,actor='test-reviewer',curator=True,allow_network=False)
        self.core.bootstrap()
        self.director=TrainingDirector(self.core)
    def tearDown(self):
        self.core.close();self.temp.cleanup()
    def source(self,n,*,train=True):
        return self.core.import_text('entropy-'+str(n),'Entropy resource '+str(n),TEXTS[n],
             rights={'store':True,'retrieve':True,'train':train,'redistribute':False},
             license_note='Local test data; reviewer supplied for testing',family_id='family-'+str(n))
    def prepare(self,*,train=True):
        assignments={};results=[]
        for i in range(3):
            result=self.source(i,train=train)
            revision=result['revision_id']
            self.core.review(revision,decision='accepted',note='Validated synthetic integration fixture')
            candidates=self.director.propose(revision)
            matches=[x for x in self.director.candidates(revision=revision) if x['kind']=='span_qa']
            self.assertEqual(len(matches),1)
            self.director.review_candidate(matches[0]['id'],accept=True,note='Answer span matches fixture')
            assignments[matches[0]['annotation_id']]=('train','validation','test')[i]
            results.append((revision,matches[0]))
        return assignments,results
    def test_default_policy(self):
        self.assertEqual(self.director.policy()['mode'],'automatic_after_approval')
        self.assertFalse(self.director.policy()['auto_deployment'])
    def test_policy_modes(self):
        for m in ['manual','automatic_after_approval','research_auto']:
            self.director.set_policy(m)
            self.assertEqual(self.director.policy()['mode'],m)
    def test_reject_policy_unknown(self):
        with self.assertRaises(CoreError):self.director.set_policy('train_everything')
    def test_policy_needs_curator(self):
        self.core.curator=False
        with self.assertRaises(AccessDenied):self.director.set_policy('manual')
    def test_propose_and_review(self):
        rid=self.source(0)['revision_id'];result=self.director.propose(rid)
        self.assertGreaterEqual(result['created'],2)
        self.assertFalse(result['training_started'])
        self.assertEqual(len(self.director.jobs()),0)
        self.assertEqual(self.core.get(rid)['data']['review_state'],'unreviewed')
    def test_idempotent_proposal(self):
        rid=self.source(0)['revision_id'];self.director.propose(rid)
        self.assertEqual(self.director.propose(rid)['created'],0)
    def test_proposals_never_automatically_accepted(self):
        rid=self.source(0)['revision_id'];self.director.propose(rid)
        self.assertTrue(all(x['status']=='proposed' for x in self.director.candidates(revision=rid)))
    def test_review_candidate_requires_note(self):
        rid=self.source(0)['revision_id'];self.director.propose(rid)
        x=self.director.candidates(revision=rid)[0]
        with self.assertRaises(CoreError):self.director.review_candidate(x['id'],accept=True,note='')
    def test_review_candidate_idempotent_disallowed(self):
        rid=self.source(0)['revision_id'];self.director.propose(rid)
        x=self.director.candidates(revision=rid)[0]
        self.director.review_candidate(x['id'],accept=True,note='Reviewed text')
        with self.assertRaises(CoreError):self.director.review_candidate(x['id'],accept=True,note='Second')
    def test_reviewed_annotation(self):
        a,_=self.prepare()
        self.assertEqual(len(a),3)
        self.assertTrue(all(self.core.get(x)['data']['review_state']=='accepted' for x in a))
    def test_no_dataset_without_three_splits(self):
        a,_=self.prepare(); a.pop(next(iter(a)))
        with self.assertRaises(CoreError):self.director.release_dataset('broken',a)
    def test_train_permission_is_required(self):
        a,_=self.prepare(train=False)
        with self.assertRaises(AccessDenied):self.director.release_dataset('not-allowed',a)
    def test_auto_queues_after_approved_dataset(self):
        a,_=self.prepare()
        result=self.director.release_dataset('qa-v1',a,trainer='span_qa',config={'epochs':1,'seed':1})
        self.assertTrue(result['training_queued'])
        self.assertEqual(self.director.jobs()[0]['state'],'queued')
    def test_manual_never_auto_queues(self):
        self.director.set_policy('manual')
        a,_=self.prepare()
        result=self.director.release_dataset('qa-v2',a,trainer='span_qa',config={'epochs':1})
        self.assertFalse(result['training_queued'])
        self.assertFalse(self.director.jobs())
    def test_demo_does_not_auto_queue_without_research_authorization(self):
        a,_=self.prepare()
        self.assertFalse(self.director.release_dataset('demo',a,demo=True,trainer='span_qa',config={'epochs':1})['training_queued'])
    def test_research_auto_requires_preapproval(self):
        self.director.set_policy('research_auto',research_preapproved=False)
        a,_=self.prepare();self.assertFalse(self.director.release_dataset('demo',a,demo=True,trainer='span_qa',config={'epochs':1})['training_queued'])
    def test_research_auto_queues_preapproved_demo(self):
        self.director.set_policy('research_auto',research_preapproved=True)
        a,_=self.prepare()
        self.assertTrue(self.director.release_dataset('demo',a,demo=True,trainer='span_qa',config={'epochs':1})['training_queued'])
    def test_cannot_queue_wrong_trainer(self):
        a,_=self.prepare();r=self.director.release_dataset('qa',a)
        with self.assertRaises(CoreError):self.director.queue_job(r['dataset_id'],trainer='classification',config={})
    def test_cannot_queue_unapproved_trainer(self):
        a,_=self.prepare();r=self.director.release_dataset('qa',a)
        with self.assertRaises(CoreError):self.director.queue_job(r['dataset_id'],trainer='arbitrary_shell',config={})
    def test_worker_idle(self):
        self.assertEqual(self.director.worker_once()['status'],'idle')
    def test_worker_uses_actual_reviewed_rows(self):
        a,_=self.prepare();self.director.release_dataset('qa',a,trainer='span_qa',config={'epochs':1})
        observed=[]
        def trainer(job,rows,output):
            observed.append((job['trainer'],len(rows),{x['split'] for x in rows}))
            return {'status':'trained_in_fixture','validation_exact_match':0}
        result=self.director.worker_once(trainer_callback=trainer)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(observed,[('span_qa',3,{'train','validation','test'})])
        self.assertTrue(result['result']['experimental'])
        self.assertFalse(result['result']['deployment_approved'])
    def test_worker_blocks_revoked_source(self):
        a,results=self.prepare();self.director.release_dataset('qa',a,trainer='span_qa',config={'epochs':1})
        self.core.withdraw_source(results[0][0],reason='Revoked')
        r=self.director.worker_once(trainer_callback=lambda *args: self.fail('Trainer should never run'))
        self.assertEqual(r['status'],'failed')
    def test_source_revision_withdrawal_hides_suggestions(self):
        rid=self.source(0)['revision_id'];self.director.propose(rid)
        self.core.withdraw_source(rid,reason='Withdraw')
        self.assertFalse(self.director.candidates())
    def test_worker_requires_curator_for_job_enqueue(self):
        a,_=self.prepare();r=self.director.release_dataset('qa',a)
        self.core.curator=False
        with self.assertRaises(AccessDenied):self.director.queue_job(r['dataset_id'],trainer='span_qa',config={'epochs':1})

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.app=create_app(self.temp.name,token='n'*32,max_upload=3*1024*1024)
        self.client=TestClient(self.app)
        self.headers={'Authorization':'Bearer '+'n'*32}
    def tearDown(self):
        self.client.close();self.temp.cleanup()
    def test_ui_is_available(self):
        r=self.client.get('/');self.assertEqual(r.status_code,200);self.assertIn('Source Studio',r.text)
    def test_auth_required(self):
        self.assertEqual(self.client.get('/api/health').status_code,401)
    def test_auth_wrong_token_rejected(self):
        self.assertEqual(self.client.get('/api/health',headers={'Authorization':'Bearer wrong'}).status_code,401)
    def test_host_rejected(self):
        self.assertEqual(self.client.get('/api/health',headers={**self.headers,'Host':'attack.example'}).status_code,403)
    def test_cross_site_origin_rejected(self):
        self.assertEqual(self.client.post('/api/policy',headers={**self.headers,'Origin':'https://evil.example'},json={'mode':'manual'}).status_code,403)
    def test_cross_port_origin_rejected(self):
        self.assertEqual(self.client.post('/api/policy',headers={**self.headers,'Origin':'http://testserver:9181'},json={'mode':'manual'}).status_code,403)
    def test_health_reports_no_automatic_deploy(self):
        r=self.client.get('/api/health',headers=self.headers).json()
        self.assertFalse(r['automatic_deployment'])
    def test_upload_text_does_not_train(self):
        r=self.client.post('/api/sources/upload',headers=self.headers,
            data={'title':'Entropy sample','source_key':'entropy-test','license_note':'Synthetic local note'},
            files={'file':('entropy.txt',TEXTS[0].encode(),'text/plain')})
        self.assertEqual(r.status_code,200,r.text)
        data=r.json();self.assertFalse(data['training_started']);self.assertTrue(data['review_required'])
        self.assertGreaterEqual(data['segments'],1)
        j=self.client.get('/api/jobs',headers=self.headers).json();self.assertEqual(j,[])
    def test_search_after_upload(self):
        self.client.post('/api/sources/upload',headers=self.headers,
            data={'title':'Entropy source','source_key':'e1','license_note':'Synthetic'},
            files={'file':('e.txt',TEXTS[0].encode(),'text/plain')})
        r=self.client.get('/api/search',params={'q':'entropy'},headers=self.headers)
        self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.json())
    def test_bad_extension_rejected(self):
        r=self.client.post('/api/sources/upload',headers=self.headers,
            data={'title':'Bad','source_key':'bad','license_note':'Synthetic'},
            files={'file':('malware.exe',b'123','application/octet-stream')})
        self.assertEqual(r.status_code,400)
    def test_empty_file_rejected(self):
        r=self.client.post('/api/sources/upload',headers=self.headers,
            data={'title':'Empty','source_key':'empty','license_note':'Synthetic'},
            files={'file':('empty.txt',b'','text/plain')})
        self.assertEqual(r.status_code,400)
    def test_upload_bounded_by_content_length(self):
        r=self.client.post('/api/sources/upload',headers=self.headers,
            data={'title':'Large','source_key':'large','license_note':'Synthetic'},
            files={'file':('large.txt',b'a'*(4*1024*1024),'text/plain')})
        self.assertEqual(r.status_code,413)
    def test_policy_change(self):
        r=self.client.post('/api/policy',headers=self.headers,json={'mode':'manual','research_preapproved':False})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['mode'],'manual')
    def test_policy_rejects_unknown(self):
        r=self.client.post('/api/policy',headers=self.headers,json={'mode':'always-automatically-deploy'})
        self.assertEqual(r.status_code,400)
    def test_get_candidates(self):
        self.client.post('/api/sources/upload',headers=self.headers,
            data={'title':'Entropy source','source_key':'e1','license_note':'Synthetic'},
            files={'file':('e.txt',TEXTS[0].encode(),'text/plain')})
        c=self.client.get('/api/candidates',headers=self.headers)
        self.assertEqual(c.status_code,200);self.assertTrue(c.json())

if __name__=='__main__':unittest.main()

# Additional source-family split proposals and manual-annotation API checks.
def test_director_split_proposal_from_reviewed_sources(tmp_path):
    with EnhancedCore(tmp_path,actor='reviewer',curator=True) as core:
        core.bootstrap();d=TrainingDirector(core)
        for i in range(3):
            imported=core.import_text(f'topic-{i}',f'Book-{i}',TEXTS[i],
                rights={'store':True,'retrieve':True,'train':True,'redistribute':False},
                license_note='Synthetic original',family_id=f'family-{i}')
            core.review(imported['revision_id'],decision='accepted',note='Checked synthetic example')
            d.propose(imported['revision_id'])
            candidate=next(x for x in d.candidates(revision=imported['revision_id']) if x['kind']=='span_qa')
            d.review_candidate(candidate['id'],accept=True,note='Reviewed synthetic answer')
        result=d.suggest_splits(task='span_qa')
        assert result['status']=='proposal' and result['families']==3
        assert set(result['assignments'].values())=={'train','validation','test'}
        assert len(result['assignments'])==3
        assert not d.jobs()

def test_split_suggestion_without_three_sources(tmp_path):
    with EnhancedCore(tmp_path,actor='reviewer',curator=True) as core:
        core.bootstrap();d=TrainingDirector(core)
        r=d.suggest_splits(task='span_qa')
        assert r['status']=='insufficient_independent_sources'
        assert r['assignments']=={}

def test_manual_qa_exact_span_requires_review(tmp_path):
    with EnhancedCore(tmp_path,actor='reviewer',curator=True) as core:
        core.bootstrap();d=TrainingDirector(core)
        source=core.import_text('s','s','Entropy: A state function with a defined unit.',
            rights={'store':True,'retrieve':True,'train':True,'redistribute':False},license_note='Original')
        sid=core.edges(source['revision_id'],relation='segment_of',reverse=True)[0]['src']
        r=d.propose_manual_annotation(task='span_qa',segment_id=sid,case_id='q1',question='What is entropy?',answer='A state function')
        assert r['status']=='proposed' and r['review_required']
        assert core.get(r['annotation_id'])['data']['review_state']=='proposed'
        assert d.reviewed_annotations(task='span_qa')==[]
        with __import__('pytest').raises(CoreError):
            d.propose_manual_annotation(task='span_qa',segment_id=sid,case_id='q2',question='Wrong?',answer='Not in source')

def test_annotation_http_requires_auth_and_retains_proposed_status(tmp_path):
    client=TestClient(create_app(tmp_path,token='a'*32))
    headers={'Authorization':'Bearer '+'a'*32}
    up=client.post('/api/sources/upload',headers=headers,
        data={'title':'Entropy','source_key':'entropy','license_note':'Original local test'},
        files={'file':('entropy.txt',b'Entropy: A state function with a defined unit.','text/plain')})
    assert up.status_code==200,up.text
    with EnhancedCore(tmp_path,curator=True) as core:
        sid=core.edges(up.json()['revision_id'],relation='segment_of',reverse=True)[0]['src']
    payload={'task':'span_qa','segment_id':sid,'case_id':'new','question':'What is entropy?','answer':'A state function'}
    assert client.post('/api/annotations',json=payload).status_code==401
    r=client.post('/api/annotations',headers=headers,json=payload)
    assert r.status_code==200,r.text
    assert r.json()['status']=='proposed'
    assert client.get('/api/annotations',headers=headers).json()==[]
    assert client.get('/api/datasets/suggest-splits',headers=headers).json()['status']=='insufficient_independent_sources'


def test_self_improving_director_five_loops_and_telemetry(tmp_path):
    books = [
        (
            "tong-dynamics",
            "Classical Dynamics Notes",
            "family-tong",
            "classical_mechanics",
            "The Hamiltonian function is defined as the Legendre transform of the Lagrangian over generalized velocities. "
            "Noether’s theorem states that every differentiable symmetry of the action corresponds to a conserved current. "
            "The Poisson bracket governs the time evolution of observables in classical phase space.",
        ),
        (
            "carroll-gr",
            "Spacetime and Geometry",
            "family-carroll",
            "relativity_cosmology",
            "The Einstein field equations relate the spacetime Einstein curvature tensor to the stress-energy momentum tensor. "
            "A Schwarzschild metric is a static spherically symmetric vacuum solution to the gravitational field equations. "
            "The geodesic equation determines the trajectory of freely falling particles in curved spacetime.",
        ),
        (
            "crowell-quantum",
            "Light and Matter Quantum",
            "family-crowell",
            "quantum_mechanics",
            "The Schrodinger equation governs the unitary time evolution of a quantum mechanical wavefunction. "
            "Heisenberg’s uncertainty principle states that conjugate position and momentum observables cannot be simultaneously sharp.",
        ),
    ]
    with EnhancedCore(tmp_path, actor="reviewer", curator=True) as core:
        core.bootstrap()
        director = TrainingDirector(core)
        prev_concepts = 0
        for key, title, fam, sub, text_body in books:
            imp = core.import_text(
                key,
                title,
                text_body,
                rights={"store": True, "retrieve": True, "train": True, "redistribute": False},
                license_note="Curated physics test fixture",
                family_id=fam,
            )
            core.review(imp["revision_id"], decision="accepted", note="Approved physics book")
            step = director.teach_from_revision(
                imp["revision_id"],
                book_title=title,
                default_subdomain=sub,
            )
            assert step["concepts_known"] >= prev_concepts
            assert step["candidates_proposed"] >= 1
            assert step["candidates_accepted"] >= 1
            prev_concepts = step["concepts_known"]

        telemetry = director.learning_telemetry()
        assert telemetry["steps_completed"] == 3
        assert telemetry["total_concepts_known"] > 100
        assert any(p["pattern_id"].startswith("pat_induced_") for p in telemetry["patterns"])
        cls_splits = director.suggest_splits(task="classification")
        qa_splits = director.suggest_splits(task="span_qa")
        assert cls_splits["status"] == "proposal" and cls_splits["families"] == 3
        assert qa_splits["status"] == "proposal" and qa_splits["families"] == 3

