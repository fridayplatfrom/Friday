window.fridayRecovery.onStatus(status=>{
 document.getElementById('recovery').hidden=false;
 document.getElementById('message').textContent=status.message;
 document.getElementById('restore').disabled=status.recovering;
});
document.getElementById('restore').onclick=()=>{
 document.getElementById('restore').disabled=true;
 void window.fridayRecovery.restore().catch(()=>{document.getElementById('restore').disabled=false;});
};
