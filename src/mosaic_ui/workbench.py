"""Local live builder workbench for semantic trees and deterministic projections."""
from __future__ import annotations

import argparse
import copy
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from .authoring import authoring_metadata, mutate_application
from .branding import verified_logo_path
from .canonical import commitment
from .headless import HeadlessUI
from .model import UIRefusal
from .pilot import build_runtime
from .review_ontology import build_review_ontology
from .review_session import ReviewSession
from .review_workbench import REVIEW_WORKBENCH_HTML
from .signature_profile import build_signature_payload
from mosaic_ui_std.signature import load_signature_profile, resolve_signature_theme


WORKBENCH_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mosaic UI Workbench</title><style>
:root{color-scheme:dark;font-family:"Segoe UI",sans-serif;--canvas:#11161a;--surface:#192025;--raised:#222c32;--field:#141b1f;--text:#f0f4f7;--quiet:#a8b3bc;--border:#3c4951;--accent:#55cfaf;--accent-hover:#7ee0c5;--selection:#21483f;--focus:#7db5e8;--info:#78b7ea;--refused:#ef8187;--radius:6px;background:var(--canvas);color:var(--text)}
*{box-sizing:border-box}body{margin:0;height:100vh;overflow:hidden}.shell{display:grid;grid-template-rows:48px 1fr;height:100vh}
header{display:flex;align-items:center;gap:10px;padding:0 14px;border-bottom:1px solid var(--border);background:var(--surface)}
header strong{font-size:16px;white-space:nowrap}.tag{font:12px "Cascadia Mono",Consolas,monospace;color:var(--accent)}.spacer{flex:1}.profile-controls{display:flex;gap:7px}.profile-controls select{max-width:176px}
button,select,input,textarea{font:inherit;color:inherit;background:var(--field);border:1px solid var(--border);border-radius:var(--radius)}
button{height:30px;padding:0 12px;cursor:pointer}button:hover{background:var(--raised)}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid var(--focus);outline-offset:1px}
.main{display:grid;grid-template-columns:300px minmax(420px,1fr) 340px;min-height:0}.pane{min-height:0;border-right:1px solid var(--border);background:var(--surface)}
.pane:last-child{border-right:0;border-left:1px solid var(--border)}.pane h2{font-size:12px;text-transform:uppercase;font-weight:600;margin:0;padding:12px;color:var(--quiet);border-bottom:1px solid var(--border)}
.tree-pane{display:grid;grid-template-rows:auto auto auto 1fr}.tree-search{padding:8px}.tree-search input{width:100%;height:30px;padding:0 9px}.tree-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px;padding:0 8px 8px}.tree-actions button,.tree-actions select{height:28px;min-width:0;padding:0 8px}.tree-actions select{grid-column:1/-1}.tree-actions button:disabled{opacity:.4;cursor:default}.tree{overflow:auto;min-height:0;padding:4px 7px 10px}.treeitem{display:grid;grid-template-columns:14px 54px minmax(0,1fr) 9px;align-items:center;gap:5px;width:100%;height:30px;margin:1px 0;padding:0 6px 0 calc(5px + (var(--depth) - 1)*14px);border:0;background:transparent;text-align:left}.treeitem.active{background:var(--selection);color:var(--text)}.treeitem.hovered{box-shadow:inset 2px 0 var(--focus)}.treeitem .expander{font:14px Consolas,monospace;text-align:center;color:var(--quiet)}.treeitem .kind{font:10px Consolas,monospace;color:var(--quiet);overflow:hidden}.treeitem .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.treeitem .status{width:7px;height:7px;border-radius:50%;background:var(--quiet)}.treeitem .status.PASS{background:var(--accent)}.treeitem .status.ATTENTION{background:var(--refused)}.tree-count{float:right;color:var(--quiet);font:11px Consolas,monospace}
.center{min-width:0;min-height:0;display:grid;grid-template-rows:42px 1fr 144px;background:var(--canvas)}.toolbar{display:flex;align-items:center;gap:8px;padding:6px 10px;border-bottom:1px solid var(--border)}.toolbar input{width:72px;height:28px;padding:0 7px}.viewport{min-height:0;overflow:auto;padding:18px;background:color-mix(in srgb,var(--canvas) 90%,black)}
.stage-wrap{position:relative;margin:auto;background:var(--canvas);box-shadow:0 0 0 1px var(--border),0 14px 36px #0004;transform-origin:top left}.node{position:absolute;overflow:hidden;color:var(--text);border:1px solid var(--border);border-radius:var(--radius);background:var(--surface);padding:7px 10px;text-align:left;font-size:12px}.node.BUTTON{background:var(--selection);font-weight:600}.node.LABEL,.node.STATUS{border-color:transparent;background:transparent}.node.LABEL{font-size:18px;font-weight:600}.node.BADGE{display:flex;align-items:center;justify-content:center;color:var(--accent-hover);background:var(--selection);font-weight:600}.node.PROGRESS{padding:0;background:var(--field)}.node.PROGRESS:after{content:"";display:block;height:100%;width:var(--progress);background:var(--accent)}.node.DATA_GRID{padding:0;overflow:auto}.node.DATA_GRID table{width:100%;border-collapse:collapse}.node.DATA_GRID th,.node.DATA_GRID td{padding:7px 9px;border-bottom:1px solid var(--border)}.node.DATA_GRID th{color:var(--quiet);font-weight:600}.node.NAVIGATION,.node.MENU{display:flex;align-items:center;gap:4px;padding:4px}.node .choice{flex:1;padding:7px;border-radius:4px;text-align:center}.node .choice.active{background:var(--selection);color:var(--accent-hover)}.node.LIST{padding:5px}.node.LIST .choice{display:block;text-align:left}.node.DIALOG{padding:14px}.node.DIALOG strong{display:block;font-size:14px}.node.DIALOG p{color:var(--quiet)}.node.NOTIFICATION{border-left:3px solid var(--info)}.node.selected{outline:2px solid var(--focus);outline-offset:1px}.node.hovered{box-shadow:0 0 0 2px var(--focus)}
.log{border-top:1px solid var(--border);overflow:auto;padding:9px 12px;font:12px/1.5 "Cascadia Mono",Consolas,monospace;color:var(--quiet);white-space:pre-wrap}
.inspector{height:calc(100% - 39px);overflow:auto;padding:12px}.breadcrumb{font:11px/1.5 Consolas,monospace;color:var(--quiet);margin-bottom:12px;word-break:break-word}.field{margin-bottom:12px}.field label{display:block;font-size:12px;color:var(--quiet);margin-bottom:5px}.field input,.field textarea,.field select{width:100%;min-height:30px;padding:5px 7px}.field textarea{height:66px;resize:vertical}.check-field{display:flex;align-items:center;gap:8px;margin-bottom:12px}.check-field input{width:16px;height:16px}.layout-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.layout-grid .field{margin-bottom:4px}.diagnostics{display:flex;flex-wrap:wrap;gap:5px;margin:8px 0 14px}.diagnostic{padding:3px 6px;border:1px solid var(--border);border-radius:var(--radius);font:10px Consolas,monospace;color:var(--quiet)}details{margin-top:14px}summary{cursor:pointer;color:var(--quiet);font-size:12px}.kv{font:12px/1.5 "Cascadia Mono",Consolas,monospace;word-break:break-word;color:var(--quiet)}.error{color:var(--refused)}.pass{color:var(--accent)}
@media(max-width:1000px){.main{grid-template-columns:230px minmax(0,1fr)}.pane:last-child{display:none}.treeitem{grid-template-columns:14px 45px minmax(0,1fr) 9px}}
@media(max-width:860px){
  .shell{grid-template-rows:auto 1fr}
  header{display:grid;grid-template-columns:auto auto 1fr auto auto;gap:7px;padding:8px 10px}
  header .spacer{display:none}header #reset{grid-column:4;grid-row:1}header #export{grid-column:5;grid-row:1}.profile-controls{grid-column:1/-1;grid-row:2;min-width:0}.profile-controls select{flex:1;min-width:0;max-width:none}
  .center{grid-template-rows:auto 1fr 112px}.toolbar{flex-wrap:wrap;gap:6px;padding:6px 8px}.toolbar input{width:66px}.toolbar .spacer{flex-basis:100%}
  .viewport{padding:10px}
}
@media(max-width:680px){.main{grid-template-columns:minmax(0,1fr)}.main>.pane{display:none}}
</style></head><body><div class="shell"><header><strong>Mosaic UI Workbench</strong><span class="tag">SIGNATURE</span><div class="profile-controls"><select id="composition" aria-label="Composition"></select><select id="theme" aria-label="Theme"></select><select id="density" aria-label="Density"></select></div><span class="spacer"></span><button id="reset">Reset</button><button id="export">Export</button></header>
<div class="main"><aside class="pane tree-pane"><h2>Semantic tree <span id="tree-count" class="tree-count"></span></h2><div class="tree-search"><input id="tree-search" type="search" aria-label="Search semantic tree" placeholder="Search nodes"></div><div><div class="tree-actions"><button id="undo" type="button">Undo</button><button id="redo" type="button">Redo</button><button id="move-up" type="button">Move up</button><button id="move-down" type="button">Move down</button></div><div class="tree-actions"><select id="add-kind" aria-label="Component kind"></select><button id="add-node" type="button">Add</button><button id="duplicate-node" type="button">Duplicate</button><button id="delete-node" type="button">Delete</button></div></div><div id="tree" class="tree" role="tree" aria-label="Application semantic tree"></div></aside>
<section class="center"><div class="toolbar"><label>W <input id="width" type="number" min="480" value="1280"></label><label>H <input id="height" type="number" min="400" value="800"></label><button id="resize">Apply viewport</button><span id="gate" class="spacer"></span></div><div id="viewport" class="viewport"><div id="stage" class="stage-wrap"></div></div><div id="log" class="log"></div></section>
<aside class="pane"><h2>Inspector</h2><div id="inspector" class="inspector"><div class="kv">Select a realized node.</div></div></aside></div></div>
<script>
let state=null,selected=null,hovered=null,treeQuery='',treeSubject=null;const collapsed=new Set(),$=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,options){const r=await fetch(path,{headers:{'Content-Type':'application/json'},...options});const v=await r.json();if(!r.ok)throw new Error(v.detail||v.refusal_code||r.statusText);return v}
function nodeIndex(tree,out=[]){out.push(tree);(tree.children||[]).forEach(c=>nodeIndex(c,out));return out}
function options(id,items,value){const e=$(id),signature=JSON.stringify(items);if(e.dataset.items!==signature){e.innerHTML=items.map(x=>`<option value="${esc(x.value??x)}">${esc(x.label??String(x).replaceAll('-',' '))}</option>`).join('');e.dataset.items=signature}e.value=value}
function applyTokens(){const t=state.presentation.tokens,c=t.colors,r=document.documentElement.style,map={canvas:c.canvas,surface:c.surface,raised:c.surface_raised,field:c.field,text:c.text,quiet:c.text_quiet,border:c.border,accent:c.accent,'accent-hover':c.accent_hover,selection:c.selection,focus:c.focus,info:c.info,refused:c.refused};for(const [k,v] of Object.entries(map))r.setProperty('--'+k,v);r.setProperty('--radius',t.radii.md+'px');r.fontFamily=t.typography.roles.body.family+',sans-serif';r.colorScheme=state.projection.gates.color_scheme.toLowerCase();const s=state.presentation.selection;options('#composition',state.presentation.compositions,s.composition_id);options('#theme',state.presentation.themes,s.theme_id);options('#density',state.presentation.densities,s.density_id)}
function render(){applyTokens();const p=state.projection,g=p.geometry,gmap=new Map(g.nodes.map(n=>[n.node_id,n.rect])),smap=new Map(p.semantics.nodes.map(n=>[n.node_id,n])),sources=new Map(nodeIndex(state.application.tree).map(n=>[n.node_id,n]));
 $('#gate').innerHTML=p.gates.disposition==='PASS'?'<span class="pass">Gates PASS</span>':'<span class="error">Gates REFUSE '+p.gates.failure_count+'</span>';
 const stage=$('#stage');stage.style.width=g.viewport.width+'px';stage.style.height=g.viewport.height+'px';stage.innerHTML='';
 const scale=Math.min(1,($('#viewport').clientWidth-40)/g.viewport.width);stage.style.transform='scale('+scale+')';stage.parentElement.style.setProperty('min-height',Math.ceil(g.viewport.height*scale+36)+'px');
 for(const [id,r] of gmap){const n=smap.get(id);if(!n)continue;const src=sources.get(id),props=src.props||{},e=document.createElement(n.kind==='BUTTON'?'button':'div');e.className='node '+n.kind+(selected===id?' selected':'')+(hovered===id?' hovered':'');e.dataset.id=id;e.style.cssText+=`;left:${r.x}px;top:${r.y}px;width:${r.width}px;height:${r.height}px`;e.style.setProperty('--progress',(n.value||0)+'%');
  const choices=props.options||props.items||[];if(n.kind==='DATA_GRID'){const head=(props.columns||[]).map(x=>`<th>${esc(x)}</th>`).join(''),rows=(props.rows||[]).map(row=>`<tr>${row.map(x=>`<td>${esc(x)}</td>`).join('')}</tr>`).join('');e.innerHTML=`<table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`}else if(['NAVIGATION','MENU','LIST'].includes(n.kind)){e.innerHTML=choices.map(x=>`<span class="choice ${(x.value??x)===n.value?'active':''}">${esc(x.label??x)}</span>`).join('')}else if(n.kind==='DIALOG'){e.innerHTML=`<strong>${esc(n.semantics.name)}</strong><p>${esc(props.message)}</p><span class="choice active">${esc((props.decisions||[])[0]?.label||'Apply')}</span>`}else if(n.kind==='PROGRESS'){e.title=n.semantics.name}else{let text=n.semantics.name;if(n.value!==null&&n.value!==undefined&&!['BUTTON','LABEL','STATUS','BADGE'].includes(n.kind))text=n.semantics.name+': '+String(n.value);e.textContent=text}e.onclick=()=>select(id);e.onmouseenter=()=>setHover(id);e.onmouseleave=()=>setHover(null);if(n.operation_ref)e.ondblclick=()=>event({intent:'ACTIVATE',node_id:id});stage.appendChild(e)}
 renderTree();renderInspector(sources);configureCommands();
 $('#log').textContent=JSON.stringify({runtime_head:state.runtime.ledger_head,gates:p.gates,revision:state.revision},null,2)}
