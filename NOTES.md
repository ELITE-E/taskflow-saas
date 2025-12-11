                   ┌────────────────────────────────────┐
                   │            FRONTEND                │
                   │     Next.js / React (SaaS UI)      │
                   └───────────────┬────────────────────┘
                                   │
                                   │  Submit Task / Login / Billing
                                   ▼
         ┌─────────────────────────────────────────────────────────┐
         │                     DJANGO API LAYER                    │
         │                 (API v1 / API v2 support)               │
         └───────────────┬────────────────────────────────────────┘
                         │
                         │  RBAC Permission Check (Cached)
                         ▼
           ┌─────────────────────────────────────┐
           │              RBAC SERVICE           │
           │          Roles / Permissions        │
           └──────────────┬──────────────────────┘
                          │   Cache Lookup
                          ▼
                ┌──────────────────┐
                │      REDIS       │
                │ RBAC + Task Cache│
                └──────────────────┘

                          ▲
                          │ Cache Miss
                          │
         ┌────────────────┴────────────────┐
         │              Postgres           │
         │ Users, Tasks, Scores, Billing   │
         └─────────────────────────────────┘

────────────────────── ASYNC TASK FLOW (RELIABLE) ──────────────────────

Frontend → Django → Celery → Scoring Service → External AI → DB

                   ┌─────────────┐
                   │  Celery     │  (Retry, Backoff, Idempotent)
                   └──────┬──────┘
                          ▼
             ┌────────────────────────────┐
             │  Task Scoring Service      │
             │  Weighted Formula + AI API │
             └──────────────┬─────────────┘
                            ▼
                     External AI API

──────────────────────── BILLING SYSTEM (SCALABLE) ───────────────────────

Frontend → Django → Billing Service → Stripe → Webhooks → DB (Atomic)

