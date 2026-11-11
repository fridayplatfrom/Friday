"""Concept graph, sense-aware language directory, and typed entity relationships."""
from collections import Counter
from urllib.parse import urlsplit, urlunsplit
import re
from .store import CoreError, text, now

PUBLIC_RELATIONS = {
    'broader': ({'concept'}, {'concept'}, True),
    'related_to': ({'concept'}, {'concept'}, False),
    'about': ({'work','edition','revision','segment','entity','website','page'}, {'concept'}, False),
    'requires_concept': ({'capability'}, {'concept'}, False),
    'denotes': ({'lexical_sense'}, {'concept'}, False),
    'operates': ({'entity'}, {'website'}, False),
    'describes': ({'page','revision','segment'}, {'entity'}, False),
    'supersedes': ({'concept','entity'}, {'concept','entity'}, True),
    'supports': ({'claim'}, {'claim'}, False),
    'contradicts': ({'claim'}, {'claim'}, False),
}


def canonical_url(url):
    text(url, 'url', 2048)
    try:
        p = urlsplit(url)
        if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password or p.port not in (None,80,443):
            raise CoreError('URL must be HTTP(S), without credentials or nonstandard ports')
        host = p.hostname.encode('idna').decode('ascii').lower()
    except (ValueError, UnicodeError) as exc:
        raise CoreError('Invalid URL') from exc
    if any(ord(c) < 33 for c in url):
        raise CoreError('URL contains controls or whitespace')
    return urlunsplit((p.scheme.lower(), host + (f':{p.port}' if p.port else ''), p.path or '/', p.query, ''))


