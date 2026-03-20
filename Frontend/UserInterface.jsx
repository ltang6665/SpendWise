import React, { useState, useEffect, useRef } from 'react';

// ─── Constants ───────────────────────────────────────────────────────────────
const CATEGORY_EMOJIS = { food: '🍔', transport: '🚗', utilities: '💡', entertainment: '🎬', shopping: '🛍️', healthcare: '🏥' };
const CATEGORY_NAMES  = { food: 'Food & Dining', transport: 'Transport', utilities: 'Utilities', entertainment: 'Entertainment', shopping: '️Shopping', healthcare: 'Healthcare' };

const INITIAL_CATEGORIES = [
  { key: 'food',          label: '🍔 Food & Dining',  total: 1250, items: [{ name: 'Grocery Shopping', date: 'Jan 28, 2026', amount: 85.50 }, { name: 'Restaurant Dinner', date: 'Jan 25, 2026', amount: 65.00 }, { name: 'Coffee Shop', date: 'Jan 23, 2026', amount: 12.50 }] },
  { key: 'transport',     label: '🚗 Transport',       total: 450,  items: [{ name: 'Gas Station', date: 'Jan 29, 2026', amount: 60.00 }, { name: 'MRT Card Top-up', date: 'Jan 20, 2026', amount: 50.00 }] },
  { key: 'utilities',     label: '💡 Utilities',        total: 320,  items: [{ name: 'Electricity Bill', date: 'Jan 15, 2026', amount: 120.00 }, { name: 'Water Bill', date: 'Jan 15, 2026', amount: 45.00 }] },
  { key: 'entertainment', label: '🎬 Entertainment',   total: 280,  items: [{ name: 'Netflix Subscription', date: 'Jan 1, 2026', amount: 15.99 }, { name: 'Movie Tickets', date: 'Jan 18, 2026', amount: 28.00 }] },
  { key: 'shopping',      label: '🛍️ Shopping',         total: 645,  items: [{ name: 'Clothing Store', date: 'Jan 22, 2026', amount: 120.00 }, { name: 'Amazon Order', date: 'Jan 10, 2026', amount: 85.50 }] },
  { key: 'healthcare',    label: '🏥 Healthcare',      total: 300,  items: [{ name: 'Doctor Visit', date: 'Jan 12, 2026', amount: 80.00 }, { name: 'Pharmacy', date: 'Jan 12, 2026', amount: 35.50 }] },
];

const NOTIFICATIONS = [
  { icon: '⚠️', title: 'Food Prices Rising',  text: 'Grocery costs increased 8% this month', time: '2 hours ago' },
  { icon: '💰', title: 'Budget Warning',       text: "You've reached 85% of your monthly budget", time: '5 hours ago' },
  { icon: '🚗', title: 'Transport Spike',      text: 'Fuel prices up 12% from last month', time: '1 day ago' },
];

const PAGE_TITLES = {
  dashboardPage: 'SPENDWISE', categoriesPage: 'CATEGORIES',
  addExpensePage: 'ADD EXPENSE', budgetPage: 'BUDGET', infoPage: 'SETTINGS',
};

