import React, { useState } from 'react';
import axios from 'axios';
import { Send, Loader, CheckCircle, AlertCircle, Lock } from 'lucide-react';
import './PaymentForm.css';

function PaymentForm({ onSubmit }) {
  const [formData, setFormData] = useState({
    user_id: 'user-' + Math.random().toString(36).substr(2, 9),
    amount: '',
    merchant: '',
    device_id: 'device-' + Math.random().toString(36).substr(2, 9),
    is_new_device: false,
    user_avg_transaction_amount: 500,
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [otpStep, setOtpStep] = useState(false);
  const [otp, setOtp] = useState('');

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/transaction', {
        user_id: formData.user_id,
        amount: parseFloat(formData.amount),
        merchant: formData.merchant,
        device_id: formData.device_id,
        is_new_device: formData.is_new_device,
        user_avg_transaction_amount: parseFloat(formData.user_avg_transaction_amount),
      });

      // Mock fraud detection response
      const mockResult = {
        transaction_id: response.data.transaction_id,
        status: response.data.status,
        decision: Math.random() > 0.7 ? (Math.random() > 0.5 ? 'flagged' : 'blocked') : 'approved',
        score: Math.random() * 0.8,
        reason: 'Mock transaction processed',
        ...formData
      };

      setResult(mockResult);
      
      if (mockResult.decision === 'flagged') {
        setOtpStep(true);
      } else {
        onSubmit(mockResult);
      }
    } catch (error) {
      setResult({
        error: error.message,
        decision: 'error'
      });
    }

    setLoading(false);
  };

  const handleOtpVerify = async () => {
    if (otp.length !== 6) {
      alert('Please enter a 6-digit OTP');
      return;
    }

    try {
      await axios.post('http://localhost:8000/verify-otp', {
        transaction_id: result.transaction_id,
        otp_code: otp
      });

      setResult(prev => ({
        ...prev,
        otpVerified: true
      }));
      
      onSubmit(result);
      
      setTimeout(() => {
        setOtpStep(false);
        setResult(null);
        setOtp('');
        setFormData({
          ...formData,
          amount: '',
          merchant: ''
        });
      }, 2000);
    } catch (error) {
      alert('OTP verification failed: ' + error.message);
    }
  };

  return (
    <div className="payment-form-container">
      <header className="form-header">
        <h2>Submit Payment</h2>
        <p>Fill in the details below to process a transaction</p>
      </header>

      <div className="form-layout">
        {/* Form */}
        <div className="form-section">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Transaction Amount *</label>
              <div className="input-group">
                <span className="currency">$</span>
                <input
                  type="number"
                  name="amount"
                  placeholder="5000.00"
                  value={formData.amount}
                  onChange={handleInputChange}
                  required
                  step="0.01"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Merchant Name *</label>
              <input
                type="text"
                name="merchant"
                placeholder="e.g., Amazon, Apple Store"
                value={formData.merchant}
                onChange={handleInputChange}
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>User ID</label>
                <input
                  type="text"
                  name="user_id"
                  value={formData.user_id}
                  onChange={handleInputChange}
                  readOnly
                  className="readonly"
                />
              </div>

              <div className="form-group">
                <label>Device ID</label>
                <input
                  type="text"
                  name="device_id"
                  value={formData.device_id}
                  onChange={handleInputChange}
                  readOnly
                  className="readonly"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Average Transaction Amount</label>
              <div className="input-group">
                <span className="currency">$</span>
                <input
                  type="number"
                  name="user_avg_transaction_amount"
                  placeholder="500.00"
                  value={formData.user_avg_transaction_amount}
                  onChange={handleInputChange}
                  step="0.01"
                />
              </div>
            </div>

            <div className="form-group checkbox">
              <input
                type="checkbox"
                id="newDevice"
                name="is_new_device"
                checked={formData.is_new_device}
                onChange={handleInputChange}
              />
              <label htmlFor="newDevice">This is a new/unrecognized device</label>
            </div>

            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? (
                <>
                  <Loader size={20} className="spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Send size={20} />
                  Submit Payment
                </>
              )}
            </button>
          </form>
        </div>

        {/* Result */}
        {result && !otpStep && (
          <div className={`result-section result-${result.decision}`}>
            <div className="result-icon">
              {result.decision === 'approved' && <CheckCircle size={48} />}
              {result.decision === 'flagged' && <AlertCircle size={48} />}
              {result.decision === 'blocked' && <AlertCircle size={48} />}
            </div>

            <h3>
              {result.decision === 'approved' && 'Payment Approved ✓'}
              {result.decision === 'flagged' && 'Payment Flagged ⚠️'}
              {result.decision === 'blocked' && 'Payment Blocked ✗'}
              {result.decision === 'error' && 'Error'}
            </h3>

            {result.error ? (
              <p className="error-message">{result.error}</p>
            ) : (
              <>
                <div className="result-details">
                  <div className="detail-row">
                    <span>Transaction ID:</span>
                    <strong>{result.transaction_id?.substring(0, 12)}...</strong>
                  </div>
                  <div className="detail-row">
                    <span>Risk Score:</span>
                    <strong>{(result.score * 100).toFixed(0)}%</strong>
                  </div>
                  <div className="detail-row">
                    <span>Amount:</span>
                    <strong>${result.amount}</strong>
                  </div>
                  <div className="detail-row">
                    <span>Merchant:</span>
                    <strong>{result.merchant}</strong>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* OTP Verification */}
        {otpStep && (
          <div className="otp-section">
            <div className="otp-icon">
              <Lock size={48} />
            </div>
            <h3>Verify Your Identity</h3>
            <p>Enter the 6-digit OTP sent to your registered email</p>

            <div className="otp-input-group">
              <input
                type="text"
                placeholder="000000"
                maxLength="6"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                className="otp-input"
              />
            </div>

            <button onClick={handleOtpVerify} className="verify-btn">
              Verify OTP
            </button>

            <p className="otp-resend">
              Didn't receive it? <a href="#resend">Resend OTP</a>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default PaymentForm;
