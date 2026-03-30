import React, { useState, useEffect, useRef } from 'react';

// ─── Constants ───────────────────────────────────────────────────────────────
const API_BASE_URL = 'http://localhost:8000'; 

const CATEGORY_EMOJIS = { food: '🍔', transport: '🚗', utilities: '💡', entertainment: '🎬', shopping: '🛍️', healthcare: '🏥' };
const CATEGORY_NAMES  = { food: 'Food & Dining', transport: 'Transport', utilities: 'Utilities', entertainment: 'Entertainment', shopping: 'Shopping', healthcare: 'Healthcare' };

const PAGE_TITLES = {
  dashboardPage: 'SPENDWISE', categoriesPage: 'CATEGORIES',
  addExpensePage: 'ADD EXPENSE', budgetPage: 'BUDGET', infoPage: 'SETTINGS',
};

// ─── Styles (Full Original Styles Restored) ──────────────────────────────────
const styles = `
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: #fef9f3; color: #2d3748; }
  .sw-app { max-width: 428px; margin: 0 auto; min-height: 100vh; background: #fef9f3; position: relative; padding-bottom: 70px; }
  .header { background: linear-gradient(135deg, #7c9cbf 0%, #8fa9c9 100%); color: #fff; padding: 20px; display: flex; justify-content: space-between; align-items: center; font-size: 18px; font-weight: 700; letter-spacing: 0.5px; box-shadow: 0 2px 8px rgba(124,156,191,0.25); }
  .header-title { flex: 1; text-align: center; }
  .content { padding: 20px; overflow-y: auto; height: calc(100vh - 130px); }
  .btn { width: 100%; padding: 16px 24px; border: none; background: linear-gradient(135deg, #8b9dc3 0%, #6b7fa8 100%); color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s; border-radius: 8px; margin-top: 10px; }
  .form-group { margin-bottom: 20px; text-align: left; }
  .form-group label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 14px; color: #2d3748; }
  .form-group input, .form-group select { width: 100%; padding: 12px; border: 2px solid #d4dce6; background: #fff; font-size: 16px; border-radius: 8px; color: #2d3748; }
  .bottom-nav { position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: 100%; max-width: 428px; background: #fff; display: flex; justify-content: space-around; padding: 10px 0; border-top: 2px solid #e8ecf1; z-index: 100; }
  .nav-item { display: flex; flex-direction: column; align-items: center; color: #a0aec0; text-decoration: none; font-size: 11px; cursor: pointer; font-weight: 600; }
  .nav-item.active { color: #8b9dc3; }
  .toast { position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); background: #2d3748; color: #fff; padding: 12px 20px; border-radius: 8px; z-index: 9999; }
`;

