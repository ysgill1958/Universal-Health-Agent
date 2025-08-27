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

  // --- Load data ---
  let all = [];
  try {
    const res = await fetch('./data/items.json?cb=' + Date.now(), {cache:'no-store'});
    if (!res.ok) throw new Error('HTTP ' + res.status);
    all = await res.json();
  } catch (e) {
    empty.style.display = '';
    count.textContent = '0 results';
    console.error('Failed to fetch items.json', e);
    return;
  }
  if (!Array.isArray(all) || all.length === 0) {
    empty.style.display = '';
    count.textContent = '0 results';
    return;
  }

  // --- Facet dictionaries ---
  const TOPICS = {
    'Longevity': ['longevity','aging','ageing','senescence','healthspan'],
    'Chronic Disease': ['diabetes','hypertension','cardiovascular','cancer','obesity','copd','arthritis','chronic'],
    'Nutrition': ['diet','nutrition','fasting','caloric restriction','keto','mediterranean','protein','supplement'],
    'Exercise': ['exercise','training','aerobic','resistance','strength','vo2','physical activity'],
    'Mental Health': ['depression','anxiety','cognitive','dementia','alzheimer','sleep','insomnia','stress'],
    'Traditional Medicine': ['ayurveda','tcm','traditional chinese medicine','qigong','yoga','acupuncture','herbal'],
    'AI in Health': ['artificial intelligence','machine learning','deep learning','ai','llm','algorithm'],
    'Microbiome': ['microbiome','gut','probiotic','prebiotic','dysbiosis'],
    'Biomarkers': ['biomarker','inflammatory markers','crp','il-6','hdl','ldl','glucose','insulin'],
    'Regenerative/Stem': ['stem cell','regenerative','senolytic','telomere','rapamycin','mtor']
  };

  const DISCIPLINES = {
    'Clinical Trials': ['randomized','randomised','double-blind','placebo','rct','crossover','phase ii','phase iii'],
    'Epidemiology': ['cohort','case-control','incidence','prevalence','population','observational','risk factor'],
    'Genomics': ['genomics','genetic','polygenic','gwas','sequencing','epigenetic','methylation'],
    'Immunology': ['immune','immunology','inflammation','cytokine','t cell','b cell','autoimmune'],
    'Cardiology': ['cardio','myocardial','arrhythmia','atherosclerosis','blood pressure','hypertension'],
    'Oncology': ['oncology','tumor','cancer','chemotherapy','immunotherapy'],
    'Endocrinology': ['endocrine','insulin','glucose','thyroid','hormone','metabolic'],
    'Neurology': ['neurology','neurodegenerative','parkinson','alzheimer','cognitive'],
    'Geriatrics': ['geriatric','frailty','sarcopenia','elderly','older adult'],
    'Pharmacology': ['pharmacology','dose','adverse event','pk','pd'],
    'Public Health': ['policy','guideline','screening','prevention program','community','surveillance'],
    'Traditional Systems': ['ayurveda','tcm','acupuncture','siddha','unani','homeopathy']
  };

  const AREAS = {
    'Prevention': ['prevention','preventive','risk reduction','screening','lifestyle intervention'],
    'Diagnostics': ['diagnostic','biomarker','screening','detection','sensitivity','specificity'],
    'Therapeutics': ['treatment','therapy','drug','intervention','therapeutic','dosage'],
    'Lifestyle': ['diet','exercise','sleep','meditation','yoga','qigong','behavior','behaviour'],
    'Devices/Wearables': ['device','wearable','sensor','tracker','smartwatch'],
    'Policy/Guidelines': ['policy','guideline','recommendation','consensus','position statement'],
    'Preclinical/Animal': ['mouse','mice','murine','rat','animal model','in vivo','in vitro'],
    'Meta-analysis/Review': ['meta-analysis','systematic review','umbrella review','scoping review']
  };

  function toISODateOnly(s){
    if(!s) return "";
    // Expect formats like "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
    return (s || "").slice(0,10);
  }

  function deriveFacet(hay, dict){
    const hits = [];
    for (const [label, words] of Object.entries(dict)) {
      if (words.some(w => hay.includes(w))) hits.push(label);
    }
    return hits;
  }

  function decorate(item){
    const hay = ((item.title || '') + ' ' + (item.summary || '') + ' ' + (item.source || '')).toLowerCase();
    return {
      ...item,
      _dateOnly: toISODateOnly(item.date),
      _topics: deriveFacet(hay, TOPICS),
      _disciplines: deriveFacet(hay, DISCIPLINES),
      _areas: deriveFacet(hay, AREAS)
    };
  }

  all = all.map(decorate);

  // --- Chips UI ---
  function makeChips(container, labels){
    container.innerHTML = '';
    const state = new Set();
    labels.forEach(lbl => {
      const id = (container.id + '_' + lbl).replace(/\W+/g,'_');
      const el = document.createElement('label');
      el.className = 'chip';
      el.innerHTML = `<input type="checkbox" id="${id}"> ${lbl}`;
      const cb = el.querySelector('input');
      cb.addEventListener('change', () => {
        if (cb.checked) state.add(lbl); else state.delete(lbl);
        refresh();
      });
      container.appendChild(el);
    });
    return state;
  }

  const topicState = makeChips(topicsWrap, Object.keys(TOPICS));
  const discState  = makeChips(discWrap,   Object.keys(DISCIPLINES));
  const areaState  = makeChips(areaWrap,   Object.keys(AREAS));

  // --- Card rendering with image/text fallback ---
  function domainFrom(url){ try { return new URL(url).hostname; } catch { return ""; } }
  function faviconURL(url){
    const d = domainFrom(url); if (!d) return "";
    return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(d)}&sz=64`;
  }
  function textMediaHTML(i){
    const fav = faviconURL(i.link);
    const title = (i.title || '').slice(0, 120);
    const summary = (i.summary || '').slice(0, 180);
    return `
      <div class="media media--text">
        <div class="media__inner">
          <div class="media__row">
            ${fav ? `<img class="favicon" alt="" src="${fav}">` : `<span class="favicon"></span>`}
            <div class="media__title">${title}</div>
          </div>
          <div class="media__summary">${summary || 'No summary available.'}</div>
        </div>
      </div>`;
  }
  function imageMediaHTML(i){ return `<img class="thumb" loading="lazy" src="${i.image}" alt="">`; }
  function badge(txt, cls){ return `<span class="badge ${cls||''}">${txt}</span>`; }

  function cardHTML(i){
    const imgOrText = i.image ? imageMediaHTML(i) : textMediaHTML(i);
    const topicBadges = (i._topics||[]).map(t=>badge(t,'b-topic')).join(' ');
    const discBadges  = (i._disciplines||[]).map(t=>badge(t,'b-disc')).join(' ');
    const areaBadges  = (i._areas||[]).map(t=>badge(t,'b-area')).join(' ');
    const srcBadge    = badge(i.source||'');

    return `<div class="card">
      <div class="inner">
        <div class="txt">
          ${topicBadges} ${discBadges} ${areaBadges} ${srcBadge}
          <h3 style="margin:.4rem 0"><a target="_blank" href="${i.link}">${i.title}</a></h3>
          <div class="muted">${i.date||''}</div>
          <p>${i.summary||''}</p>
        </div>
        <div>${imgOrText}</div>
      </div>
    </div>`;
  }

  // --- Filtering & render ---
  function withinDate(i){
    const d = i._dateOnly;
    const ds = dateStartEl.value || null;
    const de = dateEndEl.value || null;
    if (ds && d < ds) return false;
    if (de && d > de) return false;
    return true;
  }

  function matchFacet(itemVals, state){
    if (state.size === 0) return true;
    return [...state].every(x => itemVals.includes(x));
  }

  function filterAll(){
    const term=(q?.value||'').toLowerCase();
    return all.filter(i=>{
      const termOk = !term || ( (i.title||'').toLowerCase().includes(term) || (i.summary||'').toLowerCase().includes(term) );
      const dateOk = withinDate(i);
      const topicOk = matchFacet(i._topics||[], topicState);
      const discOk  = matchFacet(i._disciplines||[], discState);
      const areaOk  = matchFacet(i._areas||[], areaState);
      return termOk && dateOk && topicOk && discOk && areaOk;
    });
  }

  function render(list){
    const limited = list.slice(0, 25); // show only 25 on homepage
    grid.innerHTML = limited.map(cardHTML).join('');
    count.textContent = `${limited.length}/${list.length} shown • ${all.length} total`;
    empty.style.display = limited.length ? 'none' : '';
  }

  function refresh(){ render(filterAll()); }

  let t=null;
  if (q) q.addEventListener('input', ()=>{ clearTimeout(t); t=setTimeout(refresh, 160); });
  [dateStartEl, dateEndEl].forEach(el => el?.addEventListener('change', refresh));
  clearDates?.addEventListener('click', ()=>{ if(dateStartEl) dateStartEl.value=''; if(dateEndEl) dateEndEl.value=''; refresh(); });

  refresh();
})();