class Knowledge:
    def add_concept(self, labels, *, id=None, alias=None, definition=None, scope=None):
        if not isinstance(labels, dict) or not labels:
            raise CoreError('Language-keyed labels required')
        for lang, label in labels.items():
            text(lang, 'language', 32); text(label, 'label', 256)
        with self.transaction():
            return self._new('concept', {'labels': labels, 'definition': definition, 'scope': scope,
                                        'external_mappings': [], 'review_state': 'proposed'}, id=id, alias=alias)

    def rename_concept(self, id, labels, *, expected_version):
        with self.transaction():
            record = self.get(id, 'concept')
            if not isinstance(labels, dict) or not labels:
                raise CoreError('Labels required')
            for lang, label in labels.items():
                text(lang, 'language', 32); text(label, 'label', 256)
            self._change(id, data={**record['data'], 'labels': labels}, expected_version=expected_version)

    def link(self, src, relation, dst, *, provenance=None):
        if relation not in PUBLIC_RELATIONS:
            raise CoreError('Relationship requires a dedicated validated API')
        with self.transaction():
            a,b = self.get(src), self.get(dst)
            kinds_a,kinds_b,acyclic = PUBLIC_RELATIONS[relation]
            if a['kind'] not in kinds_a or b['kind'] not in kinds_b:
                raise CoreError('Relationship endpoint types do not match')
            if relation in {'supports','contradicts'} and not provenance:
                raise CoreError('Evidence relationships require provenance')
            if acyclic:
                pending = [b['id']]; visited = set()
                while pending:
                    node = pending.pop()
                    if node == a['id']:
                        raise CoreError('Hierarchy cycle rejected')
                    if node in visited:
                        continue
                    visited.add(node)
                    pending.extend(e['dst'] for e in self.edges(node, relation=relation))
            self._edge(a['id'], relation, b['id'], {'provenance': provenance, 'review_state': 'proposed'})
            if relation in {'related_to','contradicts'}:
                self._edge(b['id'], relation, a['id'], {'provenance': provenance, 'review_state': 'proposed'})
            self._audit('linked', a['id'], relation=relation, target=b['id'])

    def concepts_for(self, id):
        return [self.get(e['dst'], 'concept') for e in self.edges(id, relation='about')]

    def add_sense(self, form, language, concept, *, context='', provenance=None):
        text(form, 'form', 256); text(language, 'language', 32)
        concept = self.get(concept, 'concept')['id']
        with self.transaction():
            alias = 'lexical:' + language + ':' + form.casefold()
            entry = self.maybe(alias)
            if not entry:
                eid = self._new('lexical_entry', {'form': form, 'language': language,
                                                'normalized_form': form.casefold()}, alias=alias)
            else:
                eid = entry['id']
            sid = self._new('lexical_sense', {'entry_id': eid, 'concept_id': concept,
                            'domain_context': context, 'provenance': provenance, 'review_state': 'proposed'})
            self._edge(sid, 'sense_of', eid)
            self._edge(sid, 'denotes', concept)
            return sid

    def resolve_term(self, form, language, *, concept=None):
        text(form, 'form', 256)
        with self.lock:
            entry = self.maybe('lexical:' + language + ':' + form.casefold())
            senses = []
            if entry:
                senses = [self.get(e['src']) for e in self.edges(entry['id'], relation='sense_of', reverse=True)]
                if concept:
                    cid = self.get(concept, 'concept')['id']
                    senses = [s for s in senses if s['data']['concept_id'] == cid]
            return {'status': 'ambiguous' if len(senses)>1 else 'resolved' if senses else 'unknown',
                    'senses': senses, 'automatic_translation': False}

    def align_translation(self, src, dst, *, method, quality=None, provenance=None):
        a,b = self.get(src),self.get(dst)
        if a['kind'] not in {'lexical_sense','segment','edition'} or a['kind'] != b['kind']:
            raise CoreError('Translations must link matching senses, segments, or editions')
        text(method, 'method', 128)
        with self.transaction():
            id = self._new('translation', {'from_id':a['id'], 'to_id':b['id'], 'method':method,
                        'quality':quality, 'provenance':provenance, 'review_state':'proposed'})
            self._edge(id, 'derived_from', a['id']); self._edge(id, 'derived_from', b['id'])
            return id

    def observed_terms(self, *, language=None, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise CoreError('Invalid term limit')
        args=[self.tenant]
        sql='''SELECT o.language,o.form,sum(o.occurrences) count FROM occurrences o
               JOIN nodes n ON n.tenant=o.tenant AND n.id=o.revision_id
               WHERE o.tenant=? AND n.status='active' '''
        if language:
            sql+=' AND o.language=?'; args.append(language)
        sql+=' GROUP BY o.language,o.form ORDER BY count DESC,o.form LIMIT ?'; args.append(limit)
        with self.lock:
            # Permission check precedes returning observations derived from text.
            allowed = []
            for row in self.db.execute(sql,args):
                revisions=self.db.execute('SELECT revision_id FROM occurrences WHERE tenant=? AND language=? AND form=?',
                                           (self.tenant,row['language'],row['form'])).fetchall()
                count=0
                for rev in revisions:
                    try:
                        self.require_source_use(rev[0],'retrieve')
                    except CoreError:
                        continue
                    v=self.db.execute('SELECT occurrences FROM occurrences WHERE tenant=? AND revision_id=? AND language=? AND form=?',
                                      (self.tenant,rev[0],row['language'],row['form'])).fetchone()
                    count+=v[0]
                if count:
                    allowed.append({'language':row['language'],'form':row['form'],'count':count,'status':'observed_not_dictionary'})
            return allowed

    def add_entity(self, name, entity_type, *, alias=None, metadata=None):
        text(name,'name',512); text(entity_type,'entity_type',64)
        with self.transaction():
            return self._new('entity',{'name':name,'entity_type':entity_type,'metadata':metadata or {},
                                      'review_state':'unreviewed'},alias=alias)

    def add_website(self, url, title, *, crawl_allowed=False, metadata=None):
        url=canonical_url(url); text(title,'title',512)
        with self.transaction():
            existing=self.maybe('website:'+url)
            if existing:
                return existing['id']
            return self._new('website',{'url':url,'title':title,'crawl_allowed':crawl_allowed is True,
                    'metadata':metadata or {},'review_state':'unreviewed'},alias='website:'+url)

    def register_page(self, website, url):
        site=self.get(website,'website'); url=canonical_url(url)
        if urlsplit(url).hostname != urlsplit(site['data']['url']).hostname:
            raise CoreError('Page host does not match website')
        with self.transaction():
            existing=self.maybe('page:'+url)
            if existing:
                return existing['id']
            id=self._new('page',{'website_id':site['id'],'url':url},alias='page:'+url)
            self._edge(id,'hosted_by',site['id']); return id

    def record_offer(self, product, merchant, *, price, currency, available, observed_at, expires_at=None):
        from decimal import Decimal, InvalidOperation
        p,m=self.get(product,'entity'),self.get(merchant,'entity')
        if p['data']['entity_type'] not in {'product','product_variant'} or m['data']['entity_type'] != 'merchant':
            raise CoreError('Offer requires a product and a merchant')
        try:
            value=Decimal(str(price))
            if not value.is_finite() or value<0: raise CoreError('Invalid price')
        except InvalidOperation as exc:
            raise CoreError('Invalid price') from exc
        if not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency):
            raise CoreError('Currency must be a three-letter uppercase code')
        self._check_timestamp(observed_at)
        if expires_at:
            self._check_timestamp(expires_at)
            if self._check_timestamp(expires_at) <= self._check_timestamp(observed_at):
                raise CoreError('Offer expiry must follow observation')
        if type(available) is not bool:
            raise CoreError('Availability must be boolean')
        with self.transaction():
            id=self._new('offer',{'product_id':p['id'],'merchant_id':m['id'],'price':str(value),
                 'currency':currency,'available':available,'observed_at':observed_at,'expires_at':expires_at,
                 'current_price_verified':False})
            self._edge(id,'offer_for',p['id']);self._edge(id,'offered_by',m['id']);return id

    @staticmethod
    def _check_timestamp(value):
        from datetime import datetime
        try:
            dt=datetime.fromisoformat(value.replace('Z','+00:00'))
            if dt.tzinfo is None: raise ValueError('timezone missing')
        except (ValueError,TypeError,AttributeError) as exc:
            raise CoreError('An ISO timestamp with timezone is required') from exc
        return dt

    def coverage(self):
        """Direct declared scope only; no automatic mastery inheritance."""
        output=[]
        for concept in self.iter_records('concept'):
            revisions=[];capabilities=[]
            for edge in self.edges(concept['id'],reverse=True):
                row=self.get(edge['src'])
                if row['kind']=='revision' and edge['relation']=='about' and row['status']=='active':revisions.append(row)
                if row['kind']=='capability' and edge['relation']=='requires_concept':capabilities.append(row)
            output.append({'concept_id':concept['id'],'labels':concept['data']['labels'],
                'source_revisions':len(revisions),
                'reviewed_source_revisions':sum(x['data'].get('review_state')=='accepted' for x in revisions),
                'declared_capabilities':len(capabilities),
                'runtime_bound':sum(self.capability_health(x['id'])['ready'] for x in capabilities),
                'mastery_established':False})
        return output
