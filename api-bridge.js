/* Aetheria API bridge: keeps the existing Milestone 1-3 UI while routing
 * authentication, readings, dashboards and exports through the FastAPI backend. */
const AETHERIA_API_BASE = (location.protocol === 'http:' || location.protocol === 'https:')
  ? `${location.origin}/api/v1`
  : 'http://localhost:8000/api/v1';
const AETHERIA_TOKEN_KEY = 'aetheria_access_token';

async function aetheriaApi(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && options.body && !(options.body instanceof FormData) && !(options.body instanceof URLSearchParams)) headers.set('Content-Type', 'application/json');
  const token = localStorage.getItem(AETHERIA_TOKEN_KEY);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${AETHERIA_API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const body = await response.json(); message = body.detail || message; } catch (_) {}
    throw new Error(message);
  }
  const type = response.headers.get('content-type') || '';
  return type.includes('application/json') ? response.json() : response.blob();
}

function toPalmRecord(row) {
  return {
    id: `PLM-${row.id}`, date: new Date(row.created_at).toLocaleDateString(), type: 'Palm Analysis',
    focus: row.palm_shape || 'Palm analysis', score: row.guidance_score,
    image: row.image_path ? `${location.origin}/${row.image_path.replace(/^\//, '')}` : '',
    metadata: { shape: row.palm_shape || 'Not detected', fingers: row.finger_structure || 'Not detected', lifeConf: row.life_line_conf, headConf: row.head_line_conf, heartConf: row.heart_line_conf, fateConf: row.fate_line_conf, sunConf: row.sun_line_conf },
    dimensions: { vitality: row.life_line_conf, intellect: row.head_line_conf, emotion: row.heart_line_conf, destiny: row.fate_line_conf, radiance: row.sun_line_conf },
    interpretation: {
      synthesis: row.detailed_insight || row.summary || 'No interpretation available.',
      heartDesc: `Heart Line detection confidence: ${row.heart_line_conf}%.`, headDesc: `Head Line detection confidence: ${row.head_line_conf}%.`,
      lifeDesc: `Life Line detection confidence: ${row.life_line_conf}%.`, fateDesc: `Fate Line detection confidence: ${row.fate_line_conf}%.`, sunDesc: `Sun Line detection confidence: ${row.sun_line_conf}%.`
    }, mounts: []
  };
}

function toTarotRecord(row) {
  const spread = String(row.spread_name || 'three').toLowerCase().startsWith('three') ? 'three' : String(row.spread_name || 'single').toLowerCase();
  return {
    id: `TRT-${row.id}`, date: new Date(row.created_at).toLocaleDateString(), type: 'Tarot Reading',
    focus: row.spread_name, score: row.guidance_score,
    metadata: { spread, cards: (row.cards_drawn || []).map(x => ({ id: x.card.id, name: x.card.name, arcana: x.card.arcana, suit: x.card.suit || 'None', keywords: x.card.keywords || [], upright: x.card.meaning_upright, reversed: x.card.meaning_reversed, isReversed: x.is_reversed })) },
    interpretation: { synthesis: row.detailed_insight || row.summary || 'No interpretation available.', opening: row.summary || '' }
  };
}

async function syncRemoteData() {
  const [me, palms, tarot, recs, notifs] = await Promise.all([
    aetheriaApi('/users/me'), aetheriaApi('/palm/readings'), aetheriaApi('/tarot/readings'), aetheriaApi('/recommendations'), aetheriaApi('/notifications')
  ]);
  currentUser = me;
  localStorage.setItem('aetheria_users_cache', JSON.stringify([me]));
  const records = [...palms.map(toPalmRecord), ...tarot.map(toTarotRecord)].sort((a, b) => new Date(b.date) - new Date(a.date));
  localStorage.setItem('aetheria_readings', JSON.stringify(records));
  localStorage.setItem('aetheria_recommendations', JSON.stringify(recs)); localStorage.setItem('aetheria_recs', JSON.stringify(recs.map(r=>({id:r.id,email:currentUser.email,task:r.title,category:r.category,completed:r.is_completed}))));
  localStorage.setItem('aetheria_notifications', JSON.stringify(notifs.map(n => ({ id: n.id, title: n.title, message: n.message, read: n.is_read, date: new Date(n.created_at).toLocaleDateString() }))));
  updateRegisteredProfilesSidebar();
  updateDashboardData();
  renderRecommendationsList();
  renderHistoryTable();
  updateNotificationBadge();
  return me;
}

AetheriaDatabaseManager.init = function () {
  const badge = document.getElementById('db-status-badge');
  if (badge) badge.innerHTML = '<i class="fa-solid fa-circle-check text-green-500 mr-1"></i> API Connected';
};
AetheriaDatabaseManager.getUsers = function () { return JSON.parse(localStorage.getItem('aetheria_users_cache') || '[]'); };

