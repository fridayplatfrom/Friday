import json
from pathlib import Path
import socket
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import pytest

from expertos_bridge.experts import controls_map, plan, recovery, route, verify_values
from expertos_bridge.server import BridgeServer, Handler
from expertos_bridge.action_policy import train, predict, validate_records

TOKEN = 'a' * 48

@pytest.fixture
def server():
    with BridgeServer(('127.0.0.1', 0), TOKEN) as app:
        worker=threading.Thread(target=app.serve_forever,daemon=True)
        worker.start()
        yield f'http://127.0.0.1:{app.server_port}'
        app.shutdown()
        worker.join(timeout=2)

def request(url, path, obj=None, token=TOKEN, origin=False):
    body=json.dumps(obj).encode() if obj is not None else None
    headers={'Authorization':f'Bearer {token}'}
    if body is not None: headers['Content-Type']='application/json'
    if origin: headers['Origin']='https://attacker.invalid'
    return urlopen(Request(url+path,body,headers=headers),timeout=2)


def test_transport_auth_and_security(server):
    with pytest.raises(HTTPError) as err:
        request(server,'/v1/experts',token='wrong')
    assert err.value.code == 401
    with pytest.raises(HTTPError) as err:
        request(server,'/v1/experts',origin=True)
    assert err.value.code == 400
    with request(server,'/health') as response:
        assert json.load(response)['status']=='ok'
    with request(server,'/v1/experts') as response:
        data=json.load(response)
    assert any(x['id']=='form_mapper' and x['ready'] for x in data['experts'])
    assert any(x['id']=='browser_action_policy' and not x['ready'] for x in data['experts'])


def test_planner_and_route(server):
    with request(server,'/v1/plan',{'kind':'fill_form','url':'https://example.com/form','values':{'email':'me@example.com'}}) as response:
        result=json.load(response)
    assert result['status']=='planned' and result['auto_submit'] is False
    assert result['actions'][-1]['type']=='verify_fields'
    assert route({'task':'fill registration form'})['expert']=='form_mapper'
    assert route({'task':'play Beethoven music'})['status']=='abstained'
    assert plan({'kind':'submit', 'url':'https://example.com', 'values':{}})['status']=='abstained'


def test_form_mapping_ambiguity_sensitive_and_verification():
    fields=[{'index':0,'label':'Company name','id':'org','name':'org','type':'text','visible':True},
            {'index':1,'label':'Business email','type':'email','visible':True},
            {'index':2,'label':'Password','type':'password','visible':True}]
    result=controls_map({'controls':fields,'values':{'company':'Example Ltd','email':'hello@example.com','password':'secret'}})
    assert {m['key'] for m in result['matches']} == {'company','email'}
    assert result['unmatched']==[{'key':'password','reason':'sensitive_field_requires_manual_entry'}]
    assert not verify_values({'expected':{'email':'a'},'actual':{'email':'b'}})['verified']
    assert verify_values({'expected':{'email':'a'},'actual':{'email':'a'}})['verified']
    assert recovery({'error_code':'control_changed'})['next_action']=='reobserve_and_remap'
    ambiguous=controls_map({'controls':fields+[{'index':3,'label':'Business email','type':'email','visible':True}],
                            'values':{'email':'hi'}})
    assert ambiguous['status']=='abstained'


def test_source_read_without_library(server):
    with request(server,'/v1/source/read',{'document_id':'id','question':'what?'}) as response:
        result=json.load(response)
    assert result['status']=='source_library_unavailable'


def samples():
    rows=[]
    for split, site, count in [('train','site1',8),('validation','site2',3),('test','site3',3)]:
        for i in range(count):
            kind=('extract','navigate','fill_form','abstain')[i%4]
            rows.append({'task': f'{kind} page {site} {i}', 'context':f'form index {i}', 'site_id':site,
                         'case_id':f'{site}-{i}','split':split,'label':kind,
                         'reviewed':True,'reviewer':'unit_test_fixture'})
    return rows


def test_action_policy_guarded_training(tmp_path):
    rows=samples()
    assert len(validate_records(rows))==3
    report=train(rows,tmp_path/'weights',epochs=2)
    assert report['experimental'] and report['metrics']['test_count']==3
    assert predict(tmp_path/'weights','fill_form','form')['status']=='model_disabled'
    proposal=predict(tmp_path/'weights','fill_form','form',allow_experimental=True)
    assert proposal['status'] in ('abstained','experimental_proposal')
    assert proposal.get('action') in (None,'navigate','extract','fill_form')
    with open(tmp_path/'weights'/'policy.pt','ab') as f:f.write(b'bad')
    with pytest.raises(ValueError,match='checksum'):
        predict(tmp_path/'weights','fill_form','form',allow_experimental=True)


def test_action_policy_reject_leakage():
    rows=samples()
    rows[-1]['site_id']='site1'
    with pytest.raises(ValueError,match='leakage'):
        validate_records(rows)


def test_universal_7_core_bridge_endpoint(server):
    """Verify ExpertOS Harness Bridge /v1/universal endpoint and invoice/HSN synonym mapping."""
    fields = [
        {'index': 0, 'label': 'Invoice Number', 'id': 'inv_no', 'type': 'text', 'visible': True},
        {'index': 1, 'label': 'HSN Code', 'id': 'hsn_code', 'type': 'text', 'visible': True},
        {'index': 2, 'label': 'Taxable Amount', 'id': 'tax_amt', 'type': 'number', 'visible': True},
    ]
    mapped = controls_map({'controls': fields, 'values': {'invoice': 'INV-101', 'hsn': '8541', 'taxable': '50000'}})
    assert {m['key'] for m in mapped['matches']} == {'invoice', 'hsn', 'taxable'}

    with request(server, '/v1/universal', {'query': 'Write Python code for kinetic energy physics calculation'}) as response:
        res = json.load(response)
    assert res['status'] == 'completed'
    assert res['domain'] == 'coding_expert'
    assert res['result']['verification']['test_passed'] is True

