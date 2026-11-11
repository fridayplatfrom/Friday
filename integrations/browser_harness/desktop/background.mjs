// Keep provider renderers mounted and painting underneath the opaque native UI.
// Only an explicit native dock selection may place a provider above that UI.
export function presentedDock(dock,revealed){return dock&&{...dock,visible:!!(dock.visible&&revealed?.site===dock.site&&revealed?.sessionId===dock.sessionId)};}
export function arrangeBackgroundViews({contentView,harness,pages,dock,healthy,width,height}){
 harness?.setBounds({x:0,y:0,width,height});harness?.setVisible(healthy);
 let revealed;
 for(const page of pages){
  const show=healthy&&dock?.visible===true&&dock.pageId===page.id;
  if(show){page.view.setBounds(dock.bounds);revealed=page.view;}
  // The recovery shell must stay opaque too if the native interface fails.
  page.view.setVisible(healthy);
 }
 if(harness)contentView.addChildView(harness);
 if(revealed)contentView.addChildView(revealed);
}
