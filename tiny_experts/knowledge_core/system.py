"""Opt-in application facade using one registry for source and expert lookup."""
from . import KnowledgeCore
from .store import CoreError


class CoreExpertSystem:
    def __init__(self, core: KnowledgeCore, *, legacy=None):
        self.core=core
        self.core.bootstrap()
        self.legacy=legacy
        if legacy is not None:self.core.attach_legacy(legacy)

    @classmethod
    def from_repository(cls, core, repository, *, load_legacy=True):
        core.migrate_repository(repository)
        if load_legacy:
            from ..orchestrator import TinyExpertOrchestrator
            legacy=TinyExpertOrchestrator(allow_network=False,enable_reference_feeds=False)
        else:legacy=None
        return cls(core,legacy=legacy)

    def process(self, query, *, concept_ids=(), task=None, capability_id=None, permissions=('local_compute',)):
        """Choose by explicit operation and scope; never interpret source text as a plan."""
        if not isinstance(query,str) or not query.strip():raise CoreError('A question is required')
        evidence=self.core.search(query,concepts=concept_ids)
        if capability_id:
            options=[self.core.get(capability_id,'capability')]
        else:
            options=self.core.discover(task=task,concepts=concept_ids,only_ready=True) if task else []
        if not options:
            return {'status':'evidence_only' if evidence else 'unsupported','answer':None,'evidence':evidence,
                    'reason':'Specify a supported task/capability; no keyword fallback executes unrelated experts.'}
        if len(options)>1:
            return {'status':'ambiguous_capability','answer':None,'candidate_ids':[x['id'] for x in options],'evidence':evidence}
        cap=options[0]
        if concept_ids:
            requested={self.core.get(c,'concept')['id'] for c in concept_ids}
            if not requested.intersection(cap['data']['concept_ids']):raise CoreError('Capability is outside the requested concept scope')
        outcome=self.core.execute(cap['id'],{'query':query},permissions=permissions)
        return {'status':'executed','output':outcome,'evidence':evidence,
                'claims_independently_verified':False,'sources_automatically_trained':False}
