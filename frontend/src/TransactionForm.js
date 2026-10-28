import React, { useState } from "react";
import { AlertCircle, CheckCircle, Clock, Lock } from "lucide-react";
import "./TransactionForm.css";

export function TransactionForm({ onSubmit, isLoading }) {
  const [formData, setFormData] = useState({
    user_id: "user-" + Math.random().toString(36).substr(2, 9),
    amount: 100,
    merchant: "Starbucks",
    device_id: "phone-1",
    is_new_device: false,
    user_avg_transaction_amount: 150,
  });

  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]:
        type === "checkbox"
          ? checked
          : type === "number"
            ? parseFloat(value)
            : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const newErrors = {};

    if (!formData.user_id) newErrors.user_id = "User ID is required";
    if (formData.amount <= 0) newErrors.amount = "Amount must be greater than 0";
    if (!formData.merchant) newErrors.merchant = "Merchant is required";

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    onSubmit(formData);
  };

  return (
    <div className="transaction-form-container">
      <div className="form-card">
        <h2>
          <Lock size={24} /> Submit Transaction
        </h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="user_id">User ID</label>
            <input
              type="text"
              id="user_id"
              name="user_id"
              value={formData.user_id}
              onChange={handleChange}
              placeholder="e.g., user-123"
            />
            {errors.user_id && <span className="error">{errors.user_id}</span>}
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="amount">Amount ($)</label>
              <input
                type="number"
                id="amount"
                name="amount"
                value={formData.amount}
                onChange={handleChange}
                step="0.01"
                min="0"
              />
              {errors.amount && (
                <span className="error">{errors.amount}</span>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="merchant">Merchant</label>
              <input
                type="text"
                id="merchant"
                name="merchant"
                value={formData.merchant}
                onChange={handleChange}
                placeholder="e.g., Starbucks"
              />
              {errors.merchant && (
                <span className="error">{errors.merchant}</span>
              )}
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="device_id">Device ID</label>
              <input
                type="text"
                id="device_id"
                name="device_id"
                value={formData.device_id}
                onChange={handleChange}
                placeholder="e.g., phone-1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="user_avg_transaction_amount">
                Avg Transaction Amount ($)
              </label>
              <input
                type="number"
                id="user_avg_transaction_amount"
                name="user_avg_transaction_amount"
                value={formData.user_avg_transaction_amount}
                onChange={handleChange}
                step="0.01"
                min="0"
              />
            </div>
          </div>

          <div className="form-group checkbox">
            <input
              type="checkbox"
              id="is_new_device"
              name="is_new_device"
              checked={formData.is_new_device}
              onChange={handleChange}
            />
            <label htmlFor="is_new_device">New Device?</label>
          </div>

          <button type="submit" disabled={isLoading} className="submit-btn">
            {isLoading ? "Submitting..." : "Submit Transaction"}
          </button>
        </form>
      </div>
    </div>
  );
}
