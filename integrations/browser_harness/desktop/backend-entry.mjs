// Private child entrypoint. Only the owning desktop process has this IPC pipe.
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const resources=process.env.FRIDAY_BUNDLED_RESOURCES;
if(!resources||!process.send)throw Error('Friday backend requires its owning desktop process.');
let stopping=false;
const stop=()=>{if(stopping)return;stopping=true;if(process.listenerCount('SIGINT'))process.emit('SIGINT');else process.exit(0);};
process.on('message',message=>{if(message?.type==='friday-stop')stop();});
process.on('disconnect',stop);
const runtime=join(resources,'harness','dsh');
const {runDesktopCli}=await import(pathToFileURL(join(runtime,'node_modules','@deepseek-ai','dsh-desktop-host','lib','cli.js')).href);
await runDesktopCli(runtime,join(resources,'harness','runtime'));
