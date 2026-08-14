import React, { useState, useEffect, useRef } from 'react';
import api from './api';
// Note: We use Lucide icons or simple font-awesome classes as in index.html to maintain consistent visual assets.

const LINE_COLORS = {
  life: 'bg-green-500',
  head: 'bg-blue-500',
  heart: 'bg-pink-500',
  fate: 'bg-mystic-500',
  sun: 'bg-gold-500',
};

const SPREADS = [
  { id: 'single', label: 'Single Card', desc: 'One card, core focus.' },
  { id: 'three', label: 'Past / Present / Future', desc: 'A three card timeline spread.' },
  { id: 'celtic', label: 'Celtic Cross', desc: 'The full 10-card in-depth spread.' },
];

export default function App() {
  // Authentication & Session
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('home');
  const [profileDropdown, setProfileDropdown] = useState(false);
  const [notifications, setNotifications] = useState([
    { id: 1, title: 'Welcome to Aetheria', message: 'Explore the mystical insights portal. Start with a palm analysis or draw tarot cards.', read: false, date: new Date().toLocaleDateString() },
    { id: 2, title: 'Daily Guidance Alert', message: 'Reflect upon decision-making paths today. Focus and clear blockages.', read: false, date: new Date().toLocaleDateString() }
  ]);
  const [notifModal, setNotifModal] = useState(false);
  const [auditLogs, setAuditLogs] = useState(["[System Boot] React front-end container initialised."]);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');

  // Palm analysis state
  const [palmFile, setPalmFile] = useState(null);
  const [palmPreview, setPalmPreview] = useState(null);
  const [palmLoading, setPalmLoading] = useState(false);
  const [palmError, setPalmError] = useState('');
  const [palmResult, setPalmResult] = useState(null);
  const fileInputRef = useRef(null);

  // Tarot state
  const [selectedSpread, setSelectedSpread] = useState('three');
  const [focusIntent, setFocusIntent] = useState('');
  const [tarotLoading, setTarotLoading] = useState(false);
  const [tarotError, setTarotError] = useState('');
  const [tarotResult, setTarotResult] = useState(null);

  const addLog = (msg) => {
    const timestamp = new Date().toISOString().split('T')[1].slice(0, 8);
    setAuditLogs(prev => [`[${timestamp}] ${msg}`, ...prev]);
  };

  // Restore real backend session (JWT) on load, if present.
  useEffect(() => {
    const token = localStorage.getItem('aetheria_token');
    const cachedSession = localStorage.getItem('aetheria_session');

    if (token) {
      api.getMe()
        .then((me) => {
          const sessionUser = {
            email: me.email,
            name: me.full_name,
            role: me.role,
            id: me.id,
            goals: me.profile?.goals || [],
            interests: me.profile?.interests || [],
          };
          setUser(sessionUser);
          setActiveTab(sessionUser.role === 'ADMINISTRATOR' ? 'admin-dash' : 'dashboard');
        })
        .catch(() => {
          // Token expired/invalid - clear it silently and fall back to local demo session if any.
          localStorage.removeItem('aetheria_token');
          if (cachedSession) restoreLocalDemoSession(cachedSession);
        });
    } else if (cachedSession) {
      restoreLocalDemoSession(cachedSession);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const restoreLocalDemoSession = (raw) => {
    const parsed = JSON.parse(raw);
    setUser(parsed);
    setActiveTab(parsed.role === 'ADMINISTRATOR' ? 'admin-dash' : parsed.role === 'TAROT_READER' ? 'reader-dash' : parsed.role === 'SPIRITUAL_CONSULTANT' ? 'consultant-dash' : 'dashboard');
  };

  const handleLogout = () => {
    addLog(`User logged out: ${user?.email}`);
    setUser(null);
    setPalmResult(null);
    setTarotResult(null);
    localStorage.removeItem('aetheria_session');
    localStorage.removeItem('aetheria_token');
    setActiveTab('home');
  };

  // Demo login. USER logs into the real FastAPI backend (auto-registering the
  // documented demo account on first use) so Palm/Tarot actually work end to
  // end. The reader/consultant/admin roles remain local-only demo shells
  // (unchanged from before) since role-elevated accounts aren't part of the
  // Milestone 2 self-registration flow.
  const loginAsDemo = async (role) => {
    if (role !== 'USER') {
      const accounts = {
        'TAROT_READER': { email: 'reader@aetheria.ai', name: 'Reader Diana', role: 'TAROT_READER' },
        'SPIRITUAL_CONSULTANT': { email: 'consultant@aetheria.ai', name: 'Consultant Arthur', role: 'SPIRITUAL_CONSULTANT' },
        'ADMINISTRATOR': { email: 'admin@aetheria.ai', name: 'Platform Admin', role: 'ADMINISTRATOR' }
      };
      const selected = accounts[role];
      setUser(selected);
      localStorage.setItem('aetheria_session', JSON.stringify(selected));
      addLog(`User authenticated via Demo: ${selected.email} (${selected.role})`);
      setActiveTab(role === 'ADMINISTRATOR' ? 'admin-dash' : 'reader-dash');
      return;
    }

    setAuthLoading(true);
    setAuthError('');
    const email = 'user@aetheria.ai';
    const password = 'password';

    try {
      let token;
      try {
        const loginRes = await api.login(email, password);
        token = loginRes.access_token;
      } catch (loginErr) {
        // First run: demo account doesn't exist yet on this backend - register it.
        await api.register({
          email,
          password,
          full_name: 'Aurelia Vance',
          age_group: '25-34',
          interests: ['Tarot'],
          goals: ['Self Reflection'],
        });
        const loginRes = await api.login(email, password);
        token = loginRes.access_token;
      }

      localStorage.setItem('aetheria_token', token);
      const me = await api.getMe();
      const sessionUser = {
        email: me.email,
        name: me.full_name,
        role: me.role,
        id: me.id,
        goals: me.profile?.goals || [],
        interests: me.profile?.interests || [],
      };
      setUser(sessionUser);
      localStorage.removeItem('aetheria_session');
      addLog(`User authenticated via backend: ${sessionUser.email} (${sessionUser.role})`);
      setActiveTab('dashboard');
    } catch (err) {
      setAuthError(err.message);
      addLog(`Authentication failed: ${err.message}`);
    } finally {
      setAuthLoading(false);
    }
  };

  // --- Palm analysis handlers ---------------------------------------------
  const handlePalmFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPalmFile(file);
    setPalmResult(null);
    setPalmError('');
    const reader = new FileReader();
    reader.onload = () => setPalmPreview(reader.result);
    reader.readAsDataURL(file);
  };

  const handleAnalyzePalm = async () => {
    if (!palmPreview) return;
    setPalmLoading(true);
    setPalmError('');
    setPalmResult(null);
    try {
      const result = await api.analyzePalm(palmPreview);
      setPalmResult(result);
      addLog(`Palm analysis completed: reading #${result.id} (${result.palm_shape})`);
    } catch (err) {
      setPalmError(err.message);
      addLog(`Palm analysis failed: ${err.message}`);
    } finally {
      setPalmLoading(false);
    }
  };

  // --- Tarot handlers -------------------------------------------------------
  const handleDrawTarot = async () => {
    setTarotLoading(true);
    setTarotError('');
    setTarotResult(null);
    try {
      const result = await api.drawTarotReading(selectedSpread, focusIntent || 'General');
      setTarotResult(result);
      addLog(`Tarot reading completed: reading #${result.id} (${result.spread_name})`);
    } catch (err) {
      setTarotError(err.message);
      addLog(`Tarot reading failed: ${err.message}`);
    } finally {
      setTarotLoading(false);
    }
  };

  const isBackendUser = !!localStorage.getItem('aetheria_token');

  return (
    <div className="min-h-screen flex flex-col bg-mystic-950 text-mystic-50 font-sans">
      {/* Header bar */}
      <header className="glass-panel sticky top-0 z-50 px-4 py-3 flex justify-between items-center">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('home')}>
          <div className="h-10 w-10 rounded-full bg-gradient-to-tr from-mystic-500 to-gold-400 flex items-center justify-center text-mystic-950 font-bold text-xl">
            <i className="fa-solid fa-wand-magic-sparkles"></i>
          </div>
          <div>
            <h1 className="text-xl font-black tracking-wider text-white font-mystic-title">AETHERIA</h1>
            <p className="text-[9px] tracking-widest text-gold-400 uppercase font-semibold">Spiritual AI Intelligence</p>
          </div>
        </div>

        {/* Navigation */}
        {user && (
          <nav className="hidden md:flex items-center space-x-6 text-sm font-medium">
            <button onClick={() => setActiveTab('home')} className={`transition-colors ${activeTab === 'home' ? 'text-gold-400' : 'text-gray-300 hover:text-gold-400'}`}>Home</button>
            {user.role === 'USER' && (
              <>
                <button onClick={() => setActiveTab('dashboard')} className={`transition-colors ${activeTab === 'dashboard' ? 'text-gold-400' : 'text-gray-300 hover:text-gold-400'}`}>Dashboard</button>
                <button onClick={() => setActiveTab('palm')} className={`transition-colors ${activeTab === 'palm' ? 'text-gold-400' : 'text-gray-300 hover:text-gold-400'}`}>Palm Analysis</button>
                <button onClick={() => setActiveTab('tarot')} className={`transition-colors ${activeTab === 'tarot' ? 'text-gold-400' : 'text-gray-300 hover:text-gold-400'}`}>Tarot Reading</button>
              </>
            )}
            {user.role === 'ADMINISTRATOR' && <button onClick={() => setActiveTab('admin-dash')} className="text-gray-300 hover:text-gold-400">Admin Panel</button>}
            {user.role === 'TAROT_READER' && <button onClick={() => setActiveTab('reader-dash')} className="text-gray-300 hover:text-gold-400">Reader Room</button>}
            {user.role === 'SPIRITUAL_CONSULTANT' && <button onClick={() => setActiveTab('consultant-dash')} className="text-gray-300 hover:text-gold-400">Consultant Panel</button>}
          </nav>
        )}

        {/* Auth / Profile Actions */}
        <div className="flex items-center space-x-4">
          {user ? (
            <div className="relative">
              <button onClick={() => setProfileDropdown(!profileDropdown)} className="flex items-center space-x-2 border border-mystic-500/30 rounded-full bg-mystic-950/80 px-3 py-1">
                <div className="w-7 h-7 rounded-full bg-indigo-800 flex items-center justify-center text-xs font-bold text-white uppercase">{user.name[0]}</div>
                <span className="text-xs text-gray-200 font-semibold">{user.name}</span>
              </button>
              {profileDropdown && (
                <div className="absolute right-0 mt-2 w-48 rounded-xl bg-mystic-950 border border-mystic-800 p-2 shadow-2xl z-50">
                  <button onClick={handleLogout} className="w-full text-left flex items-center space-x-2 px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-red-950/20"><i className="fa-solid fa-arrow-right-from-bracket"></i> <span>Logout</span></button>
                </div>
              )}
            </div>
          ) : (
            <button onClick={() => loginAsDemo('USER')} disabled={authLoading} className="bg-gradient-to-r from-mystic-800 to-mystic-900 border border-mystic-500 hover:from-mystic-500 hover:to-gold-500 px-4 py-1.5 rounded-lg text-sm transition-all duration-300 flex items-center space-x-2 font-medium disabled:opacity-60">
              <i className={`fa-solid ${authLoading ? 'fa-circle-notch fa-spin' : 'fa-sign-in-alt'}`}></i>
              <span>{authLoading ? 'Connecting...' : 'Demo Login'}</span>
            </button>
          )}
        </div>
      </header>

      {/* Main page router wrapper */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {activeTab === 'home' && (
          <section className="text-center max-w-3xl mx-auto space-y-8 py-12">
            <h2 className="text-4xl md:text-6xl font-black font-mystic-title leading-tight text-transparent bg-clip-text bg-gradient-to-r from-white to-gold-400">
              DISCOVER YOUR SPIRITUAL ALIGNMENT
            </h2>
            <p className="text-gray-300">
              Aetheria merges computer vision edge detection overlays with the wisdom of Palmistry and Tarot spread divination models.
            </p>
            {authError && (
              <p className="text-xs text-red-400 bg-red-950/20 border border-red-500/20 rounded-lg py-2 px-3 inline-block">{authError}</p>
            )}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-6">
              <button onClick={() => loginAsDemo('USER')} disabled={authLoading} className="p-4 rounded-xl border border-mystic-800 bg-mystic-950/40 hover:border-gold-500 text-left disabled:opacity-60">
                <span className="block text-xs font-bold text-white">Guest User</span>
                <span className="text-[10px] text-gray-400 block mt-1">Readings Dashboard</span>
              </button>
              <button onClick={() => loginAsDemo('TAROT_READER')} className="p-4 rounded-xl border border-mystic-800 bg-mystic-950/40 hover:border-gold-500 text-left">
                <span className="block text-xs font-bold text-white">Reader Diana</span>
                <span className="text-[10px] text-gray-400 block mt-1">Reading Queue</span>
              </button>
              <button onClick={() => loginAsDemo('SPIRITUAL_CONSULTANT')} className="p-4 rounded-xl border border-mystic-800 bg-mystic-950/40 hover:border-gold-500 text-left">
                <span className="block text-xs font-bold text-white">Consultant Arthur</span>
                <span className="text-[10px] text-gray-400 block mt-1">Guidance Scores</span>
              </button>
              <button onClick={() => loginAsDemo('ADMINISTRATOR')} className="p-4 rounded-xl border border-mystic-800 bg-mystic-950/40 hover:border-gold-500 text-left">
                <span className="block text-xs font-bold text-white">Platform Admin</span>
                <span className="text-[10px] text-gray-400 block mt-1">Security & Telemetry</span>
              </button>
            </div>
          </section>
        )}

        {activeTab === 'dashboard' && (
          <section className="space-y-6">
            <div className="glass-panel rounded-3xl p-6 flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold font-mystic-title">Greetings, {user?.name}</h2>
                <p className="text-xs text-gray-400 mt-1">Explore your guidance records and actions plan indicators below.</p>
              </div>
              <div className="flex space-x-2">
                <button onClick={() => setActiveTab('palm')} className="bg-mystic-800 px-4 py-2 rounded-xl text-xs font-semibold hover:bg-mystic-700">New Palm Scan</button>
                <button onClick={() => setActiveTab('tarot')} className="bg-gold-500 text-mystic-950 px-4 py-2 rounded-xl text-xs font-bold hover:bg-gold-600">Draw Tarot</button>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="glass-panel p-6 rounded-2xl text-center flex flex-col items-center justify-center space-y-3">
                <span className="text-xs uppercase text-gold-400 font-bold tracking-wider">Composite Guidance Score</span>
                <span className="text-5xl font-black text-white">{palmResult?.overall_conf ? Math.round(palmResult.overall_conf) : (tarotResult ? 85 : 85)}</span>
                <span className="text-[10px] text-gray-400">Insight Normalization Index</span>
              </div>
              
              <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
                <div>
                  <span className="text-xs text-gray-400">Active Theme Archetype</span>
                  <h4 className="text-lg font-bold text-white mt-1 font-mystic-title">
                    {palmResult?.palm_shape || tarotResult?.cards_drawn?.[0]?.card?.name || 'Awaiting Assessment'}
                  </h4>
                </div>
                <p className="text-[10px] text-gray-500">Run a reading to evaluate your active cycles.</p>
              </div>

              <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
                <div>
                  <span className="text-xs text-gray-400">Spiritual Recommendations</span>
                  <div className="mt-2 text-xs space-y-1.5">
                    <div className="bg-mystic-900/30 p-2 rounded border border-mystic-800/40">Integrate analytical insights into career paths</div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'palm' && (
          <section className="max-w-3xl mx-auto glass-panel p-8 rounded-3xl space-y-6">
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-bold font-mystic-title">Palm Scanner Portal</h2>
              <p className="text-xs text-gray-400">Upload a clear, well-lit photo of an open palm. Our OpenCV pipeline extracts your Life, Head, Heart, Fate, and Sun lines directly from the image.</p>
            </div>

            <div className="flex flex-col items-center space-y-4">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handlePalmFileSelect}
              />
              <div
                onClick={() => fileInputRef.current?.click()}
                className="w-full max-w-sm aspect-square rounded-2xl border-2 border-dashed border-mystic-700 hover:border-gold-500 flex items-center justify-center cursor-pointer overflow-hidden bg-mystic-950/40"
              >
                {palmPreview ? (
                  <img src={palmPreview} alt="Palm preview" className="w-full h-full object-cover" />
                ) : (
                  <div className="text-center px-4">
                    <i className="fa-solid fa-hand text-3xl text-mystic-600 mb-2"></i>
                    <p className="text-xs text-gray-400">Click to select a palm photo</p>
                  </div>
                )}
              </div>

              <button
                onClick={handleAnalyzePalm}
                disabled={!palmPreview || palmLoading}
                className="bg-gold-500 hover:bg-gold-600 text-mystic-950 font-bold px-6 py-2.5 rounded-xl text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {palmLoading && <i className="fa-solid fa-circle-notch fa-spin"></i>}
                <span>{palmLoading ? 'Analyzing Palm...' : 'Analyze Palm'}</span>
              </button>

              {palmError && (
                <p className="text-xs text-red-400 bg-red-950/20 border border-red-500/20 rounded-lg py-2 px-4 w-full max-w-sm text-center">{palmError}</p>
              )}
            </div>

            {palmResult && (
              <div className="space-y-5 pt-4 border-t border-mystic-800">
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div className="bg-mystic-900/30 rounded-xl p-3 border border-mystic-800/40">
                    <span className="block text-[10px] text-gray-400 uppercase tracking-wider">Palm Shape</span>
                    <span className="block text-sm font-bold text-white mt-1">{palmResult.palm_shape}</span>
                  </div>
                  <div className="bg-mystic-900/30 rounded-xl p-3 border border-mystic-800/40">
                    <span className="block text-[10px] text-gray-400 uppercase tracking-wider">Finger Structure</span>
                    <span className="block text-sm font-bold text-white mt-1">{palmResult.finger_structure}</span>
                  </div>
                </div>

                <div className="space-y-2">
                  {[
                    ['life', 'Life Line', palmResult.life_line_conf],
                    ['head', 'Head Line', palmResult.head_line_conf],
                    ['heart', 'Heart Line', palmResult.heart_line_conf],
                    ['fate', 'Fate Line', palmResult.fate_line_conf],
                    ['sun', 'Sun Line', palmResult.sun_line_conf],
                  ].map(([key, label, val]) => (
                    <div key={key}>
                      <div className="flex justify-between text-[10px] text-gray-400 mb-1">
                        <span>{label}</span>
                        <span>{val}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-mystic-900 rounded-full overflow-hidden">
                        <div className={`h-full ${LINE_COLORS[key]}`} style={{ width: `${Math.min(100, val)}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="text-center">
                  <span className="text-xs uppercase text-gold-400 font-bold tracking-wider">Overall Confidence</span>
                  <div className="text-4xl font-black text-white">{palmResult.overall_conf}</div>
                </div>

                {palmResult.processed_image_path && (
                  <div className="text-center">
                    <img
                      src={api.staticUrl(palmResult.processed_image_path)}
                      alt="Processed palm analysis"
                      className="rounded-xl border border-mystic-800 max-w-sm mx-auto"
                    />
                    <p className="text-[10px] text-gray-500 mt-1">Detected contour, convex hull, and traced line segments.</p>
                  </div>
                )}

                <div className="flex justify-center gap-3 pt-2">
                  <a href={api.pdfReportUrl('palm', palmResult.id)} target="_blank" rel="noreferrer" className="text-xs border border-mystic-700 hover:border-gold-500 px-4 py-2 rounded-lg text-gray-300">Download PDF</a>
                  <a href={api.excelReportUrl('palm', palmResult.id)} target="_blank" rel="noreferrer" className="text-xs border border-mystic-700 hover:border-gold-500 px-4 py-2 rounded-lg text-gray-300">Download Excel</a>
                </div>
              </div>
            )}

            <div className="text-center pt-2">
              <button onClick={() => setActiveTab('dashboard')} className="border border-mystic-800 hover:bg-mystic-900 px-6 py-2 rounded-xl text-xs">Back to Dashboard</button>
            </div>
          </section>
        )}

        {activeTab === 'tarot' && (
          <section className="max-w-3xl mx-auto glass-panel p-8 rounded-3xl space-y-6">
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-bold font-mystic-title">Tarot Divination Oracle</h2>
              <p className="text-xs text-gray-400">Choose a spread and draw from the full 78-card deck, synthesized into an AI reading.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {SPREADS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedSpread(s.id)}
                  className={`p-3 rounded-xl border text-left transition-colors ${selectedSpread === s.id ? 'border-gold-500 bg-mystic-900/50' : 'border-mystic-800 bg-mystic-950/40 hover:border-mystic-600'}`}
                >
                  <span className="block text-xs font-bold text-white">{s.label}</span>
                  <span className="text-[10px] text-gray-400 block mt-1">{s.desc}</span>
                </button>
              ))}
            </div>

            <input
              type="text"
              value={focusIntent}
              onChange={(e) => setFocusIntent(e.target.value)}
              placeholder="What would you like guidance on? (e.g. Career Paths)"
              className="glass-input w-full rounded-xl px-4 py-2.5 text-sm"
            />

            <div className="flex justify-center">
              <button
                onClick={handleDrawTarot}
                disabled={tarotLoading}
                className="bg-gold-500 hover:bg-gold-600 text-mystic-950 font-bold px-6 py-2.5 rounded-xl text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {tarotLoading && <i className="fa-solid fa-circle-notch fa-spin"></i>}
                <span>{tarotLoading ? 'Drawing Cards...' : 'Draw Cards'}</span>
              </button>
            </div>

            {tarotError && (
              <p className="text-xs text-red-400 bg-red-950/20 border border-red-500/20 rounded-lg py-2 px-4 text-center">{tarotError}</p>
            )}

            {tarotResult && (
              <div className="space-y-4 pt-4 border-t border-mystic-800">
                <div className={`grid gap-3 ${tarotResult.cards_drawn.length > 3 ? 'grid-cols-2 md:grid-cols-5' : 'grid-cols-1 md:grid-cols-3'}`}>
                  {tarotResult.cards_drawn.map((c, i) => (
                    <div key={i} className="bg-mystic-900/30 rounded-xl p-3 border border-mystic-800/40 text-center">
                      <span className="block text-[9px] text-gold-400 uppercase tracking-wider">{c.position_name}</span>
                      <span className="block text-sm font-bold text-white mt-1 font-mystic-title">{c.card.name}</span>
                      <span className={`text-[10px] mt-1 inline-block px-2 py-0.5 rounded-full ${c.is_reversed ? 'bg-red-950/40 text-red-400' : 'bg-green-950/40 text-green-400'}`}>
                        {c.is_reversed ? 'Reversed' : 'Upright'}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="flex justify-center gap-3 pt-2">
                  <a href={api.pdfReportUrl('tarot', tarotResult.id)} target="_blank" rel="noreferrer" className="text-xs border border-mystic-700 hover:border-gold-500 px-4 py-2 rounded-lg text-gray-300">Download PDF</a>
                  <a href={api.excelReportUrl('tarot', tarotResult.id)} target="_blank" rel="noreferrer" className="text-xs border border-mystic-700 hover:border-gold-500 px-4 py-2 rounded-lg text-gray-300">Download Excel</a>
                </div>
              </div>
            )}

            <div className="text-center pt-2">
              <button onClick={() => setActiveTab('dashboard')} className="border border-mystic-800 hover:bg-mystic-900 px-6 py-2 rounded-xl text-xs">Back to Dashboard</button>
            </div>
          </section>
        )}

        {activeTab === 'admin-dash' && (
          <section className="space-y-6">
            <div className="glass-panel p-6 rounded-3xl">
              <h2 className="text-xl font-bold text-white font-mystic-title">Admin Console</h2>
              <p className="text-xs text-gray-400 mt-1">Platform management and audit logging details.</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="glass-panel p-6 rounded-2xl md:col-span-2 space-y-3">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mystic-title">System Logs</h3>
                <div className="bg-mystic-950 p-4 rounded-xl font-mono text-[10px] text-green-400 h-64 overflow-y-auto space-y-1">
                  {auditLogs.map((log, i) => <div key={i}>{log}</div>)}
                </div>
              </div>
              
              <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mystic-title">Metrics Overview</h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between"><span>Total Users:</span><span className="font-bold">4</span></div>
                  <div className="flex justify-between"><span>CV Pipeline:</span><span className="font-bold">Operational</span></div>
                  <div className="flex justify-between"><span>API Latency:</span><span className="font-bold">12ms</span></div>
                </div>
                <button onClick={() => setAuditLogs(["[Flush Log] Logs flushed by administrator.", ...auditLogs])} className="w-full mt-4 border border-red-500/20 hover:bg-red-950/20 text-red-400 py-2 rounded-xl text-xs">Flush Logs</button>
              </div>
            </div>
          </section>
        )}
      </main>

      <footer className="glass-panel mt-auto py-4 text-center text-xs text-gray-500 border-t border-mystic-900">
        <p>© 2026 Aetheria Spiritual Intelligence. Developed as a production-grade React/FastAPI demonstration.</p>
      </footer>
    </div>
  );
}
