(async function(){
  const grid = document.getElementById('grid');
  const empty = document.getElementById('empty');
  const q = document.getElementById('q');
  const count = document.getElementById('count');

  let all = [];
  try {
    const res = await fetch('./data/items.json?cb=' + Date.now(), {cache:'no-store'});
    if (!res.ok) throw new Error('HTTP ' + res.status);
    all = await res.json();
  } catch (e) {
    empty.style.display = '';
    count.textContent = '0 results';
    return;
  }
  if (!Array.isArray(all) || all.length === 0) {
    empty.style.display = '';
    count.textContent = '0 results';
    return;
  }

  function cardHTML(i){
    const img = i.image ? `<img class="thumb" loading="lazy" src="${i.image}" alt="">` : '';
    return `<div class="card">
      <span class="badge">${i.source||''}</span>
      <h3><a target="_blank" href="${i.link}">${i.title}</a></h3>
      <div style="color:#b7b5c8">${i.date||''}</div>
      <p>${i.summary||''}</p>
      ${img}
    </div>`;
  }

  function render(list){
    grid.innerHTML = list.map(cardHTML).join('');
    count.textContent = `${list.length} results`;
    empty.style.display = list.length ? 'none' : '';
  }

  function filter(){
    const term = (q.value||'').toLowerCase();
    if (!term) return all;
    return all.filter(i => (i.title+' '+(i.summary||'')).toLowerCase().includes(term));
  }
  q.addEventListener('input', () => render(filter()));

  render(all);
})();
