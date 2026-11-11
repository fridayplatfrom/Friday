"""Compatibility adapters; existing code remains usable without migrating data."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
import json
import re
from .store import CoreError, AccessDenied, digest, dumps, now


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[];self.title=[];self.description=None;self.block=0;self.in_title=False
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','template'}:self.block+=1
        if tag=='title':self.in_title=True
        attrs=dict(attrs)
        if tag=='meta' and attrs.get('name','').casefold()=='description':self.description=attrs.get('content')
        if tag in {'p','div','br','h1','h2','h3','tr','td','th','li'}:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'p','div','h1','h2','h3','tr','td','th','li','title'}:self.parts.append('\n')
        if tag in {'script','style','template'}:self.block=max(0,self.block-1)
        if tag=='title':self.in_title=False
    def handle_data(self,data):
        if self.in_title:self.title.append(data)
        if not self.block:self.parts.append(data)


class Adapters:
    def bootstrap(self):
        """Idempotently import the proposed concept seed, never scientific truth."""
        compact=json.loads((Path(__file__).parent/'data'/'seed.json').read_text(encoding='utf-8'))
        if compact.get('format')!='expertos-seed-v1':raise CoreError('Unsupported concept seed format')
        nodes=[{'id':'urn:expertos:concept:'+id,'label':label} for id,label in compact['concepts']]
        seed={'concepts':{'nodes':nodes,'edges':[
            {'from':nodes[a]['id'],'relation':rel,'to':nodes[b]['id']} for a,rel,b in compact['edges']]},
            'migration':{'core_experts':[
                {'existing_id':'expert.'+key,'legacy_route_key':key,'role':role,
                 'proposed_concept_ids':[nodes[i]['id'] for i in indices]}
                for key,role,indices in compact['experts']]}}
        from collections import Counter
        label_counts=Counter(re.sub('[^a-z0-9]+','_',c['label'].casefold()).strip('_') for c in seed['concepts']['nodes'])
        with self.transaction():
            for concept in seed['concepts']['nodes']:
                if not self.maybe(concept['id']):
                    alias='concept.'+re.sub('[^a-z0-9]+','_',concept['label'].casefold()).strip('_')
                    if label_counts[alias.removeprefix('concept.')]>1:
                        alias+='.'+concept['id'][-8:]
                    self.add_concept({'en':concept['label']},id=concept['id'],alias=alias,
                                     scope='Illustrative navigation concept; not validated expertise')
            for edge in seed['concepts']['edges']:
                if edge['relation'] in {'broader','related_to'}:
                    self.link(edge['from'],edge['relation'],edge['to'],provenance='architecture_blueprint_v0.1')
            from ..capability_registry import load_catalog
            catalog = {e['id']: e for e in load_catalog()['entries']}
            component_names = {key: entry['name'] for key, entry in catalog.items()}
            mapping={x['existing_id']:x for x in seed['migration']['core_experts']}
            for alias,info in mapping.items():
                capability = self.declare_capability(alias,name=component_names.get(alias, alias.split('.')[-1].replace('_',' ').title()),task=info['role'],
                        concepts=info['proposed_concept_ids'],implemented=True,lifecycle='implemented',
                        implementation={'legacy_route_key':info['legacy_route_key'],'kind':'legacy_adapter'},
                        input_fields=('query',))
                current = self.get(capability)
                historical_names = {alias.split('.')[-1].replace('_', ' ').title(), catalog.get(alias, {}).get('legacy_name')}
                if current['data']['name'] in historical_names and alias in component_names:
                    self._change(capability, data={**current['data'], 'name': component_names[alias]})
            self._audit('blueprint_migrated',None,concept_count=len(seed['concepts']['nodes']),
                        expert_aliases=len(mapping))
        return self.counts()

    def migrate_repository(self, repository):
        """Read-only legacy migration, repeatable; leaves source files untouched."""
        root=Path(repository).resolve();data=root/'tiny_experts'/'data'
        if not data.is_dir():raise CoreError('Repository data directory missing')
        self.bootstrap()
        summary={'capability_records':0,'book_metadata':0,'websites':0,'lexical_senses':0,'source_documents':0,'other_source_records':0}
        with self.transaction():
            registry=data/'expert_registry.json'
            if registry.is_file():
                contents=json.loads(registry.read_text(encoding='utf-8'))
                for entry in contents.get('entries',[]):
                    alias=entry['id']
                    if self.maybe(alias):continue
                    kind=entry.get('kind',entry.get('entry_type','unknown'))
                    if kind in {'neural_model','support_service'}:
                        self.add_entity(entry.get('name',alias),'model_architecture' if kind=='neural_model' else kind,
                                        alias=alias,metadata={'legacy':entry,'deployment':'not_observed'})
                    else:
                        self.declare_capability(alias,name=entry.get('name',alias),task=entry.get('task','unspecified'),
                             implemented=False,lifecycle='planned' if kind=='planned' else 'declared',
                             permissions=entry.get('required_permissions',['local_compute']),
                             implementation={'legacy':entry,'catalog_kind':kind})
                    summary['capability_records']+=1
            catalog=data/'sources'/'catalog'
            books=catalog/'universal_book_catalog.json'
            if books.is_file():
                for item in json.loads(books.read_text(encoding='utf-8')):
                    key='legacy-book:'+str(item.get('book_id'))
                    if self.maybe('source:'+key):continue
                    shelf=item.get('associated_shelf') or item.get('discipline')
                    concepts=self._shelf_concepts(shelf)
                    artifact_id=self.register_source(key,item.get('title') or 'Untitled legacy record',source_type='book',
                        language=item.get('language_primary') or 'und',edition_label=item.get('edition'),
                        metadata={'legacy_metadata':item,'metadata_verified':False,'content_acquired':False},concept_ids=concepts)
                    self._alias('book:'+str(item.get('book_id')),self.get(artifact_id)['data']['work_id'])
                    summary['book_metadata']+=1
            sites=catalog/'universal_web_directory.json'
            if sites.is_file():
                for site in json.loads(sites.read_text(encoding='utf-8')):
                    self.add_website(site['url'],site.get('title') or site['url'],metadata={'legacy':site,'authority_verified':False})
                    summary['websites']+=1
            lexicon=catalog/'multilingual_lexicon_dictionary.json'
            if lexicon.is_file():
                for word in json.loads(lexicon.read_text(encoding='utf-8')):
                    term=word.get('term')
                    if not term:continue
                    key='legacy-term:'+term
                    if self.maybe(key):continue
                    concept=self.add_concept({'en':term},alias=key,scope='Unreviewed imported dictionary claim')
                    english=self.add_sense(term,'en',concept,provenance={'legacy':word})
                    for lang,form in word.get('multilingual_translations',{}).items():
                        if isinstance(form,str) and form.strip():
                            sid=self.add_sense(form,lang,concept,provenance={'legacy_term':term})
                            self.align_translation(english,sid,method='legacy_dictionary_unreviewed')
                    summary['lexical_senses']+=1
            # In-memory legacy notes remain unreviewed and not training-permitted.
            # A catalog entry is not acquisition: actual note files get separate identities.
            booksdir=data/'sources'/'books'
            if booksdir.is_dir():
                for path in sorted(booksdir.glob('*/*')):
                    if path.suffix.lower() not in {'.txt','.md','.json'} or path.stat().st_size>8*1024*1024:continue
                    if path.is_symlink() or not path.resolve().is_relative_to(root):continue
                    relative=path.relative_to(root).as_posix();raw=path.read_bytes()
                    if path.suffix=='.json':
                        records=json.loads(raw)
                        if not isinstance(records,list):continue
                        body='\n\n'.join(str(r['text']) for r in records if isinstance(r,dict) and isinstance(r.get('text'),str))
                    else:body=raw.decode('utf-8-sig')
                    if not body.strip():continue
                    artifact=self.register_source('legacy-file:'+relative,path.name,
                            metadata={'legacy_path':relative,'original_citations_verified':False},
                            concept_ids=self._shelf_concepts(path.parent.name))
                    self.ingest(artifact,raw,extracted_text=body,rights={'store':True,'retrieve':True},
                                license_note='Existing local source; training and redistribution not authorized by migration',
                                extraction_method='legacy-note-migration-v1',concept_ids=self._shelf_concepts(path.parent.name))
                    summary['source_documents']+=1
            # Preserve the remaining directories as catalog/reference observations,
            # never as acquired recordings, fresh news, verified reviews or live prices.
            remaining=list(catalog.glob('*.json')) if catalog.is_dir() else []
            done={'universal_book_catalog.json','universal_web_directory.json','multilingual_lexicon_dictionary.json'}
            for folder in ('blogs','news','economics','demonstrations','decision_trees'):
                base=data/'sources'/folder
                if base.is_dir():remaining.extend(base.rglob('*.json'))
            for path in sorted(remaining):
                if path.parent==catalog and path.name in done:continue
                if path.is_symlink() or not path.resolve().is_relative_to(root) or path.stat().st_size>8*1024*1024:continue
                raw=path.read_bytes();payload=json.loads(raw)
                relative=path.relative_to(root).as_posix()
                artifact=self.register_source('legacy-records:'+relative,path.name,source_type='legacy_records',
                    metadata={'legacy_path':relative,'live_fetch_performed':False,'external_media_acquired':False})
                self.ingest(artifact,raw,media_type='application/json',extracted_text=dumps(payload),
                    rights={'store':True,'retrieve':True},license_note='Existing local metadata; training and redistribution not authorized by migration',
                    extraction_method='legacy-records-json-v1')
                summary['other_source_records']+=1
            self._audit('legacy_migration',None,**summary)
        return summary

    def _shelf_concepts(self,shelf):
        aliases={'pathology':'expert.pathology','toxicology':'expert.toxicity','marine':'expert.marine',
                 'evolution':'expert.evolution','communication':'expert.communicator',
                 'physics':'concept.physics','literature':'concept.literature','grammar':'concept.grammar'}
        record=self.maybe(aliases.get(shelf,'expert.'+str(shelf)))
        if not record:return []
        return [record['id']] if record['kind']=='concept' else record['data'].get('concept_ids',[])

    def attach_legacy(self, orchestrator):
        """Explicit opt-in to core-backed retrieval and registry dispatch.

        Keep old entry points intact. This method binds existing routines;
        it does not mark their scientific content reviewed or models trained.
        """
        self.bootstrap();view=CoreBookView(self)
        old=getattr(orchestrator,'book_engine',None)
        if old is not None and hasattr(old,'close'):old.close()
        orchestrator.book_engine=view
        catalog=CoreCatalogView(self)
        if hasattr(orchestrator,'catalog_engine'):orchestrator.catalog_engine=catalog
        attached=[]
        for key,expert in orchestrator.experts.items():
            if hasattr(expert,'book_engine'):expert.book_engine=view
            if hasattr(expert,'catalog_engine'):expert.catalog_engine=catalog
            cap=self.maybe('expert.'+key)
            if cap:
                if key=='vision' and getattr(expert,'leaf_model',None) is None:
                    continue
                self.bind(cap['id'],lambda context, expert=expert:expert.evaluate(context))
                attached.append(key)
        return {'bound':attached,'source_backend':'knowledge_core','legacy_process_router_unchanged':True}

    def snapshot_page(self,page,html,*,rights,license_note,concepts=()):
        record=self.get(page,'page')
        if not isinstance(html,bytes) or len(html)>8*1024*1024:raise CoreError('HTML snapshot exceeds budget')
        parser=PlainHTML();parser.feed(html.decode('utf-8-sig'))
        body=' '.join(''.join(parser.parts).split())
        if not body:raise CoreError('Page has no extractable static text')
        title=''.join(parser.title).strip() or record['data']['url']
        with self.transaction():
            artifact=self.register_source('page:'+record['id'],title,source_type='web_page',concept_ids=concepts)
            result=self.ingest(artifact,html,media_type='text/html',extracted_text=body,
                 rights=rights,license_note=license_note,concept_ids=concepts,extraction_method='static-html-v1',
                 metadata={'url':record['data']['url'],'observed_title':title,'observed_description':parser.description,
                           'observed_at':now(),'dynamic_page_executed':False})
            self._edge(result['revision_id'],'snapshot_of',record['id'])
            return result

    def fetch_text(self,url,*,source_key,title,rights,license_note,allow_network=False,concepts=()):
        if not allow_network:raise AccessDenied('Network access is disabled')
        from ..pipeline.source_fetch import fetch_public_text
        fetched=fetch_public_text(url)
        if fetched['status']!='downloaded':return {'status':'source_failed','receipt':fetched['receipt'],'indexed':False}
        with self.transaction():
            artifact=self.register_source(source_key,title,source_type='web_document',concept_ids=concepts)
            result=self.ingest(artifact,fetched['text'].encode(),rights=rights,license_note=license_note,
                 concept_ids=concepts,metadata={'fetch_receipt':fetched['receipt'],'original_response_bytes_preserved':False},
                 extraction_method='legacy-fetch-decoded-utf8-v1')
        return {**result,'status':'indexed','receipt':fetched['receipt']}

    def report_html(self):
        groups=[('Subjects','concept'),('Dictionary senses','lexical_sense'),('Translation alignments','translation'),
                ('Source works','work'),('Source revisions','revision'),('Evidence segments','segment'),('Claims','claim'),
                ('Capabilities','capability'),('Entities','entity'),('Websites','website'),('Pages','page'),
                ('Offers','offer'),('Annotations','annotation'),('Datasets','dataset'),('Models','model'),
                ('Evaluations','evaluation'),('Workflows','workflow'),('Jobs','job')]
        sections=[]
        for title,kind in groups:
            rows=self.records(kind,include_inactive=True)
            cells=[]
            for row in rows:
                data=row['data'];name=data.get('name') or data.get('title') or data.get('labels',{}).get('en') or data.get('form') or row['id']
                extra=self.capability_health(row['id'])['reason'] if kind=='capability' else data.get('review_state','not applicable')
                cells.append('<tr><td>'+escape(str(name))+'</td><td>'+escape(row['status'])+'</td><td>'+escape(str(extra))+'</td><td><code>'+escape(row['id'])+'</code></td></tr>')
            sections.append('<section><h2>'+escape(title)+' ('+str(self.counts().get(kind,0))+')</h2><table><thead><tr><th>Name / ID</th><th>Lifecycle</th><th>Review / runtime</th><th>Stable ID</th></tr></thead><tbody>'+''.join(cells)+'</tbody></table></section>')
        return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ExpertOS Knowledge Core</title>
<style>body{font:16px system-ui;margin:2rem;max-width:1500px}input{padding:.7rem;width:95%}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid #ccc;text-align:left;padding:.6rem;vertical-align:top}code{overflow-wrap:anywhere}section{margin:2rem 0}header{padding:1rem;background:#eef3f7}</style>
<header><h1>ExpertOS Knowledge Core</h1><p>Local tenant snapshot. Catalog presence is not expertise. Model approval, source review and live deployment are separate.</p></header>
<p>Filter the visible rows. Up to 1,000 records per type; use the API for pagination.</p><input id="q" placeholder="Find a concept, expert, source or status" aria-label="Filter registry">
'''+''.join(sections)+'''<script>document.getElementById('q').addEventListener('input',e=>{let q=e.target.value.toLocaleLowerCase();document.querySelectorAll('tbody tr').forEach(r=>{r.hidden=!r.textContent.toLocaleLowerCase().includes(q)})})</script></html>'''


class CoreBookView:
    """Legacy search interface, backed by the core's policy-aware incremental index."""
    def __init__(self,core):self.core=core;self.data_dir=str(core.root)
    def search(self,query,shelf=None,top_k=2,*,document_id=None):
        concepts=self.core._shelf_concepts(shelf) if shelf else []
        if shelf and not concepts:return []
        if not query or top_k<=0:return []
        revision=None
        if document_id:
            row=self.core.maybe(document_id)
            if not row:return []
            revision=row['data'].get('current_revision') if row['kind']=='artifact' else row['id']
            if not revision:return []
        return [{'passage_id':r['segment_id'],'document_id':r['revision_id'],'text':r['text'],
                 'source':self.core.get(r['revision_id'])['data']['title'],'shelf':shelf,
                 'citation':None,'verification_status':'source_consistency_only','review_status':r['review_state'],
                 'content_hash':r['text_sha256'],'score':r['rank'],'source_type':'knowledge_core'}
                for r in self.core.search(query,concepts=concepts,revision=revision,top_k=top_k)]
    def get_passage(self,id):
        try:p=self.core.evidence(id)
        except CoreError:return None
        return {'passage_id':id,'document_id':p['revision_id'],'text':p['text'],'content_hash':p['text_sha256']}
    def verify_passage(self,id):
        p=self.core.evidence(id)
        return {'passage_id':id,'document_id':p['revision_id'],'source_revision':p['text_sha256'],
                'verified_text_offsets':[p['selector'].get('start'),p['selector'].get('end')],
                'source_consistency':True,'semantic_support':'not_evaluated'}
    def lookup_document(self,id,query,top_k=3):
        if not self.core.maybe(id):return {'status':'document_not_found','passages':[],'answer':None}
        passages=self.search(query,top_k=top_k,document_id=id)
        return {'status':'retrieved' if passages else 'no_matching_evidence','passages':passages,'answer':None}
    def close(self):pass


