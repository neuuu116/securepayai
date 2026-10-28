import React, { useState } from 'react';
import axios from 'axios';
import { Send, Loader, CheckCircle, AlertCircle, Lock, IndianRupee } from 'lucide-react';
import './PaymentFormINR.css';

function PaymentFormINR({ onSubmit }) {
  const [formData, setFormData] = useState({
    user_id: 'user-' + Math.random().toString(36).substr(2, 9),
    upi_id: '',
    amount: '',
    merchant: '',
    device_id: 'device-' + Math.random().toString(36).substr(2, 9),
    device_type: 'mobile', // 'mobile' or 'web'
    is_new_device: false,
    is_new_upi_app: false,
    user_avg_transaction_amount: 5000, // Default ₹5000 for India
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [otpStep, setOtpStep] = useState(false);
  const [otp, setOtp] = useState('');
  const [upiError, setUpiError] = useState('');

  // UPI ID validation
  const validateUPI = (upi) => {
    if (!upi.includes('@')) {
      return false;
    }
    const parts = upi.split('@');
    if (parts.length !== 2) return false;
    
    const validProviders = ['okhdfcbank', 'okaxis', 'okicici', 'ybl', 'upi', 'googleplay'];
    return validProviders.includes(parts[1].toLowerCase());
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    if (name === 'upi_id') {
      setFormData(prev => ({ ...prev, [name]: value }));
      if (value) {
        setUpiError(validateUPI(value) ? '' : 'Invalid UPI ID format. Use: username@provider');
      }
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: type === 'checkbox' ? checked : value
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate UPI ID
    if (!validateUPI(formData.upi_id)) {
      setUpiError('Invalid UPI ID. Please use format: username@provider');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      // Convert INR amount to float
      const amount = parseFloat(formData.amount);
      if (amount <= 0 || amount > 100000) {
        throw new Error('Amount must be between ₹1 and ₹100,000 (RBI UPI limit)');
      }

      const payload = {
        user_id: formData.user_id,
        upi_id: formData.upi_id,
        amount: amount,
        merchant: formData.merchant,
        device_id: formData.device_id,
        device_type: formData.device_type,
        is_new_device: formData.is_new_device,
        is_new_upi_app: formData.is_new_upi_app,
        user_avg_transaction_amount: parseFloat(formData.user_avg_transaction_amount),
        currency: 'INR',
        timestamp: new Date().toISOString(),
      };

      // Call backend
      const response = await axios.post('http://localhost:8000/transaction-inr', payload);

      // Simulate fraud detection
      const riskScore = calculateLocalScore(formData);
      const decision = getDecision(riskScore);
      
      const mockResult = {
        transaction_id: response.data.transaction_id || 'txn-' + Date.now(),
        status: response.data.status || 'submitted',
        decision: decision,
        score: riskScore,
        amount: amount,
        merchant: formData.merchant,
        upi_id: formData.upi_id,
        ...formData
      };

      setResult(mockResult);
      
      if (decision === 'flagged') {
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

  // Local score calculation for demo
  const calculateLocalScore = (data) => {
    let score = 0;
    const amount = parseFloat(data.amount);
    const userAvg = parseFloat(data.user_avg_transaction_amount);
    
    if (userAvg > 0 && amount / userAvg >= 5) score += 0.4;
    if (data.is_new_device || data.is_new_upi_app) score += 0.3;
    if (new Date().getHours() < 5) score += 0.2;
    if (amount >= 25000 && amount % 5000 === 0) score += 0.1;
    
    return Math.min(score, 1.0);
  };

  const getDecision = (score) => {
    if (score >= 0.6) return 'blocked';
    if (score >= 0.3) return 'flagged';
    return 'approved';
  };

  const handleOtpVerify = async () => {
    if (otp.length !== 6) {
      alert('Please enter a 6-digit OTP');
      return;
    }

    try {
      await axios.post('http://localhost:8000/verify-otp-inr', {
        transaction_id: result.transaction_id,
        otp_code: otp,
        upi_id: result.upi_id
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
          merchant: '',
          upi_id: ''
        });
      }, 2000);
    } catch (error) {
      alert('OTP verification failed: ' + error.message);
    }
  };

  return (
    <div className="payment-form-inr-container">
      <header className="form-header-inr">
        <h2>🇮🇳 UPI Payment Gateway</h2>
        <p>Secure INR transactions with real-time fraud detection</p>
      </header>

      <div className="form-layout-inr">
        {/* Form */}
        <div className="form-section-inr">
          <form onSubmit={handleSubmit}>
            {/* UPI ID */}
            <div className="form-group-inr">
              <label>UPI ID *</label>
              <input
                type="text"
                name="upi_id"
                placeholder="username@okhdfcbank"
                value={formData.upi_id}
                onChange={handleInputChange}
                required
                className={upiError ? 'error' : ''}
              />
              {upiError && <span className="error-text">{upiError}</span>}
              <small>Examples: 9876543210@okhdfcbank, user@googleplay</small>
            </div>

            {/* Amount */}
            <div className="form-group-inr">
              <label>Amount (₹) *</label>
              <div className="input-group-inr">
                <IndianRupee size={18} />
                <input
                  type="number"
                  name="amount"
                  placeholder="5000"
                  value={formData.amount}
                  onChange={handleInputChange}
                  required
                  step="1"
                  min="1"
                  max="100000"
                />
              </div>
              <small>₹1 - ₹100,000 (RBI UPI limit)</small>
            </div>

            {/* Merchant */}
            <div className="form-group-inr">
              <label>Merchant Name *</label>
              <input
                type="text"
                name="merchant"
                placeholder="e.g., Flipkart, Zomato"
                value={formData.merchant}
                onChange={handleInputChange}
                required
              />
            </div>

            {/* Device Type */}
            <div className="form-group-inr">
              <label>Device Type</label>
              <select
                name="device_type"
                value={formData.device_type}
                onChange={handleInputChange}
              >
                <option value="mobile">📱 Mobile (UPI App)</option>
                <option value="web">💻 Web Browser</option>
              </select>
            </div>

            {/* Average Transaction */}
            <div className="form-group-inr">
              <label>Your Avg Transaction (₹)</label>
              <div className="input-group-inr">
                <IndianRupee size={18} />
                <input
                  type="number"
                  name="user_avg_transaction_amount"
                  placeholder="5000"
                  value={formData.user_avg_transaction_amount}
                  onChange={handleInputChange}
                  step="100"
                />
              </div>
            </div>

            {/* Checkboxes */}
            <div className="form-group-inr checkbox-group">
              <label>
                <input
                  type="checkbox"
                  name="is_new_device"
                  checked={formData.is_new_device}
                  onChange={handleInputChange}
                />
                New device/phone
              </label>
              <label>
                <input
                  type="checkbox"
                  name="is_new_upi_app"
                  checked={formData.is_new_upi_app}
                  onChange={handleInputChange}
                />
                New UPI app installation
              </label>
            </div>

            <button type="submit" className="submit-btn-inr" disabled={loading || !!upiError}>
              {loading ? (
                <>
                  <Loader size={20} className="spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Send size={20} />
                  Send Money
                </>
              )}
            </button>
          </form>
        </div>

        {/* Result */}
        {result && !otpStep && (
          <div className={`result-section-inr result-${result.decision}`}>
            <div className="result-icon-inr">
              {result.decision === 'approved' && <CheckCircle size={48} />}
              {result.decision === 'flagged' && <AlertCircle size={48} />}
              {result.decision === 'blocked' && <AlertCircle size={48} />}
            </div>

            <h3>
              {result.decision === 'approved' && '✓ Payment Approved'}
              {result.decision === 'flagged' && '⚠️ Verification Required'}
              {result.decision === 'blocked' && '✗ Payment Blocked'}
              {result.decision === 'error' && '❌ Error'}
            </h3>

            {result.error ? (
              <p className="error-message">{result.error}</p>
            ) : (
              <>
                <div className="result-details-inr">
                  <div className="detail-row-inr">
                    <span>UPI ID:</span>
                    <strong>{result.upi_id}</strong>
                  </div>
                  <div className="detail-row-inr">
                    <span>Amount:</span>
                    <strong>₹{parseFloat(result.amount).toLocaleString('en-IN')}</strong>
                  </div>
                  <div className="detail-row-inr">
                    <span>Merchant:</span>
                    <strong>{result.merchant}</strong>
                  </div>
                  <div className="detail-row-inr">
                    <span>Risk Score:</span>
                    <strong className={`risk-${Math.round(result.score * 100)}`}>
                      {(result.score * 100).toFixed(0)}%
                    </strong>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* OTP */}
        {otpStep && (
          <div className="otp-section-inr">
            <Lock size={48} className="lock-icon" />
            <h3>Verify with OTP</h3>
            <p>Enter the 6-digit OTP sent to {result.upi_id}</p>

            <input
              type="text"
              placeholder="000000"
              maxLength="6"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              className="otp-input-inr"
            />

            <button onClick={handleOtpVerify} className="verify-btn-inr">
              Verify OTP
            </button>

            <p className="otp-resend-inr">
              Didn't receive? <a href="#resend">Resend OTP</a>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default PaymentFormINR;
