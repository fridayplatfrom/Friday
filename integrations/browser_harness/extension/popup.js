const enabled = document.querySelector('#enabled');
for(const provider of Object.values(globalThis.FridayProviderCatalog)){
 const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.name='site';input.value=provider.id;
 label.append(input,document.createTextNode(' '+provider.name+(provider.backup?' — backup, experimental':provider.experimental?' — experimental':'')));document.querySelector('#providers').append(label);
}
const sites = [...document.querySelectorAll('[name="site"]')];
const status = document.querySelector('#status');
let downloadGranted=false;
async function refresh() {
  const state = await chrome.storage.local.get({ enabled: true, sites: Object.keys(globalThis.FridayProviderCatalog), lastStatus: '' });
  enabled.checked = state.enabled;
  downloadGranted=await chrome.permissions.contains({permissions:['downloads']});
  document.querySelector('#downloads').textContent=downloadGranted?'Disable generated download transfer':'Enable generated download transfer';
  for (const site of sites) site.checked = state.sites.includes(site.value);
  const result = await chrome.runtime.sendMessage({ type: 'connector-status' });
  status.textContent = result.ok ? `Friday ready. ${state.enabled ? 'Connection enabled.' : 'Connection disabled.'}\n${state.lastStatus}` : `Start Friday to connect.\n${result.error}`;
}
document.querySelector('#save').addEventListener('click', async () => {
  await chrome.storage.local.set({ enabled: enabled.checked, sites: sites.filter(site => site.checked).map(site => site.value) });
  await chrome.runtime.sendMessage({ type: 'connector-wake' });
  await refresh();
});
void refresh();
document.querySelector('#downloads').addEventListener('click',async()=>{
  if(downloadGranted)await chrome.permissions.remove({permissions:['downloads']});
  else await chrome.permissions.request({permissions:['downloads']});
  await refresh();
});
