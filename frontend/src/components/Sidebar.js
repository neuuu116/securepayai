import React from 'react';
import { Shield, CreditCard, History, Settings, LogOut } from 'lucide-react';
import './Sidebar.css';

function Sidebar({ currentPage, setCurrentPage }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Shield size={32} className="logo-icon" />
        <h1>SecurePayAI</h1>
      </div>

      <nav className="sidebar-nav">
        <button
          className={`nav-item ${currentPage === 'dashboard' ? 'active' : ''}`}
          onClick={() => setCurrentPage('dashboard')}
        >
          <div className="nav-icon">📊</div>
          <span>Dashboard</span>
        </button>

        <button
          className={`nav-item ${currentPage === 'payment' ? 'active' : ''}`}
          onClick={() => setCurrentPage('payment')}
        >
          <CreditCard size={20} />
          <span>Submit Payment</span>
        </button>

        <button
          className={`nav-item ${currentPage === 'history' ? 'active' : ''}`}
          onClick={() => setCurrentPage('history')}
        >
          <History size={20} />
          <span>History</span>
        </button>

        <button className="nav-item">
          <Settings size={20} />
          <span>Settings</span>
        </button>
      </nav>

      <div className="sidebar-footer">
        <button className="logout-btn">
          <LogOut size={20} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
