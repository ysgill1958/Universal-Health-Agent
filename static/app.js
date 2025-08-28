(async function(){
  const grid = document.getElementById('grid');
  const empty = document.getElementById('empty');
  const q = document.getElementById('q');
  const count = document.getElementById('count');
  const topicsWrap = document.getElementById('topicChips');
  const discWrap   = document.getElementById('disciplineChips');
  const areaWrap   = document.getElementById('areaChips');
  const dateStartEl = document.getElementById('dateStart');
  const dateEndEl   = document.getElementById('dateEnd');
  const clearDates  = document.getElementById('clearDates');

  let all = [];
  try{
    const res = await fetch('./data/items.json?cb=' + Date.now(), {cache:'no-store'});
    if(!res.ok) throw new Error('HTTP ' + res.status);
    all = await res.json();
  }catch(e){
    empty.style.display = '';
    count.textContent = '0 results';
    return;
  }
  if(!Array.isArray(all) || all.length===0){
    empty.style.display='';
    count.textContent = '0 results';
    return;
  }

  const TOPICS = {
    'Longevity': ['longevity','aging','ageing','senescence','healthspan'],
    'Chronic Disease': ['diabetes','hypertension','cardiovascular','cancer','obesity','copd','arthritis','chronic'],
    'Nutrition': ['diet','nutrition','fasting','caloric restriction','keto','mediterranean','protein','supplement'],
    'Exercise': ['exercise','training','aerobic','resistance','strength','vo2','physical activity'],
    'Traditional Medicine': ['ayurveda','tcm','yoga','acupuncture','herbal','unani','siddha'],
    'AI in Health': ['artificial intelligence','machine learning','deep learning','ai','llm','algorithm'],
    'Microbiome': ['microbiome','gut','probiotic','prebiotic','dysbiosis'],
    'Biomarkers': ['biomarker','crp','hdl','ldl','glucose','insulin'],
    'Regenerative/Stem': ['stem cell','regenerative','senolytic','telomere','rapamycin','mtor']
  };
  const DISCIPLINES = {
    'Clinical Trials': ['randomized','randomised','double-blind','placebo','rct','crossover','phase ii','phase iii'],
    'Epidemiology': ['cohort','case-control','incidence','prevalence','observational','risk factor'],
    'Genomics': ['genomics','genetic','polygenic','gwas','sequencing','epigenetic','methylation'],
    'Immunology': ['immune','immunology','inflammation','cytokine','t cell','b cell','autoimmune'],
    'Cardiology': ['cardio','myocardial','arrhythmia','atherosclerosis','blood pressure','hypertension'],
    'Oncology': ['oncology','tumor','cancer','immunotherapy'],
    'Endocrinology': ['endocrine','insulin','glucose','thyroid','hormone','metabolic'],
    'Neurology': ['neurology','parkinson','alzheimer','cognitive'],
    'Geriatrics': ['geriatric','frailty','sarcopenia','elderly','older adult'],
    'Public Health': ['policy','guideline','screening','prevention program','community','surveillance'],
    'Traditional Systems': ['ayurveda','tcm','acupuncture','siddha','unani','homeopathy']
  };
  const AREAS = {
    'Prevention': ['prevention','screening','risk reduction','lifestyle'],
    'Diagnostics': ['diagnostic','biomarker','detection','sensitivity','specificity'],
    'Therapeutics': ['treatment','therapy','drug','intervention','therapeutic','dosage'],
    'Lifestyle': ['diet','exercise','sleep','meditation','yoga','qigong','behavior','behaviour'],
    'Devices/Wearables': ['device','wearable','sensor','tracker','smartwatch'],
    'Policy/Guidelines': ['policy','guideline','recommendation','consensus','position statement'],
    'Preclinical/Animal': ['mouse','mice','murine','rat','animal model','in vivo','in vitro'],
    'Meta-analysis/Review': ['meta-analysis','systematic review','umbrella review','scoping review']
  };

  function toISODateOnly(s){ return (s||'').slice(0,10); }
  function deriveFacet(hay, dict){
    const hits=[];
    for(const [label, words] of Object.entries(dict)){
      if(words.some(w=>hay.includes(w))) hits.push(label);
    }
    return hits;
  }
  function isNewWithin24h(dateStr){
    if(!dateStr) return false;
    const d = new Date(dateStr.replace(' ','T') + 'Z');
    const now = new Date();
    const diff = now - d;
    return diff >= 0 && diff <= 86400000;
  }
  function decorate(item){
    const hay = ((item.title||'') + ' ' + (item.summary||'') + ' ' + (item.source||'')).toLowerCase();
    return {
      ...item,
      _dateOnly: toISODateOnly(item.date),
      _topics: deriveFacet(hay, TOPICS),
      _disciplines: deriveFacet(hay, DISCIPLINES),
      _areas: deriveFacet(hay, AREAS),
      _isNew: isNewWithin24h(item.date)
    };
  }
  all = all.map(decorate);

  function domainFrom(url){ try { return new URL(url).hostname; } catch { return ""; } }
  function faviconURL(url){
    const d = domainFrom(url); if (!d) return "";
    return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(d)}&sz=64`;
  }
  function textMediaHTML(i){
    const fav = faviconURL(i.link);
    const title = (i.title || '').slice(0, 120);
    const summary = (i.summary || '').slice(0, 180);
    return `<div class="media"><div class="media__inner">
      <div class="media__row">
        ${fav ? `<img class="favicon" alt="" src="${fav}">` : `<span class="favicon"></span>`}
        <div class="media__title">${title}</div>
      </div>
      <div class="media__summary">${summary || 'No summary available.'}</div>
    </div></div>`;
  }
  function imageMediaHTML(i){ return `<img class="thumb" loading="lazy" src="${i.image}" alt="">`; }
  function badge(txt, cls){ return `<span class="badge ${cls||''}">${txt}</span>`; }

  function cardHTML(i){
    const imgOrText = i.image ? imageMediaHTML(i) : textMediaHTML(i);
    const topicBadges = (i._topics||[]).map(t=>badge(t,'b-topic')).join(' ');
    const discBadges  = (i._disciplines||[]).map(t=>badge(t,'b-disc')).join(' ');
    const areaBadges  = (i._areas||[]).map(t=>badge(t,'b-area')).join(' ');
    const srcBadge    = badge(i.source||'');
    const newBadge    = i._isNew ? badge('NEW','b-area') : '';

    return `<div class="card">
      <div class="inner">
        <div class="txt">
          ${newBadge} ${topicBadges} ${discBadges} ${areaBadges} ${srcBadge}
          <h3 style="margin:.4rem 0"><a target="_blank" href="${i.link}">${i.title}</a></h3>
          <div class="muted">${i.date||''}</div>
          <p>${i.summary||''}</p>
        </div>
        <div>${imgOrText}</div>
      </div>
    </div>`;
  }

  function withinDate(i){
    const d = i._dateOnly;
    const ds = dateStartEl?.value || null;
    const de = dateEndEl?.value || null;
    if (ds && d < ds) return false;
    if (de && d > de) return false;
    return true;
  }
  function matchFacet(itemVals, state){
    if (state.size === 0) return true;
    return [...state].every(x => itemVals.includes(x));
  }

  function anyFiltersActive(){
    const term = (q?.value||'').trim();
    return !!term || !!(dateStartEl?.value) || !!(dateEndEl?.value);
  }

  function filterAll(){
    const term=(q?.value||'').toLowerCase();
    return all.filter(i=>{
      const termOk = !term || ((i.title||'').toLowerCase().includes(term) || (i.summary||'').toLowerCase().includes(term));
      const dateOk = withinDate(i);
      return termOk && dateOk;
    });
  }

  function render(list){
    const limit = anyFiltersActive() ? list.length : 25;
    const limited = list.slice(0, limit);
    grid.innerHTML = limited.map(cardHTML).join('');
    count.textContent = anyFiltersActive()
      ? `${limited.length} results (all matches shown)`
      : `${limited.length}/${list.length} shown • ${all.length} total`;
    empty.style.display = limited.length ? 'none' : '';
  }
  function refresh(){ render(filterAll()); }

  let t=null;
  if (q) q.addEventListener('input', ()=>{ clearTimeout(t); t=setTimeout(refresh, 160); });
  [dateStartEl, dateEndEl].forEach(el => el?.addEventListener('change', refresh));
  clearDates?.addEventListener('click', ()=>{ if(dateStartEl) dateStartEl.value=''; if(dateEndEl) dateEndEl.value=''; refresh(); });

  refresh();
})();