// ─── Styles ──────────────────────────────────────────────────────────────────
const styles = `
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: #fef9f3; color: #2d3748; }
  .sw-app { max-width: 428px; margin: 0 auto; min-height: 100vh; background: #fef9f3; position: relative; padding-bottom: 70px; }
  .header { background: linear-gradient(135deg, #7c9cbf 0%, #8fa9c9 100%); color: #fff; padding: 20px; display: flex; justify-content: space-between; align-items: center; font-size: 18px; font-weight: 700; letter-spacing: 0.5px; box-shadow: 0 2px 8px rgba(124,156,191,0.25); }
  .header-title { flex: 1; text-align: center; }
  .notification-bell { width: 24px; height: 24px; cursor: pointer; position: relative; font-size: 20px; }
  .notification-bell.hidden { visibility: hidden; }
  .alert-badge { background: #d67c7c; color: #fff; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; position: absolute; top: -6px; right: -6px; }
  .notification-dropdown { position: fixed; top: 60px; right: 10px; width: 320px; max-height: 400px; background: #fff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); z-index: 1000; overflow-y: auto; animation: slideDown 0.3s ease; }
  @keyframes slideDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
  .notification-header { padding: 15px; border-bottom: 2px solid #e8ecf1; display: flex; justify-content: space-between; align-items: center; }
  .notification-header h3 { font-size: 16px; color: #2d3748; margin: 0; }
  .notification-close { background: none; border: none; font-size: 20px; cursor: pointer; color: #4a5568; }
  .notification-list { padding: 10px; }
  .notification-item { padding: 12px; background: #f9fafb; margin-bottom: 8px; border-radius: 8px; border-left: 4px solid #8b9dc3; display: flex; gap: 12px; }
  .notification-item:last-child { margin-bottom: 0; }
  .notification-icon { font-size: 24px; flex-shrink: 0; }
  .notification-content { flex: 1; }
  .notification-title { font-weight: 600; color: #2d3748; margin-bottom: 4px; font-size: 14px; }
  .notification-text { font-size: 13px; color: #4a5568; line-height: 1.4; margin-bottom: 4px; }
  .notification-time { font-size: 11px; color: #a0aec0; }
  .content { padding: 20px; overflow-y: auto; height: calc(100vh - 130px); }
  .welcome-screen { text-align: center; padding: 40px 20px; }
  .welcome-screen h1 { font-size: 28px; margin-bottom: 10px; }
  .welcome-screen p { color: #666; margin-bottom: 40px; line-height: 1.5; }
  .setup-options { display: flex; flex-direction: column; gap: 15px; }
  .btn { padding: 16px 24px; border: 2px solid #8b9dc3; background: #fff; color: #2d3748; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s; border-radius: 8px; }
  .btn-primary { background: linear-gradient(135deg, #8b9dc3 0%, #6b7fa8 100%); color: #fff; border: none; }
  .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(139,157,195,0.3); }
  .btn:active { transform: translateY(0); }
  .form-group { margin-bottom: 20px; text-align: left; }
  .form-group label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 14px; color: #2d3748; }
  .form-group input, .form-group select { width: 100%; padding: 12px; border: 2px solid #d4dce6; background: #fff; font-size: 16px; border-radius: 8px; transition: border-color 0.3s; color: #2d3748; }
  .form-group input:focus, .form-group select:focus { outline: none; border-color: #8b9dc3; box-shadow: 0 0 0 3px rgba(139,157,195,0.15); }
  .form-group small { color: #4a5568; font-size: 12px; }
  .checkbox-group { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 20px; }
  .checkbox-group input[type="checkbox"] { width: 20px; height: 20px; margin-top: 2px; cursor: pointer; flex-shrink: 0; }
  .checkbox-group label { flex: 1; font-size: 13px; color: #2d3748; line-height: 1.5; font-weight: normal; }
  .month-label { font-size: 20px; font-weight: 700; color: #2d3748; margin-bottom: 15px; text-align: center; }
  .stat-card { background: #fff; border: 2px solid #e8ecf1; padding: 20px; margin-bottom: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(139,157,195,0.1); }
  .stat-card h3 { font-size: 14px; color: #4a5568; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
  .stat-card .amount { font-size: 32px; font-weight: 700; color: #2d3748; }
  .stat-card .amount.positive { color: #6b9080; }
  .stat-card .amount.warning { color: #d67c7c; }
  .budget-container { background: linear-gradient(135deg, #f0f4f8 0%, #e8ecf1 100%); border: 2px solid #c5d1de; padding: 20px; margin-bottom: 20px; border-radius: 12px; }
  .budget-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #d4dce6; }
  .budget-item:last-child { border-bottom: none; }
  .budget-item label { font-size: 14px; color: #2d3748; font-weight: 600; }
  .budget-item .value { font-size: 18px; font-weight: 700; color: #2d3748; }
  .budget-item .value.positive { color: #6b9080; }
  .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
  .stat-grid .stat-card { margin-bottom: 0; }
  .stat-grid .stat-card .amount { font-size: 24px; }
  .chart-container { background: #fff; border: 2px solid #e8ecf1; padding: 20px; margin-bottom: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(139,157,195,0.1); }
  .chart-container h3 { margin-bottom: 15px; font-size: 16px; color: #2d3748; font-weight: 700; }
  .inflation-card { background: linear-gradient(135deg, #eef6f3 0%, #dceee7 100%); border: 2px solid #b8dcc8; padding: 15px; border-radius: 12px; margin-bottom: 20px; }
  .inflation-item { display: flex; justify-content: space-between; margin-bottom: 8px; }
  .inflation-item:last-child { margin-bottom: 0; }
  .inflation-item label { color: #2d3748; font-weight: 600; font-size: 14px; }
  .inflation-item .value { color: #6b9080; font-weight: 700; }
  .progress-card { background: linear-gradient(135deg, #f0f4f8 0%, #e8ecf1 100%); border: 2px solid #c5d1de; padding: 20px; margin-bottom: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(139,157,195,0.12); }
  .progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .progress-label { font-size: 14px; font-weight: 600; color: #2d3748; text-transform: uppercase; letter-spacing: 0.5px; }
  .progress-amount { font-size: 16px; font-weight: 700; color: #2d3748; }
  .progress-bar-container { width: 100%; height: 24px; background: #e8ecf1; border-radius: 12px; overflow: hidden; margin-bottom: 8px; }
  .progress-bar-fill { height: 100%; background: linear-gradient(90deg, #8b9dc3 0%, #6b7fa8 100%); transition: width 0.3s ease; }
  .progress-percentage { font-size: 13px; color: #4a5568; margin-bottom: 15px; }
  .savings-row { display: flex; justify-content: space-between; align-items: center; padding-top: 15px; border-top: 2px solid #d4dce6; }
  .savings-label { font-size: 15px; font-weight: 600; color: #2d3748; }
  .savings-amount { font-size: 20px; font-weight: 700; color: #6b9080; }
  .bottom-nav { position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: 100%; max-width: 428px; background: #fff; display: flex; justify-content: space-around; padding: 10px 0; border-top: 2px solid #e8ecf1; box-shadow: 0 -2px 10px rgba(139,157,195,0.12); z-index: 100; }
  .nav-item { display: flex; flex-direction: column; align-items: center; color: #a0aec0; text-decoration: none; font-size: 11px; padding: 5px 10px; transition: all 0.3s; cursor: pointer; font-weight: 600; }
  .nav-item.active { color: #8b9dc3; }
  .nav-icon { font-size: 24px; margin-bottom: 4px; }
  .category-list { list-style: none; }
  .category-item { background: #fff; margin-bottom: 15px; border-radius: 12px; border: 2px solid #e8ecf1; box-shadow: 0 2px 6px rgba(139,157,195,0.1); overflow: hidden; }
  .category-header { display: flex; justify-content: space-between; align-items: center; padding: 15px; cursor: pointer; transition: background 0.3s; }
  .category-header:hover { background: #f9fafb; }
  .category-name { font-weight: 600; color: #2d3748; }
  .category-amount { font-size: 18px; font-weight: 700; color: #8b9dc3; }
  .category-details { padding: 0 15px 15px; border-top: 1px solid #e8ecf1; }
  .expense-list-item { padding: 12px; background: #f9fafb; margin-top: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
  .item-name { font-weight: 500; color: #2d3748; }
  .item-date { font-size: 12px; color: #4a5568; }
  .item-amount { font-weight: 700; color: #2d3748; }
  .filter-buttons { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
  .filter-btn { padding: 8px 16px; background: #fff; border: 2px solid #e8ecf1; color: #4a5568; border-radius: 20px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
  .filter-btn.active { background: #8b9dc3; color: #fff; border-color: #8b9dc3; }
  .filter-btn:hover { border-color: #8b9dc3; }
  .suggestion-card { background: #fff; border: 2px solid #e8ecf1; padding: 20px; margin-bottom: 15px; border-radius: 12px; }
  .suggestion-card h4 { margin-bottom: 10px; font-size: 16px; color: #2d3748; }
  .suggestion-card p { color: #4a5568; line-height: 1.6; margin-bottom: 10px; }
  .savings-badge { display: inline-block; background: linear-gradient(135deg, #6b9080 0%, #5a7a6e 100%); color: #fff; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; }
  .toggle-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; font-size: 14px; color: #2d3748; }
  .toggle { position: relative; width: 50px; height: 26px; display: inline-block; }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #d4dce6; transition: .4s; border-radius: 26px; }
  .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 4px; bottom: 4px; background-color: #fff; transition: .4s; border-radius: 50%; }
  input:checked + .slider { background-color: #8b9dc3; }
  input:checked + .slider:before { transform: translateX(24px); }
  .section-title { font-size: 18px; font-weight: 700; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #c5d1de; color: #2d3748; }
  .expense-item { background: #fff; border: 2px solid #e8ecf1; border-radius: 12px; padding: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
  .expense-details { flex: 1; }
  .expense-category-name { font-weight: 600; color: #2d3748; margin-bottom: 4px; }
  .expense-date { font-size: 12px; color: #4a5568; }
  .expense-amount-display { font-size: 18px; font-weight: 700; color: #8b9dc3; }
  .budget-mode-section { background: #fff; border: 2px solid #e8ecf1; padding: 20px; margin-bottom: 20px; border-radius: 12px; }
  .goal-toggle { display: flex; gap: 10px; margin-bottom: 15px; }
  .goal-toggle button { flex: 1; padding: 10px; background: #fff; border: 2px solid #b8dcc8; color: #2d3748; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
  .goal-toggle button.active { background: #6b9080; color: #fff; border-color: #6b9080; }
  .category-budget-list { display: flex; flex-direction: column; gap: 12px; }
  .category-budget-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #f9fafb; border-radius: 8px; }
  .category-budget-item label { font-weight: 600; color: #2d3748; font-size: 14px; }
  .category-budget-input { width: 120px; padding: 8px 12px; border: 2px solid #d4dce6; border-radius: 6px; font-size: 14px; text-align: right; color: #2d3748; }
  .category-budget-input:focus { outline: none; border-color: #8b9dc3; }
  .previous-expense-table-container { overflow-x: auto; margin-bottom: 10px; }
  .previous-expense-table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; }
  .previous-expense-table th { background: #8b9dc3; color: #fff; padding: 10px 8px; font-size: 12px; font-weight: 600; text-align: left; }
  .previous-expense-table td { padding: 8px; border-bottom: 1px solid #e8ecf1; }
  .previous-expense-table tr:last-child td { border-bottom: none; }
  .table-input { width: 100%; padding: 6px 8px; border: 1px solid #d4dce6; border-radius: 4px; font-size: 13px; color: #2d3748; }
  .table-input:focus { outline: none; border-color: #8b9dc3; }
  .toast { position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); background: #2d3748; color: #fff; padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; z-index: 9999; white-space: nowrap; }
`;

