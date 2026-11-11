// Durable admission for Electron's normal mouse-input submission. An exception
// after admission is uncertain and must never fall back to a second click.
export function submitOnce(state,{tabId,origin,jobId,x,y,width,height},dispatch){
 if(!Number.isFinite(x)||!Number.isFinite(y)||x<0||y<0||x>=width||y>=height)throw Error('Submit control is outside the provider view');
 const receipt=JSON.parse(state.receipts(tabId,origin)['harness-job:'+jobId]||'null');
 if(receipt?.state!=='submitting')throw Error('No durable submission receipt');
 state.data.submissions||={};const key=`${tabId}:${jobId}`;
 if(state.data.submissions[key])throw Error('Submission was already attempted. Inspect the paired chat; nothing was repeated.');
 state.data.submissions[key]={at:Date.now(),state:'attempted'};state.save();
 dispatch({x:Math.floor(x),y:Math.floor(y)});return {ok:true};
}
