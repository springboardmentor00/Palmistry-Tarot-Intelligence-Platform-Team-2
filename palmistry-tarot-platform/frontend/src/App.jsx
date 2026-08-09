import React, { useState, useEffect, useRef } from 'react';
// Note: We use Lucide icons or simple font-awesome classes as in index.html to maintain consistent visual assets.

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

  // Read State from localStorage if present
  useEffect(() => {
    const session = localStorage.getItem('aetheria_session');
    if (session) {
      const parsed = JSON.parse(session);
      setUser(parsed);
      setActiveTab(parsed.role === 'ADMINISTRATOR' ? 'admin-dash' : 'dashboard');
    }
  }, []);

  const addLog = (msg) => {
    const timestamp = new Date().toISOString().split('T')[1].slice(0, 8);
    setAuditLogs(prev => [`[${timestamp}] ${msg}`, ...prev]);
  };

  const handleLogout = () => {
    addLog(`User logged out: ${user?.email}`);
    setUser(null);
    localStorage.removeItem('aetheria_session');
    setActiveTab('home');
  };

  // Quick Demo logins
  const loginAsDemo = (role) => {
    const accounts = {
      'USER': { email: 'user@aetheria.ai', name: 'Aurelia Vance', role: 'USER', ageGroup: '25-34', goals: ['Self Reflection'], interests: ['Tarot'] },
      'TAROT_READER': { email: 'reader@aetheria.ai', name: 'Reader Diana', role: 'TAROT_READER' },
      'SPIRITUAL_CONSULTANT': { email: 'consultant@aetheria.ai', name: 'Consultant Arthur', role: 'SPIRITUAL_CONSULTANT' },
      'ADMINISTRATOR': { email: 'admin@aetheria.ai', name: 'Platform Admin', role: 'ADMINISTRATOR' }
    };
    const selected = accounts[role];
    setUser(selected);
    localStorage.setItem('aetheria_session', JSON.stringify(selected));
    addLog(`User authenticated via Demo: ${selected.email} (${selected.role})`);
    setActiveTab(role === 'ADMINISTRATOR' ? 'admin-dash' : role === 'TAROT_READER' ? 'reader-dash' : role === 'SPIRITUAL_CONSULTANT' ? 'consultant-dash' : 'dashboard');
  };

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
            <button onClick={() => loginAsDemo('USER')} className="bg-gradient-to-r from-mystic-800 to-mystic-900 border border-mystic-500 hover:from-mystic-500 hover:to-gold-500 px-4 py-1.5 rounded-lg text-sm transition-all duration-300 flex items-center space-x-2 font-medium">
              <i className="fa-solid fa-sign-in-alt"></i>
              <span>Demo Login</span>
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
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-6">
              <button onClick={() => loginAsDemo('USER')} className="p-4 rounded-xl border border-mystic-800 bg-mystic-950/40 hover:border-gold-500 text-left">
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
                <span class="text-xs uppercase text-gold-400 font-bold tracking-wider">Composite Guidance Score</span>
                <span className="text-5xl font-black text-white">85</span>
                <span className="text-[10px] text-gray-400">Insight Normalization Index</span>
              </div>
              
              <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
                <div>
                  <span className="text-xs text-gray-400">Active Theme Archetype</span>
                  <h4 className="text-lg font-bold text-white mt-1 font-mystic-title">Awaiting Assessment</h4>
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

        {/* Placeholder layouts for other pages in React Workspace */}
        {activeTab === 'palm' && (
          <section className="max-w-xl mx-auto glass-panel p-8 rounded-3xl text-center space-y-6">
            <h2 className="text-2xl font-bold font-mystic-title">Palm Scanner Portal</h2>
            <p className="text-xs text-gray-400">To utilize the active computer vision pipeline, launch the python main server or double-click the root index.html to run the client-side canvas tracker instantly.</p>
            <button onClick={() => setActiveTab('dashboard')} className="border border-mystic-800 hover:bg-mystic-900 px-6 py-2 rounded-xl text-xs">Back to Dashboard</button>
          </section>
        )}

        {activeTab === 'tarot' && (
          <section className="max-w-xl mx-auto glass-panel p-8 rounded-3xl text-center space-y-6">
            <h2 className="text-2xl font-bold font-mystic-title">Tarot Divination Oracle</h2>
            <p className="text-xs text-gray-400">Draw cards and select spreads dynamically. Double-click root index.html to run the interactive shuffler instantly.</p>
            <button onClick={() => setActiveTab('dashboard')} className="border border-mystic-800 hover:bg-mystic-900 px-6 py-2 rounded-xl text-xs">Back to Dashboard</button>
          </section>
        )}

        {activeTab === 'admin-dash' && (
          <section className="space-y-6">
            <div className="glass-panel p-6 rounded-3xl">
              <h2 class="text-xl font-bold text-white font-mystic-title">Admin Console</h2>
              <p class="text-xs text-gray-400 mt-1">Platform management and audit logging details.</p>
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
