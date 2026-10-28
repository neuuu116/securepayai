#!/bin/bash

# SecurePayAI Fraud Test Cases - Interactive Demo Script
# Usage: bash test_fraud.sh

API_URL="http://localhost:8000"
DELAY=2

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     SecurePayAI Fraud Detection - Test Suite               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to test health
check_health() {
    echo -e "${BLUE}Checking API health...${NC}"
    HEALTH=$(curl -s $API_URL/health)
    if [[ $HEALTH == *"ok"* ]]; then
        echo -e "${GREEN}✓ API is running${NC}"
    else
        echo -e "${RED}✗ API is NOT running${NC}"
        echo "Start API with: uvicorn app.main:app --reload"
        exit 1
    fi
    echo ""
}

# Function to submit transaction
submit_transaction() {
    local user_id=$1
    local amount=$2
    local merchant=$3
    local device_id=$4
    local is_new_device=$5
    local avg_amount=$6
    local title=$7

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📝 TEST: $title${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "User ID: $user_id"
    echo "Amount: \$$amount"
    echo "Merchant: $merchant"
    echo "Device: $device_id (New: $is_new_device)"
    echo "Avg Amount: \$$avg_amount"
    echo ""

    echo -e "${BLUE}Submitting transaction...${NC}"
    RESPONSE=$(curl -s -X POST $API_URL/transaction \
        -H "Content-Type: application/json" \
        -d "{
            \"user_id\": \"$user_id\",
            \"amount\": $amount,
            \"merchant\": \"$merchant\",
            \"device_id\": \"$device_id\",
            \"is_new_device\": $is_new_device,
            \"user_avg_transaction_amount\": $avg_amount
        }")

    TXN_ID=$(echo $RESPONSE | grep -o '"transaction_id":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$TXN_ID" ]; then
        echo -e "${RED}✗ Failed to submit transaction${NC}"
        echo "Response: $RESPONSE"
        return
    fi

    echo -e "${GREEN}✓ Transaction submitted${NC}"
    echo "Transaction ID: $TXN_ID"
    echo ""

    # Poll for status
    echo -e "${BLUE}Polling for fraud decision (every 2 seconds)...${NC}"
    POLLS=0
    MAX_POLLS=20
    STATUS="processing"

    while [ "$STATUS" = "processing" ] && [ $POLLS -lt $MAX_POLLS ]; do
        sleep $DELAY
        STATUS_RESPONSE=$(curl -s $API_URL/transaction/$TXN_ID/status)
        STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*' | cut -d'"' -f4)
        SCORE=$(echo $STATUS_RESPONSE | grep -o '"score":[0-9.]*' | cut -d':' -f2)
        
        POLLS=$((POLLS + 1))
        echo -ne "  Poll #$POLLS - Status: $STATUS, Score: $SCORE\r"
    done
    echo ""
    
    # Print full response
    echo -e "${BLUE}Final Decision:${NC}"
    echo "$STATUS_RESPONSE" | jq '.' 2>/dev/null || echo "$STATUS_RESPONSE"
    echo ""

    # Extract status for display
    if [[ $STATUS == "approved" ]]; then
        echo -e "${GREEN}✓ APPROVED${NC}"
    elif [[ $STATUS == "flagged" ]]; then
        echo -e "${YELLOW}⚠️  FLAGGED - OTP Required${NC}"
        echo "Check Terminal 2 for: [MOCK SMS] ... OTP=XXXXXX"
        echo "To verify OTP, run:"
        echo "  curl -X POST $API_URL/verify-otp \\"
        echo "    -H 'Content-Type: application/json' \\"
        echo "    -d '{\"transaction_id\": \"$TXN_ID\", \"otp_code\": \"XXXXXX\"}'"
    elif [[ $STATUS == "blocked" ]]; then
        echo -e "${RED}✗ BLOCKED${NC}"
    fi
    echo ""
    echo "Press ENTER to continue..."
    read
}

# Health check
check_health

# Menu
while true; do
    echo -e "${BLUE}SELECT TEST CASE:${NC}"
    echo ""
    echo "LOW-RISK (Auto-Approved):"
    echo "  1. Coffee Purchase ($50)"
    echo "  2. Grocery Shopping ($200)"
    echo ""
    echo "MEDIUM-RISK (Flagged - OTP Required):"
    echo "  3. New Device ($300)"
    echo "  4. Amount Spike ($800)"
    echo "  5. New Device + Spike ($1200)"
    echo ""
    echo "HIGH-RISK (Auto-Blocked):"
    echo "  6. Extreme Amount ($5000)"
    echo "  7. Multiple Red Flags ($3000)"
    echo ""
    echo "UTILITIES:"
    echo "  8. Run All Tests (5-minute demo)"
    echo "  9. Custom Transaction"
    echo "  0. Exit"
    echo ""
    echo -n "Enter choice: "
    read choice

    case $choice in
        1)
            submit_transaction "user-1" "50" "Starbucks" "phone-1" "false" "100" "Low-Risk: Coffee Purchase"
            ;;
        2)
            submit_transaction "user-2" "200" "Whole Foods" "laptop-1" "false" "250" "Low-Risk: Grocery Shopping"
            ;;
        3)
            submit_transaction "user-4" "300" "Best Buy" "new-iphone-xyz" "true" "200" "Medium-Risk: New Device"
            ;;
        4)
            submit_transaction "user-5" "800" "Amazon" "phone-2" "false" "150" "Medium-Risk: Amount Spike"
            ;;
        5)
            submit_transaction "user-6" "1200" "Electronics Store" "tablet-new-abc" "true" "300" "Medium-Risk: New Device + Spike"
            ;;
        6)
            submit_transaction "user-8" "5000" "Jewelry Store" "unknown-device" "true" "200" "High-Risk: Extreme Amount"
            ;;
        7)
            submit_transaction "user-9" "3000" "Gaming Site" "new-device-suspicious" "true" "100" "High-Risk: Multiple Red Flags"
            ;;
        8)
            echo -e "${BLUE}Running all tests (5-minute demo)...${NC}"
            submit_transaction "user-1" "50" "Starbucks" "phone-1" "false" "100" "Test 1: Low-Risk"
            submit_transaction "user-4" "300" "Best Buy" "new-iphone-xyz" "true" "200" "Test 2: Medium-Risk with OTP"
            submit_transaction "user-8" "5000" "Jewelry Store" "unknown-device" "true" "200" "Test 3: High-Risk Blocked"
            echo -e "${GREEN}✓ All tests completed!${NC}"
            ;;
        9)
            echo "Enter custom transaction details:"
            read -p "User ID: " user_id
            read -p "Amount: " amount
            read -p "Merchant: " merchant
            read -p "Device ID: " device_id
            read -p "Is New Device (true/false): " is_new_device
            read -p "User Avg Amount: " avg_amount
            submit_transaction "$user_id" "$amount" "$merchant" "$device_id" "$is_new_device" "$avg_amount" "Custom Transaction"
            ;;
        0)
            echo -e "${GREEN}Goodbye! 🎉${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
done