class HarnessCoreAdapter:
    """Typed Python side of the Harness bridge; no browser authority is granted.

    Host integration must authenticate callers before constructing this adapter.
    No source, webpage or model response may choose the tenant or permissions.
    """
    def __init__(self,core,permissions=('local_compute',)):
        self.core=core;self.permissions=frozenset(permissions)
    def handle(self,operation,payload):
        if not isinstance(payload,dict):raise CoreError('Payload must be an object')
        if operation=='directory':return self.core.discover(task=payload.get('task'),concepts=payload.get('concepts',[]))
        if operation=='lookup':return self.core.resolve_term(payload['form'],payload['language'],concept=payload.get('concept'))
        if operation=='search':return self.core.search(payload['query'],concepts=payload.get('concepts',[]))
        if operation=='evidence':return self.core.evidence(payload['segment_id'])
        if operation=='execute':return self.core.execute(payload['capability_id'],payload.get('inputs',{}),permissions=self.permissions)
        raise CoreError('Operation is not exposed to the Harness bridge')


class CoreCatalogView:
    """Read-only legacy bibliographic interface, using shared work identities."""
    def __init__(self,core):self.core=core
    def _entry(self,work):
        data=work['data'];legacy=data.get('metadata',{}).get('legacy_metadata',{})
        available=False
        for edition in self.core.edges(work['id'],relation='edition_of',reverse=True):
            for artifact in self.core.edges(edition['src'],relation='representation_of',reverse=True):
                rid=self.core.get(artifact['src'])['data'].get('current_revision')
                if rid:
                    try:self.core.require_source_use(rid,'retrieve');available=True
                    except CoreError:pass
        return {**legacy,'book_id':work['id'],'title':data['title'],'authors':legacy.get('authors',[]),
                'content_available':available,'verification_status':'unverified','review_status':'unreviewed',
                'authority_tier':'UNVERIFIED','source_type':'knowledge_core_catalog'}
    def search_books(self,query=None,faculty=None,discipline=None,author=None,year=None,lang='en',limit=10):
        if type(limit) is not int or not 1<=limit<=100:raise CoreError('Invalid catalog limit')
        terms=set(re.findall(r'\w+',query.casefold())) if query else set()
        out=[]
        for work in self.core.iter_records('work'):
            item=self._entry(work)
            if faculty and item.get('faculty')!=faculty:continue
            if discipline and item.get('discipline')!=discipline:continue
            if year is not None and item.get('year')!=year:continue
            if author and not any(author.casefold() in str(a).casefold() for a in item['authors']):continue
            corpus=set(re.findall(r'\w+',(item['title']+' '+' '.join(item['authors'])).casefold()))
            if terms and not terms&corpus:continue
            item['translated_title']=item['title']
            item['translated_summary']=item.get('subtitle')
            out.append(item)
            if len(out)==limit:break
        return out
    def get_book_by_id(self,book_id,lang='en'):
        work=self.core.maybe(book_id) or self.core.maybe('book:'+book_id)
        if not work:return None
        if work['kind']=='artifact':work=self.core.get(work['data']['work_id'],'work')
        if work['kind']!='work':return None
        return self._entry(work)
    def list_faculties_and_disciplines(self):
        result={}
        for work in self.core.iter_records('work'):
            entry=self._entry(work);f=entry.get('faculty','general');d=entry.get('discipline','general')
            faculty=result.setdefault(f,{'label':f,'disciplines':{}})
            discipline=faculty['disciplines'].setdefault(d,{'label':d,'books_count':0})
            discipline['books_count']+=1
        return result


def bind_browser_rules(core):
    """Explicit operator opt-in for the already installed, trusted browser rule package."""
    core.require_curator()
    from expertos_bridge import experts
    aliases={'task.task_router':'route','task.browser_planner':'plan','task.form_mapper':'controls_map',
             'task.browser_verifier':'verify_values','task.recovery':'recovery'}
    bound=[]
    for alias,name in aliases.items():
        capability=core.maybe(alias)
        if not capability:
            id=core.declare_capability(alias,name=name,task=name,implemented=True,
                                      implementation={'module':'expertos_bridge.experts','function':name})
        else:
            id=capability['id']
            core.mark_implemented(id,implementation={'module':'expertos_bridge.experts','function':name},
                                  validation_reference='Installed package imported by explicit operator opt-in; runtime tests remain separate')
        core.bind(id,getattr(experts,name));bound.append(id)
    return bound
