import React, { useState, useEffect } from "react";
import "./App.css";
import { api } from "./api";
import { TransactionForm } from "./TransactionForm";
import { StatusDisplay } from "./StatusDisplay";
import { OTPVerification } from "./OTPVerification";

function App() {
  const [transaction, setTransaction] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [showOTPModal, setShowOTPModal] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(null);

  // Poll transaction status when transaction is in "processing"
  useEffect(() => {
    if (!transaction || transaction.status !== "processing") {
      if (pollingInterval) clearInterval(pollingInterval);
      return;
    }

    // Poll immediately, then every 2 seconds
    const poll = async () => {
      try {
        const status = await api.getTransactionStatus(transaction.transaction_id);
        setTransaction((prev) => ({
          ...prev,
          ...status,
        }));

        // Stop polling once status changes from "processing"
        if (status.status !== "processing") {
          setPollingInterval(null);
        }
      } catch (err) {
        console.error("Poll error:", err);
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    setPollingInterval(interval);

    return () => clearInterval(interval);
  }, [transaction, pollingInterval]);

  const handleSubmitTransaction = async (formData) => {
    setError("");
    setIsLoading(true);
    try {
      const result = await api.submitTransaction(formData);
      setTransaction({
        ...result,
        status: result.status,
        transaction_id: result.transaction_id,
      });
    } catch (err) {
      setError(err.message || "Failed to submit transaction");
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOTP = async (otpCode) => {
    setError("");
    try {
      await api.verifyOTP(transaction.transaction_id, otpCode);
      // After verification, poll to get updated status
      const status = await api.getTransactionStatus(transaction.transaction_id);
      setTransaction((prev) => ({
        ...prev,
        ...status,
      }));
      setShowOTPModal(false);
    } catch (err) {
      throw err;
    }
  };

  const handleReset = () => {
    setTransaction(null);
    setError("");
    setShowOTPModal(false);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>🔒 SecurePayAI</h1>
          <p>Real-time Fraud Detection System</p>
        </div>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            <span>❌ {error}</span>
            <button onClick={() => setError("")}>Dismiss</button>
          </div>
        )}

        <div className="content-grid">
          <div className="left-panel">
            <TransactionForm onSubmit={handleSubmitTransaction} isLoading={isLoading} />
            {transaction && (
              <button className="reset-btn" onClick={handleReset}>
                Start New Transaction
              </button>
            )}
          </div>

          <div className="right-panel">
            {transaction ? (
              <StatusDisplay
                transaction={transaction}
                onOTPNeeded={() => setShowOTPModal(true)}
              />
            ) : (
              <div className="placeholder">
                <p>Submit a transaction to get started</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {showOTPModal && (
        <OTPVerification
          transactionId={transaction.transaction_id}
          onVerify={handleVerifyOTP}
          onCancel={() => setShowOTPModal(false)}
        />
      )}
    </div>
  );
}

export default App;
