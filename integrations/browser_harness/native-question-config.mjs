import {readFileSync,writeFileSync,copyFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

// Use the installed native stable-call question implementation. -1 preserves
// blocking behavior: no timeout, automatic answer or permission policy change.
// Explicitly configured native question plugins are left alone.
export function stableNativeQuestions(yaml){
 let count=0;
 const result=yaml.replace(/^( *)name: (['"]?)@deepseek-ai\/dsh-tool-ask-user\2\r?\n/gm,(line,indent,_quote,offset)=>{
  const following=yaml.slice(offset+line.length);
  if(new RegExp('^(?:[ \\t]*(?:#[^\\r\\n]*)?\\r?\\n)*'+indent+'config:').test(following))return line;
  count++;return line+`${indent}config:\n${indent}  mode: timed\n${indent}  timeout: -1\n`;
 });
 return {yaml:result,count};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const path=process.argv[2];if(!path)throw new Error('Supply the existing native profile path.');
 const result=stableNativeQuestions(readFileSync(path,'utf8'));
 if(result.count){copyFileSync(path,path+'.before-friday-questions-'+Date.now()+'.bak');writeFileSync(path,result.yaml);}
 console.log(`Native stable question configuration: ${result.count} plugins updated.`);
}
