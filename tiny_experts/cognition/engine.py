"""Auditable, bounded cognitive workflow coordinator for ExpertOS.

No general language understanding or trained policy is claimed. Decisions use
operator-defined numeric criteria; sources can supply references, never authority.
Everything is tenant-scoped; action execution is delegated to the Knowledge Core.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import secrets
import json
from typing import Any

from ..knowledge_core.store import CoreError, AccessDenied, dumps, digest, now, text
from ..knowledge_core.runtime import order_steps

SCHEMA = '''
CREATE TABLE IF NOT EXISTS cognition_schema (version INTEGER PRIMARY KEY CHECK(version=1));
CREATE TABLE IF NOT EXISTS cognitive_goals (
 tenant TEXT NOT NULL, id TEXT NOT NULL, title TEXT NOT NULL, specification TEXT NOT NULL,
 created_at TEXT NOT NULL, PRIMARY KEY(tenant,id));
CREATE TABLE IF NOT EXISTS cognitive_state (
 tenant TEXT NOT NULL, scope TEXT NOT NULL, version INTEGER NOT NULL,
 snapshot TEXT NOT NULL, observed_at TEXT NOT NULL, PRIMARY KEY(tenant,scope));
CREATE TABLE IF NOT EXISTS cognitive_events (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL, goal_id TEXT,
 event_kind TEXT NOT NULL, event TEXT NOT NULL, recorded_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS cognition_events_tenant ON cognitive_events(tenant,goal_id,seq);
CREATE TABLE IF NOT EXISTS cognitive_skills (
 tenant TEXT NOT NULL, id TEXT NOT NULL, version INTEGER NOT NULL,
 name TEXT NOT NULL, steps TEXT NOT NULL, validation TEXT NOT NULL,
 active INTEGER NOT NULL, PRIMARY KEY(tenant,id));
'''

MAX_PAYLOAD = 64000


def _bounded(obj: Any, name: str, limit: int = MAX_PAYLOAD):
    try:
        raw = dumps(obj)
    except (ValueError, TypeError, OverflowError) as exc:
        raise CoreError(name + ' must contain finite JSON data') from exc
    if len(raw.encode('utf8')) > limit:
        raise CoreError(name + ' exceeds payload budget')
    return raw


def _string_list(items, name, limit=32):
    if not isinstance(items, list) or len(items)>limit or any(not isinstance(x,str) or not x.strip() or len(x)>256 for x in items):
        raise CoreError(name + ' must be a bounded list of strings')
    return items


class CognitiveEngine:
    """Trusted-process adapter; never expose curator=True to untrusted clients."""

    def __init__(self, core):
        self.core=core
        existing=core.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cognition_schema'").fetchone()
        if existing:
            versions=core.db.execute('SELECT version FROM cognition_schema').fetchall()
            if len(versions)!=1 or versions[0][0]!=1:
                raise CoreError('Unsupported cognition schema')
        core.db.executescript(SCHEMA)
        with core.transaction():
            core.db.execute('INSERT OR IGNORE INTO cognition_schema VALUES (1)')

    def _event(self,kind,payload,goal_id=None):
        self.core.db.execute('INSERT INTO cognitive_events(tenant,goal_id,event_kind,event,recorded_at) VALUES (?,?,?,?,?)',
            (self.core.tenant,goal_id,kind,_bounded(payload,'event'),now()))

    def goal(self,title,*,success,constraints=None,budget=None):
        text(title,'goal',256)
        success=_string_list(success,'success conditions',16)
        if not success: raise CoreError('Specify measurable success conditions')
        constraints=constraints or {}
        budget=budget or {'max_steps':16}
        if not isinstance(constraints,dict) or not isinstance(budget,dict):
            raise CoreError('Goal constraints and budget must be objects')
        steps=budget.get('max_steps',16)
        if type(steps) is not int or not 1<=steps<=32:
            raise CoreError('max_steps must be 1..32')
        spec={'success':success,'constraints':constraints,'budget':budget}
        _bounded(spec,'goal specification')
        ident='goal:'+secrets.token_hex(16)
        with self.core.transaction():
            self.core.db.execute('INSERT INTO cognitive_goals VALUES (?,?,?,?,?)',
                (self.core.tenant,ident,title,dumps(spec),now()))
            self._event('goal_created',{'title':title,'success':success},ident)
        return ident

    def get_goal(self,goal_id):
        row=self.core.db.execute('SELECT * FROM cognitive_goals WHERE tenant=? AND id=?',(self.core.tenant,goal_id)).fetchone()
        if not row:raise CoreError('Goal not found')
        return {'id':row['id'],'title':row['title'],**json.loads(row['specification'])}

    def observe(self,scope,snapshot,*,expected_version=None,source='trusted_observer'):
        text(scope,'scope',256);text(source,'observer',128)
        if not isinstance(snapshot,dict):raise CoreError('Snapshot must be a JSON object')
        raw=_bounded(snapshot,'observation')
        with self.core.transaction():
            old=self.core.db.execute('SELECT version FROM cognitive_state WHERE tenant=? AND scope=?',
               (self.core.tenant,scope)).fetchone()
            current=old['version'] if old else 0
            if expected_version is not None and (type(expected_version) is not int or expected_version!=current):
                raise CoreError('World-state version conflict')
            version=current+1
            self.core.db.execute('INSERT INTO cognitive_state VALUES (?,?,?,?,?) ON CONFLICT(tenant,scope) DO UPDATE SET version=excluded.version,snapshot=excluded.snapshot,observed_at=excluded.observed_at',
                (self.core.tenant,scope,version,raw,now()))
            self._event('state_observed',{'scope':scope,'version':version,'observer':source,'snapshot_sha256':digest(raw.encode())})
        return version

    def state(self,scope):
        row=self.core.db.execute('SELECT * FROM cognitive_state WHERE tenant=? AND scope=?',(self.core.tenant,scope)).fetchone()
        if not row: return {'scope':scope,'version':0,'snapshot':None}
        return {'scope':scope,'version':row['version'],'snapshot':json.loads(row['snapshot']),'observed_at':row['observed_at']}

    def compare(self,goal_id,options,*,weights,minimum_score=0.0,minimum_margin=0.0):
        """Transparent weighted decision, NOT a trained neural decision model.

        Scores must be operator/verified metric inputs, never model-generated permissions.
        Reversing options must preserve the selected underlying option.
        """
        self.get_goal(goal_id)
        if not isinstance(options,list) or not 2<=len(options)<=16 or not isinstance(weights,dict) or not weights:
            raise CoreError('Compare 2..16 options with criteria weights')
        if not all(isinstance(k,str) and k and type(w) in (int,float) and math.isfinite(w) and w>=0 for k,w in weights.items()) or sum(weights.values())<=0:
            raise CoreError('Weights must be finite nonnegative numbers')
        if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 or x>1 for x in (minimum_score,minimum_margin)):
            raise CoreError('Invalid decision thresholds')
        scored=[];ids=set()
        for option in options:
            if not isinstance(option,dict) or set(option)!={'id','metrics','allowed','evidence_ids'}:
                raise CoreError('Option requires id, metrics, allowed and evidence_ids')
            key=text(option['id'],'option',128)
            if key in ids:raise CoreError('Duplicate option')
            ids.add(key)
            if type(option['allowed']) is not bool:raise CoreError('Allowed must be a verified boolean')
            metrics=option['metrics']
            if not isinstance(metrics,dict) or set(metrics)!=set(weights):
                raise CoreError('Metrics must match weighted criteria')
            if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in metrics.values()):
                raise CoreError('Metrics must be normalized finite numbers')
            evidence=_string_list(option['evidence_ids'],'evidence IDs',20)
            for sid in evidence:
                proof=self.core.evidence(sid)
                self.core.require_source_use(proof['revision_id'],'retrieve')
            score=sum(weights[k]*metrics[k] for k in weights)/sum(weights.values())
            scored.append({'id':key,'allowed':option['allowed'],'score':round(score,10),'evidence_ids':evidence})
        allowed=sorted((r for r in scored if r['allowed']),key=lambda r:(-r['score'],r['id']))
        result={'status':'no_acceptable_option','selected':None,'candidates':sorted(scored,key=lambda r:r['id']),
                'decision_basis':'operator_supplied_normalized_metrics','is_neural':False}
        if allowed:
            if allowed[0]['score']<minimum_score:result['status']='below_minimum_quality'
            elif len(allowed)>1 and allowed[0]['score']-allowed[1]['score']<=minimum_margin:
                result['status']='ambiguous'
            else:result.update(status='selected',selected=allowed[0]['id'])
        _bounded(result,'decision result')
        with self.core.transaction():self._event('decision_recorded',result,goal_id)
        return result

    def plan(self,goal_id,steps,*,permissions=('local_compute',)):
        goal=self.get_goal(goal_id)
        ordered=order_steps(steps)
        if len(ordered)>goal['budget'].get('max_steps',16):raise CoreError('Plan exceeds goal step budget')
        _bounded(ordered,'plan')
        checked=[]
        for s in ordered:
            if set(s)-{'id','capability','inputs','depends_on','requires_approval'}:raise CoreError('Unsupported plan field')
            cap=self.core.get(s.get('capability'),'capability')
            health=self.core.capability_health(cap['id'])
            if not health['ready']:raise CoreError('Unbound or affected capability in plan')
            if not isinstance(s.get('inputs'),dict):raise CoreError('Every step needs explicit inputs')
            if not set(cap['data']['input_fields'])<=set(s['inputs']):raise CoreError('Required inputs missing')
            requires=set(cap['data']['permissions']); granted=set(permissions)
            if not requires<=granted:raise AccessDenied('Plan requests unauthorized capability')
            checked.append({'id':s['id'],'capability':cap['id'],'inputs':s['inputs'],
                            'depends_on':s.get('depends_on',[]),
                            'requires_approval':bool(requires & {'browser_submit','purchase','delete','external_write','shell'})})
        with self.core.transaction():self._event('plan_validated',{'steps':checked},goal_id)
        return {'goal_id':goal_id,'status':'validated','steps':checked,'safe_to_auto_execute':not any(s['requires_approval'] for s in checked)}

    def execute_plan(self,validated,*,permissions=('local_compute',),approvals=None,verify=None):
        if not isinstance(validated,dict) or validated.get('status')!='validated':raise CoreError('Validated plan required')
        goal_id=validated.get('goal_id');self.get_goal(goal_id)
        steps=validated.get('steps'); self.plan(goal_id,steps,permissions=permissions)  # re-check current capability health
        approvals=approvals or {}; outcomes={}; trace=[]
        for step in order_steps(steps):
            if any(outcomes.get(dep,{}).get('status')!='verified' for dep in step.get('depends_on',[])):
                trace.append({'step_id':step['id'],'status':'blocked_by_dependency'});break
            result=self.core.execute(step['capability'],step['inputs'],permissions=permissions,approval=approvals.get(step['id']))
            is_verified=False
            # Only trusted deterministic verifiers supplied by the host may confirm success.
            if verify is not None:
                if not callable(verify):raise CoreError('Verifier must be an explicit trusted callable')
                is_verified=verify(step,result) is True
            outcomes[step['id']]={'status':'verified' if is_verified else 'unverified','result':result}
            trace.append({'step_id':step['id'],'status':outcomes[step['id']]['status']})
            with self.core.transaction():self._event('step_executed',{'step_id':step['id'],'verified':is_verified},goal_id)
            if not is_verified: break
        return {'status':'verified' if len(trace)==len(steps) and all(x['status']=='verified' for x in trace) else 'incomplete',
                'results':outcomes,'trace':trace,'goal_id':goal_id}

    def register_skill(self,name,steps,*,validation_reference):
        self.core.require_curator();text(name,'skill name',256);text(validation_reference,'validation reference',4096)
        order_steps(steps);_bounded(steps,'skill steps')
        # Registered patterns are templates, never arbitrary executable Python.
        for item in steps:
            self.core.get(item.get('capability'),'capability')
        ident='skill:'+secrets.token_hex(16)
        with self.core.transaction():
            self.core.db.execute('INSERT INTO cognitive_skills VALUES (?,?,?,?,?,?,1)',
                (self.core.tenant,ident,1,name,dumps(steps),validation_reference))
            self._event('skill_registered',{'id':ident,'validation_reference':validation_reference})
        return ident

    def skill(self,ident):
        row=self.core.db.execute('SELECT * FROM cognitive_skills WHERE tenant=? AND id=? AND active=1',
                                 (self.core.tenant,ident)).fetchone()
        if not row:raise CoreError('Skill unavailable')
        return {'id':row['id'],'name':row['name'],'version':row['version'],'steps':json.loads(row['steps']),
                'validation_reference':row['validation']}

    def retire_skill(self,ident):
        self.core.require_curator();self.skill(ident)
        with self.core.transaction():
            self.core.db.execute('UPDATE cognitive_skills SET active=0,version=version+1 WHERE tenant=? AND id=?',
                                 (self.core.tenant,ident))
            self._event('skill_retired',{'id':ident})

    def history(self,*,goal_id=None,limit=100):
        if goal_id is not None:self.get_goal(goal_id)
        if type(limit) is not int or not 1<=limit<=500:raise CoreError('Invalid history limit')
        sql='SELECT seq,event_kind,event,recorded_at FROM cognitive_events WHERE tenant=?'
        args=[self.core.tenant]
        if goal_id:
            sql+=' AND goal_id=?';args.append(goal_id)
        rows=self.core.db.execute(sql+' ORDER BY seq DESC LIMIT ?',(*args,limit)).fetchall()
        return [{'seq':r['seq'],'kind':r['event_kind'],'details':json.loads(r['event']),'at':r['recorded_at']} for r in rows]

    def capability_choices(self,*,task,concept_ids=(),permissions=('local_compute',),only_ready=True):
        text(task,'task',128)
        candidates=self.core.discover(task=task,concepts=concept_ids,only_ready=only_ready)
        return [{'id':r['id'],'name':r['data']['name'],'ready':r['runtime']['ready'],
                 'permitted':set(r['data']['permissions'])<=set(permissions),
                 'evaluation_known':False} for r in candidates]

    @staticmethod
    def validate_gstin(gstin: str) -> dict:
        """Validate 15-character Indian GSTIN structure (State Code + PAN + Entity + Z + Checksum)."""
        import re
        clean = (gstin or "").strip().upper()
        pattern = r"^([0-3][0-9])([A-Z]{5}[0-9]{4}[A-Z])([1-9A-Z])Z([0-9A-Z])$"
        m = re.match(pattern, clean)
        if not m:
            return {"valid": False, "gstin": clean, "error": "Invalid 15-character GSTIN format."}
        return {
            "valid": True,
            "gstin": clean,
            "state_code": m.group(1),
            "pan": m.group(2),
            "entity_code": m.group(3),
            "check_digit": m.group(4),
        }

    def prepare_gst_return_workflow(
        self,
        *,
        supplier_gstin: str,
        return_period: str,
        invoices: list[dict],
        itc_available: float = 0.0,
    ) -> dict:
        """Core Pillar 5: GST Return Calculation, Field Mapping & Portal Action Plan."""
        sup_check = self.validate_gstin(supplier_gstin)
        if not sup_check["valid"]:
            raise CoreError(f"Supplier GSTIN invalid: {sup_check['error']}")
        sup_state = sup_check["state_code"]

        total_taxable = 0.0
        total_cgst = 0.0
        total_sgst = 0.0
        total_igst = 0.0
        processed_invoices = []

        for idx, inv in enumerate(invoices, start=1):
            b_gstin = str(inv.get("buyer_gstin") or "").strip().upper()
            b_check = self.validate_gstin(b_gstin)
            if not b_check["valid"]:
                raise CoreError(f"Invoice #{idx} buyer GSTIN invalid: {b_check['error']}")
            taxable = float(inv.get("taxable_value", 0.0))
            rate = float(inv.get("gst_rate", 18.0))
            if rate > 1.0:
                rate = rate / 100.0
            tax_amount = round(taxable * rate, 2)
            intra_state = b_check["state_code"] == sup_state
            cgst = round(tax_amount / 2.0, 2) if intra_state else 0.0
            sgst = round(tax_amount - cgst, 2) if intra_state else 0.0
            igst = 0.0 if intra_state else tax_amount

            total_taxable = round(total_taxable + taxable, 2)
            total_cgst = round(total_cgst + cgst, 2)
            total_sgst = round(total_sgst + sgst, 2)
            total_igst = round(total_igst + igst, 2)
            processed_invoices.append({
                "invoice_no": inv.get("invoice_no", f"INV-{idx:03d}"),
                "buyer_gstin": b_gstin,
                "supply_type": "INTRA_STATE" if intra_state else "INTER_STATE",
                "hsn_sac": inv.get("hsn_sac", "9983"),
                "taxable_value": taxable,
                "cgst": cgst,
                "sgst": sgst,
                "igst": igst,
                "invoice_total": round(taxable + cgst + sgst + igst, 2),
            })

        gross_tax_liability = round(total_cgst + total_sgst + total_igst, 2)
        itc_used = round(min(max(0.0, float(itc_available)), gross_tax_liability), 2)
        net_cash_payable = round(gross_tax_liability - itc_used, 2)

        ui_action_steps = [
            {"step": 1, "action": "navigate", "target": "gst_portal://returns/dashboard", "value": return_period},
            {"step": 2, "action": "fill_form", "target": "table_4A_b2b_invoices", "value": processed_invoices},
            {"step": 3, "action": "fill_form", "target": "gstr3b_table_3_1_outward_supplies", "value": {
                "taxable_value": total_taxable,
                "igst": total_igst,
                "cgst": total_cgst,
                "sgst": total_sgst,
            }},
            {"step": 4, "action": "fill_form", "target": "gstr3b_table_4_eligible_itc", "value": {"itc_applied": itc_used}},
            {"step": 5, "action": "await_human_commit", "target": "btn_preview_and_file_gstr3b", "requires_approval": True},
        ]
        summary = {
            "supplier_gstin": sup_check["gstin"],
            "return_period": return_period,
            "invoice_count": len(processed_invoices),
            "total_taxable_value": total_taxable,
            "total_cgst": total_cgst,
            "total_sgst": total_sgst,
            "total_igst": total_igst,
            "gross_tax_liability": gross_tax_liability,
            "itc_applied": itc_used,
            "net_cash_payable": net_cash_payable,
            "invoices": processed_invoices,
            "ui_action_plan": ui_action_steps,
            "requires_human_commit_gate": True,
        }
        with self.core.transaction():
            self._event("gst_workflow_prepared", {"period": return_period, "net_payable": net_cash_payable})
        return summary

    def compile_software_workflow(
        self,
        *,
        app_name: str,
        task_title: str,
        ui_schema: list[dict],
        field_values: dict,
    ) -> dict:
        """Core Pillar 5: Universal Software UI/DOM State-to-Action Workflow Compiler."""
        text(app_name, "app_name", 128)
        text(task_title, "task_title", 256)
        actions = []
        for idx, elem in enumerate(ui_schema, start=1):
            elem_id = str(elem.get("id") or f"elem_{idx}")
            role = str(elem.get("role") or "input").lower()
            field_key = elem.get("field_key") or elem_id
            if role in {"input", "textbox", "number"} and field_key in field_values:
                actions.append({
                    "step": len(actions) + 1,
                    "action": "fill_field",
                    "element_id": elem_id,
                    "value": field_values[field_key],
                    "post_condition": f"verify_element_value({elem_id})",
                    "requires_approval": False,
                })
            elif role in {"select", "dropdown"} and field_key in field_values:
                actions.append({
                    "step": len(actions) + 1,
                    "action": "select_option",
                    "element_id": elem_id,
                    "value": field_values[field_key],
                    "post_condition": f"verify_selected({elem_id})",
                    "requires_approval": False,
                })
            elif role in {"submit", "commit_button"}:
                actions.append({
                    "step": len(actions) + 1,
                    "action": "await_human_commit",
                    "element_id": elem_id,
                    "value": None,
                    "post_condition": "human_signature_verified",
                    "requires_approval": True,
                })
        result = {
            "app_name": app_name,
            "task_title": task_title,
            "steps_count": len(actions),
            "actions": actions,
            "safe_to_auto_execute": not any(a["requires_approval"] for a in actions),
        }
        with self.core.transaction():
            self._event("software_workflow_compiled", {"app_name": app_name, "steps_count": len(actions)})
        return result
