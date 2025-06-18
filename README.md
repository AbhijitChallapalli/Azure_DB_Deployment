Block diagram for Cache:
           ┌────────────┐
           │  User      │
           └─────┬──────┘
                 │ Query (e.g., mag 2-4)
        ┌────────▼────────┐
        │ Check Redis     │
        └─────┬──────┬────┘
              │      │
        HIT ──┘      └───► MISS
       │                   │
Return Cached         Query SQL DB
  Result              Store Result in Redis
       │                   │
       └──────────┬────────┘
                  ▼
             Show Result
