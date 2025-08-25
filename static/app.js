(async function(){
  const grid=document.getElementById('grid');
  const empty=document.getElementById('empty');
  let all=[];
  try {
    const res=await fetch('./data/items.json');
    all=await res.json();
  } catch(e){ empty.style.display=''; return; }
  if(all.length===0){ empty.style.display=''; return; }
  all.forEach(i=>{
    const div=document.createElement('div');
    div.innerHTML=`<div style="border:1px solid #444;margin:8px;padding:8px">
      <span>${i.source}</span>
      <h3><a href="${i.link}" target="_blank">${i.title}</a></h3>
      <p>${i.summary||''}</p>
      ${i.image?`<img src="${i.image}" width="200">`:''}
    </div>`;
    grid.appendChild(div);
  });
})();
