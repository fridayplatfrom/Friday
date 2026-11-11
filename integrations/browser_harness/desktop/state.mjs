import fs from 'node:fs';
import {dirname} from 'node:path';
export class DesktopState {
  constructor(path){this.path=path;this.data={tabs:[],receipts:{},storage:{}};if(fs.existsSync(path))this.data=JSON.parse(fs.readFileSync(path,'utf8'));}
  save(){fs.mkdirSync(dirname(this.path),{recursive:true});fs.writeFileSync(this.path+'.tmp',JSON.stringify(this.data),{mode:0o600});fs.renameSync(this.path+'.tmp',this.path);}
  receipts(id,origin){return this.data.receipts[`${id}:${origin}`]||{};}
  receipt(id,origin,key,value){if(!/^(harness-job:|harness-pending-files:|harness-captures:)/.test(key)||key.length>300||typeof value!=='string'||value.length>2000000)throw Error('Invalid receipt');const scope=`${id}:${origin}`;this.data.receipts[scope]||={};this.data.receipts[scope][key]=value;this.save();}
}
