import test from 'node:test';
import assert from 'node:assert/strict';
import {interactionFact,mergeInteraction,interactionDefinitions} from '../interactions.mjs';
import {emptyActivity,projectEvent} from '../ag-ui-client.mjs';
import {BrowserBridge} from '../bridge.mjs';
import {stableNativeQuestions} from '../native-question-config.mjs';

const question={type:'tool/call',seq:2,time:100,data:{callId:'q',name:'ask_user_question',arguments:JSON.stringify({questions:[{id:'colour',question:'Which colour?',options:[{label:'Blue'},{label:'Green'}],multi_select:true}]})}};
test('stable native question configuration preserves blocking, explicit settings and all other profile data',()=>{
 const source="- id: ask\n  name: '@deepseek-ai/dsh-tool-ask-user'\n- id: next\n  config:\n    untouched: true\n";
 const next=stableNativeQuestions(source);assert.equal(next.count,1);assert.match(next.yaml,/mode: timed\n    timeout: -1/);assert.ok(next.yaml.endsWith('- id: next\n  config:\n    untouched: true\n'));
 assert.equal(stableNativeQuestions(next.yaml).count,0);
 const configured=source.replace('- id: next','  config:\n    mode: legacy\n- id: next');assert.equal(stableNativeQuestions(configured).yaml,configured);
 const commented=configured.replace('  config:\n    mode: legacy','\n  # existing native choice\n  config:\n    mode: legacy');assert.equal(stableNativeQuestions(commented).yaml,commented);
});
test('native approval audit uses exact IDs and never manufactures a grant or a response action',()=>{
 let items=mergeInteraction([] ,interactionFact({type:'approval/asked',data:{id:'a',toolName:'pwsh',callId:'tool',reason:'Read-only fixture'}}));
 assert.equal(items[0].status,'requested');assert.equal(items[0].callId,'tool');
 items=mergeInteraction(items,interactionFact({type:'approval/decided',data:{id:'unrelated',outcome:'allowed-once'}}));assert.equal(items[0].status,'requested');
 items=mergeInteraction(items,interactionFact({type:'approval/decided',data:{id:'a',outcome:'rejected'}}));assert.equal(items.length,1);assert.equal(items[0].status,'rejected');assert.equal(items[0].answer,undefined);
});
test('questions retain options, pending status and native answers; ordinary tool output cannot create a question',()=>{
 let items=mergeInteraction([],interactionFact(question));assert.equal(items[0].questions[0].options.length,2);assert.equal(items[0].questions[0].multiSelect,true);
 items=mergeInteraction(items,interactionFact({type:'tool/result',data:{message:{toolCallId:'q',content:[{type:'text',text:'{"pending":true}'}]}}}));assert.equal(items[0].status,'continued');
 items=mergeInteraction(items,interactionFact({type:'user/message',data:{source:{kind:'user-question-reply',callId:'q'},content:[{type:'text',text:'{"answers":[{"id":"colour","selected":["Blue"],"custom":"test"}]}'}]}}));assert.equal(items[0].status,'answered');assert.equal(items[0].answers[0].custom,'test');
 assert.equal(mergeInteraction([],interactionFact({type:'tool/result',data:{message:{toolCallId:'ordinary',content:[]}}})).length,0);
 assert.equal(interactionFact({...question,data:{...question.data,arguments:'broken'}}),null);
});
test('native conversation definitions replay matching audit records while preserving native tool ownership',()=>{
 const definition=interactionDefinitions().find(d=>d.kind.endsWith('approval'));
 const asked={type:'approval/asked',seq:1,time:10,data:{id:'a',toolName:'pwsh'}};
 assert.equal(definition.match(asked).exclusive,false);
 const context={key:'native-key',id:'a',start:{location:{kind:'unresolved'}}};
 context.state=definition.start(context,{event:asked});
 context.state=definition.update(context,{event:{type:'approval/decided',data:{id:'a',outcome:'allowed-once'}}});
 const node=definition.buildViewNode(context);assert.equal(node.data.status,'allowed-once');assert.equal(node.anchorSeq,1);assert.equal(node.kind,'friday-native-interaction');
 assert.equal(definition.buildViewNode({}),null);
});
test('AG-UI and activity expose native decisions and questions; ending an unanswered turn clears waiting status',()=>{
 const bridge=new BrowserBridge({token:'test-token-long-enough-for-local-auth-0000'});bridge.sessions.update('thread',{});
 const native=(seq,type,data)=>{const event={seq,type,data};bridge.agui.native('thread',event);bridge.activity.native('thread',event);};
 native(1,'turn/start',{turn:1});native(2,'approval/asked',{id:'a',toolName:'pwsh',callId:'call'});
 assert.equal(bridge.activity.get('thread').phase,'approval');
 native(3,'approval/decided',{id:'a',outcome:'rejected'});native(4,'tool/call',question.data);
 assert.equal(bridge.activity.get('thread').phase,'question');
 native(5,'turn/end',{reason:{kind:'aborted'}});
 const run=bridge.agui.runs('thread')[0];let projected=emptyActivity();
 for(const record of bridge.agui.records('thread',run.runId))projected=projectEvent(projected,record.data.event,record.seq);
 assert.equal(projected.interactions.find(x=>x.kind==='approval').status,'rejected');assert.equal(projected.interactions.find(x=>x.kind==='question').status,'interrupted');assert.equal(projected.phase,'cancelled');
});
