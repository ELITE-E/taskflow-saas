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