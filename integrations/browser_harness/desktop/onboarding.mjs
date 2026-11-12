import {randomUUID} from 'node:crypto';
export const setupSites=['chatgpt-web','gemini-web','deepseek-web','kimi-web'];
/** Existing data is an explicit migration boundary, not an invitation to reset setup. */
export function initializeSetup(state,{existing=false,now=Date.now()}={}){
 if(!state.data.onboarding){state.data.onboarding={version:1,status:existing?'existing':'pending',updatedAt:now};state.save();}
 else if(state.data.onboarding.test?.status==='running'){
  state.data.onboarding.test.status='interrupted';state.data.onboarding.test.message='The test was interrupted. Inspect the provider chat before starting a new test.';state.save();
 }
 return state.data.onboarding;
}
export class FirstRunSetup{
 constructor({state,existing,open,test,complete=async()=>{},disable=async()=>{},idle=()=>true,now=Date.now}){Object.assign(this,{state,open,test,complete,disable,idle,now});const setup=initializeSetup(state,{existing,now:now()});setup.providers??={};if(setup.site&&setup.test&&!setup.providers[setup.site])setup.providers[setup.site]={test:{...setup.test}};this.visible=setup.status==='pending';this.mode='setup';this.running=false;}
 snapshot(){return {...this.state.data.onboarding,visible:this.visible,mode:this.mode};}
 save(){this.state.data.onboarding.updatedAt=this.now();this.state.save();return this.snapshot();}
 async action(input={}){
  const setup=this.state.data.onboarding;
  if(input.action==='status')return this.snapshot();
  if(!this.idle()||this.running)throw Error('Finish the active task or connection test first. Nothing was resent.');
  if(input.action==='show'){this.visible=true;this.mode='manage';return this.snapshot();}
  if(input.action==='skip'){this.visible=false;if(setup.status==='pending')setup.status='skipped';return this.save();}
  if(input.action==='select'){
   if(!setupSites.includes(input.site))throw Error('Unknown provider.');
   if(setup.site===input.site)return this.snapshot();
   await this.open(input.site);setup.site=input.site;setup.test=setup.providers[input.site]?.test||null;return this.save();
  }
  if(input.action==='test'){
   if(!this.visible||!setupSites.includes(setup.site))throw Error('Choose a provider first.');
   const id=randomUUID();setup.test={id,status:'running',startedAt:this.now()};this.running=true;this.save();
   // Persist admission before sending. Reload/restart never invokes this callback again.
   void Promise.resolve().then(()=>this.test(setup.site,id)).then(result=>{
    setup.test={id,status:result.ok?'passed':'failed',message:result.message,finishedAt:this.now()};
   },error=>{setup.test={id,status:'failed',message:String(error.message).slice(0,400),finishedAt:this.now()};})
    .finally(()=>{this.running=false;setup.providers[setup.site]={...setup.providers[setup.site],test:{...setup.test},...(setup.test.status==='passed'?{disabled:false}:{})};this.save();});return this.snapshot();
  }
  if(input.action==='disable'){
   if(!setupSites.includes(setup.site))throw Error('Choose a provider first.');
   await this.disable(setup.site);setup.providers[setup.site]={...setup.providers[setup.site],disabled:true};return this.save();
  }
  if(input.action==='finish'||input.action==='default'){
   if(setup.test?.status!=='passed')throw Error('Verify one provider, or choose Set up later.');
   if(setup.providers[setup.site]?.disabled)throw Error('Test the connection to enable this provider first.');
   await this.complete(setup.site,setup.test.id);
   setup.status='completed';setup.defaultProvider=setup.site;if(input.action==='finish')this.visible=false;return this.save();
  }
  throw Error('Unknown setup action.');
 }
}
