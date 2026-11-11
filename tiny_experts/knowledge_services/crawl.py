"""Persistent, same-site static crawler with budgets and fail-closed robots checks.

Public content acquisition is separate from browser automation and from training
permission. This is a bounded vertical crawler, not whole-web search infrastructure.
"""
from html.parser import HTMLParser
from urllib.parse import urlsplit,urljoin,quote
import hashlib
import json
import math
import re
import secrets
import time
from ..knowledge_core.store import CoreError, AccessDenied, dumps, now, digest
from ..knowledge_core.sources import rights_policy
from .network import safe_url,USER_AGENT,FetchError


class Robots:
    def __init__(self,body,agent='expertosbot'):
        if len(body.encode())>512000:raise CoreError('Robots file exceeds parsing budget')
        groups=[];agents=[];rules=[];delay=None;directives=False
        for raw in body.splitlines():
            line=raw.split('#',1)[0].strip()
            if ':' not in line:continue
            key,value=(v.strip() for v in line.split(':',1));key=key.lower()
            if key=='user-agent':
                if directives:
                    groups.append((agents,rules,delay));agents=[];rules=[];delay=None;directives=False
                agents.append(value.casefold())
            elif agents:
                directives=True
                if key in {'allow','disallow'} and value:rules.append((key,value))
                if key=='crawl-delay':
                    try:
                        d=float(value)
                        if math.isfinite(d) and d>=0:delay=d
                    except ValueError:pass
        if agents:groups.append((agents,rules,delay))
        matches=[];best=-1
        for names,rs,d in groups:
            specificity=max((0 if a=='*' else len(a) for a in names if a=='*' or a in agent),default=-1)
            if specificity>best:best=specificity;matches=[(rs,d)]
            elif specificity==best and specificity>=0:matches.append((rs,d))
        self.rules=[r for rs,d in matches for r in rs] if best>=0 else []
        self.delay=max([d for rs,d in matches if d is not None],default=0)

    @staticmethod
    def normal(value):
        value=quote(value,safe='/%*?$&=:@!~(),;+-._')
        def octet(match):
            n=int(match.group()[1:],16);c=chr(n)
            return c if c.isascii() and (c.isalnum() or c in '-._~') else '%'+match.group()[1:].upper()
        return re.sub(r'%[0-9a-fA-F]{2}',octet,value)

    def allows(self,url):
        p=urlsplit(url);path=self.normal((p.path or '/')+('?' +p.query if p.query else ''))
        matches=[]
        for action,raw in self.rules:
            raw=self.normal(raw);end=raw.endswith('$');raw=raw[:-1] if end else raw
            pattern='^'+'.*'.join(re.escape(s) for s in raw.split('*'))+('$' if end else '')
            if re.search(pattern,path):matches.append((len(raw.replace('*','')),action=='allow'))
        return max(matches)[1] if matches else True


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.links=[];self.robots=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag.lower()=='a' and a.get('href') and 'nofollow' not in a.get('rel','').lower().split():
            self.links.append(a['href'])
        if tag.lower()=='meta' and a.get('name','').lower() in {'robots','expertosbot'}:
            self.robots.update(re.split(r'[,\s]+',a.get('content','').lower()))


