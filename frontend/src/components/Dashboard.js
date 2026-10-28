import React from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import './Dashboard.css';

function Dashboard({ fraudStats, transactions }) {
  const chartData = [
    { name: 'Mon', approved: 45, flagged: 12, blocked: 3 },
    { name: 'Tue', approved: 52, flagged: 18, blocked: 5 },
    { name: 'Wed', approved: 48, flagged: 15, blocked: 4 },
    { name: 'Thu', approved: 61, flagged: 22, blocked: 7 },
    { name: 'Fri', approved: 55, flagged: 19, blocked: 6 },
    { name: 'Sat', approved: 67, flagged: 25, blocked: 8 },
    { name: 'Sun', approved: 72, flagged: 28, blocked: 9 },
  ];

  const pieData = [
    { name: 'Approved', value: fraudStats.approvedCount || 245 },
    { name: 'Flagged', value: fraudStats.flaggedCount || 68 },
    { name: 'Blocked', value: fraudStats.blockedCount || 12 },
  ];

  const COLORS = ['#10b981', '#f59e0b', '#ef4444'];

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h2>Fraud Detection Dashboard</h2>
        <p>Real-time transaction monitoring and analysis</p>
      </header>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon approved">
            <CheckCircle size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Approved</p>
            <h3>{fraudStats.approvedCount || 245}</h3>
            <span className="stat-change">↑ 12.5% this week</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon flagged">
            <AlertTriangle size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Flagged</p>
            <h3>{fraudStats.flaggedCount || 68}</h3>
            <span className="stat-change">↑ 8.2% this week</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon blocked">
            <XCircle size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Blocked</p>
            <h3>{fraudStats.blockedCount || 12}</h3>
            <span className="stat-change">↓ 2.1% this week</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon score">
            <TrendingUp size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Avg Risk Score</p>
            <h3>{(fraudStats.avgScore || 0).toFixed(2)}</h3>
            <span className="stat-change">Stable</span>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="charts-container">
        <div className="chart-box">
          <h3>Transaction Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ backgroundColor: '#1a2847', border: '1px solid #3b82f6', borderRadius: '8px', color: '#e2e8f0' }} />
              <Legend />
              <Bar dataKey="approved" fill="#10b981" radius={[8, 8, 0, 0]} />
              <Bar dataKey="flagged" fill="#f59e0b" radius={[8, 8, 0, 0]} />
              <Bar dataKey="blocked" fill="#ef4444" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-box">
          <h3>Decision Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Transactions */}
      <div className="recent-transactions">
        <h3>Recent Transactions</h3>
        <div className="transaction-list">
          {transactions.length > 0 ? (
            transactions.map((txn, idx) => (
              <div key={idx} className="transaction-item">
                <div className="txn-info">
                  <p className="txn-id">ID: {txn.transaction_id?.substring(0, 8)}</p>
                  <p className="txn-details">{txn.merchant} • ${txn.amount}</p>
                </div>
                <div className={`txn-status status-${txn.decision}`}>
                  {txn.decision?.toUpperCase()}
                </div>
                <div className="txn-score">{txn.score?.toFixed(2)}</div>
              </div>
            ))
          ) : (
            <p className="no-data">No transactions yet. Submit your first payment!</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