function renderTree(){const subject=state.presentation.selection.composition_id;if(treeSubject!==subject){treeSubject=subject;collapsed.clear();for(const row of state.authoring.nodes)if(row.child_count&&row.depth>=2)collapsed.add(row.node_id)}const rows=state.authoring.nodes,byId=new Map(rows.map(row=>[row.node_id,row])),query=treeQuery.trim().toLowerCase(),included=new Set();if(query){for(const row of rows)if((row.node_id+' '+row.kind+' '+row.name).toLowerCase().includes(query))for(const id of row.path)included.add(id)}const visible=rows.filter(row=>query?included.has(row.node_id):row.path.slice(0,-1).every(id=>!collapsed.has(id)));$('#tree-count').textContent=visible.length+'/'+rows.length;$('#tree').innerHTML=visible.map(row=>`<button type="button" role="treeitem" aria-level="${row.depth}" ${row.child_count?`aria-expanded="${!collapsed.has(row.node_id)}"`:''} aria-selected="${selected===row.node_id}" tabindex="${selected===row.node_id?'0':'-1'}" data-id="${esc(row.node_id)}" class="treeitem${selected===row.node_id?' active':''}${hovered===row.node_id?' hovered':''}" style="--depth:${row.depth}"><span class="expander" aria-hidden="true">${row.child_count?(collapsed.has(row.node_id)?'+':'-'):''}</span><span class="kind">${esc(row.kind)}</span><span class="name">${esc(row.name)}</span><span class="status ${esc(row.disposition)}" title="${esc(row.disposition)}"></span></button>`).join('');for(const item of $('#tree').querySelectorAll('.treeitem')){const id=item.dataset.id,row=byId.get(id);item.onclick=e=>{if(e.target.classList.contains('expander')&&row.child_count){collapsed.has(id)?collapsed.delete(id):collapsed.add(id);renderTree();return}select(id,true)};item.onmouseenter=()=>setHover(id);item.onmouseleave=()=>setHover(null);item.onkeydown=e=>treeKey(e,id,visible,byId)}}
function treeKey(e,id,rows,byId){const index=rows.findIndex(row=>row.node_id===id),row=byId.get(id);if(e.key==='ArrowDown'&&index<rows.length-1){e.preventDefault();select(rows[index+1].node_id,true)}else if(e.key==='ArrowUp'&&index>0){e.preventDefault();select(rows[index-1].node_id,true)}else if(e.key==='Home'){e.preventDefault();select(rows[0].node_id,true)}else if(e.key==='End'){e.preventDefault();select(rows[rows.length-1].node_id,true)}else if(e.key==='ArrowRight'&&row.child_count){e.preventDefault();if(collapsed.has(id)){collapsed.delete(id);renderTree();focusTree(id)}else{const child=rows.find(candidate=>candidate.parent_id===id);if(child)select(child.node_id,true)}}else if(e.key==='ArrowLeft'){e.preventDefault();if(row.child_count&&!collapsed.has(id)){collapsed.add(id);renderTree();focusTree(id)}else if(row.parent_id)select(row.parent_id,true)}else if(e.key==='Enter'||e.key===' '){e.preventDefault();select(id,true)}}
function focusTree(id){queueMicrotask(()=>{const item=[...$('#tree').querySelectorAll('.treeitem')].find(element=>element.dataset.id===id);if(item){item.focus();item.scrollIntoView({block:'nearest'})}})}
function setHover(id){hovered=id;for(const element of document.querySelectorAll('[data-id]'))element.classList.toggle('hovered',element.dataset.id===id)}
function select(id,focus=false){selected=id;const row=state.authoring.nodes.find(item=>item.node_id===id);for(const ancestor of row?.path.slice(0,-1)||[])collapsed.delete(ancestor);render();if(focus)focusTree(id)}
function renderInspector(sources){const row=state.authoring.nodes.find(item=>item.node_id===selected),source=sources.get(selected);if(!row||!source){$('#inspector').innerHTML='<div class="kv">Select a semantic node.</div>';return}const byId=new Map(state.authoring.nodes.map(item=>[item.node_id,item])),path=row.path.map(id=>byId.get(id)?.name||id).join(' / '),sem=source.semantics||{},props=source.props||{},layout=props.layout_item||{},container=props.layout;$('#inspector').innerHTML=`<div class="breadcrumb">${esc(path)}</div><div class="diagnostics">${row.diagnostics.map(item=>`<span class="diagnostic">${esc(item)}</span>`).join('')}</div><div class="field"><label>Node ID</label><input value="${esc(row.node_id)}" disabled></div><div class="field"><label>Kind</label><input value="${esc(row.kind)}" disabled></div><div class="field"><label for="edit-name">Accessible name</label><input id="edit-name" value="${esc(sem.name)}"></div><div class="field"><label for="edit-description">Description</label><textarea id="edit-description">${esc(sem.description||'')}</textarea></div><label class="check-field"><input id="edit-focusable" type="checkbox" ${sem.focusable?'checked':''}>Focusable</label><div class="field"><label>Layout item</label><div class="layout-grid">${['height','width','grow','span'].map(key=>`<div class="field"><label for="layout-${key}">${key}</label><input id="layout-${key}" type="number" min="${key==='grow'||key==='span'?1:0}" value="${layout[key]??''}"></div>`).join('')}</div></div>${container?`<div class="field"><label for="layout-type">Container layout</label><select id="layout-type"><option>COLUMN</option><option>ROW</option><option>GRID</option></select></div><div class="layout-grid"><div class="field"><label for="layout-gap">gap</label><input id="layout-gap" type="number" min="0" value="${container.gap??''}"></div><div class="field"><label for="layout-padding">padding</label><input id="layout-padding" type="number" min="0" value="${container.padding??''}"></div></div>`:''}<button id="apply-node" type="button">Apply changes</button><details><summary>Node evidence</summary><div class="kv">${esc(JSON.stringify(row,null,2))}</div></details>`;if(container)$('#layout-type').value=container.type;$('#apply-node').onclick=()=>applyNode(source)}
function numeric(id){const element=$(id);return element&&element.value!==''?Number(element.value):null}
async function applyNode(source){try{const app=structuredClone(state.application),target=nodeIndex(app.tree).find(x=>x.node_id===source.node_id);target.semantics.name=$('#edit-name').value.trim();target.semantics.description=$('#edit-description').value;target.semantics.focusable=$('#edit-focusable').checked;target.semantics.actions=target.semantics.focusable?['select']:[];if('display_text' in target.props)target.props.display_text=target.semantics.name;const item={};for(const key of ['height','width','grow','span']){const value=numeric('#layout-'+key);if(value!==null)item[key]=value}if(Object.keys(item).length)target.props.layout_item=item;else delete target.props.layout_item;if(target.props.layout&&$('#layout-type')){target.props.layout.type=$('#layout-type').value;for(const key of ['gap','padding']){const value=numeric('#layout-'+key);if(value===null)delete target.props.layout[key];else target.props.layout[key]=value}}state=await api('/api/document',{method:'PUT',body:JSON.stringify({application:app,selected_node_id:selected,width:+$('#width').value,height:+$('#height').value})});selected=state.authoring.selected_node_id||selected;render()}catch(e){$('#log').textContent=e.stack}}
function configureCommands(){const rows=state.authoring.nodes,row=rows.find(item=>item.node_id===selected),parent=row&&rows.find(item=>item.node_id===row.parent_id),siblings=parent?rows.filter(item=>item.parent_id===parent.node_id):[],index=siblings.findIndex(item=>item.node_id===selected);$('#undo').disabled=!state.authoring.can_undo;$('#redo').disabled=!state.authoring.can_redo;$('#add-node').disabled=!row;$('#duplicate-node').disabled=!row||row.protected;$('#delete-node').disabled=!row||row.protected;$('#move-up').disabled=!row||row.protected||index<=0;$('#move-down').disabled=!row||row.protected||index<0||index>=siblings.length-1;options('#add-kind',state.authoring.addable_kinds,$('#add-kind').value||'LABEL')}
async function mutate(operation){if(!selected)return;try{const body={operation,node_id:selected,width:+$('#width').value,height:+$('#height').value};if(operation==='ADD_CHILD'){body.kind=$('#add-kind').value;body.name=body.kind.replaceAll('_',' ').toLowerCase().replace(/^./,letter=>letter.toUpperCase())}state=await api('/api/mutation',{method:'POST',body:JSON.stringify(body)});selected=state.authoring.selected_node_id;for(const id of state.authoring.nodes.find(item=>item.node_id===selected)?.path||[])collapsed.delete(id);render();focusTree(selected)}catch(e){$('#log').textContent=e.stack}}
async function history(action){try{state=await api('/api/history',{method:'POST',body:JSON.stringify({action,width:+$('#width').value,height:+$('#height').value})});selected=state.authoring.selected_node_id||state.authoring.nodes[0]?.node_id;render()}catch(e){$('#log').textContent=e.stack}}
async function event(v){try{state=await api('/api/event',{method:'POST',body:JSON.stringify({event:v,width:+$('#width').value,height:+$('#height').value})});render()}catch(e){$('#log').textContent=e.stack}}
async function presentation(){try{state=await api('/api/presentation',{method:'PUT',body:JSON.stringify({selection:{composition_id:$('#composition').value,theme_id:$('#theme').value,density_id:$('#density').value},width:+$('#width').value,height:+$('#height').value})});selected=state.authoring.nodes[0]?.node_id;render()}catch(e){$('#log').textContent=e.stack}}
async function load(){state=await api('/api/state?width='+$('#width').value+'&height='+$('#height').value);selected=state.authoring.selected_node_id||selected||state.authoring.nodes[0]?.node_id;render()}
$('#resize').onclick=load;$('#composition').onchange=presentation;$('#theme').onchange=presentation;$('#density').onchange=presentation;$('#tree-search').oninput=e=>{treeQuery=e.target.value;renderTree()};$('#undo').onclick=()=>history('UNDO');$('#redo').onclick=()=>history('REDO');$('#add-node').onclick=()=>mutate('ADD_CHILD');$('#duplicate-node').onclick=()=>mutate('DUPLICATE');$('#delete-node').onclick=()=>{if(confirm('Delete the selected semantic node?'))mutate('DELETE')};$('#move-up').onclick=()=>mutate('MOVE_UP');$('#move-down').onclick=()=>mutate('MOVE_DOWN');$('#reset').onclick=async()=>{state=await api('/api/reset',{method:'POST',body:'{}'});selected=state.authoring.nodes[0]?.node_id;treeSubject=null;render()};$('#export').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(state.application,null,2)],{type:'application/json'}));a.download='mosaic-ui-application.json';a.click();URL.revokeObjectURL(a.href)};addEventListener('keydown',e=>{if(!(e.ctrlKey||e.metaKey)||['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName))return;if(e.key.toLowerCase()==='z'){e.preventDefault();history(e.shiftKey?'REDO':'UNDO')}else if(e.key.toLowerCase()==='y'){e.preventDefault();history('REDO')}});addEventListener('resize',()=>state&&render());load().catch(e=>$('#log').textContent=e.stack);
</script></body></html>"""


class WorkbenchSession:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.revision = 0
        self.runtime = build_runtime()
        self.profile = load_signature_profile()
        self.review_ontology = build_review_ontology()
        self.review = ReviewSession(self.review_ontology, realizer="BROWSER")
        self.selection = {
            "composition_id": "operational-dashboard",
            "theme_id": self.profile["default_theme"],
            "density_id": self.profile["default_density"],
        }
        self.preview = HeadlessUI(build_signature_payload(**self.selection))
        self.undo_stack: list[dict[str, Any]] = []
        self.redo_stack: list[dict[str, Any]] = []
        self.last_operation: dict[str, Any] | None = None
        self.selected_node_id: str | None = None

    @property
    def ui(self) -> HeadlessUI:
        return self.preview

    def _presentation(self) -> dict[str, Any]:
        resolved = resolve_signature_theme(self.selection["theme_id"], self.selection["density_id"])
        return {
            "profile_id": self.profile["profile_id"], "profile_version": self.profile["profile_version"],
            "selection": copy.deepcopy(self.selection),
            "compositions": [{"value": item["composition_id"], "label": item["name"]}
                             for item in self.profile["compositions"]],
            "themes": list(self.profile["themes"]), "densities": list(self.profile["densities"]),
            "tokens": resolved["tokens"], "control_height": resolved["control_height"],
            "resolution_commitment": resolved["commitment"], "authority_effect": "NONE",
        }

    def state(self, width: int, height: int) -> dict[str, Any]:
        with self.lock:
            projection = self.ui.project(width, height).as_dict()
            value = {
                "schema": "mosaic.ui.builder-workbench-state.v0.1",
                "revision": self.revision,
                "application": copy.deepcopy(self.ui.application),
                "projection": projection,
                "presentation": self._presentation(),
                "runtime": self.runtime.snapshot(),
                "standing": "LOCAL_CANDIDATE_EVIDENCE",
                "authority_effect": "NONE",
                "claim_boundary": "BROWSER_WORKBENCH_IS_A_REVIEW_SURFACE_NOT_A_PRODUCTION_REALIZER",
            }
            value["authoring"] = authoring_metadata(
                value["application"], projection, undo_depth=len(self.undo_stack),
                redo_depth=len(self.redo_stack), last_operation=self.last_operation,
                selected_node_id=self.selected_node_id,
            )
            value["commitment"] = commitment("MOSAIC.UI.BUILDER_WORKBENCH_STATE.v0.1", value)
            return value

    def ontology(self) -> dict[str, Any]:
        with self.lock:
            return copy.deepcopy(self.review_ontology)

    def review_state(self) -> dict[str, Any]:
        with self.lock:
            return self.review.state()

    def review_action(self, action: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            return self.review.dispatch(action)

    def review_snapshot(self) -> dict[str, Any]:
        with self.lock:
            return self.review.snapshot()

    def event(self, event: dict[str, Any], width: int, height: int) -> dict[str, Any]:
        with self.lock:
            self.preview.apply(event)
            self.revision += 1
            return self.state(width, height)

    def set_presentation(self, selection: dict[str, Any], width: int, height: int) -> dict[str, Any]:
        with self.lock:
            if not isinstance(selection, dict) or set(selection) != set(self.selection):
                raise UIRefusal("WORKBENCH_PRESENTATION_REFUSED", "SELECTION_SHAPE")
            candidate = HeadlessUI(build_signature_payload(**selection))
            projection = candidate.project(width, height)
            if projection.gates["disposition"] != "PASS":
                raise UIRefusal("WORKBENCH_PRESENTATION_REFUSED", json.dumps(projection.gates["failures"], sort_keys=True))
            self.selection = copy.deepcopy(selection)
            self.preview = candidate
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.last_operation = None
            self.selected_node_id = None
            self.revision += 1
            return self.state(width, height)

    def _candidate(self, application: dict[str, Any], width: int, height: int) -> HeadlessUI:
        payload = build_signature_payload(**self.selection)
        payload["application"] = copy.deepcopy(application)
        payload["input_root"] = commitment("MOSAIC.UI.SIGNATURE.WORKBENCH_DRAFT.v0.1", {
            "library": payload["library"], "application": payload["application"],
            "signature": payload["signature"],
        })
        candidate = HeadlessUI(payload)
        projection = candidate.project(width, height)
        if projection.gates["disposition"] != "PASS":
            raise UIRefusal("WORKBENCH_DRAFT_GATES_REFUSED", json.dumps(projection.gates["failures"], sort_keys=True))
        return candidate

    def _install(self, application: dict[str, Any], width: int, height: int, *,
                 operation: dict[str, Any], selected_node_id: str | None,
                 record_history: bool = True) -> dict[str, Any]:
        candidate = self._candidate(application, width, height)
        current = copy.deepcopy(self.ui.application)
        if record_history and current != application:
            self.undo_stack.append(current)
            del self.undo_stack[:-50]
            self.redo_stack.clear()
        self.preview = candidate
        self.last_operation = copy.deepcopy(operation)
        self.selected_node_id = selected_node_id
        self.revision += 1
        return self.state(width, height)

    def replace(self, application: dict[str, Any], width: int, height: int,
                selected_node_id: str | None = None) -> dict[str, Any]:
        with self.lock:
            operation = {
                "schema": "mosaic.ui.authoring-operation.v0.1", "operation": "UPDATE_NODE",
                "before_commitment": commitment("MOSAIC.UI.AUTHORING.APPLICATION.v0.1", self.ui.application),
                "after_commitment": commitment("MOSAIC.UI.AUTHORING.APPLICATION.v0.1", application),
                "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
            }
            operation["commitment"] = commitment("MOSAIC.UI.AUTHORING_OPERATION.v0.1", operation)
            return self._install(application, width, height, operation=operation,
                                 selected_node_id=selected_node_id or self.selected_node_id)

    def mutate(self, operation: str, node_id: str, width: int, height: int, *,
               kind: str | None = None, name: str | None = None) -> dict[str, Any]:
        with self.lock:
            application, selected, receipt = mutate_application(
                self.ui.application, operation, node_id, kind=kind, name=name,
            )
            return self._install(application, width, height, operation=receipt,
                                 selected_node_id=selected)

    def history(self, action: str, width: int, height: int) -> dict[str, Any]:
        with self.lock:
            if action not in {"UNDO", "REDO"}:
                raise UIRefusal("AUTHORING_HISTORY_REFUSED", action)
            source = self.undo_stack if action == "UNDO" else self.redo_stack
            target = self.redo_stack if action == "UNDO" else self.undo_stack
            if not source:
                raise UIRefusal("AUTHORING_HISTORY_EMPTY", action)
            application = copy.deepcopy(source[-1])
            candidate = self._candidate(application, width, height)
            current = copy.deepcopy(self.ui.application)
            source.pop()
            target.append(current)
            del target[:-50]
            receipt = {
                "schema": "mosaic.ui.authoring-operation.v0.1", "operation": action,
                "before_commitment": commitment("MOSAIC.UI.AUTHORING.APPLICATION.v0.1", current),
                "after_commitment": commitment("MOSAIC.UI.AUTHORING.APPLICATION.v0.1", application),
                "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
            }
            receipt["commitment"] = commitment("MOSAIC.UI.AUTHORING_OPERATION.v0.1", receipt)
            self.preview = candidate
            self.last_operation = receipt
            self.selected_node_id = None
            self.revision += 1
            return self.state(width, height)

    def reset(self) -> dict[str, Any]:
        with self.lock:
            self.runtime = build_runtime()
            self.selection = {
                "composition_id": "operational-dashboard",
                "theme_id": self.profile["default_theme"],
                "density_id": self.profile["default_density"],
            }
            self.preview = HeadlessUI(build_signature_payload(**self.selection))
            self.review = ReviewSession(self.review_ontology, realizer="BROWSER")
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.last_operation = None
            self.selected_node_id = None
            self.revision += 1
            return self.state(1280, 800)


def authoring_witness() -> dict[str, Any]:
    """Exercise the refuse-closed authoring transaction and history surfaces."""
    session = WorkbenchSession()
    cases: list[dict[str, Any]] = []

    def record(case_id: str, state: dict[str, Any], expected_nodes: int) -> None:
        passed = state["projection"]["gates"]["disposition"] == "PASS" \
            and state["authoring"]["node_count"] == expected_nodes
        cases.append({
            "case_id": case_id, "node_count": state["authoring"]["node_count"],
            "expected_node_count": expected_nodes,
            "authoring_commitment": state["authoring"]["commitment"],
            "gate_commitment": state["projection"]["gates"]["commitment"],
            "operation_commitment": (state["authoring"].get("last_operation") or {}).get("commitment"),
            "disposition": "PASS" if passed else "REFUSE",
        })

    record("HIERARCHY", session.state(1280, 800), 16)
    added = session.mutate("ADD_CHILD", "ops.actions", 1280, 800, kind="LABEL", name="Review note")
    record("ADD_CHILD", added, 17)
    record("UNDO", session.history("UNDO", 1280, 800), 16)
    record("REDO", session.history("REDO", 1280, 800), 17)
    duplicated = session.mutate("DUPLICATE", "ops.refresh", 1280, 800)
    copy_id = str(duplicated["authoring"]["selected_node_id"])
    record("DUPLICATE", duplicated, 18)
    record("MOVE_DOWN", session.mutate("MOVE_DOWN", copy_id, 1280, 800), 18)
    record("DELETE", session.mutate("DELETE", copy_id, 1280, 800), 17)
    value = {
        "schema": "mosaic.ui.workbench-authoring-witness.v0.1",
        "case_count": len(cases), "cases": cases,
        "disposition": "PASS_LOCAL_CANDIDATE" if all(case["disposition"] == "PASS" for case in cases)
                       else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "DETERMINISTIC_AUTHORING_TRANSACTIONS_DO_NOT_ESTABLISH_COMPLETE_HUMAN_USABILITY",
    }
    value["commitment"] = commitment("MOSAIC.UI.WORKBENCH_AUTHORING_WITNESS.v0.1", value)
    return value


def handler_factory(
    session: WorkbenchSession, selection: tuple[str, str] | None = None,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "MosaicUIWorkbench/0.7"

        def log_message(self, _format: str, *args: Any) -> None:
            return None

        def _json(self, value: Any, status: int = 200) -> None:
            body = json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json_download(self, value: Any, filename: str) -> None:
            body = (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _input(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 2_000_000:
                raise UIRefusal("WORKBENCH_REQUEST_SIZE_REFUSED", str(length))
            value = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(value, dict):
                raise UIRefusal("WORKBENCH_REQUEST_REFUSED", "not-object")
            return value

        def _dimensions(self, query: str = "") -> tuple[int, int]:
            from urllib.parse import parse_qs, urlsplit

            values = parse_qs(urlsplit(query or self.path).query)
            width = int(values.get("width", [1280])[0])
            height = int(values.get("height", [800])[0])
            return width, height

        def do_GET(self) -> None:
            if self.path == "/" or self.path.startswith("/?") or self.path.startswith("/index.html"):
                from .review_library import resolve_request

                status, page = resolve_request(self.path, selection)
                body = page.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path in {"/library", "/library/"}:
                from .review_library import library_page

                body = library_page().encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/assets/deeper-logo.png":
                body = verified_logo_path().read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path in {"/authoring", "/authoring/"} or self.path.startswith("/authoring?"):
                body = WORKBENCH_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path.startswith("/api/review-ontology"):
                self._json(session.ontology())
                return
            if self.path.startswith("/api/review-snapshot"):
                snapshot = session.review_snapshot()
                if "download=1" in self.path:
                    self._json_download(snapshot, "mosaic-ui-review-session.json")
                else:
                    self._json(snapshot)
                return
            if self.path.startswith("/api/review-session"):
                self._json(session.review_state())
                return
            if self.path.startswith("/api/state"):
                try:
                    self._json(session.state(*self._dimensions()))
                except Exception as exc:
                    self._refusal(exc)
                return
            self._json({"detail": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            try:
                value = self._input()
                if self.path == "/api/event":
                    self._json(session.event(value.get("event", {}), int(value.get("width", 1280)), int(value.get("height", 800))))
                elif self.path == "/api/reset":
                    self._json(session.reset())
                elif self.path == "/api/review-action":
                    self._json(session.review_action(value.get("action", {})))
                elif self.path == "/api/mutation":
                    self._json(session.mutate(
                        str(value.get("operation", "")), str(value.get("node_id", "")),
                        int(value.get("width", 1280)), int(value.get("height", 800)),
                        kind=value.get("kind"), name=value.get("name"),
                    ))
                elif self.path == "/api/history":
                    self._json(session.history(
                        str(value.get("action", "")), int(value.get("width", 1280)),
                        int(value.get("height", 800)),
                    ))
                else:
                    self._json({"detail": "not found"}, HTTPStatus.NOT_FOUND)
            except Exception as exc:
                self._refusal(exc)

        def do_PUT(self) -> None:
            try:
                value = self._input()
                if self.path == "/api/presentation":
                    self._json(session.set_presentation(value.get("selection", {}), int(value.get("width", 1280)), int(value.get("height", 800))))
                    return
                if self.path != "/api/document":
                    self._json({"detail": "not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._json(session.replace(
                    value.get("application", {}), int(value.get("width", 1280)),
                    int(value.get("height", 800)), value.get("selected_node_id"),
                ))
            except Exception as exc:
                self._refusal(exc)

        def _refusal(self, exc: Exception) -> None:
            self._json({
                "schema": "mosaic.ui.builder-workbench-refusal.v0.1",
                "disposition": "REFUSE", "refusal_code": getattr(exc, "code", "WORKBENCH_REQUEST_REFUSED"),
                "detail": getattr(exc, "detail", str(exc)), "authority_effect": "NONE",
            }, HTTPStatus.BAD_REQUEST)

    return Handler


def create_server(
    host: str = "127.0.0.1", port: int = 0, *, pack: str | None = None, theme: str | None = None,
) -> tuple[ThreadingHTTPServer, WorkbenchSession]:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise UIRefusal("WORKBENCH_BIND_REFUSED", host)
    if (pack is None) != (theme is None):
        raise UIRefusal("REVIEW_LIBRARY_SELECTION_INCOMPLETE", "pack and theme are required together")
    selection = None
    if pack is not None and theme is not None:
        from .review_library import validate_selection

        validate_selection(pack, theme)
        selection = (pack, theme)
    session = WorkbenchSession()
    return ThreadingHTTPServer((host, port), handler_factory(session, selection)), session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Mosaic UI live builder workbench")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--pack")
    parser.add_argument("--theme")
    args = parser.parse_args(argv)
    server, _ = create_server(args.host, args.port, pack=args.pack, theme=args.theme)
    host, port = server.server_address[:2]
    print(json.dumps({"url": f"http://{host}:{port}/", "standing": "LOCAL_CANDIDATE", "authority_effect": "NONE"}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
