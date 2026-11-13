"""Gera docs/index.html: página única e autocontida com o alerta do dia, histórico e filtros."""
import datetime, json, sys

CAMPOS = ["data", "edicao", "tipo_edicao", "classe", "titulo", "instrumento", "orgao", "sei", "valor_max",
          "excerto", "url_pdf", "sev", "alertas", "prioridades", "ordem", "id_edicao"]

MODELO = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOM Anápolis · Alerta do dia</title>
<style>
:root{color-scheme:light;--bg:#f6f5f2;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#6f6e69;--line:#e1dfd9;
--blue:#2a78d6;--blue-soft:#cde2fb;--crit:#d03b3b;--serious:#ec835a;--info:#2a78d6;--focus:#184f95}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#121211;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#9a998f;--line:#353533;
--blue:#3987e5;--blue-soft:#184f95;--focus:#9ec5f4}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:20px 16px 60px}
header.top{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin-bottom:18px}
h1{font-size:20px;margin:0}h1 small{display:block;font-weight:400;color:var(--muted);font-size:13px;margin-top:2px}
h2{font-size:16px;margin:28px 0 10px}h3{font-size:14px;margin:0 0 6px}
.nav{display:flex;gap:6px;align-items:center}
button,select,input{font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:7px 10px}
button{cursor:pointer}button:hover{border-color:var(--muted)}button:focus-visible,select:focus-visible,input:focus-visible,a:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.tile .n{font-size:26px;font-weight:650;line-height:1.1}.tile .l{color:var(--ink2);font-size:13px}.tile .c{color:var(--muted);font-size:12px;margin-top:2px}
.chip{display:inline-flex;gap:5px;align-items:center;font-size:12px;font-weight:650;border:1px solid currentColor;border-radius:999px;padding:1px 9px;color:var(--ink)}
.chip i{font-style:normal;font-size:11px}
.ALTA .chip,.chip.ALTA{border-color:var(--crit)}.MEDIA .chip,.chip.MEDIA{border-color:var(--serious)}.ACOMPANHAR .chip,.chip.ACOMPANHAR{border-color:var(--info)}
.ALTA .chip i,.chip.ALTA i{color:var(--crit)}.MEDIA .chip i,.chip.MEDIA i{color:var(--serious)}.ACOMPANHAR .chip i,.chip.ACOMPANHAR i{color:var(--info)}
.card{background:var(--surface);border:1px solid var(--line);border-left:5px solid var(--info);border-radius:10px;padding:12px 14px;margin:0 0 10px}
.card.ALTA{border-left-color:var(--crit)}.card.MEDIA{border-left-color:var(--serious)}
.card header{display:flex;flex-wrap:wrap;gap:8px;align-items:center;color:var(--ink2);font-size:13px;margin-bottom:4px}
.card h4{margin:0 0 4px;font-size:14.5px}.motivo{margin:2px 0;font-size:13.5px}.exc{margin:6px 0;color:var(--ink2);font-size:13px}
.card footer{color:var(--muted);font-size:12.5px;display:flex;flex-wrap:wrap;gap:4px 14px}a{color:var(--blue)}
.dia-alert{border:1px solid var(--line);border-left:5px solid var(--crit);background:var(--surface);border-radius:10px;padding:10px 14px;margin-bottom:10px}
.dia-alert.MEDIA{border-left-color:var(--serious)}
details.mais>summary{cursor:pointer;color:var(--ink2);margin:6px 0 10px}
.vazio{color:var(--ink2);padding:14px;border:1px dashed var(--line);border-radius:10px}
.prio{display:flex;flex-wrap:wrap;gap:8px}.prio button{display:flex;gap:8px;align-items:center}.prio b{background:var(--blue-soft);color:var(--ink);border-radius:999px;padding:0 8px;font-size:12px}
#grafico{position:relative}svg text{fill:var(--ink2);font-size:11px}.leg{display:flex;gap:16px;font-size:12.5px;color:var(--ink2);margin:0 0 6px}.leg span{display:inline-flex;gap:6px;align-items:center}.sw{width:12px;height:12px;border-radius:3px;display:inline-block}
#tip{position:absolute;pointer-events:none;background:var(--ink);color:var(--bg);font-size:12px;padding:6px 9px;border-radius:6px;display:none;white-space:nowrap;z-index:5}
.filtros{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}.filtros input{min-width:220px;flex:1}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--ink2);font-weight:600;position:sticky;top:0;background:var(--surface)}
.scroll{overflow:auto;max-height:560px;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
.nota{color:var(--muted);font-size:12.5px;margin-top:22px}
</style></head><body><div class="wrap">
<header class="top"><h1>DOM Anápolis · Alerta do dia<small>Monitoramento do Diário Oficial do Município para a SEGOV</small></h1>
<div class="nav"><button id="ant" aria-label="Dia anterior">◀</button><select id="seldia" aria-label="Escolher dia"></select><button id="prox" aria-label="Próximo dia">▶</button></div></header>
<section id="hoje"></section>
<h2>Prioridades de governo no dia <span style="font-weight:400;color:var(--muted);font-size:13px">(clique para filtrar a tabela)</span></h2>
<div class="prio" id="prio"></div>
<h2>Últimos 30 dias com edição</h2>
<div class="panel"><div class="leg"><span><i class="sw" style="background:var(--crit)"></i>Alta</span><span><i class="sw" style="background:var(--serious)"></i>Média</span><span style="color:var(--muted)">clique numa barra para abrir o dia</span></div><div id="grafico"><div id="tip"></div></div></div>
<h2>Todos os atos</h2>
<div class="filtros"><input id="q" type="search" placeholder="Buscar por assunto, SEI, instrumento…" aria-label="Buscar">
<select id="fsev"><option value="">Qualquer alerta</option><option value="ALTA">Alta</option><option value="MEDIA">Média</option><option value="ACOMPANHAR">Acompanhar</option><option value="-">Sem alerta</option></select>
<select id="forg"><option value="">Todos os órgãos</option></select><select id="fcla"><option value="">Todos os tipos</option></select>
<select id="fpri"><option value="">Todas as prioridades</option></select><button id="csv">Baixar CSV</button></div>
<div class="scroll"><table><thead><tr><th>Alerta</th><th>Data</th><th>Órgão</th><th>Ato</th><th>Valor</th><th>SEI</th><th></th></tr></thead><tbody id="tb"></tbody></table></div>
<div id="conta" class="nota"></div>
<p class="nota" id="rodape"></p>
</div>
<script type="application/json" id="dados">__DADOS__</script>
<script>
const D=JSON.parse(document.getElementById('dados').textContent);
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const SEV={ALTA:['▲','Alta'],MEDIA:['◆','Média'],ACOMPANHAR:['●','Acompanhar']};
const ORD={ALTA:3,MEDIA:2,ACOMPANHAR:1,'':0};
const chip=s=>s?`<span class="chip ${s}"><i>${SEV[s][0]}</i>${SEV[s][1]}</span>`:'<span style="color:var(--muted)">—</span>';
const brl=v=>v==null?'—':'R$ '+v.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});
const dt=iso=>{const d=new Date(iso+'T12:00:00');return d.toLocaleDateString('pt-BR',{weekday:'short',day:'2-digit',month:'2-digit',year:'numeric'})};
const datas=Object.keys(D.resumo).sort();let dia=datas[datas.length-1];let prioSel='';
function atosDoDia(d){return D.atos.filter(a=>a.data===d)}
function media(campo,d){const i=datas.indexOf(d);const ant=datas.slice(Math.max(0,i-20),i).map(x=>D.resumo[x][campo]);return ant.length>=3?ant.reduce((a,b)=>a+b,0)/ant.length:null}
function cmp(v,m){if(m==null)return'';const p=Math.round((v/m-1)*100);return `média recente ${m.toFixed(0)} (${p>=0?'+':''}${p}%)`}
function card(a){const als=a.alertas.filter(x=>x.sev!=='ACOMPANHAR');const mot=(als.length?als:a.alertas).map(x=>`<p class="motivo"><b>${esc(x.regra)}:</b> ${esc(x.motivo)}</p>`).join('');
return `<article class="card ${a.sev}"><header>${chip(a.sev)}<span>${esc(a.orgao)}</span><span>·</span><span>${esc(a.classe)}</span></header><h4>${esc(a.titulo)}</h4>${mot}<p class="exc">${esc(a.excerto)}…</p>
<footer>${a.instrumento?`<span>Instrumento ${esc(a.instrumento)}</span>`:''}${a.sei.length?`<span>SEI ${esc(a.sei.join('; '))}</span>`:''}${a.valor_max&&a.classe!=='Portaria'?`<span>Maior valor citado: ${brl(a.valor_max)}</span>`:''}<span>Edição ${esc(a.edicao)} (${esc(a.tipo_edicao)})</span><a href="${esc(a.url_pdf)}" target="_blank" rel="noopener">PDF oficial</a></footer></article>`}
function renderHoje(){const r=D.resumo[dia],as=atosDoDia(dia);
const altas=as.filter(a=>a.sev==='ALTA'),medias=as.filter(a=>a.sev==='MEDIA');
const vmax=as.filter(a=>a.valor_max&&a.classe!=='Portaria').sort((x,y)=>y.valor_max-x.valor_max)[0];
let h=`<div class="tiles">
<div class="tile"><div class="n">${r.atos}</div><div class="l">atos publicados</div><div class="c">${cmp(r.atos,media('atos',dia))}</div></div>
<div class="tile"><div class="n">${altas.length}</div><div class="l">alertas de prioridade alta</div><div class="c">${cmp(r.alta,media('alta',dia))}</div></div>
<div class="tile"><div class="n">${medias.length}</div><div class="l">alertas de prioridade média</div><div class="c">${cmp(r.media,media('media',dia))}</div></div>
<div class="tile"><div class="n">${r.pessoal}</div><div class="l">movimentações de pessoal</div><div class="c">${cmp(r.pessoal,media('pessoal',dia))}</div></div>
<div class="tile"><div class="n" style="font-size:19px;padding-top:6px">${vmax?brl(vmax.valor_max):'—'}</div><div class="l">maior valor citado</div><div class="c">${vmax?esc(vmax.classe+' · '+vmax.orgao):''}</div></div></div>
<div class="panel" style="margin-bottom:10px;color:var(--ink2);font-size:13.5px"><b style="color:var(--ink)">${dt(dia)}</b> · ${r.edicoes.map(esc).join(' · ')}</div>`;
h+=r.alertas_dia.map(x=>`<div class="dia-alert ${x.sev}"><span class="chip ${x.sev}"><i>${SEV[x.sev][0]}</i>${SEV[x.sev][1]}</span> <b>${esc(x.regra)}</b> — ${esc(x.motivo)}</div>`).join('');
h+=`<h2 style="margin-top:14px">Alerta de prioridade alta (${altas.length})</h2>`+(altas.length?altas.map(card).join(''):'<div class="vazio">Nenhum ato de prioridade alta neste dia.</div>');
h+=`<h2>Alerta de prioridade média (${medias.length})</h2>`+(medias.length?(medias.length>6?`${medias.slice(0,6).map(card).join('')}<details class="mais"><summary>Mostrar os outros ${medias.length-6}</summary>${medias.slice(6).map(card).join('')}</details>`:medias.map(card).join('')):'<div class="vazio">Nenhum ato de prioridade média neste dia.</div>');
$('#hoje').innerHTML=h;
const c={};as.forEach(a=>a.prioridades.forEach(p=>c[p]=(c[p]||0)+1));
const ks=Object.keys(c).sort((a,b)=>c[b]-c[a]);
$('#prio').innerHTML=ks.length?ks.map(k=>`<button data-p="${esc(k)}">${esc(k)} <b>${c[k]}</b></button>`).join(''):'<div class="vazio">Nenhum ato ligado às prioridades de governo neste dia.</div>';
document.querySelectorAll('#prio button').forEach(b=>b.onclick=()=>{$('#fpri').value=b.dataset.p;renderTabela();$('#tb').scrollIntoView({behavior:'smooth'})});
const i=datas.indexOf(dia);$('#ant').disabled=i<=0;$('#prox').disabled=i>=datas.length-1;$('#seldia').value=dia;}
function renderGrafico(){const ult=datas.slice(-30);const W=1080,H=210,m={l:34,r:8,t:10,b:30};const iw=W-m.l-m.r,ih=H-m.t-m.b;
const tot=ult.map(d=>D.resumo[d].alta+D.resumo[d].media);const mx=Math.max(4,...tot);const bw=iw/ult.length;
let s=`<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Alertas por dia, alta e média">`;
[0,.5,1].forEach(f=>{const y=m.t+ih*(1-f);s+=`<line x1="${m.l}" x2="${W-m.r}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-width="1"/><text x="${m.l-6}" y="${y+4}" text-anchor="end">${Math.round(mx*f)}</text>`});
ult.forEach((d,i)=>{const r=D.resumo[d],x=m.l+i*bw+bw*.18,w=bw*.64;const ha=ih*r.alta/mx,hm=ih*r.media/mx;const y0=m.t+ih;
if(hm>0)s+=`<rect x="${x}" y="${y0-ha-hm}" width="${w}" height="${Math.max(0,hm-(ha>0?2:0))}" rx="3" fill="var(--serious)"/>`;
if(ha>0)s+=`<rect x="${x}" y="${y0-ha}" width="${w}" height="${ha}" rx="3" fill="var(--crit)"/>`;
if(d===dia)s+=`<rect x="${m.l+i*bw}" y="${m.t}" width="${bw}" height="${ih}" fill="none" stroke="var(--ink)" stroke-width="1.5" rx="4"/>`;
s+=`<rect class="hit" data-d="${d}" x="${m.l+i*bw}" y="${m.t}" width="${bw}" height="${ih+ m.b}" fill="transparent" style="cursor:pointer"/>`;
if(i%3===0||i===ult.length-1)s+=`<text x="${x+w/2}" y="${H-8}" text-anchor="middle">${d.slice(8)}/${d.slice(5,7)}</text>`});
$('#grafico').innerHTML=s+'</svg><div id="tip"></div>';
const tip=$('#tip');document.querySelectorAll('.hit').forEach(el=>{const d=el.dataset.d,r=D.resumo[d];
el.onmousemove=e=>{const b=$('#grafico').getBoundingClientRect();tip.style.display='block';tip.style.left=Math.min(e.clientX-b.left+12,b.width-190)+'px';tip.style.top=(e.clientY-b.top-44)+'px';tip.innerHTML=`<b>${dt(d)}</b><br>${r.atos} atos · ${r.alta} alta · ${r.media} média`};
el.onmouseleave=()=>tip.style.display='none';el.onclick=()=>{dia=d;renderHoje();renderGrafico();window.scrollTo({top:0,behavior:'smooth'})}})}
function filtrados(){const q=$('#q').value.trim().toLowerCase(),fs=$('#fsev').value,fo=$('#forg').value,fc=$('#fcla').value,fp=$('#fpri').value;
return D.atos.filter(a=>(!fs||(fs==='-'?!a.sev:a.sev===fs))&&(!fo||a.orgao===fo)&&(!fc||a.classe===fc)&&(!fp||a.prioridades.includes(fp))&&
(!q||(a.titulo+' '+a.excerto+' '+(a.instrumento||'')+' '+a.sei.join(' ')+' '+a.orgao).toLowerCase().includes(q))).sort((x,y)=>y.data.localeCompare(x.data)||ORD[y.sev]-ORD[x.sev]||x.ordem-y.ordem)}
function renderTabela(){const f=filtrados();const m=300;
$('#tb').innerHTML=f.slice(0,m).map(a=>`<tr><td>${chip(a.sev)}</td><td>${a.data.split('-').reverse().join('/')}</td><td>${esc(a.orgao)}</td><td><b>${esc(a.classe)}</b> ${esc(a.titulo)}</td><td>${a.classe!=='Portaria'?brl(a.valor_max):'—'}</td><td>${esc(a.sei.join('; '))}</td><td><a href="${esc(a.url_pdf)}" target="_blank" rel="noopener">PDF</a></td></tr>`).join('');
$('#conta').textContent=`${f.length} atos encontrados`+(f.length>m?` (mostrando os ${m} mais recentes; use os filtros ou baixe o CSV)`:'')}
function csv(){const f=filtrados();const L=['data;edição;alerta;órgão;tipo;título;instrumento;valor_max;sei;prioridades'];
f.forEach(a=>L.push([a.data,a.edicao,a.sev,a.orgao,a.classe,a.titulo,a.instrumento||'',a.valor_max||'',a.sei.join(' | '),a.prioridades.join(' | ')].map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(';')));
const b=new Blob(['﻿'+L.join('\n')],{type:'text/csv;charset=utf-8'});const u=document.createElement('a');u.href=URL.createObjectURL(b);u.download='atos_dom_anapolis.csv';u.click()}
function opts(sel,vals){vals.forEach(v=>{const o=document.createElement('option');o.value=o.textContent=v;sel.appendChild(o)})}
opts($('#forg'),[...new Set(D.atos.map(a=>a.orgao))].sort());opts($('#fcla'),[...new Set(D.atos.map(a=>a.classe))].sort());opts($('#fpri'),[...new Set(D.atos.flatMap(a=>a.prioridades))].sort());
datas.slice().reverse().forEach(d=>{const o=document.createElement('option');o.value=d;o.textContent=dt(d);$('#seldia').appendChild(o)});
$('#seldia').onchange=e=>{dia=e.target.value;renderHoje();renderGrafico()};
$('#ant').onclick=()=>{dia=datas[datas.indexOf(dia)-1];renderHoje();renderGrafico()};$('#prox').onclick=()=>{dia=datas[datas.indexOf(dia)+1];renderHoje();renderGrafico()};
['#q','#fsev','#forg','#fcla','#fpri'].forEach(s=>$(s).oninput=renderTabela);$('#csv').onclick=csv;
$('#rodape').textContent=`Gerado em ${D.gerado}. Alertas são sinais para conferência, não conclusões: confronte sempre com o PDF oficial e o processo SEI. Cortes atuais: valor médio a partir de ${brl(D.config.valor_corte)}, alto a partir de ${brl(D.config.valor_alto)}. Valores de ARP podem ser teto potencial, não despesa executada. Edições cobertas: ${datas[0].split('-').reverse().join('/')} a ${datas[datas.length-1].split('-').reverse().join('/')}.`;
renderHoje();renderGrafico();renderTabela();
</script></body></html>"""

def main(entrada="dados/atos_alertas.jsonl", saida="docs/index.html"):
    atos = [json.loads(l) for l in open(entrada, encoding="utf-8")]
    atos = [{k: a.get(k) for k in CAMPOS} for a in atos]
    resumo = json.load(open("dados/resumo_diario.json", encoding="utf-8"))
    cfg = json.load(open("config/regras.json", encoding="utf-8"))
    agora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    dados = {"atos": atos, "resumo": resumo, "gerado": agora,
             "config": {"valor_corte": cfg["valor_corte"], "valor_alto": cfg["valor_alto"]}}
    blob = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    open(saida, "w", encoding="utf-8").write(MODELO.replace("__DADOS__", blob))
    print(saida, len(blob) // 1024, "KB de dados")

if __name__ == "__main__":
    main(*sys.argv[1:3])
