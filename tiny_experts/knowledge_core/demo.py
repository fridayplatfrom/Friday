"""Synthetic end-to-end acceptance demonstration; not scientific-model training."""
from .adapters import HarnessCoreAdapter


def run_demo(core):
    core.bootstrap()
    thermal=core.get('concept.thermodynamics')['id'];physics=core.get('concept.physics')['id']
    rights={'store':True,'retrieve':True,'train':False,'redistribute':False}
    body=('Synthetic test document. For this fixture the hot reservoir is 600 K and the cold reservoir is 300 K. '
          'The ideal reversible efficiency is computed as one minus cold temperature divided by hot temperature.')
    source=core.import_text('demo-thermal','Synthetic thermal fixture',body,rights=rights,
                           license_note='Original synthetic software test, not an authenticated textbook',concepts=[thermal,physics])
    hits=core.search('reservoir',concepts=[thermal])
    reference=core.evidence(hits[0]['segment_id'],quote='600 K')
    capability=core.declare_capability('demo.carnot',name='Demonstration Carnot calculator',task='calculate',
            concepts=[thermal],implemented=True,input_fields=('hot_k','cold_k'))
    def calculate(inputs):
        hot,cold=inputs['hot_k'],inputs['cold_k']
        if not (type(hot) in (int,float) and type(cold) in (int,float) and hot>cold>0):
            raise ValueError('Require hot > cold > 0 K')
        return {'efficiency':1-cold/hot,'assumptions':['Ideal reversible heat engine'],
                'neural_inference':False}
    core.bind(capability,calculate)
    result=core.execute(capability,{'hot_k':600,'cold_k':300},permissions=['local_compute'])
    # Two different senses of cell remain different concepts and both are returned.
    for concept,context in [('concept.biological_cell','biology'),('concept.spreadsheet_cell','spreadsheet')]:
        if not core.resolve_term('cell','en',concept=concept)['senses']:
            core.add_sense('cell','en',concept,context=context,provenance={'fixture':True})
    bridge=HarnessCoreAdapter(core)
    return {'counts':core.counts(),'source':source,'retrieval_count':len(hits),
            'evidence':reference,'calculation':result,'ambiguous_term':core.resolve_term('cell','en')['status'],
            'bridge_directory_count':len(bridge.handle('directory',{'task':'calculate'})),
            'neural_training_started':False,'real_world_accuracy_claim':False}
