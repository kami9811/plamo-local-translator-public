import { build } from 'esbuild';
import { mkdir, cp, rm } from 'node:fs/promises';
const apiBase=process.env.PLAMO_API_BASE||'http://127.0.0.1:8765';
if(!/^http:\/\/(127\.0\.0\.1|localhost):[0-9]{1,5}$/.test(apiBase))throw new Error('API base must be loopback HTTP');
await rm('dist',{recursive:true,force:true});await mkdir('dist',{recursive:true});
await cp('extension/public','dist',{recursive:true});
await cp('licenses','dist/licenses',{recursive:true});await cp('LICENSE','dist/LICENSE');await cp('NOTICE.md','dist/NOTICE.md');
await build({entryPoints:{background:'extension/src/background.ts',content:'extension/src/content.ts',app:'extension/src/app.ts',popup:'extension/src/popup.ts'},outdir:'dist',define:{__PLAMO_API_BASE__:JSON.stringify(apiBase)},bundle:true,loader:{'.css':'text'},format:'iife',target:'chrome120',minify:false,sourcemap:false});
console.log('Built unpacked Chrome extension in dist/');