class StructuredDOMExtractor(HTMLParser):
    """Clean DOM Article, Table & Temporal Metadata Extractor (Core Pillar 7).

    Strips script/style/nav/footer boilerplate and extracts structured headings,
    paragraphs, HTML data tables (e.g., GST slabs, prices, benchmarks), and
    publication timestamps.
    """
    SKIP_TAGS = {"script", "style", "noscript", "nav", "footer", "aside", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._current_tag = None
        self._buf: list[str] = []
        self.title = ""
        self.headings: list[str] = []
        self.paragraphs: list[str] = []
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._in_cell = False
        self._cell_buf: list[str] = []
        self.published_date: str | None = None
        self.author: str | None = None

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        a = {k.lower(): v for k, v in attrs if k}
        if t in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        self._current_tag = t
        if t == "meta":
            prop = (a.get("property") or a.get("name") or "").lower()
            content = (a.get("content") or "").strip()
            if prop in {"article:published_time", "pubdate", "date", "dc.date"} and content:
                self.published_date = content
            elif prop in {"author", "article:author", "dc.creator"} and content:
                self.author = content
        elif t == "time" and a.get("datetime") and not self.published_date:
            self.published_date = a["datetime"].strip()
        elif t == "table":
            self._in_table = True
            self._current_table = []
        elif t == "tr" and self._in_table:
            self._current_row = []
        elif t in {"td", "th"} and self._in_table:
            self._in_cell = True
            self._cell_buf = []

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if self._skip_depth > 0:
            return
        if t in {"td", "th"} and self._in_cell:
            cell_txt = re.sub(r"\s+", " ", "".join(self._cell_buf)).strip()
            self._current_row.append(cell_txt)
            self._in_cell = False
            self._cell_buf = []
        elif t == "tr" and self._in_table:
            if any(self._current_row):
                self._current_table.append(self._current_row)
            self._current_row = []
        elif t == "table" and self._in_table:
            if self._current_table:
                self.tables.append(self._current_table)
            self._in_table = False
            self._current_table = []
        elif t == "title":
            txt = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if txt and not self.title:
                self.title = txt
            self._buf = []
        elif t in {"h1", "h2", "h3"}:
            txt = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if txt:
                self.headings.append(txt)
            self._buf = []
        elif t in {"p", "li", "article"}:
            txt = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if len(txt) >= 20:
                self.paragraphs.append(txt)
            self._buf = []

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if self._in_cell:
            self._cell_buf.append(data)
        elif self._current_tag in {"title", "h1", "h2", "h3", "p", "li", "article"}:
            self._buf.append(data)


def classify_source_trust(url_or_host: str) -> dict:
    """Assigns epistemic trust tier and corroboration weight to web sources."""
    host = (urlsplit(url_or_host).hostname or url_or_host).lower().strip()
    if host.endswith((".gov", ".gov.in", ".nic.in", ".mil")):
        return {"trust_tier": "gov_official", "trust_weight": 0.98, "auto_supersede_allowed": True}
    if host.endswith((".edu", ".ac.in", ".ac.uk", "arxiv.org", "doi.org")):
        return {"trust_tier": "academic_peer_reviewed", "trust_weight": 0.92, "auto_supersede_allowed": True}
    if any(k in host for k in ("reuters.", "apnews.", "bbc.", "thehindu.", "pib.gov")):
        return {"trust_tier": "verified_news_org", "trust_weight": 0.82, "auto_supersede_allowed": False}
    return {"trust_tier": "general_web", "trust_weight": 0.45, "auto_supersede_allowed": False}


def extract_structured_dom(html_body: str, url: str = "") -> dict:
    """Extracts clean article text, structured tables, temporal metadata, and trust tier from HTML."""
    extractor = StructuredDOMExtractor()
    extractor.feed(html_body)
    trust = classify_source_trust(url)
    clean_text = "\n\n".join(extractor.headings + extractor.paragraphs).strip()
    return {
        "url": url,
        "title": extractor.title,
        "headings": extractor.headings,
        "paragraphs": extractor.paragraphs,
        "clean_text": clean_text,
        "tables": extractor.tables,
        "published_date": extractor.published_date,
        "author": extractor.author,
        "trust": trust,
    }


class Crawling:
    def configure_crawl(self,website,*,rights,license_note,delay_seconds=1.0,max_pages=100,max_depth=2,refresh_seconds=86400):
        self.require_curator();site=self.get(website,'website')
        if not site['data'].get('crawl_allowed'):raise AccessDenied('Website is not approved for crawling')
        host=urlsplit(site['data']['url']).hostname
        safe_url(site['data']['url'],{host});policy=rights_policy(rights)
        if not isinstance(license_note,str) or not license_note.strip():raise CoreError('Crawl rights note required')
        if type(delay_seconds) not in (int,float) or not math.isfinite(delay_seconds) or not 1<=delay_seconds<=3600:
            raise CoreError('Per-host delay must be 1..3600 seconds')
        if type(max_pages) is not int or not 1<=max_pages<=self.limits.crawl_pages or type(max_depth) is not int or not 0<=max_depth<=self.limits.crawl_depth:
            raise CoreError('Crawl page/depth budget invalid')
        if type(refresh_seconds) is not int or refresh_seconds<3600:raise CoreError('Refresh interval must be at least one hour')
        config={'host':host,'rights':policy,'license_note':license_note,'delay':delay_seconds,'max_pages':max_pages,
                'max_depth':max_depth,'refresh_seconds':refresh_seconds,'robots':None}
        with self.transaction():
            previous=self.db.execute('SELECT data FROM crawl_config WHERE tenant=? AND website_id=?',(self.tenant,site['id'])).fetchone()
            if previous and json.loads(previous[0])['rights']!=policy:
                for row in self.db.execute('SELECT revision_id FROM crawl_frontier WHERE tenant=? AND website_id=? AND revision_id IS NOT NULL',(self.tenant,site['id'])).fetchall():
                    self.set_rights(row[0],policy,reason='Crawler permission configuration changed')
            self.db.execute('INSERT OR REPLACE INTO crawl_config VALUES (?,?,?)',(self.tenant,site['id'],dumps(config)))
            self._audit('crawl_configured',site['id'],host=host)
        self.enqueue_url(site['id'],site['data']['url'])
        return config

    def _crawl_config(self,website):
        site=self.get(website,'website')
        if site['status']!='active' or not site['data'].get('crawl_allowed'):raise AccessDenied('Website crawling unavailable')
        row=self.db.execute('SELECT data FROM crawl_config WHERE tenant=? AND website_id=?',(self.tenant,site['id'])).fetchone()
        if not row:raise CoreError('Website has no operator-approved crawl configuration')
        return site,json.loads(row[0])

    def enqueue_url(self,website,url,*,depth=0):
        site,cfg=self._crawl_config(website);url=safe_url(url,{cfg['host']})
        if type(depth) is not int or not 0<=depth<=cfg['max_depth']:return False
        with self.transaction():
            if self.db.execute('SELECT 1 FROM crawl_frontier WHERE tenant=? AND website_id=? AND url=?',(self.tenant,site['id'],url)).fetchone():return False
            n=self.db.execute('SELECT count(*) FROM crawl_frontier WHERE tenant=? AND website_id=?',(self.tenant,site['id'])).fetchone()[0]
            if n>=min(self.limits.crawl_frontier,cfg['max_pages']):return False
            self.db.execute('''INSERT INTO crawl_frontier(tenant,website_id,url,depth,state,available_at)
                VALUES(?,?,?,?,'pending',?)''',(self.tenant,site['id'],url,depth,time.time()))
        return True

    def _request_slot(self,site,cfg):
        with self.transaction():
            row=self.db.execute('SELECT next_request FROM crawl_hosts WHERE tenant=? AND website_id=?',(self.tenant,site)).fetchone()
            clock=time.time()
            if row and row[0]>clock:return row[0]-clock
            self.db.execute('INSERT OR REPLACE INTO crawl_hosts VALUES (?,?,?)',(self.tenant,site,clock+cfg['delay']))
        return 0

    def _robots(self,site,cfg):
        cached=cfg.get('robots')
        if cached and cached['expires']>time.time():
            if cached['state']!='allowed':raise AccessDenied('Robots acquisition denied or temporarily unavailable')
            return Robots(cached['body'])
        wait=self._request_slot(site['id'],cfg)
        if wait:return None
        state='denied';body='';reason='robots_unavailable'
        try:
            response=self.fetcher.fetch('https://'+cfg['host']+'/robots.txt',allowed_hosts={cfg['host']},max_bytes=512000)
            if response.status==200:body=response.body.decode('utf-8-sig');state='allowed';Robots(body)
            elif response.status==404:state='allowed'
            elif response.status in {401,403}:reason='robots_access_denied'
            # Redirects and 5xx fail closed; operator can repair the origin policy.
            else:reason='robots_http_'+str(response.status)
        except (CoreError,UnicodeError):pass
        cfg['robots']={'state':state,'body':body,'expires':time.time()+(3600 if state=='allowed' else 300),'reason':reason}
        with self.transaction():self.db.execute('UPDATE crawl_config SET data=? WHERE tenant=? AND website_id=?',(dumps(cfg),self.tenant,site['id']))
        if state!='allowed':raise AccessDenied(reason)
        rules=Robots(body)
        if rules.delay>cfg['delay']:
            with self.transaction():
                self.db.execute('INSERT INTO crawl_hosts VALUES (?,?,?) ON CONFLICT(tenant,website_id) DO UPDATE SET next_request=MAX(next_request,excluded.next_request)',(self.tenant,site['id'],time.time()+rules.delay))
        return rules

    def crawl(self,website,*,max_pages=10,cancelled=lambda:False):
        self.require_curator();site,cfg=self._crawl_config(website)
        if type(max_pages) is not int or not 1<=max_pages<=cfg['max_pages']:raise CoreError('Invalid crawl execution budget')
        if cancelled():raise CoreError('Operation cancelled')
        rules=self._robots(site,cfg)
        if rules is None:return {'status':'rate_limited','processed':0,'website_id':site['id']}
        cfg['delay']=max(cfg['delay'],rules.delay)
        processed=0;outcomes=[]
        while processed<max_pages:
            if cancelled():raise CoreError('Operation cancelled')
            clock=time.time()
            with self.transaction():
                self.db.execute("UPDATE crawl_frontier SET state='failed',error='attempt_budget_exhausted' WHERE tenant=? AND website_id=? AND attempts>=3 AND (state='pending' OR (state='running' AND lease_until<=?))",(self.tenant,site['id'],clock))
                row=self.db.execute('''SELECT * FROM crawl_frontier WHERE tenant=? AND website_id=? AND attempts<3
                    AND ((state='pending' AND available_at<=?) OR (state='running' AND lease_until<=?) OR (state IN ('indexed','noindex','gone','blocked','redirected') AND available_at<=?))
                    ORDER BY depth,url LIMIT 1''',(self.tenant,site['id'],clock,clock,clock)).fetchone()
                if not row:break
                token=secrets.token_hex(24)
                self.db.execute("UPDATE crawl_frontier SET state='running',lease_token=?,lease_until=?,attempts=attempts+1 WHERE tenant=? AND website_id=? AND url=?",
                         (token,clock+120,self.tenant,site['id'],row['url']))
            url=row['url'];state='failed';error=None;rid=row['revision_id'];status=None;etag=row['etag'];modified=row['modified'];next_at=clock+cfg['refresh_seconds']
            if not rules.allows(url):state='blocked';error='robots_disallow'
            elif (wait:=self._request_slot(site['id'],cfg)):
                with self.transaction():self.db.execute("UPDATE crawl_frontier SET state='pending',attempts=attempts-1,available_at=?,lease_token=NULL,lease_until=NULL WHERE tenant=? AND website_id=? AND url=? AND lease_token=?",(time.time()+wait,self.tenant,site['id'],url,token))
                break
            else:
                try:
                    self._crawl_config(site['id'])
                    conditional={}
                    if etag:conditional['If-None-Match']=etag
                    if modified:conditional['If-Modified-Since']=modified
                    response=self.fetcher.fetch(url,allowed_hosts={cfg['host']},max_bytes=self.limits.crawl_response_bytes,headers=conditional)
                    status=response.status
                    if cancelled():raise CoreError('Operation cancelled')
                    if status in {301,302,303,307,308}:
                        target=safe_url(urljoin(url,response.headers.get('location','')),{cfg['host']})
                        self.enqueue_url(site['id'],target,depth=row['depth']);state='redirected'
                    elif status==304:
                        if not rid:raise CoreError('304 without a stored source revision')
                        self.require_source_use(rid,'store');state='indexed'
                    elif status in {429,500,502,503,504}:
                        state='pending';error='retryable_http';next_at=time.time()+min(300,2**(row['attempts']+1))
                    elif status in {404,410}:
                        state='gone'
                        if rid:self.withdraw_source(rid,reason='Crawler observed HTTP '+str(status))
                    elif status!=200:error='http_'+str(status)
                    else:
                        mime=response.headers.get('content-type','').split(';',1)[0].strip().lower()
                        if mime not in {'text/html','text/plain','text/markdown'}:raise CoreError('Unsupported crawler content type')
                        decoded=response.body.decode('utf-8-sig')
                        if '\x00' in decoded:raise CoreError('Binary content in text page')
                        parser=PageParser()
                        if mime=='text/html':parser.feed(decoded)
                        flags=parser.robots|set(re.split(r'[,\s]+',response.headers.get('x-robots-tag','').lower()))
                        if flags&{'none','noindex'}:
                            state='noindex'
                            if rid:self.withdraw_source(rid,reason='Publisher requested noindex')
                        else:
                            with self.transaction():
                                current_site,current_cfg=self._crawl_config(site['id'])
                                if current_cfg['rights']!=cfg['rights']:
                                    raise AccessDenied('Crawl rights changed during fetch')
                                lease=self.db.execute('SELECT lease_token,lease_until FROM crawl_frontier WHERE tenant=? AND website_id=? AND url=?',(self.tenant,site['id'],url)).fetchone()
                                if not lease or lease[0]!=token or lease[1]<=time.time():
                                    raise AccessDenied('Crawl lease expired before publication')
                                if cancelled():raise AccessDenied('Operation cancelled before publication')
                                old=self.maybe(rid,'revision') if rid else None
                                if old and old['status']=='active' and old['data']['sha256']==digest(response.body):state='indexed'
                                else:
                                    page=self.register_page(site['id'],url)
                                    if mime=='text/html':result=self.snapshot_page(page,response.body,rights=cfg['rights'],license_note=cfg['license_note'])
                                    else:
                                        artifact=self.register_source('crawl:'+page,url,source_type='web_page')
                                        result=self.ingest(artifact,response.body,media_type=mime,rights=cfg['rights'],license_note=cfg['license_note'],metadata={'url':url})
                                        with self.transaction():self._edge(result['revision_id'],'snapshot_of',page)
                                    rid=result['revision_id'];state='indexed'
                                if not flags&{'none','nofollow'}:
                                    for href in parser.links[:1000]:
                                        try:self.enqueue_url(site['id'],urljoin(url,href),depth=row['depth']+1)
                                        except CoreError:continue
                        etag=response.headers.get('etag');modified=response.headers.get('last-modified')
                        if etag and (len(etag)>512 or '\n' in etag or '\r' in etag):etag=None
                        if modified and (len(modified)>512 or '\n' in modified or '\r' in modified):modified=None
                except (CoreError,UnicodeError,OSError) as exc:
                    error=type(exc).__name__;state='pending' if isinstance(exc,FetchError) else 'failed'
                    next_at=time.time()+min(300,2**(row['attempts']+1))
            with self.transaction():
                current=self.db.execute('SELECT lease_token,lease_until FROM crawl_frontier WHERE tenant=? AND website_id=? AND url=?',(self.tenant,site['id'],url)).fetchone()
                if not current or current[0]!=token or current[1]<=time.time():raise AccessDenied('Crawl lease expired')
                self.db.execute('''UPDATE crawl_frontier SET state=?,revision_id=?,etag=?,modified=?,error=?,status_code=?,available_at=?,
                    lease_token=NULL,lease_until=NULL,attempts=CASE WHEN ?='indexed' THEN 0 ELSE attempts END
                    WHERE tenant=? AND website_id=? AND url=?''',
                    (state,rid,etag,modified,error,status,next_at,state,self.tenant,site['id'],url))
                self._audit('crawl_observed',site['id'],url_hash=digest(url.encode()),state=state,http_status=status)
            outcomes.append({'url':url,'state':state,'http_status':status,'revision_id':rid,'error':error});processed+=1
        return {'status':'batch_complete','website_id':site['id'],'processed':processed,'outcomes':outcomes,
                'dynamic_browser_used':False,'training_permission_inferred':False}