window.onload = async function () {
  AetheriaDatabaseManager.init();
  const token = localStorage.getItem(AETHERIA_TOKEN_KEY);
  if (!token) { navigate('home'); return; }
  try { await syncRemoteData(); initializeUserWorkspace(); }
  catch (_) { localStorage.removeItem(AETHERIA_TOKEN_KEY); localStorage.removeItem('aetheria_session'); navigate('home'); }
};

window.handleLoginSubmit = async function (e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const pass = document.getElementById('login-password').value;
  try {
    const body = new URLSearchParams({ username: email, password: pass });
    const token = await aetheriaApi('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body });
    localStorage.setItem(AETHERIA_TOKEN_KEY, token.access_token);
    await syncRemoteData();
    initializeUserWorkspace();
  } catch (err) {
    const banner = document.getElementById('login-alert-banner');
    if (banner) { banner.className = 'p-3.5 rounded-xl border border-red-500/40 bg-red-500/10 text-red-300 text-xs font-semibold'; banner.textContent = err.message; banner.classList.remove('hidden'); }
  }
};

window.handleRegisterSubmit = async function (e) {
  e.preventDefault();
  const name = document.getElementById('reg-name').value.trim();
  const ageGroup = document.getElementById('reg-age').value;
  const email = document.getElementById('reg-email').value.trim();
  const pass = document.getElementById('reg-password').value;
  const confirm = document.getElementById('reg-password-confirm').value;
  if (pass !== confirm) { alert('Passwords do not match.'); return; }
  const goals = [...document.querySelectorAll('input[name="reg-goals"]:checked')].map(x => x.value);
  const interests = [...document.querySelectorAll('input[name="reg-interests"]:checked')].map(x => x.value);
  try {
    await aetheriaApi('/auth/register', { method: 'POST', body: JSON.stringify({ full_name: name, email, password: pass, age_group: ageGroup, interests, goals }) });
    document.getElementById('login-email').value = email;
    document.getElementById('login-password').value = '';
    document.getElementById('register-wizard-form').reset(); moveWizard(1); navigate('login');
    const banner = document.getElementById('login-alert-banner');
    if (banner) { banner.className = 'p-3.5 rounded-xl border border-green-500/40 bg-green-500/10 text-green-300 text-xs font-semibold'; banner.textContent = 'Registration complete. Log in with the password you chose.'; banner.classList.remove('hidden'); }
  } catch (err) { alert(err.message); }
};

window.logout = function () {
  localStorage.removeItem(AETHERIA_TOKEN_KEY); localStorage.removeItem('aetheria_session'); localStorage.removeItem('aetheria_readings');
  currentUser = null; navigate('home');
};

window.runPalmCVAnalysis = async function () {
  if (!imageToAnalyze) return;
  const loading = document.getElementById('cv-loading-overlay'); const idle = document.getElementById('cv-idle-overlay');
  loading.classList.remove('hidden'); idle.classList.add('hidden');
  try {
    const row = await aetheriaApi('/palm/analyze', { method: 'POST', body: JSON.stringify({ image_base64: imageToAnalyze }) });
    const record = toPalmRecord(row); lastAnalysisMetrics = { clarity: row.overall_conf, life: row.life_line_conf, head: row.head_line_conf, heart: row.heart_line_conf, fate: row.fate_line_conf, sun: row.sun_line_conf };
    const img = new Image(); img.onload = () => { const canvas = document.getElementById('cvCanvas'); canvas.width = 360; canvas.height = 360; canvas.getContext('2d').drawImage(img, 0, 0, 360, 360); renderPalmLinesOnCanvas(lastAnalysisMetrics); };
    img.src = record.image;
    document.getElementById('cv-val-heart').innerText = `${row.heart_line_conf}%`; document.getElementById('cv-val-head').innerText = `${row.head_line_conf}%`; document.getElementById('cv-val-life').innerText = `${row.life_line_conf}%`; document.getElementById('cv-val-fate').innerText = `${row.fate_line_conf}%`; document.getElementById('cv-val-sun').innerText = `${row.sun_line_conf}%`;
    localStorage.setItem('aetheria_readings', JSON.stringify([record, ...getReadings()]));
    currentReading = record; await syncRemoteData(); showPalmResult(record);
  } catch (err) { alert(err.message); idle.classList.remove('hidden'); }
  finally { loading.classList.add('hidden'); }
};

window.submitTarotInterpretation = async function () {
  if (!selectedCards.length || !currentUser) return;
  const focus = document.getElementById('tarot-focus-intent').value;
  try {
    const row = await aetheriaApi('/tarot/readings', { method: 'POST', body: JSON.stringify({ spread_name: activeSpreadMode, focus_intent: focus, card_ids: selectedCards.map(c => c.id), reversed_flags: selectedCards.map(c => !!c.isReversed) }) });
    const record = toTarotRecord(row); currentReading = record; await syncRemoteData(); showTarotResult(record);
  } catch (err) { alert(err.message); }
};

window.saveProfileChanges = async function () {
  if (!currentUser) return;
  const goals = [...document.querySelectorAll('input[name="profile-goals"]:checked')].map(x => x.value);
  const interests = [...document.querySelectorAll('input[name="profile-interests"]:checked')].map(x => x.value);
  const payload = { age_group: document.getElementById('edit-profile-age')?.value || currentUser.profile?.age_group, goals: goals.length ? goals : (currentUser.profile?.goals || []), interests: interests.length ? interests : (currentUser.profile?.interests || []) };
  try { await aetheriaApi('/users/me', { method: 'PUT', body: JSON.stringify(payload) }); await syncRemoteData(); updateProfileView(); alert('Profile preferences updated.'); }
  catch (err) { alert(err.message); }
};

window.updateAdminConsole = async function () {
  try {
    const [stats, users] = await Promise.all([aetheriaApi('/analytics/executive'), aetheriaApi('/admin/users')]);
    document.getElementById('admin-kpi-users').innerText = stats.total_users; document.getElementById('admin-kpi-readings').innerText = stats.total_readings;
    const cv = document.getElementById('admin-kpi-cv'); if (cv) cv.innerText = stats.palm_readings;
    const latency = document.getElementById('admin-kpi-latency'); if (latency) latency.innerText = stats.average_api_latency_ms == null ? '—' : `${stats.average_api_latency_ms}ms`;
    document.getElementById('admin-users-table-body').innerHTML = users.map(u => `<tr class="border-b border-mystic-900"><td class="p-3 font-semibold text-white">${u.full_name}</td><td class="p-3 text-gray-400">${u.email}</td><td class="p-3">${u.role}</td><td class="p-3">${u.is_active ? 'Active' : 'Inactive'}</td><td class="p-3 text-right">${u.id === currentUser.id ? 'Current' : '—'}</td></tr>`).join('');
  } catch (err) { addAuditLog(`Admin analytics unavailable: ${err.message}`); }
};

window.updateReaderConsole = async function () {
  try { const data = await aetheriaApi('/analytics/reader'); document.getElementById('reader-queue-table-body').innerHTML = data.recent_readings.map(r => `<tr class="border-b border-mystic-900"><td class="p-3 font-mono">TRT-${r.id}</td><td class="p-3">User ${r.user_id}</td><td class="p-3">${r.spread_name}</td><td class="p-3">${new Date(r.created_at).toLocaleDateString()}</td><td class="p-3 text-right">—</td></tr>`).join(''); } catch (err) { addAuditLog(`Reader analytics unavailable: ${err.message}`); }
};
window.updateConsultantConsole = async function () {
  try {
    const data = await aetheriaApi('/analytics/consultant');
    const sessions = document.getElementById('consultant-kpi-sessions');
    if (sessions) sessions.innerText = data.reading_count;
    const avg = document.getElementById('consultant-kpi-score');
    if (avg) avg.innerText = data.average_guidance_score == null ? '—' : data.average_guidance_score;
    const retention = document.getElementById('consultant-kpi-retention');
    if (retention) retention.innerText = `${Number(data.repeat_client_rate || 0).toFixed(1)}%`;
    const activeDays = document.getElementById('consultant-kpi-active-days');
    if (activeDays) activeDays.innerText = data.active_days_30d ?? 0;
    const reports = document.getElementById('consultant-kpi-reports');
    if (reports) reports.innerText = data.report_ready_count ?? 0;
    const latest = document.getElementById('consultant-latest-session');
    if (latest) latest.innerText = data.latest_session_at ? `Latest session: ${new Date(data.latest_session_at).toLocaleString()}` : 'No session data';

    const body = document.getElementById('consultant-sessions-body');
    if (body) {
      body.innerHTML = (data.recent_readings || []).slice(0, 10).map(r => `<tr class="border-b border-mystic-900">
        <td class="p-3 font-mono">PLM-${r.id}</td>
        <td class="p-3">User ${r.user_id}</td>
        <td class="p-3">${new Date(r.created_at).toLocaleDateString()}</td>
        <td class="p-3 text-right">${r.has_guidance_score ? 'Scored' : 'Pending'}</td>
        <td class="p-3 text-right">${r.report_ready ? 'Ready' : 'Pending'}</td>
      </tr>`).join('') || '<tr><td colspan="5" class="p-3 text-gray-500">No consultation sessions yet.</td></tr>';
    }

    const canvas = document.getElementById('consultantChart');
    if (canvas && typeof Chart !== 'undefined') {
      const ctx = canvas.getContext('2d');
      if (consultantChartObj) consultantChartObj.destroy();
      consultantChartObj = new Chart(ctx, {
        type: 'line',
        data: {
          labels: (data.readings_by_day || []).map(x => new Date(`${x.date}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })),
          datasets: [{
            label: 'Guidance effectiveness',
            data: (data.readings_by_day || []).map(x => x.average),
            borderColor: '#fbbf24',
            backgroundColor: 'rgba(251, 191, 36, 0.1)',
            tension: 0.4,
            fill: true,
            spanGaps: true
          }, {
            label: 'Consultations',
            data: (data.readings_by_day || []).map(x => x.count),
            borderColor: '#8b5cf6',
            backgroundColor: 'rgba(139, 92, 246, 0.08)',
            tension: 0.4,
            yAxisID: 'y1',
            spanGaps: true
          }]
        },
        options: {
          scales: {
            y: { beginAtZero: true, title: { display: true, text: 'Guidance score' } },
            y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Sessions' } },
            x: { ticks: { maxTicksLimit: 8 } }
          },
          plugins: { legend: { display: true } }
        }
      });
    }
  } catch (err) { addAuditLog(`Consultant analytics unavailable: ${err.message}`); }
};

let combinedPalmImageBase64 = null;
window.useLatestPalmScan = async function () {
  try {
    const palms = await aetheriaApi('/palm/readings');
    if (!palms.length) { alert('Complete a palm scan before starting the combined master analysis.'); return; }
    const latest = palms[0];
    const label = document.getElementById('combined-line-overall-label');
    if (label) label.textContent = `${latest.overall_conf}% Overall`;
    ['life','head','heart','fate'].forEach(key => { const el=document.getElementById(`slider-${key}-conf`); if(el) el.value=latest[`${key}_line_conf`]; const out=document.getElementById(`label-${key}-conf`); if(out) out.textContent=`${latest[`${key}_line_conf`]}%`; });
    const prompt=document.getElementById('combined-palm-upload-prompt'); const container=document.getElementById('combined-palm-canvas-container'); if(prompt) prompt.classList.add('hidden'); if(container) container.classList.remove('hidden');
    window._combinedPalmReadingId = latest.id;
  } catch (err) { alert(err.message); }
};
window.handleCombinedPalmUpload = function (event) {
  const file = event.target.files && event.target.files[0]; if (!file) return;
  const reader = new FileReader(); reader.onload = () => { combinedPalmImageBase64 = reader.result; window._combinedPalmReadingId = null; const prompt=document.getElementById('combined-palm-upload-prompt'); const container=document.getElementById('combined-palm-canvas-container'); if(prompt) prompt.classList.add('hidden'); if(container) container.classList.remove('hidden'); const canvas=document.getElementById('combinedPalmCanvas'); if(canvas){ const img=new Image(); img.onload=()=>{canvas.width=400; canvas.height=300; canvas.getContext('2d').drawImage(img,0,0,400,300);}; img.src=reader.result; }}; reader.readAsDataURL(file);
};
window.initCombinedWizard = function () { masterDrawnCards = []; renderCombinedDrawnCardsGrid(); useLatestPalmScan(); };
window.redrawCombinedTarotSpread = function () {
  const selected = String(document.getElementById('combined-spread-select')?.value || 'three').toLowerCase();
  const count = selected.includes('celtic') ? 10 : selected.includes('five') ? 5 : 3;
  const pool = [...TAROT_CARDS];
  selectedCards = [];
  while (selectedCards.length < count && pool.length) {
    const idx = Math.floor(Math.random() * pool.length);
    const card = pool.splice(idx, 1)[0];
    selectedCards.push({ ...card, isReversed: Math.random() > 0.7 });
  }
  masterDrawnCards = selectedCards.map((c, i) => ({ name:c.name, position:`Position ${i+1}`, orientation:c.isReversed?'reversed':'upright', arcana:c.arcana, meaning:c.isReversed?c.reversed:c.upright }));
  renderCombinedDrawnCardsGrid();
};
window.executeCombinedMasterAnalysis = async function () {
  if (!currentUser) { alert('Please sign in first.'); return; }
  try {
    const focusIntent = document.getElementById('combined-focus-intent')?.value.trim() || 'General Reflection';
    const selectedSpread = document.getElementById('combined-spread-select')?.value || 'Three Card (Past, Present, Future)'; const spreadName = selectedSpread.toLowerCase().includes('celtic') ? 'celtic' : selectedSpread.toLowerCase().includes('five') ? 'five card elemental alignment' : 'three';
    let palmId = window._combinedPalmReadingId || null;
    if (!palmId && !combinedPalmImageBase64) { const palms = await aetheriaApi('/palm/readings'); palmId = palms[0]?.id || null; }
    if (!palmId && !combinedPalmImageBase64) { alert('Complete or upload a real palm analysis first.'); return; }
    if (!selectedCards.length) { alert('Draw a tarot spread first so the combined report uses an actual persisted spread.'); return; }
    const report = await aetheriaApi('/combined/analyze', { method:'POST', body: JSON.stringify({ palm_reading_id:palmId, image_base64: palmId ? null : combinedPalmImageBase64, spread_name:spreadName, focus_intent:focusIntent, card_ids:selectedCards.map(c=>c.id), reversed_flags:selectedCards.map(c=>!!c.isReversed) }) });
    currentMasterReport = { id:`AETH-MASTER-${report.id}`, clientName:report.user_name, date:new Date(report.created_at).toLocaleDateString(), focusIntent, spreadName, backendReadingId:report.id, compositeScore:report.composite_score, palmMetrics:{ shape:report.palm_metrics.palm_shape, overallConf:report.palm_metrics.overall_conf, lifeConf:report.palm_metrics.life_line_conf, headConf:report.palm_metrics.head_line_conf, heartConf:report.palm_metrics.heart_line_conf, fateConf:report.palm_metrics.fate_line_conf }, tarotCards:report.tarot_cards.map(c=>({name:c.card_name,position:c.position,orientation:c.orientation,arcana:c.arcana,meaning:c.meaning})), synthesis:{ executive:report.categories.executive_synthesis, mindset:report.categories.mindset_cognition, career:report.categories.career_ambition, love:report.categories.love_relationships, health:report.categories.health_vitality, destiny:report.categories.destiny_milestones }, recommendations:report.recommendations };
    masterDrawnCards = currentMasterReport.tarotCards; renderCombinedDrawnCardsGrid(); renderMasterReportUI(currentMasterReport); await syncRemoteData();
    const resultContainer=document.getElementById('view-combined-result'); if(resultContainer){resultContainer.classList.remove('hidden'); resultContainer.scrollIntoView({behavior:'smooth'});}
  } catch (err) { alert(err.message); }
};

// Normalize the backend user shape for the preserved UI without persisting credentials.
const _syncRemoteData = syncRemoteData;
syncRemoteData = async function () {
  const me = await aetheriaApi('/users/me');
  currentUser = { ...me, name: me.full_name, ageGroup: me.profile?.age_group, interests: me.profile?.interests || [], goals: me.profile?.goals || [], preferences: me.profile?.preferences || {} };
  localStorage.setItem('aetheria_users_cache', JSON.stringify([currentUser]));
  const [palms, tarot, recs, notifs] = await Promise.all([aetheriaApi('/palm/readings'), aetheriaApi('/tarot/readings'), aetheriaApi('/recommendations'), aetheriaApi('/notifications')]);
  const records = [...palms.map(toPalmRecord), ...tarot.map(toTarotRecord)].sort((a,b)=>new Date(b.date)-new Date(a.date));
  localStorage.setItem('aetheria_readings', JSON.stringify(records));
  localStorage.setItem('aetheria_recommendations', JSON.stringify(recs)); localStorage.setItem('aetheria_recs', JSON.stringify(recs.map(r=>({id:r.id,email:currentUser.email,task:r.title,category:r.category,completed:r.is_completed}))));
  localStorage.setItem('aetheria_notifications', JSON.stringify(notifs)); localStorage.setItem('aetheria_notifs', JSON.stringify(notifs.map(n=>({id:n.id,title:n.title,message:n.message,read:n.is_read,date:new Date(n.created_at).toLocaleDateString()}))));
  updateRegisteredProfilesSidebar(); updateDashboardData(); updateProfileView(); renderRecommendationsList(); renderHistoryTable(); updateNotificationBadge();
  return currentUser;
};

window.saveSettingsPreferences = function () {
  const preferences = {
    tone: document.getElementById('pref-ai-tone')?.value || 'mystical',
    provider: 'server',
    camLens: document.getElementById('pref-cam-lens')?.value || 'user',
    camRes: document.getElementById('pref-cam-res')?.value || '720p',
    camMirror: !!document.getElementById('pref-cam-mirror')?.checked,
    notifDaily: !!document.getElementById('settings-notif-daily')?.checked,
    notifRemind: !!document.getElementById('settings-notif-remind')?.checked,
    notifWeekly: !!document.getElementById('pref-notif-weekly')?.checked,
    lowMotion: !!document.getElementById('pref-low-motion')?.checked,
    highContrast: !!document.getElementById('pref-high-contrast')?.checked
  };
  localStorage.setItem('aetheria_preferences', JSON.stringify(preferences));
  alert('Preferences saved. AI provider credentials remain server-side.');
};
window.loadSettingsPreferences = function () {
  const p = JSON.parse(localStorage.getItem('aetheria_preferences') || '{}');
  if (p.tone && document.getElementById('pref-ai-tone')) document.getElementById('pref-ai-tone').value=p.tone;
  if (document.getElementById('settings-ai-provider')) document.getElementById('settings-ai-provider').value='server';
  if (p.camLens && document.getElementById('pref-cam-lens')) document.getElementById('pref-cam-lens').value=p.camLens;
  if (p.camRes && document.getElementById('pref-cam-res')) document.getElementById('pref-cam-res').value=p.camRes;
  if (p.camMirror !== undefined && document.getElementById('pref-cam-mirror')) document.getElementById('pref-cam-mirror').checked=p.camMirror;
};

window.renderMasterReportUI = function (report) {
  if (!report) return;
  const set=(id,v)=>{const e=document.getElementById(id); if(e) e.textContent=v;};
  set('master-report-id', `#${report.id}`); set('master-report-client-name', `Unified Report for ${report.clientName}`); set('master-report-date-intent', `Generated on ${report.date} • Focus: ${report.focusIntent}`); set('master-score-val', `${report.compositeScore} / 100`); set('metric-palm-score', `${report.palmMetrics.overallConf}%`); set('metric-tarot-score', `${report.tarotCards.length} cards`); set('master-palm-archetype-badge', report.palmMetrics.shape); set('master-spread-title-badge', report.spreadName); set('rec-client-name', report.clientName);
  const sections={executive:'master-executive-synthesis',mindset:'syn-mindset',career:'syn-career',love:'syn-love',health:'syn-health',destiny:'syn-destiny'};
  Object.entries(sections).forEach(([key,id])=>set(id,report.synthesis?.[key] || ''));
  const canvas=document.getElementById('masterReportPalmCanvas'); const path=report.palmMetrics.processed_image_path || report.palmMetrics.image_path;
  if(canvas && path){ const img=new Image(); img.onload=()=>{canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;canvas.getContext('2d').drawImage(img,0,0);}; img.src=`${location.origin}/${String(path).replace(/^\//,'')}`; }
  const cards=report.tarotCards||[]; masterDrawnCards=cards; renderCombinedDrawnCardsGrid();
  const recContainer=document.getElementById('master-recommendations-container'); if(recContainer) recContainer.innerHTML=(report.recommendations||[]).map(r=>`<div class="bg-mystic-950/60 border border-mystic-800 rounded-xl p-4"><div class="flex justify-between gap-3"><strong class="text-white text-xs">${r.title}</strong><span class="text-[9px] text-gold-400 uppercase">${r.category}</span></div><p class="text-[10px] text-gray-400 mt-1">${r.description}</p></div>`).join('');
};

async function downloadBackendReport(type) {
  if (!currentMasterReport) { alert('Generate a combined report first.'); return; }
  const readingId = currentMasterReport.backendReadingId || String(currentMasterReport.id).replace(/\D/g,'');
  try {
    const blob = await aetheriaApi(`/reports/${type}/combined/${readingId}`);
    const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=`aetheria_combined_${readingId}.${type==='pdf'?'pdf':'xlsx'}`; a.click(); URL.revokeObjectURL(url);
  } catch(err){ alert(err.message); }
}
window.exportMasterReportPDF=()=>downloadBackendReport('pdf');
window.exportMasterReportExcel=()=>downloadBackendReport('excel');

// Keep specialist KPI cards tied to persisted analytics.
const _updateConsultantConsole = window.updateConsultantConsole;
window.updateConsultantConsole = async function(){
  try { const data=await aetheriaApi('/analytics/consultant'); const a=document.getElementById('consultant-kpi-clients'); if(a)a.textContent=data.client_count; const b=document.getElementById('consultant-kpi-score'); if(b)b.textContent=data.average_guidance_score==null?'—':`${data.average_guidance_score}/100`; const c=document.getElementById('consultant-kpi-sessions'); if(c)c.textContent=`${data.reading_count} Sessions`; } catch(err){ addAuditLog(`Consultant analytics unavailable: ${err.message}`); }
};
window.toggleTaskComplete = async function(id) {
  try { await aetheriaApi(`/recommendations/${id}/complete`, {method:'PUT'}); await syncRemoteData(); renderRecommendationsList(); }
  catch(err) { alert(err.message); }
};

// ---------------------------------------------------------------------------
// Milestone 4: bind existing dashboard/report UI to persisted backend data.
// These overrides intentionally preserve the existing HTML and visual design.
// ---------------------------------------------------------------------------
async function loadUserAnalytics() {
  const data = await aetheriaApi('/analytics/user');
  localStorage.setItem('aetheria_user_analytics', JSON.stringify(data));
  return data;
}

const _m4UpdateDashboardData = window.updateDashboardData;
window.updateDashboardData = async function () {
  if (!currentUser) return;
  try {
    const data = await loadUserAnalytics();
    const readings = getReadings();
    const latest = readings[0];
    const set = (id, value) => { const el = document.getElementById(id); if (el) el.innerText = value; };
    set('dash-greeting-name', currentUser.name || currentUser.full_name || '');
    set('dash-palm-count', data.palm_readings);
    set('dash-tarot-count', data.tarot_readings);
    set('dash-guidance-score', data.average_guidance_score == null ? '—' : Math.round(data.average_guidance_score));
    set('dash-palm-weight', latest?.metadata?.lifeConf == null ? '--' : `${latest.metadata.lifeConf}%`);
    set('dash-tarot-weight', data.tarot_readings ? `${Math.round(data.average_guidance_score || 0)}%` : '--');
    set('dash-personality-weight', data.average_guidance_score == null ? '--' : `${Math.round(data.average_guidance_score)}%`);
    if (latest) {
      set('dash-current-theme', latest.focus || '');
      set('dash-current-theme-desc', latest.interpretation?.opening || latest.interpretation?.synthesis || '');
    }
    renderGuidanceScoreGauge(data.average_guidance_score == null ? 0 : data.average_guidance_score);
    const recs = (JSON.parse(localStorage.getItem('aetheria_recommendations') || '[]')).slice(0, 2);
    const container = document.getElementById('dash-recs-container');
    const empty = document.getElementById('dash-recs-empty');
    if (container && empty) {
      if (!recs.length) { container.classList.add('hidden'); empty.classList.remove('hidden'); }
      else { empty.classList.add('hidden'); container.classList.remove('hidden'); container.innerHTML = recs.map(r => `<div class="flex items-center space-x-2 bg-mystic-900/30 p-2.5 rounded-lg border border-mystic-800/40 text-xs"><i class="fa-solid fa-circle-notch text-gold-400"></i><span class="text-gray-300 font-medium truncate flex-1">${r.title}</span><span class="text-[9px] bg-mystic-900 text-gray-400 px-2 py-0.5 rounded">${r.category}</span></div>`).join(''); }
    }
    const tableBody = document.getElementById('dash-history-table-body');
    if (tableBody) {
      const mini = readings.slice(0, 3);
      tableBody.innerHTML = mini.length ? mini.map(r => `<tr class="border-b border-mystic-900/50 hover:bg-mystic-900/10"><td class="p-3 font-semibold text-white font-mono">${r.id}</td><td class="p-3">${r.date}</td><td class="p-3 text-gray-400">${r.type}</td><td class="p-3">${r.focus}</td><td class="p-3 font-bold text-gold-400">${r.score == null ? '—' : `${r.score}/100`}</td><td class="p-3 text-right"><button onclick="viewReadingDetails('${r.id}')" class="text-gold-400 hover:text-gold-500 text-xs font-semibold">View</button></td></tr>`).join('') : '<tr><td colspan="6" class="p-3 text-center text-gray-500">No readings found.</td></tr>';
    }
  } catch (err) {
    addAuditLog(`User analytics unavailable: ${err.message}`);
    if (typeof _m4UpdateDashboardData === 'function') _m4UpdateDashboardData();
  }
};

window.renderInsightsRadar = async function () {
  const empty = document.getElementById('personality-empty');
  const container = document.getElementById('personality-container');
  if (!currentUser) return;
  try {
    const profile = await aetheriaApi('/insights/personality');
    if (empty) empty.classList.add('hidden');
    if (container) container.classList.remove('hidden');
    const strengths = document.getElementById('pers-strengths');
    if (strengths) strengths.innerText = profile.summary || 'Personality profile generated from your persisted reading history.';
    const values = profile.big_five || {};
    const labels = ['Openness', 'Conscientiousness', 'Extraversion', 'Agreeableness', 'Emotional Stability'];
    const data = [values.openness, values.conscientiousness, values.extraversion, values.agreeableness, values.emotional_stability].map(v => Number(v) || 0);
    const canvas = document.getElementById('insightsRadarChart');
    if (!canvas || typeof Chart === 'undefined') return;
    const ctx = canvas.getContext('2d');
    if (radarChartObj) radarChartObj.destroy();
    radarChartObj = new Chart(ctx, { type: 'radar', data: { labels, datasets: [{ label: 'Reading-derived profile', data, backgroundColor: 'rgba(139, 92, 246, 0.2)', borderColor: '#8b5cf6', borderWidth: 2, pointBackgroundColor: '#fbbf24' }] }, options: { scales: { r: { min: 0, max: 100, ticks: { display: false } } }, plugins: { legend: { display: false } } } });
  } catch (err) {
    if (empty) empty.classList.remove('hidden');
    if (container) container.classList.add('hidden');
  }
};

window.updateAdminConsole = async function () {
  try {
    const [data, users] = await Promise.all([aetheriaApi('/analytics/executive'), aetheriaApi('/admin/users')]);
    const set = (id, value) => { const el = document.getElementById(id); if (el) el.innerText = value; };
    set('admin-kpi-users', data.total_users); set('admin-kpi-readings', data.total_readings); set('admin-kpi-cv', data.palm_readings ? `${Math.round(data.palm_readings / Math.max(data.total_readings, 1) * 100)}%` : '0%'); set('admin-kpi-latency', data.average_api_latency_ms == null ? '—' : `${data.average_api_latency_ms} ms`);
    const tbody = document.getElementById('admin-users-table-body');
    if (tbody) tbody.innerHTML = users.map(u => `<tr class="border-b border-mystic-900 hover:bg-mystic-900/20"><td class="p-3 font-semibold text-white">${u.full_name}</td><td class="p-3 text-gray-400">${u.email}</td><td class="p-3"><span class="bg-mystic-900 text-gold-400 px-2 py-0.5 rounded text-[10px] border border-mystic-800 font-bold">${u.role}</span></td><td class="p-3 ${u.is_active ? 'text-green-400' : 'text-red-400'}">${u.is_active ? 'Active' : 'Inactive'}</td><td class="p-3 text-right text-gray-500">ID ${u.id}</td></tr>`).join('');
  } catch (err) { addAuditLog(`Admin analytics unavailable: ${err.message}`); }
};

window.updateReaderConsole = async function () {
  try {
    const data = await aetheriaApi('/analytics/reader');
    const tbody = document.getElementById('reader-queue-table-body');
    if (tbody) tbody.innerHTML = data.recent_readings.length ? data.recent_readings.map(r => `<tr class="border-b border-mystic-900 hover:bg-mystic-900/20"><td class="p-3 font-semibold text-white font-mono">TRT-${r.id}</td><td class="p-3">Authenticated client</td><td class="p-3 text-gray-400">${r.spread_name}</td><td class="p-3">${new Date(r.created_at).toLocaleDateString()}</td><td class="p-3 text-right text-gray-500">Persisted</td></tr>`).join('') : '<tr><td colspan="5" class="p-4 text-center text-gray-500">No persisted Tarot readings found.</td></tr>';
    const ctx = document.getElementById('readerChart')?.getContext('2d');
    if (ctx && typeof Chart !== 'undefined') { if (readerChartObj) readerChartObj.destroy(); const labels = Object.keys(data.category_breakdown); const values = Object.values(data.category_breakdown); readerChartObj = new Chart(ctx, { type: 'doughnut', data: { labels, datasets: [{ data: values, borderWidth: 0 }] }, options: { plugins: { legend: { display: true, labels: { color: '#ede9fe' } } } } }); }
  } catch (err) { addAuditLog(`Reader analytics unavailable: ${err.message}`); }
};

window.updateConsultantConsole = async function () {
  try {
    const data = await aetheriaApi('/analytics/consultant');
    const set = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
    set('consultant-kpi-sessions', `${data.reading_count} Sessions`); set('consultant-kpi-score', data.average_guidance_score == null ? '—' : `${data.average_guidance_score}/100`);
    const ctx = document.getElementById('consultantChart')?.getContext('2d');
    if (ctx && typeof Chart !== 'undefined') { if (consultantChartObj) consultantChartObj.destroy(); const points = data.readings_by_day.filter(x => x.average != null); consultantChartObj = new Chart(ctx, { type: 'line', data: { labels: points.map(x => x.date), datasets: [{ label: 'Avg Guidance Trend', data: points.map(x => x.average), tension: 0.4, fill: false }] }, options: { scales: { y: { min: 0, max: 100 } }, plugins: { legend: { display: false } } } }); }
  } catch (err) { addAuditLog(`Consultant analytics unavailable: ${err.message}`); }
};

async function downloadPersistedReport(type, reading) {
  if (!reading) { alert('Select a persisted reading first.'); return; }
  const match = String(reading.id).match(/^(PLM|TRT)-(\d+)$/);
  if (!match) { alert('This report is not linked to a persisted backend reading.'); return; }
  const readingType = match[1] === 'PLM' ? 'palm' : 'tarot';
  try {
    const blob = await aetheriaApi(`/reports/${type}/${readingType}/${match[2]}`);
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `aetheria_${readingType}_${match[2]}.${type === 'pdf' ? 'pdf' : 'xlsx'}`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    addAuditLog(`Exported persisted ${type.toUpperCase()} report for ${reading.id}`);
  } catch (err) { alert(err.message); }
}
window.exportCurrentReportPDF = () => downloadPersistedReport('pdf', currentReading);
window.exportCurrentReportExcel = () => downloadPersistedReport('excel', currentReading);
window.generateSpiritualConsulteReport = async function () {
  try {
    const blob = await aetheriaApi('/reports/excel/consultant');
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'aetheria_consultant_analytics.xlsx'; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    addAuditLog('Exported persisted consultant analytics workbook');
  } catch (err) { alert(err.message); }
};
