import {realpathSync,statSync,readFileSync} from 'node:fs';
import {basename,relative,isAbsolute,extname} from 'node:path';
import {MAX_FILE_BYTES,FILE_TYPES} from './file-store.mjs';

// Only a newly created browser download beneath the configured Downloads root
// can enter this path. It cannot read arbitrary paths supplied by a model.
export function importBrowserDownload(files,job,input,{directory,pair,now=Date.now()}={}){
  if(!job?.claimed||job.terminal||!Number.isSafeInteger(input.downloadId)||input.downloadId<0)throw new Error('No active browser download job.');
  if(!directory||!pair?.url)throw new Error('Browser download import is not configured.');
  const source=new URL(input.referrer||input.url),expected=new URL(pair.url);
  if(source.origin!==expected.origin||source.protocol!=='blob:'&&source.pathname!==expected.pathname&&source.pathname!=='/')throw new Error('Download is not from the paired website.');
  const started=Date.parse(input.startTime);
  if(!Number.isFinite(started)||started<job.createdAt-1000||started>now+5000)throw new Error('Download is not new for this request.');
  const root=realpathSync(directory),path=realpathSync(input.filename),inside=relative(root,path);
  if(!inside||isAbsolute(inside)||inside==='..'||inside.startsWith('../')||inside.startsWith('..\\'))throw new Error('Download is outside the allowed Downloads folder.');
  if(!FILE_TYPES[extname(path).slice(1).toLowerCase()]||basename(path).length>180)throw new Error('Unsupported downloaded file format.');
  const info=statSync(path);
  if(!info.isFile()||!Number.isSafeInteger(input.size)||info.size!==input.size||info.size>MAX_FILE_BYTES||info.birthtimeMs<job.createdAt-1000)throw new Error('Download size, type or creation time is invalid.');
  job.downloadImports ||= new Map();
  if(job.downloadImports.has(input.downloadId))return job.downloadImports.get(input.downloadId);
  if(job.downloadImports.size>=8)throw new Error('Output file limit reached.');
  const file=files.put(job.sessionId,basename(path),readFileSync(path),'from-website');
  job.downloadImports.set(input.downloadId,file);return file;
}
