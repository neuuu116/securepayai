import React, { useState } from "react";
import { AlertCircle } from "lucide-react";
import "./OTPVerification.css";

export function OTPVerification({ transactionId, onVerify, onCancel }) {
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!otp || otp.length !== 6) {
      setError("OTP must be exactly 6 digits");
      return;
    }

    if (!/^\d{6}$/.test(otp)) {
      setError("OTP must contain only digits");
      return;
    }

    setIsLoading(true);
    try {
      await onVerify(otp);
    } catch (err) {
      setError(err.message || "OTP verification failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 6);
    setOtp(value);
    setError("");
  };

  return (
    <div className="otp-overlay">
      <div className="otp-modal">
        <h2>🔐 Enter OTP</h2>
        <p>Enter the 6-digit code sent to your phone</p>

        {error && (
          <div className="otp-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            inputMode="numeric"
            placeholder="000000"
            value={otp}
            onChange={handleInputChange}
            maxLength="6"
            className="otp-input"
            disabled={isLoading}
            autoFocus
          />

          <div className="otp-buttons">
            <button
              type="button"
              className="btn-cancel"
              onClick={onCancel}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-verify"
              disabled={isLoading || otp.length !== 6}
            >
              {isLoading ? "Verifying..." : "Verify"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
