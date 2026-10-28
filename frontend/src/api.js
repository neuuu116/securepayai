/**
 * API Service - Handles all communication with SecurePayAI backend
 * Base URL: http://localhost:8000
 */

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

export const api = {
  /**
   * Submit a transaction for fraud analysis
   */
  submitTransaction: async (transactionData) => {
    const response = await fetch(`${API_BASE}/transaction`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(transactionData),
    });
    if (!response.ok) {
      throw new Error(`Submit failed: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Poll transaction status
   */
  getTransactionStatus: async (transactionId) => {
    const response = await fetch(
      `${API_BASE}/transaction/${transactionId}/status`
    );
    if (!response.ok) {
      throw new Error(`Status fetch failed: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Verify OTP for flagged transaction
   */
  verifyOTP: async (transactionId, otpCode) => {
    const response = await fetch(`${API_BASE}/verify-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transaction_id: transactionId,
        otp_code: otpCode,
      }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "OTP verification failed");
    }
    return response.json();
  },

  /**
   * Health check
   */
  healthCheck: async () => {
    const response = await fetch(`${API_BASE}/health`);
    return response.json();
  },
};
