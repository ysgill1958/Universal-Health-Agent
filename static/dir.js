fetch('./data/catalog.json').then(r=>r.json()).then(c=>{
  document.getElementById('dir').textContent=JSON.stringify(c,null,2);
});
