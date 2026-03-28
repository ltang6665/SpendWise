import React, { useState, useEffect, useRef } from 'react';

const SpendWiseAdmin = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [activeSection, setActiveSection] = useState('overview');
  const [users, setUsers] = useState([
    { id: 'U2410544A', name: 'Yeo Sze Yun, Gwyneth', email: 'gwyneth.yeo@example.com', status: 'active', joined: 'Jan 15, 2026', lastActive: '2 hours ago' },
    { id: 'U2410284B', name: 'Murukesan Neha', email: 'neha.murukesan@example.com', status: 'suspended', joined: 'Jan 20, 2026', lastActive: '5 hours ago' },
    { id: 'U2423611L', name: 'Lakshita Sweta D/O Kathiresan', email: 'lakshita.sweta@example.com', status: 'active', joined: 'Feb 01, 2026', lastActive: '1 day ago' },
    { id: 'U2423950C', name: 'Tang Wei Heng Luther', email: 'luther.tang@example.com', status: 'active', joined: 'Jan 28, 2026', lastActive: '3 days ago' },
    { id: 'U2521378A', name: 'Soh Jing Shan Sabrina', email: 'sabrina.soh@example.com', status: 'active', joined: 'Feb 05, 2026', lastActive: '30 minutes ago' },
  ]);
  const [userFilter, setUserFilter] = useState('all');
  const [userSearch, setUserSearch] = useState('');
  const [announcements, setAnnouncements] = useState([
    { date: 'Feb 18, 2026', title: 'New Feature: Budget Recommendations', priority: 'medium', views: 8234 },
  ]);
  const [announcementForm, setAnnouncementForm] = useState({ title: '', content: '', priority: 'low' });
  const [exportStartDate, setExportStartDate] = useState('');
  const [exportEndDate, setExportEndDate] = useState('');
  const [anonymizeData, setAnonymizeData] = useState(true);
  const [syncSchedule, setSyncSchedule] = useState('monthly');
  const [autoBackup, setAutoBackup] = useState(true);
  const [backupSchedule, setBackupSchedule] = useState('daily');
  const [retentionDays, setRetentionDays] = useState(30);
  const [encryptBackups, setEncryptBackups] = useState(true);
  const [toast, setToast] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [deleteInput, setDeleteInput] = useState('');
  const userGrowthRef = useRef(null);
  const activityRef = useRef(null);
  const chartsInitialized = useRef(false);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleLogin = (e) => {
    e.preventDefault();
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to logout?')) {
      setIsLoggedIn(false);
      chartsInitialized.current = false;
    }
  };

  // Charts
  useEffect(() => {
    if (!isLoggedIn || activeSection !== 'overview') return;
    if (chartsInitialized.current) return;

    const script = document.getElementById('chartjs-script');
    const initCharts = () => {
      if (!userGrowthRef.current || !activityRef.current) return;
      if (typeof Chart === 'undefined') return;

      chartsInitialized.current = true;

      new Chart(userGrowthRef.current, {
        type: 'line',
        data: {
          labels: ['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb'],
          datasets: [{
            label: 'Total Users',
            data: [8500, 9200, 10100, 10800, 11600, 12458],
            borderColor: '#8b9dc3',
            backgroundColor: 'rgba(139, 157, 195, 0.1)',
            borderWidth: 3,
            tension: 0,
            fill: true,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: false, ticks: { color: '#2d3748' } },
            x: { ticks: { color: '#2d3748' } },
          },
        },
      });

      new Chart(activityRef.current, {
        type: 'bar',
        data: {
          labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
          datasets: [{
            label: 'API Requests',
            data: [42000, 45000, 48000, 46000, 50000, 38000, 35000],
            backgroundColor: 'rgba(139, 157, 195, 0.7)',
            borderColor: '#8b9dc3',
            borderWidth: 1,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, ticks: { color: '#2d3748' } },
            x: { ticks: { color: '#2d3748' } },
          },
        },
      });
    };

    if (!script) {
      const s = document.createElement('script');
      s.id = 'chartjs-script';
      s.src = 'https://cdn.jsdelivr.net/npm/chart.js';
      s.onload = initCharts;
      document.head.appendChild(s);
    } else {
      setTimeout(initCharts, 100);
    }
  }, [isLoggedIn, activeSection]);

  const suspendUser = (id) => {
    setUsers(prev => prev.map(u => u.id === id ? { ...u, status: 'suspended' } : u));
    showToast(`User suspended successfully.`);
  };

  const activateUser = (id) => {
    setUsers(prev => prev.map(u => u.id === id ? { ...u, status: 'active' } : u));
    showToast(`User activated successfully.`);
  };

  const confirmDelete = (user) => {
    setDeleteConfirm(user);
    setDeleteInput('');
  };

  const executeDelete = () => {
    if (deleteInput === deleteConfirm.name) {
      setUsers(prev => prev.filter(u => u.id !== deleteConfirm.id));
      showToast(`User ${deleteConfirm.name} permanently deleted.`);
      setDeleteConfirm(null);
    } else {
      showToast('Confirmation text did not match.', 'error');
    }
  };

  const exportData = (type) => {
    showToast(`Exporting ${type} data... Download will start shortly.`);
  };

  const runDataValidation = () => {
    showToast('Validation complete! No critical issues found.');
  };

  const triggerSync = (source) => {
    showToast(`Sync triggered for ${source}. 1,245 records updated.`);
  };

  const createBackup = () => {
    if (window.confirm('Create a new backup? This may take several minutes.')) {
      showToast('Backup created successfully!');
    }
  };

  const restoreBackup = (id) => {
    if (window.confirm(`Restore system to backup ${id}? Current data will be replaced.`)) {
      showToast('System restored successfully!');
    }
  };

  const handleCreateAnnouncement = (e) => {
    e.preventDefault();
    const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    setAnnouncements(prev => [{ date: today, title: announcementForm.title, priority: announcementForm.priority, views: 0 }, ...prev]);
    setAnnouncementForm({ title: '', content: '', priority: 'low' });
    showToast(`Announcement "${announcementForm.title}" published successfully!`);
  };

  const deleteAnnouncement = (idx) => {
    setAnnouncements(prev => prev.filter((_, i) => i !== idx));
    showToast('Announcement deleted.');
  };

  const filteredUsers = users.filter(u => {
    const matchesFilter = userFilter === 'all' || u.status === userFilter;
    const matchesSearch = !userSearch || u.name.toLowerCase().includes(userSearch.toLowerCase()) || u.email.toLowerCase().includes(userSearch.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const styles = `
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: #f5f7fa; color: #2d3748; }
    .admin-header { background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: #ffffff; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .admin-header h1 { font-size: 24px; font-weight: 700; }
    .admin-header .admin-info { display: flex; align-items: center; gap: 15px; }
    .admin-avatar { width: 40px; height: 40px; background: #8b9dc3; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 18px; }
    .logout-btn { background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: #fff; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.3s; }
    .logout-btn:hover { background: rgba(255,255,255,0.3); }
    .admin-container { display: flex; min-height: calc(100vh - 80px); }
    .admin-sidebar { width: 260px; background: #2d3748; color: #fff; padding: 30px 0; flex-shrink: 0; }
    .sidebar-menu { list-style: none; }
    .sidebar-menu li { padding: 15px 30px; cursor: pointer; transition: all 0.3s; display: flex; align-items: center; gap: 12px; font-size: 15px; border-left: 4px solid transparent; }
    .sidebar-menu li:hover { background: rgba(255,255,255,0.1); }
    .sidebar-menu li.active { background: rgba(139,157,195,0.2); border-left-color: #8b9dc3; }
    .sidebar-icon { font-size: 20px; }
    .admin-main { flex: 1; padding: 40px; overflow-y: auto; }
    .page-title { font-size: 28px; font-weight: 700; margin-bottom: 10px; color: #2d3748; }
    .page-subtitle { color: #718096; margin-bottom: 30px; font-size: 14px; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
    .stat-card { background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid #8b9dc3; }
    .stat-card h3 { font-size: 14px; color: #718096; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
    .stat-card .stat-value { font-size: 32px; font-weight: 700; color: #2d3748; }
    .stat-card .stat-change { font-size: 13px; margin-top: 8px; color: #6b9080; }
    .chart-container { background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; }
    .chart-container h3 { margin-bottom: 20px; font-size: 16px; font-weight: 700; color: #2d3748; }
    .content-card { background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; overflow-x: auto; }
    .content-card h3 { font-size: 18px; font-weight: 700; margin-bottom: 20px; color: #2d3748; }
    .data-table { width: 100%; border-collapse: collapse; }
    .data-table thead { background: #f7fafc; }
    .data-table th { padding: 12px 15px; text-align: left; font-size: 13px; font-weight: 600; color: #4a5568; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #e2e8f0; }
    .data-table td { padding: 15px; border-bottom: 1px solid #e2e8f0; font-size: 14px; color: #2d3748; }
    .data-table tr:hover { background: #f7fafc; }
    .status-badge { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; display: inline-block; }
    .status-active { background: #d1fae5; color: #064e3b; }
    .status-suspended { background: #fee2e2; color: #991b1b; }
    .status-inactive { background: #e5e7eb; color: #374151; }
    .status-success { background: #d1fae5; color: #064e3b; }
    .status-failed { background: #fee2e2; color: #991b1b; }
    .status-pending { background: #fef3c7; color: #92400e; }
    .btn { padding: 10px 20px; border: none; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
    .btn-primary { background: #8b9dc3; color: #fff; }
    .btn-primary:hover { background: #6b7fa8; }
    .btn-success { background: #6b9080; color: #fff; }
    .btn-success:hover { background: #5a7a6e; }
    .btn-danger { background: #d67c7c; color: #fff; }
    .btn-danger:hover { background: #c66666; }
    .btn-warning { background: #f0ad4e; color: #fff; }
    .btn-warning:hover { background: #ec971f; }
    .btn-secondary { background: #e2e8f0; color: #4a5568; }
    .btn-secondary:hover { background: #cbd5e0; }
    .btn-small { padding: 6px 12px; font-size: 12px; }
    .action-buttons { display: flex; gap: 8px; }
    .form-group { margin-bottom: 20px; }
    .form-group label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 14px; color: #2d3748; }
    .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 12px; border: 2px solid #e2e8f0; border-radius: 6px; font-size: 14px; color: #2d3748; transition: border-color 0.3s; }
    .form-group input:focus, .form-group select:focus, .form-group textarea:focus { outline: none; border-color: #8b9dc3; }
    .form-group textarea { resize: vertical; min-height: 100px; }
    .filter-bar { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
    .filter-bar select, .filter-bar input { padding: 8px 12px; border: 2px solid #e2e8f0; border-radius: 6px; font-size: 14px; color: #2d3748; }
    .export-options { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
    .export-card { padding: 20px; border: 2px solid #e2e8f0; border-radius: 8px; text-align: center; cursor: pointer; transition: all 0.3s; }
    .export-card:hover { border-color: #8b9dc3; background: #f7fafc; }
    .export-card-icon { font-size: 32px; margin-bottom: 10px; }
    .export-card-title { font-weight: 600; color: #2d3748; margin-bottom: 5px; }
    .export-card-desc { font-size: 12px; color: #718096; }
    .sync-status { display: flex; align-items: center; gap: 10px; padding: 15px; background: #f7fafc; border-radius: 8px; margin-bottom: 20px; }
    .sync-indicator { width: 12px; height: 12px; border-radius: 50%; animation: pulse 2s infinite; }
    .sync-indicator.success { background: #10b981; }
    .sync-indicator.pending { background: #f59e0b; }
    .sync-indicator.failed { background: #ef4444; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    .admin-login { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); }
    .login-card { background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); max-width: 400px; width: 90%; }
    .login-card h1 { text-align: center; margin-bottom: 10px; font-size: 28px; color: #2d3748; }
    .login-card p { text-align: center; color: #718096; margin-bottom: 30px; font-size: 14px; }
    .toast { position: fixed; bottom: 30px; right: 30px; padding: 14px 22px; border-radius: 8px; font-size: 14px; font-weight: 600; z-index: 9999; box-shadow: 0 4px 16px rgba(0,0,0,0.15); }
    .toast-success { background: #d1fae5; color: #064e3b; border-left: 4px solid #10b981; }
    .toast-error { background: #fee2e2; color: #991b1b; border-left: 4px solid #ef4444; }
    .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; }
    .modal-content { background: #fff; padding: 30px; border-radius: 12px; max-width: 480px; width: 90%; }
    .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .modal-header h2 { font-size: 20px; font-weight: 700; color: #2d3748; }
    .modal-close { background: none; border: none; font-size: 24px; cursor: pointer; color: #718096; }
    @media (max-width: 768px) {
      .admin-container { flex-direction: column; }
      .admin-sidebar { width: 100%; }
      .stats-grid { grid-template-columns: 1fr; }
      .admin-main { padding: 20px; }
      .filter-bar { flex-direction: column; }
      .action-buttons { flex-direction: column; }
    }
  `;

  if (!isLoggedIn) {
    return (
      <div className="admin-login">
        <style>{styles}</style>
        <div className="login-card">
          <h1>Admin Login</h1>
          <p>SpendWise Administration Panel</p>
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label>Admin Email</label>
              <input type="email" placeholder="admin@spendwise.com" required />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input type="password" placeholder="••••••••" required />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: 10 }}>Sign In</button>
          </form>
        </div>
      </div>
    );
  }

  const navItems = [
    { key: 'overview', icon: '📊', label: 'Overview' },
    { key: 'users', icon: '👥', label: 'Manage Users' },
    { key: 'export', icon: '📥', label: 'Export Data' },
    { key: 'monitor', icon: '📈', label: 'System Monitoring' },
    { key: 'quality', icon: '✅', label: 'Data Quality' },
    { key: 'announcements', icon: '📢', label: 'Announcements' },
    { key: 'sync', icon: '🔄', label: 'Data Sync' },
    { key: 'backup', icon: '💾', label: 'Backup & Recovery' },
  ];

  return (
    <div>
      <style>{styles}</style>

      {/* Toast */}
      {toast && (
        <div className={`toast toast-${toast.type}`}>{toast.msg}</div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>⚠️ Delete User</h2>
              <button className="modal-close" onClick={() => setDeleteConfirm(null)}>×</button>
            </div>
            <p style={{ marginBottom: 16, color: '#718096', fontSize: 14 }}>
              Permanently delete <strong>{deleteConfirm.name}</strong> ({deleteConfirm.id})?
              This will delete all user data, expense records, budgets, and forecasts.
            </p>
            <div className="form-group">
              <label>Type "{deleteConfirm.name}" to confirm:</label>
              <input
                type="text"
                value={deleteInput}
                onChange={e => setDeleteInput(e.target.value)}
                placeholder={deleteConfirm.name}
              />
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-danger" onClick={executeDelete}>Delete Permanently</button>
              <button className="btn btn-secondary" onClick={() => setDeleteConfirm(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="admin-header">
        <h1>🎛️ SpendWise Admin</h1>
        <div className="admin-info">
          <div className="admin-avatar">A</div>
          <span>Admin User</span>
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </div>

      <div className="admin-container">
        {/* Sidebar */}
        <div className="admin-sidebar">
          <ul className="sidebar-menu">
            {navItems.map(item => (
              <li
                key={item.key}
                className={activeSection === item.key ? 'active' : ''}
                onClick={() => setActiveSection(item.key)}
              >
                <span className="sidebar-icon">{item.icon}</span>
                <span>{item.label}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Main Content */}
        <div className="admin-main">

          {/* Overview */}
          {activeSection === 'overview' && (
            <div>
              <h1 className="page-title">Dashboard Overview</h1>
              <p className="page-subtitle">System statistics and key metrics</p>
              <div className="stats-grid">
                <div className="stat-card"><h3>Total Users</h3><div className="stat-value">12,458</div><div className="stat-change">↑ 234 this month</div></div>
                <div className="stat-card"><h3>Active Users</h3><div className="stat-value">8,923</div><div className="stat-change">↑ 156 this week</div></div>
                <div className="stat-card"><h3>System Uptime</h3><div className="stat-value">99.8%</div><div className="stat-change">Last 30 days</div></div>
                <div className="stat-card"><h3>Data Syncs</h3><div className="stat-value">847</div><div className="stat-change">Last sync: 2 hours ago</div></div>
              </div>
              <div className="chart-container">
                <h3>User Growth (Last 6 Months)</h3>
                <canvas ref={userGrowthRef} id="userGrowthChart"></canvas>
              </div>
              <div className="chart-container">
                <h3>System Activity (Last 7 Days)</h3>
                <canvas ref={activityRef} id="activityChart"></canvas>
              </div>
            </div>
          )}

          {/* Manage Users */}
          {activeSection === 'users' && (
            <div>
              <h1 className="page-title">Manage User Accounts</h1>
              <p className="page-subtitle">View, suspend, or deactivate user accounts</p>
              <div className="filter-bar">
                <select value={userFilter} onChange={e => setUserFilter(e.target.value)}>
                  <option value="all">All Users</option>
                  <option value="active">Active</option>
                  <option value="suspended">Suspended</option>
                  <option value="inactive">Inactive</option>
                </select>
                <input
                  type="text"
                  placeholder="Search by email or name..."
                  value={userSearch}
                  onChange={e => setUserSearch(e.target.value)}
                />
              </div>
              <div className="content-card">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>User ID</th><th>Name</th><th>Email</th><th>Status</th><th>Joined Date</th><th>Last Active</th><th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map(user => (
                      <tr key={user.id}>
                        <td>{user.id}</td>
                        <td>{user.name}</td>
                        <td>{user.email}</td>
                        <td><span className={`status-badge status-${user.status}`}>{user.status.charAt(0).toUpperCase() + user.status.slice(1)}</span></td>
                        <td>{user.joined}</td>
                        <td>{user.lastActive}</td>
                        <td>
                          <div className="action-buttons">
                            {user.status === 'active' ? (
                              <button className="btn btn-warning btn-small" onClick={() => suspendUser(user.id)}>Suspend</button>
                            ) : (
                              <button className="btn btn-success btn-small" onClick={() => activateUser(user.id)}>Activate</button>
                            )}
                            <button className="btn btn-danger btn-small" onClick={() => confirmDelete(user)}>Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {filteredUsers.length === 0 && (
                      <tr><td colSpan={7} style={{ textAlign: 'center', color: '#718096', padding: 30 }}>No users found.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Export Data */}
          {activeSection === 'export' && (
            <div>
              <h1 className="page-title">Export Data</h1>
              <p className="page-subtitle">Download system data in CSV format</p>
              <div className="content-card">
                <h3>Select Data to Export</h3>
                <div className="export-options">
                  {[
                    { type: 'cpi', icon: '📊', title: 'Personal CPI', desc: 'User inflation rates' },
                    { type: 'expenses', icon: '💰', title: 'Expenses', desc: 'All user expenses' },
                    { type: 'budgets', icon: '🎯', title: 'Budgets', desc: 'User budget data' },
                    { type: 'forecasts', icon: '📈', title: 'Forecasts', desc: 'Spending forecasts' },
                  ].map(item => (
                    <div key={item.type} className="export-card" onClick={() => exportData(item.type)}>
                      <div className="export-card-icon">{item.icon}</div>
                      <div className="export-card-title">{item.title}</div>
                      <div className="export-card-desc">{item.desc}</div>
                    </div>
                  ))}
                </div>
                <div className="form-group" style={{ marginTop: 30 }}>
                  <label>Date Range</label>
                  <div style={{ display: 'flex', gap: 10 }}>
                    <input type="date" value={exportStartDate} onChange={e => setExportStartDate(e.target.value)} style={{ flex: 1 }} />
                    <input type="date" value={exportEndDate} onChange={e => setExportEndDate(e.target.value)} style={{ flex: 1 }} />
                  </div>
                </div>
                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 'normal' }}>
                    <input type="checkbox" checked={anonymizeData} onChange={e => setAnonymizeData(e.target.checked)} style={{ width: 'auto' }} />
                    Anonymize user data (recommended)
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* System Monitoring */}
          {activeSection === 'monitor' && (
            <div>
              <h1 className="page-title">System Monitoring</h1>
              <p className="page-subtitle">Activity logs and usage analytics</p>
              <div className="stats-grid">
                <div className="stat-card"><h3>API Requests</h3><div className="stat-value">45.2K</div><div className="stat-change">Today</div></div>
                <div className="stat-card"><h3>Failed Logins</h3><div className="stat-value">23</div><div className="stat-change">Last 24 hours</div></div>
                <div className="stat-card"><h3>System Errors</h3><div className="stat-value">5</div><div className="stat-change">Last 7 days</div></div>
                <div className="stat-card"><h3>Avg Response Time</h3><div className="stat-value">245ms</div><div className="stat-change">Within target</div></div>
              </div>
              <div className="content-card">
                <h3>Recent Activity Logs</h3>
                <div className="filter-bar">
                  <select>
                    <option>All Activities</option>
                    <option>Login/Logout</option>
                    <option>Data Modifications</option>
                    <option>Failed Attempts</option>
                  </select>
                  <input type="date" />
                </div>
                <table className="data-table">
                  <thead>
                    <tr><th>Timestamp</th><th>User</th><th>Activity</th><th>Status</th><th>IP Address</th></tr>
                  </thead>
                  <tbody>
                    <tr><td>2026-02-20 14:23:45</td><td>gwyneth.yeo@example.com</td><td>User Login</td><td><span className="status-badge status-success">Success</span></td><td>192.168.1.100</td></tr>
                    <tr><td>2026-02-20 14:20:12</td><td>luther.tang@example.com</td><td>Expense Created</td><td><span className="status-badge status-success">Success</span></td><td>192.168.1.105</td></tr>
                    <tr><td>2026-02-20 14:15:33</td><td>unknown@example.com</td><td>Failed Login</td><td><span className="status-badge status-failed">Failed</span></td><td>203.45.67.89</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Data Quality */}
          {activeSection === 'quality' && (
            <div>
              <h1 className="page-title">Data Quality Management</h1>
              <p className="page-subtitle">Monitor and maintain data integrity</p>
              <div className="content-card">
                <h3>Data Validation Status</h3>
                <button className="btn btn-primary" onClick={runDataValidation}>Run Validation Check</button>
                <div style={{ marginTop: 20 }}>
                  <table className="data-table">
                    <thead>
                      <tr><th>Check Type</th><th>Status</th><th>Issues Found</th><th>Last Checked</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Expense Data Integrity</td>
                        <td><span className="status-badge status-success">Passed</span></td>
                        <td>0</td><td>2 hours ago</td>
                        <td><button className="btn btn-secondary btn-small">Review</button></td>
                      </tr>
                      <tr>
                        <td>User Profile Completeness</td>
                        <td><span className="status-badge status-pending">Warning</span></td>
                        <td>15</td><td>5 hours ago</td>
                        <td><button className="btn btn-secondary btn-small" onClick={() => showToast('Showing 15 incomplete user profiles.')}>Review</button></td>
                      </tr>
                      <tr>
                        <td>External Data Consistency</td>
                        <td><span className="status-badge status-success">Passed</span></td>
                        <td>0</td><td>1 day ago</td>
                        <td><button className="btn btn-secondary btn-small">Review</button></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="content-card">
                <h3>Data Correction Log</h3>
                <table className="data-table">
                  <thead>
                    <tr><th>Timestamp</th><th>Admin</th><th>Data Type</th><th>Action</th><th>Records Affected</th></tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>2026-02-19 10:30:00</td>
                      <td>admin@spendwise.com</td>
                      <td>CPI Data</td>
                      <td>Updated inconsistent values</td>
                      <td>23</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Announcements */}
          {activeSection === 'announcements' && (
            <div>
              <h1 className="page-title">Broadcast Announcements</h1>
              <p className="page-subtitle">Create and manage system-wide announcements</p>
              <div className="content-card">
                <h3>Create New Announcement</h3>
                <form onSubmit={handleCreateAnnouncement}>
                  <div className="form-group">
                    <label>Announcement Title</label>
                    <input
                      type="text"
                      placeholder="e.g., System Maintenance Notice"
                      value={announcementForm.title}
                      onChange={e => setAnnouncementForm(f => ({ ...f, title: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Announcement Content</label>
                    <textarea
                      placeholder="Enter your announcement message..."
                      value={announcementForm.content}
                      onChange={e => setAnnouncementForm(f => ({ ...f, content: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Priority</label>
                    <select value={announcementForm.priority} onChange={e => setAnnouncementForm(f => ({ ...f, priority: e.target.value }))}>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                  <div style={{ display: 'flex', gap: 10 }}>
                    <button type="submit" className="btn btn-primary">Publish Now</button>
                    <button type="button" className="btn btn-secondary" onClick={() => showToast('Announcement saved as draft.')}>Save as Draft</button>
                  </div>
                </form>
              </div>
              <div className="content-card">
                <h3>Published Announcements</h3>
                <table className="data-table">
                  <thead>
                    <tr><th>Date</th><th>Title</th><th>Priority</th><th>Views</th><th>Actions</th></tr>
                  </thead>
                  <tbody>
                    {announcements.map((ann, idx) => (
                      <tr key={idx}>
                        <td>{ann.date}</td>
                        <td>{ann.title}</td>
                        <td><span className="status-badge status-success">{ann.priority.charAt(0).toUpperCase() + ann.priority.slice(1)}</span></td>
                        <td>{ann.views.toLocaleString()}</td>
                        <td>
                          <div className="action-buttons">
                            <button className="btn btn-secondary btn-small">Edit</button>
                            <button className="btn btn-danger btn-small" onClick={() => deleteAnnouncement(idx)}>Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Data Sync */}
          {activeSection === 'sync' && (
            <div>
              <h1 className="page-title">Data Synchronization</h1>
              <p className="page-subtitle">Manage external data source connections</p>
              <div className="sync-status">
                <div className="sync-indicator success"></div>
                <div>
                  <strong>Last Sync: Success</strong><br />
                  <small>February 20, 2026 at 12:00 PM • Next sync: March 1, 2026</small>
                </div>
              </div>
              <div className="content-card">
                <h3>Data Sources</h3>
                <table className="data-table">
                  <thead>
                    <tr><th>Source</th><th>Data Type</th><th>Last Sync</th><th>Status</th><th>Actions</th></tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>data.gov.sg</td><td>National CPI Data</td><td>2 hours ago</td>
                      <td><span className="status-badge status-success">Connected</span></td>
                      <td>
                        <div className="action-buttons">
                          <button className="btn btn-primary btn-small" onClick={() => triggerSync('CPI')}>Sync Now</button>
                          <button className="btn btn-secondary btn-small">View Logs</button>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td>SingStat API</td><td>Inflation Indices</td><td>1 day ago</td>
                      <td><span className="status-badge status-success">Connected</span></td>
                      <td>
                        <div className="action-buttons">
                          <button className="btn btn-primary btn-small" onClick={() => triggerSync('Inflation')}>Sync Now</button>
                          <button className="btn btn-secondary btn-small">View Logs</button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="content-card">
                <h3>Synchronization Settings</h3>
                <div className="form-group">
                  <label>Automatic Sync Schedule</label>
                  <select value={syncSchedule} onChange={e => setSyncSchedule(e.target.value)}>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 'normal' }}>
                    <input type="checkbox" checked={autoBackup} onChange={e => setAutoBackup(e.target.checked)} style={{ width: 'auto' }} />
                    Create backup before sync
                  </label>
                </div>
                <button className="btn btn-success" onClick={() => showToast('Sync settings saved.')}>Save Settings</button>
              </div>
              <div className="content-card">
                <h3>Sync History</h3>
                <table className="data-table">
                  <thead>
                    <tr><th>Timestamp</th><th>Source</th><th>Records Updated</th><th>Status</th><th>Details</th></tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>2026-02-20 12:00:00</td><td>data.gov.sg</td><td>1,245</td>
                      <td><span className="status-badge status-success">Success</span></td>
                      <td><button className="btn btn-secondary btn-small">View Log</button></td>
                    </tr>
                    <tr>
                      <td>2026-02-19 12:00:00</td><td>SingStat API</td><td>856</td>
                      <td><span className="status-badge status-success">Success</span></td>
                      <td><button className="btn btn-secondary btn-small">View Log</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Backup & Recovery */}
          {activeSection === 'backup' && (
            <div>
              <h1 className="page-title">Backup & Recovery</h1>
              <p className="page-subtitle">Manage system backups and data recovery</p>
              <div className="content-card">
                <h3>Create New Backup</h3>
                <p style={{ color: '#718096', marginBottom: 20 }}>Create a manual backup of the system database</p>
                <button className="btn btn-primary" onClick={createBackup}>🔒 Create Backup Now</button>
              </div>
              <div className="content-card">
                <h3>Backup History</h3>
                <table className="data-table">
                  <thead>
                    <tr><th>Backup ID</th><th>Created</th><th>Type</th><th>Size</th><th>Status</th><th>Actions</th></tr>
                  </thead>
                  <tbody>
                    {[
                      { id: 'BKP-20260220-001', created: 'Feb 20, 2026 06:00 AM', type: 'Automatic', size: '2.4 GB' },
                      { id: 'BKP-20260219-001', created: 'Feb 19, 2026 06:00 AM', type: 'Automatic', size: '2.3 GB' },
                    ].map(bkp => (
                      <tr key={bkp.id}>
                        <td>{bkp.id}</td><td>{bkp.created}</td><td>{bkp.type}</td><td>{bkp.size}</td>
                        <td><span className="status-badge status-success">Complete</span></td>
                        <td>
                          <div className="action-buttons">
                            <button className="btn btn-success btn-small" onClick={() => restoreBackup(bkp.id)}>Restore</button>
                            <button className="btn btn-secondary btn-small">Download</button>
                            <button className="btn btn-danger btn-small">Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="content-card">
                <h3>Backup Settings</h3>
                <div className="form-group">
                  <label>Automatic Backup Schedule</label>
                  <select value={backupSchedule} onChange={e => setBackupSchedule(e.target.value)}>
                    <option value="hourly">Every Hour</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Retention Period (days)</label>
                  <input type="number" value={retentionDays} min={1} onChange={e => setRetentionDays(e.target.value)} />
                </div>
                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 'normal' }}>
                    <input type="checkbox" checked={encryptBackups} onChange={e => setEncryptBackups(e.target.checked)} style={{ width: 'auto' }} />
                    Encrypt backup files
                  </label>
                </div>
                <button className="btn btn-success" onClick={() => showToast('Backup settings saved.')}>Save Settings</button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default SpendWiseAdmin;
