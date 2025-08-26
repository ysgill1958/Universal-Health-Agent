fetch('./data/longevity_plan.json').then(r=>r.json()).then(c=>{
  document.getElementById('plan').textContent=JSON.stringify(c,null,2);
});
