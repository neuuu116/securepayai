#!/bin/bash

API="http://localhost:8000"

test_transaction() {
    local name=$1
    local user_id=$2
    local amount=$3
    local merchant=$4
    local device_id=$5
    local is_new=$6
    local avg=$7
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 TEST: $name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Amount: \$$amount | Device: $device_id (New: $is_new) | Avg: \$$avg"
    echo ""
    
    # Submit
    RESPONSE=$(curl -s -X POST $API/transaction \
        -H "Content-Type: application/json" \
        -d "{
            \"user_id\": \"$user_id\",
            \"amount\": $amount,
            \"merchant\": \"$merchant\",
            \"device_id\": \"$device_id\",
            \"is_new_device\": $is_new,
            \"user_avg_transaction_amount\": $avg
        }")
    
    TXN_ID=$(echo $RESPONSE | grep -o '"transaction_id":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$TXN_ID" ]; then
        echo "❌ FAILED - Response: $RESPONSE"
        echo ""
        return
    fi
    
    echo "✓ Submitted: $TXN_ID"
    echo "Polling for decision..."
    
    # Poll
    for i in {1..15}; do
        sleep 1
        STATUS=$(curl -s $API/transaction/$TXN_ID/status)
        DECISION=$(echo $STATUS | grep -o '"status":"[^"]*' | cut -d'"' -f4)
        SCORE=$(echo $STATUS | grep -o '"score":[0-9.]*' | cut -d':' -f2)
        REASONS=$(echo $STATUS | grep -o '"reasons":"[^"]*' | cut -d'"' -f4)
        
        if [ "$DECISION" != "processing" ]; then
            break
        fi
        echo -ne "  Poll $i: $DECISION | Score: $SCORE\r"
    done
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ "$DECISION" = "approved" ]; then
        echo "✅ RESULT: APPROVED | Score: $SCORE"
    elif [ "$DECISION" = "flagged" ]; then
        echo "⚠️  RESULT: FLAGGED | Score: $SCORE"
        echo "   Reasons: $REASONS"
    elif [ "$DECISION" = "blocked" ]; then
        echo "❌ RESULT: BLOCKED | Score: $SCORE"
    else
        echo "⚠️  RESULT: Unknown ($DECISION)"
    fi
    
    echo ""
}

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          SecurePayAI - Complete Test Suite                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# LOW-RISK TESTS
echo "🟢 LOW-RISK TESTS (Should be APPROVED)"
echo ""
test_transaction "Test 1: Coffee Purchase" "user-1" "50" "Starbucks" "phone-1" "false" "100"
test_transaction "Test 2: Grocery Shopping" "user-2" "200" "Whole Foods" "laptop-1" "false" "250"

# MEDIUM-RISK TESTS
echo "🟡 MEDIUM-RISK TESTS (Should be FLAGGED)"
echo ""
test_transaction "Test 3: New Device" "user-4" "300" "Best Buy" "new-iphone" "true" "200"
test_transaction "Test 4: Amount Spike" "user-5" "800" "Amazon" "phone-2" "false" "150"
test_transaction "Test 5: Multi-Risk" "user-6" "1200" "Electronics" "tablet-new" "true" "300"

# HIGH-RISK TESTS
echo "🔴 HIGH-RISK TESTS (Should be BLOCKED)"
echo ""
test_transaction "Test 6: Extreme Amount" "user-8" "5000" "Jewelry Store" "unknown" "true" "200"
test_transaction "Test 7: Multiple Flags" "user-9" "3000" "Crypto Exchange" "new-device" "true" "100"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 ALL TESTS COMPLETED ✅                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
