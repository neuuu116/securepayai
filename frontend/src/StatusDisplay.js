import React, { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Clock, XCircle } from "lucide-react";
import "./StatusDisplay.css";

export function StatusDisplay({ transaction, onOTPNeeded }) {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [nextRefreshIn, setNextRefreshIn] = useState(0);

  useEffect(() => {
    if (!autoRefresh || !transaction || transaction.status !== "processing") {
      return;
    }

    let interval = setInterval(() => {
      setNextRefreshIn((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, transaction]);

  if (!transaction) {
    return null;
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case "approved":
        return <CheckCircle className="status-icon approved" size={40} />;
      case "flagged":
        return <AlertCircle className="status-icon flagged" size={40} />;
      case "blocked":
        return <XCircle className="status-icon blocked" size={40} />;
      case "processing":
        return <Clock className="status-icon processing" size={40} />;
      default:
        return <Clock className="status-icon" size={40} />;
    }
  };

  const getStatusText = (status) => {
    const map = {
      approved: "✓ Approved",
      flagged: "⚠ Flagged for Verification",
      blocked: "✗ Blocked",
      processing: "⟳ Processing",
    };
    return map[status] || status;
  };

  return (
    <div className="status-container">
      <div className={`status-card ${transaction.status}`}>
        <div className="status-header">
          {getStatusIcon(transaction.status)}
          <h3>{getStatusText(transaction.status)}</h3>
        </div>

        <div className="status-details">
          <div className="detail-row">
            <span className="label">Transaction ID:</span>
            <code className="txid">{transaction.transaction_id}</code>
          </div>

          {transaction.score !== undefined && (
            <div className="detail-row">
              <span className="label">Fraud Score:</span>
              <span className="score">{transaction.score.toFixed(2)}</span>
            </div>
          )}

          {transaction.reasons && transaction.reasons !== "none" && (
            <div className="detail-row">
              <span className="label">Reasons:</span>
              <span className="reasons">{transaction.reasons}</span>
            </div>
          )}

          {transaction.explanation && (
            <div className="detail-row">
              <span className="label">Explanation:</span>
              <p className="explanation">{transaction.explanation}</p>
            </div>
          )}
        </div>

        {transaction.status === "processing" && (
          <div className="processing-info">
            <p>
              Auto-refreshing...
              {nextRefreshIn > 0 && ` (next in ${nextRefreshIn}s)`}
            </p>
            <button
              className="toggle-refresh"
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? "Pause" : "Resume"} Auto-Refresh
            </button>
          </div>
        )}

        {transaction.status === "flagged" && transaction.otp_required && (
          <button className="verify-otp-btn" onClick={onOTPNeeded}>
            Enter OTP
          </button>
        )}
      </div>
    </div>
  );
}
