(async function(){
  const grid = document.getElementById('grid');
  const empty = document.getElementById('empty');
  const q = document.getElementById('q');
  const count = document.getElementById('count');

  const topicsWrap = document.getElementById('topicChips');
  const discWrap   = document.getElementById('disciplineChips');
  const areaWrap   = document.getElementById('areaChips');

  // --- 1) Load data ---
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

  // --- 2) Facet dictionaries (edit/extend freely) ---
  // Topics (broad themes)
  const TOPICS = {
    'Longevity': ['longevity','aging','ageing','senescence','healthspan'],
    'Chronic Disease': ['diabetes','hypertension','cardiovascular','cancer','obesity','copd','arthritis','chronic'],
    'Nutrition': ['diet','nutrition','fasting','caloric restriction','keto','mediterranean','protein','supplement'],
    'Exercise': ['exercise','training','aerobic','resistance','strength','VO2','physical activity'],
    'Mental Health': ['depression','anxiety','cognitive','dementia','alzheimer','sleep','insomnia','stress'],
    'Traditional Medicine': ['ayurveda','tcm','traditional chinese medicine','qigong','yoga','acupuncture','herbal'],
    'AI in Health': ['artificial intelligence','machine learning','deep learning','ai','llm','algorithm'],
    'Microbiome': ['microbiome','gut','probiotic','prebiotic','dysbiosis'],
    'Biomarkers': ['biomarker','inflammatory markers','crp','il-6','hdl','ldl','glucose','insulin'],
    'Regenerative/Stem': ['stem cell','regenerative','senolytic','telomere','rapamycin','mTOR']
  };

  // Disciplines (fields of study)
  const DISCIPLINES = {
    'Clinical Trials': ['randomized','randomised','double-blind','placebo','rct','crossover','phase ii','phase iii'],
    'Epidemiology': ['cohort','case-control','incidence','prevalence','population','observational','risk factor'],
    'Genomics': ['genomics','genetic','polygenic','gwass','sequencing','epigenetic','methylation'],
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

  // Areas of Research (what the work aims to do)
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

  // --- 3) Derive facets from item text ---
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
      _topics: deriveFacet(hay, TOPICS),
      _disciplines: deriveFacet(hay, DISCIPLINES),
      _areas: deriveFacet(hay, AREAS)
    };
  }

  all = all.map(decorate);

  // --- 4) Build chip UIs for each facet ---
  function makeChips(container, labels){
    container.innerHTML = '';
    const state = new Set(); // empty = no filtering by this facet
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

  const topicLabels = Object.keys(TOPICS);
  const discLabels  = Object.keys(DISCIPLINES);
  const areaLabels  = Object.keys(AREAS);

  const topicState = makeChips(topicsWrap, topicLabels);
  const discState  = makeChips(discWrap,   discLabels);
  const areaState  = makeChips(areaWrap,   areaLabels);

  // --- 5) Rendering & filtering ---
  function badge(txt, cls){ return `<span class="badge ${cls||''}">${txt}</span>`; }
  function cardHTML(i){
    const img = i.image ? `<img class="thumb" loading="lazy" src="${i.image}" alt="">` : '<div class="thumb"></div>';
    const topicBadges = (i._topics||[]).map(t=>badge(t,'b-topic')).join(' ');
    const discBadges  = (i._disciplines||[]).map(t=>badge(t,'b-disc')).join(' ');
    const areaBadges  = (i._areas||[]).map(t=>badge(t,'b-area')).join(' ');
    return `<div class="card">
      <div class="inner">
        <div class="txt">
          ${topicBadges} ${discBadges} ${areaBadges} ${badge(i.source||'')}
          <h3 style="margin:.4rem 0"><a target="_blank" href="${i.link}">${i.title}</a></h3>
          <div class="muted">${i.date||''}</div>
          <p>${i.summary||''}</p>
        </div>
        <div>${img}</div>
      </div>
    </div>`;
  }

  function matchFacet(itemVals, state){
    // If nothing selected in this facet, accept.
    if (state.size === 0) return true;
    // Require ALL selected chips to be present in item.
    return [...state].every(x => itemVals.includes(x));
  }

  function filterAll(){
    const term=(q.value||'').toLowerCase();
    return all.filter(i=>{
      const termOk = !term || ( (i.title||'').toLowerCase().includes(term) || (i.summary||'').toLowerCase().includes(term) );
      const topicOk = matchFacet(i._topics||[], topicState);
      const discOk  = matchFacet(i._disciplines||[], discState);
      const areaOk  = matchFacet(i._areas||[], areaState);
      return termOk && topicOk && discOk && areaOk;
    });
  }

  function render(list){
    grid.innerHTML = list.map(cardHTML).join('');
    count.textContent = `${list.length} results`;
    empty.style.display = list.length ? 'none' : '';
  }

  function refresh(){ render(filterAll()); }

  let t=null; q.addEventListener('input', ()=>{ clearTimeout(t); t=setTimeout(refresh, 160); });

  // Initial render
  render(all);
})();
