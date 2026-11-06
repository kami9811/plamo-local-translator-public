export type Model = '2b' | '8b';
export interface Options {model:Model; source_lang:'en'|'ja';target_lang:'en'|'ja';form:'plain'|'polite';domain:string;context:string;glossary:{source:string;target:string}[];theme?:'light'|'dark'|'system'}
export interface Segment {skip?:boolean;id:string;source:string;separator:string;translation:string;status:string;warnings:string[];error?:string;metrics?:Record<string,unknown>}
export interface Job {id:string;title:string;format:string;source:string;options:Options;status:string;segments:Segment[];error?:string}
export interface Task {theme?:Options['theme'];id:string;status:string;translation:string;warnings:string[];error?:string;metrics?:{elapsed_seconds:number;ttft_seconds:number;cache_hit:boolean}}
export interface State {engine:{state:string;model:Model|null;error:string;load_seconds:number|null;models:{id:Model;available:boolean;bytes:number}[]};settings:Options;jobs:{id:string;title:string;status:string;total:number;completed:number;format:string}[];profiles:{id:string;name:string;options:Options}[]}
declare const __PLAMO_API_BASE__: string;
export const BASE=typeof __PLAMO_API_BASE__==='string'?__PLAMO_API_BASE__:'http://127.0.0.1:8765';
if(!/^http:\/\/(127\.0\.0\.1|localhost):[0-9]{1,5}$/.test(BASE))throw new Error('接続先はPC内に限ります。');
export const isExtension=typeof chrome!=='undefined' && !!chrome.runtime?.id;
let token='';
export async function readToken(){if(isExtension){const key=(await chrome.storage.local.get('connectionKey')).connectionKey;token=typeof key==='string'?key:'';}return token;}
export async function pair(value:string){token=value.trim();await api('/api/state');if(isExtension)await chrome.storage.local.set({connectionKey:token});}
export async function api<T=unknown>(path:string,method='GET',body?:unknown,signal?:AbortSignal):Promise<T>{
 if(!token)await readToken();
 if(!/^\/api\/[a-z0-9/?=&._-]+$/i.test(path))throw new Error('接続先が不正です。');
 const r=await fetch(BASE+path,{method,redirect:'error',credentials:'omit',referrerPolicy:'no-referrer',headers:{Authorization:'Bearer '+token,...(body!==undefined?{'Content-Type':'application/json'}:{})},body:body===undefined?undefined:JSON.stringify(body),signal});
 const data=await r.json();if(!r.ok)throw new Error(data.error||'ローカルAPIに接続できません。');return data as T;
}
export const wait=(ms:number)=>new Promise<void>(resolve=>setTimeout(resolve,ms));
export const labels:Record<string,string>={queued:'待機中',running:'翻訳中',done:'完了',error:'要確認',paused:'中断',pending:'未処理',cancelled:'キャンセル',ready:'準備完了',loading:'読み込み中',stopped:'停止中'};
export function el<K extends keyof HTMLElementTagNameMap>(tag:K,text?:string,className?:string){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;}
export async function download(name:string,text:string,type='text/plain;charset=utf-8'){const url=URL.createObjectURL(new Blob([text],{type}));const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
