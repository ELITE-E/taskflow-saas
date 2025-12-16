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

--------------------------------------------------------------------------------
Component,Trigger,Action Performed,Expected Outcome
1. Login Page,User Clicks 'Submit'.,"Calls handleLogin(credentials, ...) located in auth-api.ts.",Sends credentials to the backend.
2. Django Backend (/login/),Receives POST request.,Verifies credentials (email/password). Generates access and refresh tokens.,"Returns 200 OK with access, refresh, and user data."
3. handleLogin (Frontend),Receives 200 OK response.,Saves tokens to js-cookie. Dispatches setUser(user_data) to Redux. Calls router.push('/home').,Redux state: isAuthenticated: true. Navigation initiated to /home.
4. /src/app/page.tsx,Page Load (/home) is initiated.,useAuthCheck runs first. The component conditionally renders based on Redux state.,useAuthCheck validates session; Router waits for Redux state to settle.
5. useAuthCheck.ts,Runs on new page load.,Reads tokens from cookies. Calls the protected /auth/user/ endpoint.,Confirms tokens are active and sets Redux state explicitly.
6. Axios Interceptor,Implicitly used by useAuthCheck.,"Attaches access_token to the header. If 401 occurs, it tries to refresh tokens before failing.",Ensures the session is renewed/validated seamlessly.
7. Final Redux State,After useAuthCheck returns success.,State remains isAuthenticated: true and loading: false.,Crucial: State is stable and verified.
8. /src/app/home/page.tsx,Component Renders.,Sees isAuthenticated: true and renders the dashboard UI.,User sees the content and the loop is broken.
----------------------------SHORT-CIRCUIT-PRINCIPLES----------------------
## Short-Circuiting: Fundamental Axioms

| # | Principle | Definition | Why It Exists | System Implication |
|---|----------|------------|---------------|-------------------|
| 1 | Semantic Dominance | A task maps clearly to exactly one strategic goal | AI adds no new information | Safe to skip AI |
| 2 | Pre-Weight Isolation | Short-circuiting occurs before user weights are applied | Prevents distortion from user preferences | User weights remain fully expressive |
| 3 | Outcome Invariance | Rule-based output ≈ AI output | Downstream decisions remain unchanged | Deterministic equivalence |
| 4 | Conservative Bias | When in doubt, call AI | Prevents silent misclassification | Safety over optimization |
| 5 | Binary Decision Rule | Short-c## Short-Circuiting: Threshold & Decision Rules

| Condition | Threshold | Action |
|---------|----------|--------|
| No goal match | hits == 0 | Call AI |
| Single clear goal match | hits == 1 | Short-circuit |
| Multiple goal matches | hits ≥ 2 | Call AI |
| Keyword match type | Exact inclusion only | Eligible |
| Fuzzy / partial match | Not allowed | Call AI |
| Numeric relevance threshold | Not used | Avoid drift |
| Emotional or ambiguous language | Present | Call AI |
| Any uncertainty | Present | Call AI |
ircuiting is yes/no, not probabilistic | Avoids hidden heuristics | Debuggable logic |
| 6 | Explainability First | Rule must be auditable and obvious | User trust & transparency | Predictable behavior |
| 7 | Semantic-Only Scope | Rules affect relevance only, never importance | Keeps business logic pure | No weight leakage |
| 8 | User-Invariant Semantics | Semantic meaning does not change per user | Fairness across profiles | Stable behavior |

## Short-Circuiting: Threshold & Decision Rules

| Condition | Threshold | Action |
|---------|----------|--------|
| No goal match | hits == 0 | Call AI |
| Single clear goal match | hits == 1 | Short-circuit |
| Multiple goal matches | hits ≥ 2 | Call AI |
| Keyword match type | Exact inclusion only | Eligible |
| Fuzzy / partial match | Not allowed | Call AI |
| Numeric relevance threshold | Not used | Avoid drift |
| Emotional or ambiguous language | Present | Call AI |
| Any uncertainty | Present | Call AI |

Short-circuit only when semantic relevance is unambiguous, user-invariant, and outcome-preserving.