const SpendWise = () => {
  // ─── 1. SECURE STORAGE (The Backpack) ───
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('user_data')));
  const [page, setPage] = useState(token ? 'app' : 'welcomePage');
  const [activePage, setActivePage] = useState('dashboardPage');
  const [toast, setToast] = useState(null);

  // ─── 2. FORM DATA (Brain-Matched Labels) ───
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [setupData, setSetupData] = useState({ MonthlyIncome: '', HouseholdSize: '', TransportationTypes: 'public' });
  const [expForm, setExpForm] = useState({ Type: '', ItemName: '', AmountSpent: '', DatePurchased: new Date().toISOString().split('T')[0], Note: '' });
  const [categoryData, setCategoryData] = useState([]);

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(null), 2500); };

  // ─── 3. THE HANDSHAKE (Network Calls) ───

  // A helper function to show the "VIP Wristband" (Token) to the Brain
  const fetchWithAuth = async (url, options = {}) => {
    const headers = { ...options.headers, 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
    return fetch(`${API_BASE_URL}${url}`, { ...options, headers });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('username', loginForm.username);
    formData.append('password', loginForm.password);

    try {
      const response = await fetch(`${API_BASE_URL}/login`, { method: 'POST', body: formData });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('access_token', data.AccessToken);
        setToken(data.AccessToken);
        setPage('setup'); // Force setup after login
        showToast("Welcome back!");
      } else {
        showToast("Wrong name or password!");
      }
    } catch (err) { showToast("Brain is sleeping (Backend Error)"); }
  };

  const handleCompleteSetup = async (e) => {
    e.preventDefault();
    try {
      const res = await fetchWithAuth(`/settings/1/setup`, { // Hardcoded 1 for demo, should use user.id
        method: 'POST',
        body: JSON.stringify({ ...setupData, MonthlyIncome: parseFloat(setupData.MonthlyIncome), HouseholdSize: parseInt(setupData.HouseholdSize) })
      });
      if (res.ok) { setPage('app'); showToast("Setup Saved!"); }
    } catch (err) { setPage('app'); }
  };

  const loadCategories = async () => {
    try {
      const res = await fetchWithAuth('/categories/?period=all_time');
      const data = await res.json();
      setCategoryData(data);
    } catch (err) { console.log("Category sync failed"); }
  };

  const handleAddExpense = async (e) => {
    e.preventDefault();
    try {
      const res = await fetchWithAuth('/expenses/', {
        method: 'POST',
        body: JSON.stringify({ ...expForm, AmountSpent: parseFloat(expForm.AmountSpent) })
      });
      if (res.ok) { 
        showToast("Saved!"); 
        setExpForm({ Type: '', ItemName: '', AmountSpent: '', DatePurchased: new Date().toISOString().split('T')[0], Note: '' });
        setActivePage('dashboardPage');
        loadCategories();
      }
    } catch (err) { showToast("Save failed!"); }
  };

  useEffect(() => { if (token && activePage === 'categoriesPage') loadCategories(); }, [token, activePage]);

  // ─── 4. RENDER ───
  return (
    <div className="sw-app">
      <style>{styles}</style>
      {toast && <div className="toast">{toast}</div>}

      {/* LOGIN PAGE */}
      {page === 'welcomePage' && (
        <div className="content">
          <h1 style={{textAlign: 'center', marginTop: '50px', color: '#7c9cbf'}}>SPENDWISE</h1>
          <form onSubmit={handleLogin} style={{marginTop: '40px'}}>
            <div className="form-group">
              <label>Email</label>
              <input type="text" onChange={e => setLoginForm({...loginForm, username: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input type="password" onChange={e => setLoginForm({...loginForm, password: e.target.value})} required />
            </div>
            <button type="submit" className="btn">Sign In</button>
          </form>
        </div>
      )}

      {/* FORCED SETUP */}
      {page === 'setup' && (
        <div className="content">
          <h2>Initial Setup</h2>
          <p style={{color: '#666', marginBottom: '20px'}}>Mandatory for all users.</p>
          <form onSubmit={handleCompleteSetup}>
            <div className="form-group">
              <label>Monthly Income ($)</label>
              <input type="number" onChange={e => setSetupData({...setupData, MonthlyIncome: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Household Size</label>
              <input type="number" onChange={e => setSetupData({...setupData, HouseholdSize: e.target.value})} required />
            </div>
            <div className="form-group">
              <label>Transport Type</label>
              <select onChange={e => setSetupData({...setupData, TransportationTypes: e.target.value})}>
                <option value="public">Public Transport</option>
                <option value="car">Private Car</option>
              </select>
            </div>
            <button type="submit" className="btn">Finish Setup</button>
          </form>
        </div>
      )}

      {/* MAIN APP */}
      {page === 'app' && (
        <div>
          <div className="header"><div className="header-title">{PAGE_TITLES[activePage]}</div></div>
          <div className="content">
            {activePage === 'dashboardPage' && <div style={{textAlign: 'center', paddingTop: '50px'}}>📊 Dashboard Ready! <br/> Welcome to SpendWise.</div>}
            
            {activePage === 'categoriesPage' && (
              <div>
                {categoryData.map(cat => (
                  <div key={cat.category} className="form-group" style={{background: '#fff', padding: '15px', borderRadius: '10px', border: '1px solid #ddd', display: 'flex', justifyContent: 'space-between'}}>
                    <span>{CATEGORY_EMOJIS[cat.category.toLowerCase()] || '💰'} {cat.category}</span>
                    <span style={{fontWeight: 'bold'}}>${cat.total}</span>
                  </div>
                ))}
              </div>
            )}

            {activePage === 'addExpensePage' && (
              <form onSubmit={handleAddExpense}>
                <div className="form-group"><label>Item</label><input type="text" value={expForm.ItemName} onChange={e => setExpForm({...expForm, ItemName: e.target.value})} required /></div>
                <div className="form-group">
                  <label>Category</label>
                  <select value={expForm.Type} onChange={e => setExpForm({...expForm, Type: e.target.value})} required>
                    <option value="">Choose...</option>
                    {Object.keys(CATEGORY_NAMES).map(k => <option key={k} value={k}>{CATEGORY_NAMES[k]}</option>)}
                  </select>
                </div>
                <div className="form-group"><label>Amount ($)</label><input type="number" value={expForm.AmountSpent} onChange={e => setExpForm({...expForm, AmountSpent: e.target.value})} required /></div>
                <button type="submit" className="btn">Save to Cloud</button>
              </form>
            )}

            {activePage === 'infoPage' && (
              <div style={{textAlign: 'center'}}>
                <button className="btn" style={{background: '#d67c7c'}} onClick={() => { localStorage.clear(); window.location.reload(); }}>Log Out</button>
              </div>
            )}
          </div>

          <div className="bottom-nav">
            <div className={`nav-item ${activePage === 'dashboardPage' ? 'active' : ''}`} onClick={() => setActivePage('dashboardPage')}>📊<br/>Dash</div>
            <div className={`nav-item ${activePage === 'categoriesPage' ? 'active' : ''}`} onClick={() => setActivePage('categoriesPage')}>📁<br/>Cats</div>
            <div className={`nav-item ${activePage === 'addExpensePage' ? 'active' : ''}`} onClick={() => setActivePage('addExpensePage')}>➕<br/>Add</div>
            <div className={`nav-item ${activePage === 'infoPage' ? 'active' : ''}`} onClick={() => setActivePage('infoPage')}>⚙️<br/>Settings</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SpendWise;