// ─── Component ───────────────────────────────────────────────────────────────
const SpendWise = () => {
  // Auth & page state
  const [page, setPage]             = useState('welcomePage');
  const [authMode, setAuthMode]     = useState('login');    // 'login' | 'signup'
  const [setupStep, setSetupStep]   = useState(null);       // null | 'selection' | 'quick' | 'detailed'
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Auth forms
  const [loginContact,  setLoginContact]  = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [regContact,    setRegContact]    = useState('');
  const [regPassword,   setRegPassword]   = useState('');
  const [regConfirm,    setRegConfirm]    = useState('');
  const [dataConsent,   setDataConsent]   = useState(false);
  const [account,       setAccount]       = useState(null);

  // Setup forms
  const [quickIncome,      setQuickIncome]      = useState('');
  const [detailedContact,  setDetailedContact]  = useState('');
  const [detailedPassword, setDetailedPassword] = useState('');
  const [detailedIncome,   setDetailedIncome]   = useState('');
  const [householdSize,    setHouseholdSize]     = useState('');
  const [transportType,    setTransportType]     = useState('public');
  const [transportSpend,   setTransportSpend]    = useState('');
  const [utilityBill,      setUtilityBill]       = useState('');

  // App state
  const [activePage, setActivePage]       = useState('dashboardPage');
  const [showNotif,  setShowNotif]        = useState(false);
  const [notifCount, setNotifCount]       = useState(3);
  const [filterPeriod, setFilterPeriod]   = useState('all');
  const [openCategories, setOpenCategories] = useState({});
  const [budgetMode,   setBudgetMode]     = useState('auto');
  const [totalBudget,  setTotalBudget]    = useState('4200');
  const [categoryBudgets, setCategoryBudgets] = useState({ food: '', transport: '', utilities: '', entertainment: '', shopping: '', healthcare: '' });
  const [expenses,     setExpenses]       = useState([]);
  const [expForm,      setExpForm]        = useState({ category: '', item: '', amount: '', date: new Date().toISOString().split('T')[0], notes: '' });
  const [profileAlertPriceIncrease, setProfileAlertPriceIncrease] = useState(true);
  const [profileAlertBudget,        setProfileAlertBudget]        = useState(true);
  const [alertThreshold,            setAlertThreshold]            = useState('80');
  const [infoContact,    setInfoContact]   = useState('');
  const [infoIncome,     setInfoIncome]    = useState('');
  const [infoHousehold,  setInfoHousehold] = useState('');
  const [infoTransport,  setInfoTransport] = useState('public');
  const [infoTransportSpend, setInfoTransportSpend] = useState('');
  const [infoUtility,    setInfoUtility]   = useState('');
  const [prevExpenses, setPrevExpenses]   = useState([
    { month: '2025-12', food: '', transport: '', utilities: '', entertainment: '', shopping: '', healthcare: '' },
    { month: '2025-11', food: '', transport: '', utilities: '', entertainment: '', shopping: '', healthcare: '' },
    { month: '2025-10', food: '', transport: '', utilities: '', entertainment: '', shopping: '', healthcare: '' },
  ]);
  const [toast, setToast] = useState(null);

  // Charts
  const forecastRef  = useRef(null);
  const categoryRef  = useRef(null);
  const trendRef     = useRef(null);
  const chartsReady  = useRef(false);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  };

  // Load Chart.js once
  useEffect(() => {
    if (!document.getElementById('chartjs')) {
      const s = document.createElement('script');
      s.id  = 'chartjs';
      s.src = 'https://cdn.jsdelivr.net/npm/chart.js';
      document.head.appendChild(s);
    }
  }, []);

  // Init charts when dashboard is shown
  useEffect(() => {
    if (activePage !== 'dashboardPage' || !isLoggedIn) return;
    if (chartsReady.current) return;

    const init = () => {
      if (typeof Chart === 'undefined' || !forecastRef.current || !categoryRef.current || !trendRef.current) return;
      chartsReady.current = true;

      new Chart(forecastRef.current, {
        type: 'line',
        data: { labels: ['Feb','Mar','Apr','May','Jun','Jul'], datasets: [{ label: 'Projected Expenses', data: [3245,3420,3310,3580,3490,3720], borderColor: '#8b9dc3', backgroundColor: 'rgba(139,157,195,0.15)', borderWidth: 3, tension: 0, fill: true }] },
        options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: false, ticks: { callback: v => '$'+v, color: '#2d3748' }, grid: { color: '#e8ecf1' } }, x: { ticks: { color: '#2d3748' }, grid: { color: '#e8ecf1' } } } },
      });

      new Chart(categoryRef.current, {
        type: 'pie',
        data: { labels: ['Food','Transport','Utilities','Entertainment','Shopping','Healthcare'], datasets: [{ data: [1250,450,320,280,645,300], backgroundColor: ['#8b9dc3','#a8b8d8','#c5d1de','#6b9080','#b8dcc8','#d4a5a5'], borderWidth: 2, borderColor: '#fff' }] },
        options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { color: '#2d3748' } } } },
      });

      new Chart(trendRef.current, {
        type: 'line',
        data: { labels: ['Nov','Dec','Jan'], datasets: [
          { label: 'Actual Spending', data: [2980,3120,3245], borderColor: '#8b9dc3', backgroundColor: 'rgba(139,157,195,0.15)', borderWidth: 3, tension: 0, fill: true },
          { label: 'Budget',          data: [4200,4200,4200], borderColor: '#6b9080', backgroundColor: 'rgba(107,144,128,0.1)',  borderWidth: 3, borderDash: [5,5], tension: 0, fill: false },
        ]},
        options: { responsive: true, plugins: { legend: { display: true, position: 'bottom', labels: { color: '#2d3748' } } }, scales: { y: { beginAtZero: false, ticks: { callback: v => '$'+v, color: '#2d3748' }, grid: { color: '#e8ecf1' } }, x: { ticks: { color: '#2d3748' }, grid: { color: '#e8ecf1' } } } },
      });
    };

    setTimeout(init, 200);
  }, [activePage, isLoggedIn]);

  // ── Auth handlers ──
  const handleLogin = (e) => {
    e.preventDefault();
    if (!account) { showToast('No account found. Please create an account first.'); return; }
    if (account.contact === loginContact && account.password === loginPassword) {
      setIsLoggedIn(true);
      setActivePage('dashboardPage');
      setPage('app');
    } else {
      showToast('Invalid email/phone or password.');
    }
  };

  const handleRegister = (e) => {
    e.preventDefault();
    if (regPassword !== regConfirm) { showToast('Passwords do not match!'); return; }
    setAccount({ contact: regContact, password: regPassword });
    setPage('setup');
    setSetupStep('selection');
  };

  const handleQuickSetup = (e) => {
    e.preventDefault();
    setIsLoggedIn(true);
    setActivePage('dashboardPage');
    setPage('app');
  };

  const handleDetailedSetup = (e) => {
    e.preventDefault();
    setIsLoggedIn(true);
    setActivePage('dashboardPage');
    setPage('app');
  };

  const handleAddExpense = (e) => {
    e.preventDefault();
    setExpenses(prev => [{ id: Date.now(), ...expForm, amount: parseFloat(expForm.amount) }, ...prev]);
    setExpForm({ category: '', item: '', amount: '', date: new Date().toISOString().split('T')[0], notes: '' });
    showToast('Expense added successfully!');
  };

  const toggleCategory = (key) => setOpenCategories(p => ({ ...p, [key]: !p[key] }));

  const addPrevRow = () => setPrevExpenses(p => [...p, { month: '', food: '', transport: '', utilities: '', entertainment: '', shopping: '', healthcare: '' }]);

  const updatePrevRow = (i, field, val) => setPrevExpenses(p => p.map((r, idx) => idx === i ? { ...r, [field]: val } : r));

  // ── Render helpers ──
  const navItems = [
    { id: 'dashboardPage', icon: '📊', label: 'Dashboard' },
    { id: 'categoriesPage', icon: '📁', label: 'Categories' },
    { id: 'addExpensePage', icon: '➕', label: 'Add' },
    { id: 'budgetPage', icon: '💡', label: 'Budget' },
    { id: 'infoPage', icon: '⚙️', label: 'Info' },
  ];

  // ── Render ──
  return (
    <div className="sw-app">
      <style>{styles}</style>

      {/* Toast */}
      {toast && <div className="toast">{toast}</div>}

      {/* ── PRE-LOGIN SCREENS ── */}
      {page === 'welcomePage' && (
        <div>
          <div className="header">
            <div style={{ width: 24 }} />
            <div className="header-title">SPENDWISE</div>
            <div style={{ width: 24 }} />
          </div>
          <div className="content">
            <div className="welcome-screen">
              <h1>{authMode === 'login' ? 'Welcome Back!' : 'Create Account'}</h1>
              <p>{authMode === 'login' ? 'Sign in to continue managing your expenses.' : 'Start your journey to better financial management.'}</p>
            </div>

            {authMode === 'login' && (
              <form onSubmit={handleLogin}>
                <div className="form-group">
                  <label>Email / Phone Number</label>
                  <input type="text" placeholder="your@email.com or +65 1234 5678" value={loginContact} onChange={e => setLoginContact(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Password</label>
                  <input type="password" placeholder="••••••••" value={loginPassword} onChange={e => setLoginPassword(e.target.value)} required />
                </div>
                <div style={{ textAlign: 'right', marginBottom: 15 }}>
                  <a href="#" style={{ color: '#8b9dc3', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>Forgot Password?</a>
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Sign In</button>
                <p style={{ textAlign: 'center', marginTop: 15, color: '#4a5568', fontSize: 14 }}>
                  Don't have an account?{' '}
                  <a href="#" style={{ color: '#8b9dc3', fontWeight: 600, textDecoration: 'none' }} onClick={e => { e.preventDefault(); setAuthMode('signup'); }}>Create Account</a>
                </p>
              </form>
            )}

            {authMode === 'signup' && (
              <form onSubmit={handleRegister}>
                <div className="form-group">
                  <label>Email / Phone Number</label>
                  <input type="text" placeholder="your@email.com or +65 1234 5678" value={regContact} onChange={e => setRegContact(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Password</label>
                  <input type="password" placeholder="••••••••" value={regPassword} onChange={e => setRegPassword(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Confirm Password</label>
                  <input type="password" placeholder="••••••••" value={regConfirm} onChange={e => setRegConfirm(e.target.value)} required />
                </div>
                <div className="checkbox-group">
                  <input type="checkbox" id="dataConsent" checked={dataConsent} onChange={e => setDataConsent(e.target.checked)} required />
                  <label htmlFor="dataConsent">I allow my anonymized data to be used for further app development and to inform government policy decisions regarding financial planning and inflation management.</label>
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Create Account</button>
                <p style={{ textAlign: 'center', marginTop: 15, color: '#4a5568', fontSize: 14 }}>
                  Already have an account?{' '}
                  <a href="#" style={{ color: '#8b9dc3', fontWeight: 600, textDecoration: 'none' }} onClick={e => { e.preventDefault(); setAuthMode('login'); }}>Sign In</a>
                </p>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ── SETUP SCREENS ── */}
      {page === 'setup' && (
        <div>
          <div className="header"><div style={{ width: 24 }} /><div className="header-title">SPENDWISE</div><div style={{ width: 24 }} /></div>
          <div className="content">
            {setupStep === 'selection' && (
              <div className="welcome-screen">
                <h1>Welcome!</h1>
                <p>Let's get started tracking your expenses and helping you save money.</p>
                <div className="setup-options">
                  <button className="btn btn-primary" onClick={() => setSetupStep('quick')}>Quick Setup (Just Income)</button>
                  <button className="btn" onClick={() => setSetupStep('detailed')}>Detailed Setup</button>
                  <button className="btn" onClick={() => { setIsLoggedIn(true); setActivePage('dashboardPage'); setPage('app'); }}>Fill in Later</button>
                </div>
              </div>
            )}

            {setupStep === 'quick' && (
              <div>
                <h2 className="section-title">Quick Setup</h2>
                <form onSubmit={handleQuickSetup}>
                  <div className="form-group"><label>Monthly Income</label><input type="number" placeholder="$5000" value={quickIncome} onChange={e => setQuickIncome(e.target.value)} required /></div>
                  <div className="form-group"><label>Email (Optional)</label><input type="email" placeholder="your@email.com" /></div>
                  <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Continue</button>
                  <button type="button" className="btn" style={{ width: '100%', marginTop: 10 }} onClick={() => setSetupStep('selection')}>Back</button>
                </form>
              </div>
            )}

            {setupStep === 'detailed' && (
              <div>
                <h2 className="section-title">Detailed Setup</h2>
                <form onSubmit={handleDetailedSetup}>
                  <div className="form-group"><label>Email / Phone</label><input type="text" placeholder="your@email.com" value={detailedContact} onChange={e => setDetailedContact(e.target.value)} required /></div>
                  <div className="form-group"><label>Password</label><input type="password" placeholder="••••••••" value={detailedPassword} onChange={e => setDetailedPassword(e.target.value)} required /></div>
                  <div className="form-group"><label>Monthly Income</label><input type="number" placeholder="$5000" value={detailedIncome} onChange={e => setDetailedIncome(e.target.value)} required /></div>
                  <div className="form-group"><label>Household Size</label><input type="number" placeholder="4" value={householdSize} onChange={e => setHouseholdSize(e.target.value)} required /></div>
                  <div className="form-group">
                    <label>Transportation Type</label>
                    <select value={transportType} onChange={e => setTransportType(e.target.value)}>
                      <option value="public">Public Transport</option>
                      <option value="bike">Bike</option>
                      <option value="electric">Electric/Hybrid Car</option>
                      <option value="normal">Normal Car</option>
                    </select>
                  </div>
                  <div className="form-group"><label>Monthly Transport Spending</label><input type="number" placeholder="$300" value={transportSpend} onChange={e => setTransportSpend(e.target.value)} /></div>
                  <div className="form-group"><label>Monthly Utility Bill</label><input type="number" placeholder="$150" value={utilityBill} onChange={e => setUtilityBill(e.target.value)} /></div>
                  <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Complete Setup</button>
                  <button type="button" className="btn" style={{ width: '100%', marginTop: 10 }} onClick={() => setSetupStep('selection')}>Back</button>
                </form>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── MAIN APP ── */}
      {page === 'app' && (
        <div>
          {/* Header */}
          <div className="header">
            <div style={{ width: 24 }} />
            <div className="header-title">{PAGE_TITLES[activePage] || 'SPENDWISE'}</div>
            <div className="notification-bell" onClick={() => setShowNotif(v => !v)}>
              🔔
              {notifCount > 0 && <div className="alert-badge">{notifCount}</div>}
            </div>
          </div>

          {/* Notification Dropdown */}
          {showNotif && (
            <div className="notification-dropdown">
              <div className="notification-header">
                <h3>🔔 Notifications</h3>
                <button className="notification-close" onClick={() => { setShowNotif(false); setNotifCount(0); }}>×</button>
              </div>
              <div className="notification-list">
                {NOTIFICATIONS.map((n, i) => (
                  <div key={i} className="notification-item">
                    <div className="notification-icon">{n.icon}</div>
                    <div className="notification-content">
                      <div className="notification-title">{n.title}</div>
                      <div className="notification-text">{n.text}</div>
                      <div className="notification-time">{n.time}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pages */}
          <div className="content">

            {/* Dashboard */}
            {activePage === 'dashboardPage' && (
              <div>
                <div className="month-label">February 2026</div>
                <div className="progress-card">
                  <div className="progress-header">
                    <span className="progress-label">Budget Progress</span>
                    <span className="progress-amount">$3,245 / $4,200</span>
                  </div>
                  <div className="progress-bar-container"><div className="progress-bar-fill" style={{ width: '77.3%' }} /></div>
                  <div className="progress-percentage">77% used</div>
                  <div className="savings-row">
                    <span className="savings-label">💰 Savings This Month</span>
                    <span className="savings-amount">$1,755</span>
                  </div>
                </div>
                <div className="inflation-card">
                  <h3 style={{ color: '#2d3748', marginBottom: 12, fontSize: 16 }}>📈 Inflation Rates</h3>
                  <div className="inflation-item"><label>Personal Inflation Rate</label><div className="value">4.2%</div></div>
                  <div className="inflation-item"><label>National Inflation Rate</label><div className="value">3.1%</div></div>
                </div>
                <div className="chart-container"><h3>6-Month Forecast</h3><canvas ref={forecastRef} /></div>
                <div className="chart-container"><h3>Spending Breakdown</h3><canvas ref={categoryRef} /></div>
                <div className="chart-container"><h3>Monthly Trend: Spending vs Budget</h3><canvas ref={trendRef} /></div>
              </div>
            )}

            {/* Categories */}
            {activePage === 'categoriesPage' && (
              <div>
                <h2 className="section-title">Category Breakdown</h2>
                <div className="filter-buttons">
                  {[['all','All Time'],['year','Past Year'],['6months','6 Months'],['month','This Month']].map(([val, label]) => (
                    <button key={val} className={`filter-btn${filterPeriod === val ? ' active' : ''}`} onClick={() => setFilterPeriod(val)}>{label}</button>
                  ))}
                </div>
                <ul className="category-list">
                  {INITIAL_CATEGORIES.map(cat => (
                    <li key={cat.key} className="category-item">
                      <div className="category-header" onClick={() => toggleCategory(cat.key)}>
                        <span className="category-name">{cat.label}</span>
                        <span className="category-amount">${cat.total.toLocaleString()}</span>
                      </div>
                      {openCategories[cat.key] && (
                        <div className="category-details">
                          {cat.items.map((item, i) => (
                            <div key={i} className="expense-list-item">
                              <div><div className="item-name">{item.name}</div><div className="item-date">{item.date}</div></div>
                              <div className="item-amount">${item.amount.toFixed(2)}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Add Expense */}
            {activePage === 'addExpensePage' && (
              <div>
                <h2 className="section-title">Add Expense</h2>
                <form onSubmit={handleAddExpense}>
                  <div className="form-group">
                    <label>Category</label>
                    <select value={expForm.category} onChange={e => setExpForm(f => ({ ...f, category: e.target.value }))} required>
                      <option value="">Select Category</option>
                      <option value="food">🍔 Food & Dining</option>
                      <option value="transport">🚗 Transport</option>
                      <option value="utilities">💡 Utilities</option>
                      <option value="entertainment">🎬 Entertainment</option>
                      <option value="shopping">🛍️ Shopping</option>
                      <option value="healthcare">🏥 Healthcare</option>
                    </select>
                  </div>
                  <div className="form-group"><label>Item/Description</label><input type="text" placeholder="e.g., Groceries, Gas, Movie tickets" value={expForm.item} onChange={e => setExpForm(f => ({ ...f, item: e.target.value }))} required /></div>
                  <div className="form-group"><label>Amount ($)</label><input type="number" step="0.01" placeholder="0.00" value={expForm.amount} onChange={e => setExpForm(f => ({ ...f, amount: e.target.value }))} required /></div>
                  <div className="form-group"><label>Date</label><input type="date" value={expForm.date} onChange={e => setExpForm(f => ({ ...f, date: e.target.value }))} required /></div>
                  <div className="form-group"><label>Notes (Optional)</label><input type="text" placeholder="Additional details" value={expForm.notes} onChange={e => setExpForm(f => ({ ...f, notes: e.target.value }))} /></div>
                  <button type="submit" className="btn btn-primary" style={{ width: '100%', marginBottom: 10 }}>Add Expense</button>
                  <button type="button" className="btn" style={{ width: '100%' }} onClick={() => setActivePage('dashboardPage')}>Cancel</button>
                </form>
                <h3 className="section-title" style={{ marginTop: 30 }}>Recent Expenses</h3>
                {expenses.length === 0
                  ? <p style={{ color: '#718096', textAlign: 'center', padding: 20 }}>No expenses yet. Add your first expense above!</p>
                  : expenses.slice(0, 5).map(exp => (
                    <div key={exp.id} className="expense-item">
                      <div className="expense-details">
                        <div className="expense-category-name">{CATEGORY_EMOJIS[exp.category]} {exp.item}</div>
                        <div className="expense-date">{new Date(exp.date).toLocaleDateString()}{exp.notes ? ' • ' + exp.notes : ''}</div>
                      </div>
                      <div className="expense-amount-display">${exp.amount.toFixed(2)}</div>
                    </div>
                  ))
                }
              </div>
            )}

            {/* Budget */}
            {activePage === 'budgetPage' && (
              <div>
                <h2 className="section-title">Budget Settings</h2>
                <div className="budget-mode-section">
                  <h3 style={{ color: '#2d3748', marginBottom: 15, fontSize: 16 }}>Budget Mode</h3>
                  <div className="goal-toggle">
                    <button className={budgetMode === 'auto' ? 'active' : ''} onClick={() => setBudgetMode('auto')}>Auto Budget</button>
                    <button className={budgetMode === 'manual' ? 'active' : ''} onClick={() => setBudgetMode('manual')}>Set Budget</button>
                  </div>
                  <p style={{ color: '#4a5568', fontSize: 13, marginTop: 10 }}>Auto budget is calculated based on your past 3 months of spending.</p>
                </div>

                {budgetMode === 'manual' && (
                  <div>
                    <h3 className="section-title" style={{ marginTop: 30 }}>Set Monthly Budget</h3>
                    <div className="form-group"><label>Total Monthly Budget ($)</label><input type="number" placeholder="4200" value={totalBudget} onChange={e => setTotalBudget(e.target.value)} /></div>
                    <h4 style={{ color: '#2d3748', margin: '25px 0 15px', fontSize: 15 }}>Category Budgets (Optional)</h4>
                    <p style={{ color: '#4a5568', fontSize: 13, marginBottom: 15 }}>Set specific budgets for each category, or leave blank to distribute automatically.</p>
                    <div className="category-budget-list">
                      {Object.entries(CATEGORY_EMOJIS).map(([key, emoji]) => (
                        <div key={key} className="category-budget-item">
                          <label>{emoji} {CATEGORY_NAMES[key]}</label>
                          <input type="number" placeholder="Auto" className="category-budget-input" value={categoryBudgets[key]} onChange={e => setCategoryBudgets(p => ({ ...p, [key]: e.target.value }))} />
                        </div>
                      ))}
                    </div>
                    <button className="btn btn-primary" style={{ width: '100%', marginTop: 20 }} onClick={() => showToast('Budget settings saved successfully!')}>Save Budget</button>
                  </div>
                )}

                <h2 className="section-title" style={{ marginTop: 40 }}>Budget Suggestions</h2>
                {[
                  { title: 'Reduce Dining Out', text: "You've spent $1,250 on food this month. Consider meal prepping on Sundays to reduce dining expenses by 30%.", badge: 'Save $375/month' },
                  { title: 'Switch to Public Transport', text: 'Based on your commute patterns, switching to public transport 3 days a week could reduce your transport costs significantly.', badge: 'Save $150/month' },
                  { title: 'Entertainment Subscription Audit', text: 'You have 5 active subscriptions. Cancel 2 unused services to optimize your entertainment budget.', badge: 'Save $45/month' },
                  { title: 'Energy Efficiency', text: 'Your utility bills are 20% higher than similar households. Consider upgrading to LED bulbs and adjusting thermostat settings.', badge: 'Save $65/month' },
                ].map((s, i) => (
                  <div key={i} className="suggestion-card">
                    <h4>{s.title}</h4>
                    <p>{s.text}</p>
                    <span className="savings-badge">{s.badge}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Info / Settings */}
            {activePage === 'infoPage' && (
              <div>
                <h2 className="section-title">Account Information</h2>
                <div className="form-group"><label>Email / Phone</label><input type="text" placeholder="your@email.com" value={infoContact} onChange={e => setInfoContact(e.target.value)} /></div>
                <div className="form-group"><label>Monthly Income</label><input type="number" placeholder="$5000" value={infoIncome} onChange={e => setInfoIncome(e.target.value)} /></div>
                <div className="form-group"><label>Household Size</label><input type="number" placeholder="4" value={infoHousehold} onChange={e => setInfoHousehold(e.target.value)} /></div>
                <div className="form-group">
                  <label>Transportation Type</label>
                  <select value={infoTransport} onChange={e => setInfoTransport(e.target.value)}>
                    <option value="public">Public Transport</option>
                    <option value="bike">Bike</option>
                    <option value="electric">Electric/Hybrid Car</option>
                    <option value="normal">Normal Car</option>
                  </select>
                </div>
                <div className="form-group"><label>Monthly Transport Spending</label><input type="number" placeholder="$300" value={infoTransportSpend} onChange={e => setInfoTransportSpend(e.target.value)} /></div>
                <div className="form-group"><label>Monthly Utility Bill</label><input type="number" placeholder="$150" value={infoUtility} onChange={e => setInfoUtility(e.target.value)} /></div>

                <h3 className="section-title" style={{ marginTop: 30 }}>Alert Settings</h3>
                <div className="toggle-container">
                  <span>Price Increase Alerts</span>
                  <label className="toggle"><input type="checkbox" checked={profileAlertPriceIncrease} onChange={e => setProfileAlertPriceIncrease(e.target.checked)} /><span className="slider" /></label>
                </div>
                <div className="toggle-container">
                  <span>Budget Threshold Alerts</span>
                  <label className="toggle"><input type="checkbox" checked={profileAlertBudget} onChange={e => setProfileAlertBudget(e.target.checked)} /><span className="slider" /></label>
                </div>
                <div className="form-group"><label>Alert Threshold (%)</label><input type="number" placeholder="80" value={alertThreshold} onChange={e => setAlertThreshold(e.target.value)} /></div>
                <button className="btn btn-primary" style={{ width: '100%', marginTop: 20 }} onClick={() => showToast('Settings saved successfully!')}>Save Changes</button>

                <h3 className="section-title" style={{ marginTop: 40 }}>📊 Import Previous Expenses</h3>
                <p style={{ color: '#4a5568', marginBottom: 15, fontSize: 14 }}>Add your expenses from before using SpendWise to get better forecasting.</p>
                <div className="previous-expense-table-container">
                  <table className="previous-expense-table">
                    <thead>
                      <tr><th>Month</th><th>Food</th><th>Transport</th><th>Utilities</th><th>Entertainment</th><th>Shopping</th><th>Healthcare</th></tr>
                    </thead>
                    <tbody>
                      {prevExpenses.map((row, i) => (
                        <tr key={i}>
                          <td><input type="month" className="table-input" value={row.month} onChange={e => updatePrevRow(i, 'month', e.target.value)} /></td>
                          {['food','transport','utilities','entertainment','shopping','healthcare'].map(f => (
                            <td key={f}><input type="number" className="table-input" placeholder="0" value={row[f]} onChange={e => updatePrevRow(i, f, e.target.value)} /></td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ display: 'flex', gap: 10, marginTop: 15 }}>
                  <button className="btn" style={{ flex: 1 }} onClick={addPrevRow}>+ Add Month</button>
                  <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => showToast('Previous expenses saved successfully!')}>Save Previous Expenses</button>
                </div>
              </div>
            )}

          </div>

          {/* Bottom Nav */}
          <div className="bottom-nav">
            {navItems.map(item => (
              <div key={item.id} className={`nav-item${activePage === item.id ? ' active' : ''}`} onClick={() => setActivePage(item.id)}>
                <div className="nav-icon">{item.icon}</div>
                <div>{item.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SpendWise;
