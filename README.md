# SecurePayAI

Real-time fraud detection pipeline. A transaction is scored by a
rule-based fraud engine as it streams through Kafka; flagged
transactions trigger OTP-based verification instead of blocking
every transaction equally.

## Stack
- **FastAPI** — API layer, publishes transactions to Kafka
- **Kafka** — stream processing (`raw-transactions` → `approved` / `flagged` / `blocked`)
- **PostgreSQL** — transaction + fraud analysis history
- **Redis** — OTP TTL + attempt rate-limiting
- **Claude API** — plain-English explanation for flagged/blocked transactions

## Why rule-based, not ML, for v1
Every decision is traceable to a specific rule (amount multiplier,
new device, night transaction, round amount). That's a defensible
architecture for a judged submission — you can explain exactly why
any transaction was scored the way it was. Swapping in a trained
model later is a contained change: `fraud_engine.score_transaction()`
is the only function that needs to change.

## Run it

```bash
# 1. Start infra
docker compose up -d

# 2. Install deps
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY

# 3. Terminal A - API
uvicorn app.main:app --reload

# 4. Terminal B - fraud engine worker
python -m app.kafka_consumer

# 5. Test it
curl -X POST localhost:8000/transaction -H "Content-Type: application/json" -d '{
  "user_id": "u1", "amount": 5000, "merchant": "Test Store",
  "device_id": "d1", "is_new_device": true, "user_avg_transaction_amount": 500
}'
```

Watch Terminal B — it prints the decision as it's made. Check
Postgres `fraud_analysis` table for the stored score and Claude's
explanation.

## Tests

```bash
pytest tests/
```

These run without Kafka/Postgres/Redis — use them as the fallback
demo if live infra has issues during judging.
