(async function(){
  const root = document.getElementById('dir');
  const search = document.getElementById('dirSearch');

  function card(html){ return `<div class="card"><div class="txt">${html}</div></div>`; }
  function itemBlock(x, meta){
    const img = x.image ? `<img src="${x.image}" alt="" style="width:90px;height:90px;object-fit:cover;border-radius:10px;margin-right:12px;border:1px solid #dee2e6">` : "";
    const line2 = meta || "";
    return `<div style="display:flex;align-items:flex-start">
      ${img}
      <div>
        <div style="font-weight:600;margin-bottom:4px"><a href="${x.url}" target="_blank">${x.name}</a></div>
        <div style="color:#6c757d;margin-bottom:6px">${line2}</div>
        ${x.tags && x.tags.length ? x.tags.map(t=>`<span class="badge">${t}</span>`).join(' ') : ''}
      </div>
    </div>`;
  }

  let data = {programs:[],experts:[],institutions:[]};
  try{
    const r = await fetch('./data/catalog.json?cb=' + Date.now(), {cache:'no-store'});
    if(r.ok) data = await r.json();
  }catch(_){}

  const wrap = document.createElement('div');
  root.appendChild(wrap);

  function hay(x){
    return [x.name, x.category, x.description, x.focus, x.location, x.specialty, (x.tags||[]).join(' ')].join(' ').toLowerCase();
  }

  function render() {
    const term = (search.value || '').toLowerCase();
    const progs = (data.programs||[]).filter(x => !term || hay(x).includes(term));
    const exps  = (data.experts||[]).filter(x => !term || hay(x).includes(term));
    const insts = (data.institutions||[]).filter(x => !term || hay(x).includes(term));

    wrap.innerHTML =
      `<h2>Programs & Therapies (${progs.length})</h2>` +
      (progs.length ? progs.map(p => card(itemBlock(p, `${p.category||'—'} • ${p.location||'—'}`))).join('') : card('No programs yet')) +
      `<h2 style="margin-top:18px">Experts (${exps.length})</h2>` +
      (exps.length ? exps.map(e => card(itemBlock(e, `${e.specialty||'—'} • ${e.location||'—'}`))).join('') : card('No experts yet')) +
      `<h2 style="margin-top:18px">Institutions (${insts.length})</h2>` +
      (insts.length ? insts.map(i => card(itemBlock(i, `${i.focus||'—'} • ${i.location||'—'}`))).join('') : card('No institutions yet'));
  }

  search.addEventListener('input', () => render());
  render();
})();
