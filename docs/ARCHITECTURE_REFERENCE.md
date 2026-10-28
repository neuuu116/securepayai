# SecurePayAI Fraud Detection System — Complete Architecture Reference

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Core Components](#core-components)
4. [Data Models](#data-models)
5. [Database Schema](#database-schema)
6. [API Endpoints](#api-endpoints)
7. [Fraud Scoring Engine](#fraud-scoring-engine)
8. [Kafka Message Flow](#kafka-message-flow)
9. [Redis Operations](#redis-operations)
10. [Configuration & Environment](#configuration--environment)
11. [File-by-File Breakdown](#file-by-file-breakdown)
12. [Execution Flow Examples](#execution-flow-examples)

---

## System Overview

**SecurePayAI** is a real-time fraud detection platform for payment transactions. It uses a **two-process architecture**:
- **FastAPI Server** (process 1): Validates and publishes transactions to Kafka
- **Kafka Consumer** (process 2): Scores transactions, stores results, generates OTPs, explains flagged cases

**Key Features:**
- Rule-based scoring (explainable, not a black box)
- Real-time OTP verification for flagged transactions
- Claude AI explanations for risky transactions
- Kafka-based async processing (API and fraud engine scale independently)
- PostgreSQL for audit trail, Redis for time-based OTP storage

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT MOBILE/WEB                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ POST /transaction (TransactionIn)
                     ▼
        ┌────────────────────────────┐
        │   FastAPI Server           │
        │   (app/main.py)            │
        │   (app/routes.py)          │
        │                            │
        │ 1. Validate input          │
        │ 2. Generate transaction_id │
        │ 3. Publish to Kafka        │
        └────────────┬───────────────┘
                     │
        ┌────────────▼─────────────────┐
        │   Kafka Topic:               │
        │   "raw-transactions"         │
        └────────────┬─────────────────┘
                     │
        ┌────────────▼──────────────────────┐
        │  Kafka Consumer Worker Process    │
        │  (app/kafka_consumer.py)          │
        │                                   │
        │  1. Read from raw-transactions    │
        │  2. Score via fraud_engine.py     │
        │  3. Store in PostgreSQL           │
        │  4. Generate OTP (if flagged)     │
        │  5. Get Claude explanation        │
        │  6. Publish to output topic       │
        └────────┬──────────┬──────────┬────┘
                 │          │          │
        ┌────────▼──┐  ┌────▼──┐  ┌───▼──────────┐
        │ Approved  │  │Flagged│  │ Blocked      │
        │Transactions
        │ Topic     │  │Topic  │  │ Topic        │
        └───────────┘  └───────┘  └──────────────┘
                     │
        ┌────────────▼──────────────────────┐
        │   PostgreSQL Database             │
        │   - transactions (audit)          │
        │   - fraud_analysis (verdicts)     │
        │   - verification_events (OTP log) │
        └───────────────────────────────────┘
        
        ┌──────────────────────────────────┐
        │   Redis                          │
        │   - otp:{transaction_id}         │
        │   - otp_attempts:{tx_id}         │
        └──────────────────────────────────┘

        ┌──────────────────────────────────┐
        │   External: Claude API           │
        │   (explain_flagged_transaction)  │
        └──────────────────────────────────┘
        
        ┌──────────────────────────────────┐
        │   Client: POST /verify-otp       │
        │   (verify OTP and unblock)       │
        └──────────────────────────────────┘
```

---

## Core Components

### 1. **FastAPI Server** (Entry Point)
- **Purpose:** Accept transactions, validate, and queue for processing
- **Key Point:** Does NOT make fraud decisions — only accepts and publishes
- **Port:** 8000 (default)
- **Health Check:** `GET /health` → `{"status": "ok"}`

### 2. **Kafka Consumer** (Decision Engine)
- **Purpose:** Process queued transactions, score them, store results, trigger OTP
- **Key Point:** Runs separately; can be scaled independently
- **Command:** `python -m app.kafka_consumer`

### 3. **PostgreSQL** (Audit & Results)
- **Purpose:** Permanent record of all transactions and fraud verdicts
- **Port:** 5432
- **Tables:**
  - `transactions` — every incoming transaction
  - `fraud_analysis` — fraud engine's decision + reasoning
  - `verification_events` — OTP attempts (rate-limiting history)

### 4. **Redis** (Ephemeral State)
- **Purpose:** OTP storage with auto-expiry, rate-limit counters
- **Port:** 6379
- **Keys:**
  - `otp:{transaction_id}` — 6-digit OTP, expires after `otp_ttl_seconds`
  - `otp_attempts:{transaction_id}` — attempt counter, expires after `otp_ttl_seconds`

### 5. **Kafka** (Async Messaging)
- **Purpose:** Decouple API from fraud engine; enable scaling
- **Port:** 9092
- **Topics:**
  - `raw-transactions` — API publishes here; consumer reads from here
  - `approved-transactions`, `flagged-transactions`, `blocked-transactions` — consumer publishes decisions

### 6. **Claude AI** (Explanation)
- **Purpose:** Generate human-readable explanations for flagged/blocked transactions
- **Called Only For:** Decision = FLAGGED or BLOCKED (not every transaction)
- **Cost Optimization:** Explanations only when needed

---

## Data Models

### **TransactionIn** (What the client sends)
```python
{
    "user_id": str,                      # User identifier
    "amount": float (> 0),               # Transaction amount
    "merchant": str,                     # Merchant name
    "device_id": str,                    # Device identifier
    "is_new_device": bool (default False),     # New or recognized
    "user_avg_transaction_amount": float (default 0.0)  # User's rolling average
}
```

### **Transaction** (What server adds)
```python
{
    # All fields from TransactionIn, plus:
    "transaction_id": str,       # Generated UUID
    "timestamp": datetime        # Generated server-side
}
```

### **FraudResult** (Fraud engine output)
```python
{
    "transaction_id": str,
    "score": float,              # 0.0 (safe) to 1.0 (definitely fraud)
    "decision": str,             # "approved" | "flagged" | "blocked"
    "reasons": list[str],        # Why each rule triggered
    "explanation": str | None    # Claude explanation (if flagged/blocked)
}
```

### **OTPVerifyRequest** (Client submits OTP)
```python
{
    "transaction_id": str,
    "otp_code": str              # 6-digit code
}
```

---

## Database Schema

### Table: `transactions`
| Column | Type | Key | Notes |
|--------|------|-----|-------|
| `transaction_id` | VARCHAR | PRIMARY KEY | UUID, uniquely identifies transaction |
| `user_id` | VARCHAR | INDEXED | For querying user's history |
| `amount` | FLOAT | | Transaction amount |
| `merchant` | VARCHAR | | Merchant name |
| `device_id` | VARCHAR | | Device identifier |
| `is_new_device` | BOOLEAN | | Flag: new or recognized |
| `timestamp` | DATETIME | | When transaction occurred |

### Table: `fraud_analysis`
| Column | Type | Key | Notes |
|--------|------|-----|-------|
| `transaction_id` | VARCHAR | PRIMARY KEY | Foreign key to transactions |
| `score` | FLOAT | | 0.0–1.0 fraud risk score |
| `decision` | VARCHAR | | "approved" \| "flagged" \| "blocked" |
| `reasons` | TEXT | | Comma-separated rule triggers |
| `explanation` | TEXT | NULLABLE | Claude's explanation |
| `created_at` | DATETIME | | When fraud engine processed |

### Table: `verification_events`
| Column | Type | Key | Notes |
|--------|------|-----|-------|
| `id` | VARCHAR | PRIMARY KEY | UUID of the OTP attempt |
| `transaction_id` | VARCHAR | INDEXED | Which transaction being verified |
| `success` | BOOLEAN | | Did OTP match? |
| `attempted_at` | DATETIME | | When user submitted OTP |

---

## API Endpoints

### `POST /transaction` — Submit a Transaction
**Request:**
```json
{
    "user_id": "user-123",
    "amount": 2500.50,
    "merchant": "Amazon",
    "device_id": "device-abc123",
    "is_new_device": false,
    "user_avg_transaction_amount": 500.0
}
```

**Response (200):**
```json
{
    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "submitted",
    "message": "Transaction is being processed. Poll /transaction/{id}/status or check for an OTP prompt."
}
```

**What Happens Next:**
1. FastAPI generates a UUID for `transaction_id`
2. Sets `timestamp` to current UTC time
3. Publishes entire `Transaction` object to Kafka topic `raw-transactions`
4. Returns immediately (async)
5. Kafka consumer picks it up asynchronously

---

### `POST /verify-otp` — Verify OTP for a Flagged Transaction
**Request:**
```json
{
    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
    "otp_code": "123456"
}
```

**Response (200 — Success):**
```json
{
    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "verified",
    "message": "Verified successfully."
}
```

**Response (400 — Failure):**
```json
{
    "detail": "Incorrect code. 2 attempt(s) remaining."
}
```
or
```json
{
    "detail": "Too many attempts. Transaction blocked."
}
```
or
```json
{
    "detail": "OTP expired or never issued. Request a new one."
}
```

**What Happens:**
1. Check Redis for attempt counter
2. If >= 3, reject immediately
3. Fetch stored OTP from Redis
4. If expired (not in Redis), reject
5. Compare submitted code with stored
6. Increment attempt counter
7. If match: delete OTP key, return success
8. If mismatch: return failure with remaining attempts

---

### `GET /health` — Health Check
**Response (200):**
```json
{"status": "ok"}
```

---

### `GET /` — Root Endpoint
**Response (200):**
```json
{
    "message": "SecurePayAI Fraud Detection API",
    "version": "0.1.0"
}
```

---

## Fraud Scoring Engine

### Scoring Logic (`app/fraud_engine.py`)

#### Rule 1: Large Amount
- **Weight:** 0.4 points
- **Trigger Condition:** `(txn.amount / txn.user_avg_transaction_amount) >= fraud_amount_multiplier` (default 5x)
- **Reason:** `"amount is 8.2x user's average"`
- **Example:** User's average = $100, transaction = $820 → triggers

#### Rule 2: New Device
- **Weight:** 0.3 points
- **Trigger Condition:** `txn.is_new_device == True`
- **Reason:** `"transaction from a new/unrecognized device"`
- **Example:** First transaction on a new phone → triggers

#### Rule 3: Night Transaction
- **Weight:** 0.2 points
- **Trigger Condition:** `fraud_night_start_hour <= hour < fraud_night_end_hour` (default 0–5 = midnight–5 AM)
- **Reason:** `"occurred at 02:30 (outside 0:00-5:00 window)"`
- **Example:** Transaction at 2:30 AM → triggers

#### Rule 4: Suspiciously Round Amount
- **Weight:** 0.1 points
- **Trigger Condition:** `amount % 1000 == 0 AND amount >= 5000`
- **Reason:** `"suspiciously round transaction amount"`
- **Example:** Exactly $50,000.00 (no cents) → triggers

### Decision Thresholds
```python
score >= 0.6    → BLOCKED    (too risky; customer must verify)
0.3 <= score < 0.6 → FLAGGED    (suspicious; OTP required to proceed)
score < 0.3     → APPROVED   (safe; process normally)
```

### Max Score
- Scores are capped at 1.0 (even if all 4 rules trigger: 0.4 + 0.3 + 0.2 + 0.1 = 1.0)

### Example Scoring Walkthrough

**Scenario 1: Safe Transaction**
```
User Average: $500
Transaction: $520, regular device, 2 PM, merchant="Starbucks"
Score: 0.0 (no rules trigger)
Decision: APPROVED
Reasons: []
```

**Scenario 2: Flagged Transaction**
```
User Average: $500
Transaction: $2500 (5x), new device, 2 PM
Score: 0.4 (large amount) + 0.3 (new device) = 0.7 → capped at 1.0
Decision: BLOCKED (score 0.7 >= 0.6)
Reasons: ["amount is 5.0x user's average", "transaction from a new/unrecognized device"]
Action: Generate OTP, ask for verification
```

**Scenario 3: Blocked by Night + Amount**
```
User Average: $200
Transaction: $1500 (7.5x), regular device, 3 AM
Score: 0.4 (large amount) + 0.2 (night) = 0.6
Decision: BLOCKED (score 0.6 >= 0.6)
Reasons: ["amount is 7.5x user's average", "occurred at 03:00 (outside 0:00-5:00 window)"]
```

---

## Kafka Message Flow

### Message 1: Raw Transaction Published by API
**Topic:** `raw-transactions`
**Payload:**
```json
{
    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user-123",
    "amount": 2500.50,
    "merchant": "Amazon",
    "device_id": "device-abc123",
    "is_new_device": false,
    "user_avg_transaction_amount": 500.0,
    "timestamp": "2026-08-23T14:32:10.123456"
}
```
**Published By:** `app/kafka_producer.py` → `publish_transaction(txn_dict)`
**Consumed By:** `app/kafka_consumer.py` → `run()` function

---

### Message 2: Decision Published by Consumer
**Topic:** Depends on decision
- `approved-transactions` (if score < 0.3)
- `flagged-transactions` (if 0.3 <= score < 0.6)
- `blocked-transactions` (if score >= 0.6)

**Payload:**
```json
{
    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
    "decision": "blocked",
    "score": 0.7
}
```
**Published By:** `app/kafka_consumer.py` → `process_message()`

---

### Consumer Processing Sequence (in `process_message()`)
```
1. Deserialize message from Kafka
2. Parse into Transaction object
3. Call fraud_engine.score_transaction() → (score, reasons)
4. Call fraud_engine.decide(score) → decision
5. IF decision == FLAGGED or BLOCKED:
     a. Call claude_reasoning.explain_flagged_transaction() → explanation
     b. IF decision == FLAGGED:
        - Call redis_client.generate_and_store_otp() → otp_code
6. Save Transaction to database (transactions table)
7. Save FraudAnalysisRow to database (fraud_analysis table)
8. Commit to database
9. Publish to appropriate output topic (approved/flagged/blocked)
10. Log decision
```

---

## Redis Operations

### OTP Generation & Storage
**Function:** `redis_client.generate_and_store_otp(transaction_id)`
```python
code = f"{random.randint(0, 999999):06d}"  # e.g., "034782"
r.setex(f"otp:{transaction_id}", otp_ttl_seconds, code)
```
**Key:** `otp:{transaction_id}`
**Value:** 6-digit string (e.g., `"034782"`)
**TTL:** `otp_ttl_seconds` (default 300 seconds = 5 minutes)
**Expiry:** Automatic (Redis handles cleanup)

---

### Attempt Tracking
**Function:** `redis_client.verify_otp(transaction_id, submitted_code)`

**Step 1: Check Attempts**
```python
attempts = int(r.get(f"otp_attempts:{transaction_id}") or 0)
if attempts >= otp_max_attempts (default 3):
    return (False, "Too many attempts. Transaction blocked.")
```

**Step 2: Fetch Stored OTP**
```python
stored_code = r.get(f"otp:{transaction_id}")
if stored_code is None:
    return (False, "OTP expired or never issued. Request a new one.")
```

**Step 3: Increment Attempts**
```python
r.incr(f"otp_attempts:{transaction_id}")
r.expire(f"otp_attempts:{transaction_id}", otp_ttl_seconds)
```

**Step 4: Compare**
```python
if submitted_code == stored_code:
    r.delete(f"otp:{transaction_id}")
    return (True, "Verified successfully.")
else:
    remaining = otp_max_attempts - (attempts + 1)
    return (False, f"Incorrect code. {remaining} attempt(s) remaining.")
```

---

### Redis Key Patterns
| Key Pattern | Set By | Used For | TTL |
|-------------|--------|----------|-----|
| `otp:{tx_id}` | Consumer | Store OTP code | `otp_ttl_seconds` (300s) |
| `otp_attempts:{tx_id}` | Verify endpoint | Rate-limit OTP guesses | `otp_ttl_seconds` (300s) |

---

## Configuration & Environment

### `.env` File (loaded by `pydantic_settings`)
```bash
# Database
DATABASE_URL=postgresql://securepay:securepay@localhost:5432/securepayai

# Cache & Messaging
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Claude API
ANTHROPIC_API_KEY=your-key-here

# Fraud Engine Parameters
FRAUD_AMOUNT_MULTIPLIER=5              # Rule 1: Transactions > 5x average are risky
FRAUD_NIGHT_START_HOUR=0               # Rule 3: Start of night window (hour, 0-23)
FRAUD_NIGHT_END_HOUR=5                 # Rule 3: End of night window
OTP_TTL_SECONDS=300                    # OTP and attempt counter expire after 5 min
OTP_MAX_ATTEMPTS=3                     # Max incorrect OTP guesses before lockout
```

### Configuration Object (`app/config.py`)
```python
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    kafka_bootstrap_servers: str
    anthropic_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()  # Loaded on module import
```

**Usage Throughout Codebase:**
```python
from app.config import settings

# Access like:
settings.database_url
settings.fraud_amount_multiplier
settings.otp_ttl_seconds
```

---

## File-by-File Breakdown

### `app/main.py` — FastAPI Application Entry Point
```python
from fastapi import FastAPI
from app.db import init_db
from app.routes import router

app = FastAPI(title="SecurePayAI", version="0.1.0")
app.include_router(router)

# Startup hook: Initialize database tables
@app.on_event("startup")
def on_startup():
    init_db()

# Health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

# Root endpoint
@app.get("/")
def root():
    return {"message": "SecurePayAI Fraud Detection API", "version": "0.1.0"}
```
**To Run:** `uvicorn app.main:app --reload`

---

### `app/routes.py` — API Endpoints
```python
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.models import TransactionIn, Transaction, OTPVerifyRequest
from app.kafka_producer import publish_transaction
from app.redis_client import verify_otp

router = APIRouter()

@router.post("/transaction")
def submit_transaction(txn_in: TransactionIn):
    # Step 1: Build full Transaction object with server-generated fields
    txn = Transaction(
        transaction_id=str(uuid.uuid4()),        # Generate unique ID
        timestamp=datetime.utcnow(),             # Current timestamp
        **txn_in.model_dump(),                   # Include all input fields
    )
    
    # Step 2: Publish to Kafka (async, doesn't wait for processing)
    publish_transaction(txn.model_dump())
    
    # Step 3: Return immediately (user polls or waits for OTP)
    return {
        "transaction_id": txn.transaction_id,
        "status": "submitted",
        "message": "Transaction is being processed..."
    }

@router.post("/verify-otp")
def verify_transaction_otp(req: OTPVerifyRequest):
    # Check OTP via Redis
    success, message = verify_otp(req.transaction_id, req.otp_code)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "transaction_id": req.transaction_id,
        "status": "verified",
        "message": message
    }
```
**Key Insight:** Routes are "dumb" — they validate input and publish. All logic is in Kafka consumer.

---

### `app/models.py` — Pydantic Data Models
```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class Decision(str, Enum):
    """Fraud engine decision outcomes"""
    APPROVED = "approved"    # Process normally
    FLAGGED = "flagged"      # Requires OTP verification
    BLOCKED = "blocked"      # Requires OTP verification, higher risk

class TransactionIn(BaseModel):
    """What client sends to API"""
    user_id: str
    amount: float = Field(gt=0)                        # Must be positive
    merchant: str
    device_id: str
    is_new_device: bool = False
    user_avg_transaction_amount: float = Field(default=0.0)

class Transaction(TransactionIn):
    """Full transaction with server-generated fields"""
    transaction_id: str                                 # UUID, unique
    timestamp: datetime                                 # Server time

class FraudResult(BaseModel):
    """Fraud engine output"""
    transaction_id: str
    score: float                                        # 0.0–1.0
    decision: Decision                                  # Enum
    reasons: list[str]                                  # Why each rule triggered
    explanation: str | None = None                      # Claude explanation

class OTPVerifyRequest(BaseModel):
    """OTP verification request"""
    transaction_id: str
    otp_code: str
```

---

### `app/config.py` — Configuration Loader
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://securepay:securepay@localhost:5432/securepay"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    
    # Claude API (optional)
    anthropic_api_key: Optional[str] = None
    
    # Fraud engine parameters
    fraud_amount_multiplier: float = 5.0
    fraud_night_start_hour: int = 0
    fraud_night_end_hour: int = 5
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 3
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Silently ignore unknown fields

settings = Settings()  # Global singleton, loaded on import
```

---

### `app/db.py` — Database Layer
```python
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Create engine with connection pooling
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class TransactionRow(Base):
    """Audit table: every transaction that came in"""
    __tablename__ = "transactions"
    
    transaction_id = Column(String, primary_key=True)    # UUID
    user_id = Column(String, index=True, nullable=False) # Query by user
    amount = Column(Float, nullable=False)
    merchant = Column(String, nullable=False)
    device_id = Column(String, nullable=False)
    is_new_device = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class FraudAnalysisRow(Base):
    """Verdict table: fraud engine's decision per transaction"""
    __tablename__ = "fraud_analysis"
    
    transaction_id = Column(String, primary_key=True)    # FK to transactions
    score = Column(Float, nullable=False)                # 0.0–1.0
    decision = Column(String, nullable=False)           # "approved", "flagged", "blocked"
    reasons = Column(Text, nullable=False)              # Comma-joined rule names
    explanation = Column(Text, nullable=True)           # Claude explanation
    created_at = Column(DateTime, default=datetime.utcnow)

class VerificationEventRow(Base):
    """Audit table: OTP verification attempts"""
    __tablename__ = "verification_events"
    
    id = Column(String, primary_key=True)               # UUID of the attempt
    transaction_id = Column(String, index=True, nullable=False)
    success = Column(Boolean, nullable=False)           # Did it match?
    attempted_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    """Create all tables if they don't exist"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """FastAPI dependency: yield a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### `app/fraud_engine.py` — Scoring & Decision Logic
```python
from datetime import datetime
from app.config import settings
from app.models import Decision, Transaction

# Rule weights (sum to 1.0)
RULE_WEIGHT_LARGE_AMOUNT = 0.4
RULE_WEIGHT_NEW_DEVICE = 0.3
RULE_WEIGHT_NIGHT_TXN = 0.2
RULE_WEIGHT_ROUND_AMOUNT = 0.1

def _is_night_transaction(ts: datetime) -> bool:
    """Check if transaction occurred during night hours"""
    return settings.fraud_night_start_hour <= ts.hour < settings.fraud_night_end_hour

def _is_suspiciously_round(amount: float) -> bool:
    """Exact multiples of 1000 >= 5000 are suspicious (e.g., 50000.00)"""
    return amount % 1000 == 0 and amount >= 5000

def score_transaction(txn: Transaction) -> tuple[float, list[str]]:
    """
    Returns: (score 0.0–1.0, list of reasons)
    
    Each rule independently adds to score. No interactions.
    Score is capped at 1.0.
    """
    score = 0.0
    reasons: list[str] = []

    # Rule 1: Large amount (> 5x user average)
    if txn.user_avg_transaction_amount > 0:
        multiplier = txn.amount / txn.user_avg_transaction_amount
        if multiplier >= settings.fraud_amount_multiplier:
            score += RULE_WEIGHT_LARGE_AMOUNT
            reasons.append(f"amount is {multiplier:.1f}x user's average")

    # Rule 2: New device
    if txn.is_new_device:
        score += RULE_WEIGHT_NEW_DEVICE
        reasons.append("transaction from a new/unrecognized device")

    # Rule 3: Night transaction (0:00–5:00)
    if _is_night_transaction(txn.timestamp):
        score += RULE_WEIGHT_NIGHT_TXN
        reasons.append(
            f"occurred at {txn.timestamp.strftime('%H:%M')} "
            f"(outside {settings.fraud_night_start_hour}:00-{settings.fraud_night_end_hour}:00 window)"
        )

    # Rule 4: Suspiciously round amount
    if _is_suspiciously_round(txn.amount):
        score += RULE_WEIGHT_ROUND_AMOUNT
        reasons.append("suspiciously round transaction amount")

    return min(score, 1.0), reasons  # Cap at 1.0

def decide(score: float) -> Decision:
    """Map score to decision threshold"""
    if score >= 0.6:
        return Decision.BLOCKED     # Too risky
    if score >= 0.3:
        return Decision.FLAGGED     # Suspicious, needs OTP
    return Decision.APPROVED        # Safe
```

---

### `app/kafka_producer.py` — Publish Transactions
```python
import json
from kafka import KafkaProducer
from app.config import settings

# Global producer instance
producer = KafkaProducer(
    bootstrap_servers=settings.kafka_bootstrap_servers,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),  # JSON→bytes
)

def publish_transaction(txn_dict: dict) -> None:
    """
    Publish transaction to Kafka "raw-transactions" topic.
    Called by routes.py after API validation.
    
    Arg: txn_dict — serialized Transaction object (dict)
    """
    producer.send("raw-transactions", value=txn_dict)
    # NOTE: Should call producer.flush() here to ensure send before process exit
```

---

### `app/kafka_consumer.py` — Process & Score Transactions
```python
import json
import uuid
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from app.config import settings
from app.models import Decision, Transaction
from app.fraud_engine import score_transaction, decide
from app.claude_reasoning import explain_flagged_transaction
from app.redis_client import generate_and_store_otp
from app.db import SessionLocal, TransactionRow, FraudAnalysisRow, VerificationEventRow, init_db

OUTPUT_TOPICS = {
    Decision.APPROVED: "approved-transactions",
    Decision.FLAGGED: "flagged-transactions",
    Decision.BLOCKED: "blocked-transactions",
}

def process_message(txn_dict: dict, producer: KafkaProducer) -> None:
    """
    Main processing function. Called for each message from Kafka.
    
    Steps:
    1. Deserialize and score transaction
    2. Generate OTP if flagged/blocked
    3. Get Claude explanation if needed
    4. Store in database
    5. Publish decision to output topic
    """
    
    # Step 1: Parse and score
    txn = Transaction(**txn_dict)
    score, reasons = score_transaction(txn)
    decision = decide(score)

    # Step 2: Get explanation (if needed) and OTP (if flagged)
    explanation = None
    if decision in (Decision.FLAGGED, Decision.BLOCKED):
        explanation = explain_flagged_transaction(txn, reasons, score)
        if decision == Decision.FLAGGED:
            generate_and_store_otp(txn.transaction_id)

    # Step 3: Store in database
    db = SessionLocal()
    try:
        # Insert original transaction
        db.add(TransactionRow(
            transaction_id=txn.transaction_id,
            user_id=txn.user_id,
            amount=txn.amount,
            merchant=txn.merchant,
            device_id=txn.device_id,
            is_new_device=txn.is_new_device,
            timestamp=txn.timestamp,
        ))
        
        # Insert fraud verdict
        db.add(FraudAnalysisRow(
            transaction_id=txn.transaction_id,
            score=score,
            decision=decision.value,
            reasons=", ".join(reasons) if reasons else "none",
            explanation=explanation,
        ))
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error processing transaction {txn.transaction_id}: {e}")
        return
    finally:
        db.close()

    # Step 4: Publish decision
    producer.send(OUTPUT_TOPICS[decision], value={
        "transaction_id": txn.transaction_id,
        "decision": decision.value,
        "score": score,
    })
    
    # Step 5: Log
    print(f"[{datetime.utcnow().isoformat()}] {txn.transaction_id} -> {decision.value} (score={score:.2f})")

def run():
    """
    Main consumer loop. Run as: `python -m app.kafka_consumer`
    
    Reads from raw-transactions indefinitely.
    """
    init_db()

    consumer = KafkaConsumer(
        "raw-transactions",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",  # Skip old messages on first run
        group_id="fraud-engine-workers",
    )
    
    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    print("Consumer started, listening on raw-transactions...")
    try:
        for message in consumer:
            process_message(message.value, producer)
    except KeyboardInterrupt:
        print("Shutting down consumer...")
    finally:
        consumer.close()
        producer.close()

if __name__ == "__main__":
    run()
```

---

### `app/redis_client.py` — OTP Storage & Verification
```python
import random
import redis
from app.config import settings

# Global Redis connection
r = redis.from_url(settings.redis_url, decode_responses=True)

def _otp_key(transaction_id: str) -> str:
    """Redis key for OTP code"""
    return f"otp:{transaction_id}"

def _attempts_key(transaction_id: str) -> str:
    """Redis key for attempt counter"""
    return f"otp_attempts:{transaction_id}"

def generate_and_store_otp(transaction_id: str) -> str:
    """
    Generate 6-digit OTP and store in Redis with TTL.
    Called by kafka_consumer when decision is FLAGGED.
    
    Returns: OTP code (as string, e.g., "034782")
    """
    code = f"{random.randint(0, 999999):06d}"
    r.setex(_otp_key(transaction_id), settings.otp_ttl_seconds, code)
    return code

def verify_otp(transaction_id: str, submitted_code: str) -> tuple[bool, str]:
    """
    Verify submitted OTP against stored code.
    Implements rate limiting and expiry checks.
    
    Args:
        transaction_id: Transaction being verified
        submitted_code: User-submitted code
    
    Returns:
        (success: bool, message: str)
    """
    attempts_key = _attempts_key(transaction_id)
    attempts = int(r.get(attempts_key) or 0)

    # Check rate limit
    if attempts >= settings.otp_max_attempts:
        return False, "Too many attempts. Transaction blocked."

    # Check if OTP still exists (not expired)
    stored_code = r.get(_otp_key(transaction_id))
    if stored_code is None:
        return False, "OTP expired or never issued. Request a new one."

    # Increment attempt counter
    r.incr(attempts_key)
    r.expire(attempts_key, settings.otp_ttl_seconds)

    # Compare codes
    if submitted_code == stored_code:
        r.delete(_otp_key(transaction_id))
        return True, "Verified successfully."

    # Count remaining attempts
    remaining = settings.otp_max_attempts - (attempts + 1)
    return False, f"Incorrect code. {remaining} attempt(s) remaining."
```

---

### `app/claude_reasoning.py` — AI Explanations
```python
from app.models import Transaction

def explain_flagged_transaction(txn: Transaction, reasons: list[str], score: float) -> str:
    """
    Generate human-readable explanation for flagged/blocked transaction.
    
    Current: Template-based (Claude integration disabled due to SDK issues)
    Future: Call Anthropic API for AI-generated explanations
    
    Args:
        txn: The transaction object
        reasons: List of rule triggers (e.g., ["amount 8.2x average", "new device"])
        score: Fraud score (0.0–1.0)
    
    Returns:
        Explanation string
    """
    return f"Transaction flagged with risk score {score:.2f}. Triggered rules: {', '.join(reasons)}"
```

---

### `docker-compose.yml` — Infrastructure
```yaml
services:
  # Message broker (required by Kafka)
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181  # Zookeeper port
    ports:
      - "2181:2181"

  # Event streaming platform (async message queue)
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"  # Broker port
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  # Database (permanent audit trail)
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: securepay
      POSTGRES_PASSWORD: securepay
      POSTGRES_DB: securepayai
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data  # Persist data

  # Cache (ephemeral OTP storage)
  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  pgdata:  # PostgreSQL data persistence
```

**To Start All Services:**
```bash
docker-compose up -d
```

---

## Execution Flow Examples

### Example 1: Normal Transaction (Approved)

**Timeline:**
```
Time  Actor                  Action
────  ─────────────────────  ────────────────────────────────────
T0    Client                 POST /transaction
                             {user_id: "user-1", amount: 100, device_id: "d1"}

T1    FastAPI               - Validate input
                             - Generate UUID: "tx-001"
                             - Generate timestamp: 2026-08-23 14:00:00
                             - Publish to Kafka: raw-transactions

T2    Client                 ✓ Response 200 (tx-001, status=submitted)

T3    Kafka Consumer        - Read message from raw-transactions
                             - Parse Transaction
                             - Score: 0.0 (no rules trigger)
                             - Decide: APPROVED
                             - Save to postgres.transactions
                             - Save to postgres.fraud_analysis (score=0.0)
                             - Publish to approved-transactions

T4    Database              ✓ New rows inserted
                             transactions[tx-001]
                             fraud_analysis[tx-001, score=0.0, APPROVED]

T5    Kafka                 ✓ Decision published
                             {tx-001, APPROVED, score=0.0}
```

---

### Example 2: Flagged Transaction (OTP Required)

**Timeline:**
```
Time  Actor                  Action
────  ─────────────────────  ────────────────────────────────────
T0    Client                 POST /transaction
                             {user_id: "user-1", amount: 5000, device_id: "new-device", is_new_device: true}

T1    FastAPI               - Validate input
                             - Generate UUID: "tx-002"
                             - Publish to Kafka

T2    Kafka Consumer        - Score: 0.4 (large amount) + 0.3 (new device) = 0.7
                             - Decide: BLOCKED (0.7 >= 0.6)
                             - Generate OTP via Redis: "634891"
                             - Get Claude explanation
                             - Save to postgres
                             - Publish to blocked-transactions

T3    Redis                 SET otp:tx-002 = "634891" (TTL: 300s)

T4    Database              ✓ Inserted
                             fraud_analysis[tx-002, score=0.7, BLOCKED, reasons="amount 5x, new device", explanation="..."]

T5    Client (receives       - Prompt: "Unusual activity detected. Enter OTP sent to your phone."
        out-of-band)         - SMS arrives: "Your verification code is 634891"

T6    Client                 POST /verify-otp
                             {transaction_id: "tx-002", otp_code: "634891"}

T7    FastAPI               - Call redis_client.verify_otp(tx-002, "634891")
                             - Fetch from Redis: stored = "634891"
                             - Compare: stored == submitted ✓
                             - Delete redis key
                             - Return success

T8    Client                 ✓ Response 200 (verified)
                             Transaction approved after verification
```

---

### Example 3: Brute-force OTP Attack (Rate Limiting)

**Timeline:**
```
Time  Actor                  Action
────  ────────────────────────────────────
T0    Attacker               POST /verify-otp {tx-002, otp: "000000"}
T1    FastAPI               - Verify: incorrect
                             - Increment otp_attempts:tx-002 to 1
                             - Response: "Incorrect. 2 remaining."

T2    Attacker               POST /verify-otp {tx-002, otp: "111111"}
T3    FastAPI               - Verify: incorrect
                             - Increment otp_attempts:tx-002 to 2
                             - Response: "Incorrect. 1 remaining."

T4    Attacker               POST /verify-otp {tx-002, otp: "222222"}
T5    FastAPI               - Verify: incorrect
                             - Increment otp_attempts:tx-002 to 3
                             - Response: "Incorrect. 0 remaining."

T6    Attacker               POST /verify-otp {tx-002, otp: "634891"}
T7    FastAPI               - Check attempts: 3 >= 3 ✗
                             - Response: 400 "Too many attempts. Transaction blocked."
                             - Attacker locked out; must wait 300s or request new OTP
```

---

### Example 4: Two-Process Architecture (Scaling)

**Process 1: FastAPI (Scalable)**
```bash
# Terminal 1
$ uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
# Can spin up 4+ workers to handle incoming requests
```

**Process 2: Kafka Consumer (Independent Scaling)**
```bash
# Terminal 2
$ python -m app.kafka_consumer
# Can spin up multiple consumer processes, each handles messages

# Terminal 3
$ python -m app.kafka_consumer
# Messages auto-distributed across workers (Kafka partition assignment)
```

**Benefit:** If Kafka falls behind, API keeps accepting transactions. If API is down, Kafka consumer processes backlog once it's back.

---

## Common Queries & Debugging

### Database Queries

**Find all transactions by user:**
```sql
SELECT * FROM transactions WHERE user_id = 'user-123' ORDER BY timestamp DESC;
```

**Find recent flagged/blocked transactions:**
```sql
SELECT t.*, f.* 
FROM transactions t
JOIN fraud_analysis f ON t.transaction_id = f.transaction_id
WHERE f.decision IN ('flagged', 'blocked')
ORDER BY f.created_at DESC
LIMIT 10;
```

**Average fraud score by merchant:**
```sql
SELECT t.merchant, AVG(f.score) as avg_score, COUNT(*) as count
FROM transactions t
JOIN fraud_analysis f ON t.transaction_id = f.transaction_id
GROUP BY t.merchant
ORDER BY avg_score DESC;
```

### Redis Debugging

**Check if OTP exists:**
```bash
redis-cli GET otp:tx-001
# If nil: expired or never issued
# If string: "634891"
```

**Check attempt count:**
```bash
redis-cli GET otp_attempts:tx-001
# 0, 1, 2, or 3
```

**Manually test OTP:**
```bash
redis-cli SETEX otp:test-tx 300 "123456"
redis-cli GET otp:test-tx
# => "123456"
```

### Kafka Debugging

**List topics:**
```bash
docker exec -it <kafka-container> kafka-topics --list --bootstrap-server localhost:9092
```

**Read messages from topic:**
```bash
docker exec -it <kafka-container> kafka-console-consumer --topic raw-transactions --from-beginning --bootstrap-server localhost:9092
```

---

## Deployment Checklist

- [ ] Set strong DATABASE_URL credentials (not "securepay/securepay")
- [ ] Set real ANTHROPIC_API_KEY
- [ ] Change OTP_MAX_ATTEMPTS to 3–5 (don't allow unlimited)
- [ ] Change FRAUD_NIGHT_START_HOUR / FRAUD_NIGHT_END_HOUR to match your region
- [ ] Enable Kafka auto-offset-reset to "earliest" (don't lose transactions)
- [ ] Add producer.flush() in kafka_producer.py
- [ ] Add try/except around Claude API calls
- [ ] Add healthcheck for all services (docker-compose)
- [ ] Set up monitoring for Kafka lag
- [ ] Run tests: `pytest tests/`
- [ ] Load test with multiple concurrent transactions
- [ ] Document OTP delivery mechanism (SMS/email)

---

## Summary

This system is a **two-process fraud detection pipeline**:

1. **API Process** — accepts transactions, publishes to Kafka, stays responsive
2. **Consumer Process** — scores transactions, stores results, generates OTPs, calls Claude

**Key Strengths:**
- Explainable decisions (rules, not black box)
- Scalable (API and consumer independent)
- Resilient (async, Kafka queue buffers load)
- Auditable (all decisions in PostgreSQL)
- Cost-optimized (Claude only for risky cases)

**You should now be able to explain every line to another engineer.**

