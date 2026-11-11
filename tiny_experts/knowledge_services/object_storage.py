"""Optional private S3-compatible blob replication; metadata stays transactional locally.

This is explicit replication, not automatic migration to distributed metadata.
Credentials are resolved by the standard SDK chain, never source records.
"""
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
from ..knowledge_core.store import CoreError,AccessDenied,digest


class S3Mirror:
    def __init__(self,*,bucket,prefix='expertos',endpoint_url=None,client=None):
        if not isinstance(bucket,str) or not bucket or '/' in bucket:raise CoreError('Explicit bucket required')
        if not isinstance(prefix,str) or not prefix or '..' in prefix.split('/'):raise CoreError('Invalid object prefix')
        if endpoint_url:
            p=urlsplit(endpoint_url)
            if p.scheme!='https' or not p.hostname or p.username or p.password:raise AccessDenied('Object-store endpoint must be operator-configured HTTPS')
        if client is None:
            try:import boto3
            except ImportError as exc:raise CoreError('Install object-storage optional dependencies') from exc
            client=boto3.client('s3',endpoint_url=endpoint_url)
        self.client=client;self.bucket=bucket;self.prefix=prefix.strip('/')

    def key(self,core,sha):
        core._asset_path(sha)
        return self.prefix+'/'+digest(core.tenant.encode())+'/sha256/'+sha

    def replicate(self,core,revision):
        core.require_curator();source=core.require_source_use(revision,'store')
        hashes={source['data']['sha256'],source['data'].get('text_sha256')}-{None}
        receipts=[]
        for sha in sorted(hashes):
            path=core.verify_asset(sha);key=self.key(core,sha)
            with path.open('rb') as stream:
                self.client.upload_fileobj(stream,self.bucket,key,ExtraArgs={
                    'ServerSideEncryption':'AES256','Metadata':{'sha256':sha,'tenant_hash':digest(core.tenant.encode())}})
            head=self.client.head_object(Bucket=self.bucket,Key=key)
            if head.get('ContentLength')!=path.stat().st_size or head.get('Metadata',{}).get('sha256')!=sha:
                raise CoreError('Object replication verification failed')
            receipts.append({'sha256':sha,'bytes':path.stat().st_size,'object_key':key})
        with core.transaction():core._audit('assets_replicated',source['id'],count=len(receipts))
        return {'replicated':receipts,'metadata_distributed':False,'backups_auto_purged':False}
