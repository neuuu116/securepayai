import React from 'react';
import { ChevronDown } from 'lucide-react';
import './TransactionHistory.css';

function TransactionHistory({ transactions }) {
  const [expandedId, setExpandedId] = React.useState(null);

  return (
    <div className="transaction-history">
      <header className="history-header">
        <h2>Transaction History</h2>
        <p>Complete record of all fraud detection decisions</p>
      </header>

      <div className="filters">
        <select className="filter-select">
          <option>All Decisions</option>
          <option>Approved</option>
          <option>Flagged</option>
          <option>Blocked</option>
        </select>
        <select className="filter-select">
          <option>Last 24 Hours</option>
          <option>Last 7 Days</option>
          <option>Last 30 Days</option>
        </select>
      </div>

      <div className="history-table">
        <div className="table-header">
          <div className="col-id">Transaction ID</div>
          <div className="col-user">User</div>
          <div className="col-amount">Amount</div>
          <div className="col-merchant">Merchant</div>
          <div className="col-score">Risk Score</div>
          <div className="col-decision">Decision</div>
          <div className="col-time">Time</div>
        </div>

        <div className="table-body">
          {transactions.length > 0 ? (
            transactions.map((txn, idx) => (
              <div key={idx} className="table-row">
                <div className="col-id">
                  <code>{txn.transaction_id?.substring(0, 12)}...</code>
                </div>
                <div className="col-user">{txn.user_id}</div>
                <div className="col-amount">${txn.amount}</div>
                <div className="col-merchant">{txn.merchant}</div>
                <div className="col-score">
                  <div className="score-bar">
                    <div
                      className="score-fill"
                      style={{
                        width: `${(txn.score || 0) * 100}%`,
                        backgroundColor: txn.score > 0.6 ? '#ef4444' : txn.score > 0.3 ? '#f59e0b' : '#10b981'
                      }}
                    ></div>
                  </div>
                  <span>{(txn.score * 100).toFixed(0)}%</span>
                </div>
                <div className={`col-decision status-${txn.decision}`}>
                  {txn.decision?.toUpperCase()}
                </div>
                <div className="col-time">
                  {new Date().toLocaleTimeString()}
                </div>
              </div>
            ))
          ) : (
            <div className="empty-state">
              <p>No transactions yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TransactionHistory;
