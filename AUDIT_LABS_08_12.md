# Portfolio Labs 08–12 — Full Repository Audit

**Audit date:** 24 October 2026  
**Repository:** SkynetAI-Labs/Revolut-fintech-api-security-case-study  
**Reviewed baseline:** [`1e3a3a2b822aadd50b8a9de139f5635513b9691b`](https://github.com/SkynetAI-Labs/Revolut-fintech-api-security-case-study/tree/1e3a3a2b822aadd50b8a9de139f5635513b9691b)

Labs 08–12 are five phases of one independent educational repository, corresponding to internal Labs 1–5. Test counts describe one combined suite. This audit covers all application modules, tests, dependency manifests, container/CI configuration, the root README and all 33 GTM files. It is not an external penetration test, production certification or assessment of Revolut's systems. No real banking data, funds, outreach or account applications were used.

## Evidence and verification

The baseline [workflow 39882693931](https://github.com/SkynetAI-Labs/Revolut-fintech-api-security-case-study/actions/runs/39882693931), run on 23 October 2026, reported **200 tests passed, 10 warnings**, no Bandit issues, no known pip-audit vulnerabilities, no Gitleaks findings and a passing configured Trivy HIGH/CRITICAL gate. Job logs were inspected. These are point-in-time results, not guarantees about future builds.

This audit adds **31 regression cases**: 27 invalid input combinations and four stored-balance/overflow boundary cases. Targeted standard-library checks reproduced the two defects before remediation and confirmed rejection after remediation. The full resulting suite and security checks are validated by the corresponding pull-request/main workflow runs; consult those runs for the final result rather than treating the historical 200 count as current. Local full-suite execution was unavailable in this session's Python environment, which lacks the application dependencies; no existing private environment or database was modified.

Local structural checks parsed all Python files, resolved relative Markdown links, checked 25 ordered unique source IDs and recalculated headline budget, funnel and segment scores. Original source access dates and historical milestones were retained.

## Lab 08 — Business Banking API

**Reviewed:** app/database.py, models.py, schemas.py, main.py, payments.py and API/payment/integrity tests.

Confirmed controls include parameterised queries, foreign-key enforcement, non-negative balances, transaction constraints, explicit `BEGIN IMMEDIATE`, rollback on failure and atomic payment/alert storage. Payment execution remains an internal Python helper; there is no public payment HTTP endpoint.

### Fixed: permissive integer inputs

The previous helper accepted `transfer_funds(True, 2, True)`, moving one penny from account 1. Python booleans are integer subclasses. Integer annotations alone did not enforce the contract. Account IDs and pence amounts now require exact positive integers within SQLite's signed 64-bit range, before a database connection is opened. Booleans, fractional numbers, strings, nulls, nonpositive values and oversized integers are rejected. The regression matrix covers all three arguments.

### Fixed: recipient balance overflow

A recipient balance of `9223372036854775807` plus one penny previously committed as floating-point storage, losing the integer-money invariant. The helper now checks both stored balances are nonnegative SQLite-range integers and rejects recipient overflow before updates. Tests cover unchanged ledger on rejection, a successful transfer reaching the exact integer limit and rejection of non-integer stored balances.

**Remaining recommendations:**

- **P2:** Add bounded pagination to customer/account/transaction history routes; current transaction retrieval can return an unbounded list.
- **P2:** Add transfer idempotency before exposing payment initiation to retrying clients. Do not add a public payment endpoint without caller authorization checks.
- **P2:** Use reviewed migrations and stronger schema typing if the prototype evolves; service validation does not prevent direct database edits.
- **P2:** Exercise concurrent transfers and rollback under realistic load before making broader financial-integrity claims.

## Lab 09 — Authentication and API Security

**Reviewed:** auth.py, config.py, dependencies.py, users.py, security.py, rate_limiting.py, security_headers.py, protected routes and authentication/RBAC/tenant tests.

JWT decoding uses a configured algorithm allowlist and requires expiry and subject; authenticated users are checked against the database. Customer scope is derived server-side. Administrator routes check the stored role. Password hashing uses pwdlib's recommended Argon2id implementation. Registration assigns the user role. SQL arguments are parameterised. Rate limits use remote-address keys and in-memory storage.

Public login/registration endpoints, MFA, token revocation and refresh tokens are not implemented. Internal credential helpers must not be presented as public authentication APIs.

**Remaining recommendations:**

- **P2:** Validate signing-key strength, allowed algorithm and positive token lifetime at startup. Required environment-variable presence is not a strength check.
- **P2 before deployment:** Define key rotation, revocation, secure token issuance and trusted-proxy address handling. Current in-memory IP limits are per process and not distributed abuse protection.
- **P2:** Add integration checks for response headers on error paths and an explicit TLS/deployment policy if hosted.
- **P3:** Review credential-validation and audit-log requirements before extending internal helpers into public endpoints.

No authentication or authorization bypass was demonstrated by this scoped review. That statement is limited to the code and tests examined, not a claim that no vulnerabilities exist.

## Lab 10 — Docker, GitHub Actions and DevSecOps

**Reviewed:** Dockerfile, .dockerignore, .gitignore, requirements*.txt, tests/conftest.py and .github/workflows/tests.yml, plus baseline logs.

The base image is digest-pinned; runtime dependencies use binary wheels and pip consistency checks; pip and ensurepip are removed after installation. The application runs as UID/GID 10001. The build excludes local secrets/databases. CI has read-only content permissions, disabled checkout credential persistence and a timeout. It builds and scans an image without publishing it.

**Fixed:** Both direct workflow actions are now pinned to full commit SHAs resolved from the official actions/checkout and actions/setup-python v7 references on the audit date. Scanner containers retain explicit versions and the HIGH/CRITICAL failure threshold is unchanged. No vulnerability exceptions were added.

**Remaining recommendations:**

- **P2:** Add a complete transitive dependency lock with hashes and reviewed automated updates. Direct pins are not a reproducible full lock.
- **P2:** Pin scanner container images by verified digest and retain machine-readable scan reports, resolved dependency inventory and an SBOM.
- **P2:** Separate independent checks so an early test failure cannot prevent all later security scans from running.
- **P2:** Add a scheduled scan and a full-history secrets assessment; checked-out-file scanning does not prove the Git history is clean.
- **P2:** Define durable database storage, schema initialization/readiness and backup/restore checks before hosting. The current health route does not test database readiness.
- **P3:** Address the documented Starlette and SlowAPI deprecation warnings through reviewed compatibility updates.

No new local Docker runtime check was performed in this Windows session. CI image building/scanning and historical runtime evidence are distinct.

## Lab 11 — Fraud Detection and Transaction Monitoring

**Reviewed:** monitoring.py, monitoring_rules.py, monitoring_schema.py, monitoring_review.py, monitoring_routes.py, payment integration and all monitoring tests.

The four rule thresholds, GBP-only amount rules, inclusive UTC windows, equal-time transaction ordering and sender scoping match the documentation. Alert ownership is derived from the sender's customer. The unique transaction/rule constraint prevents duplicate alerts. Historical replay requires a caller-owned transaction and uses an upper-ID boundary. Review decisions require administrator access and conditionally update only open alerts inside a write transaction; original detection evidence is preserved.

Rule matches are review alerts, not confirmed fraud, and do not themselves reject payments. Monitoring exceptions do roll back payments. The payment-integrity fixes in Lab 08 also protect this integrated phase.

**Remaining recommendations:**

- **P2:** Bound per-assessment history reads and add appropriate indexes with normalized timestamp storage. A bounded replay batch does not bound the sender-history read for each transaction.
- **P2:** Define malformed historical-data handling and monitoring failure recovery; one bad historical timestamp can interrupt assessment/payment completion.
- **P2:** Decide the intended payment/monitoring availability trade-off and test it under failure/load conditions.
- **P2:** Preserve historical account ownership and currency snapshots if historical reassessment must reflect the original transaction context.
- **P3:** Add an append-only review-event history if decisions need operational traceability or reopening. Current decisions are final and store only final-review metadata.

No claim of calibrated fraud accuracy, production monitoring or automated containment is made.

## Lab 12 — Market Intelligence and GTM Strategy

**Reviewed:** all 33 GTM documents/CSV files, 25 primary-source URLs, source/claim consistency, pricing assumptions, competitor scope, segment scoring, resource/funnel calculations, messaging and hypothetical pilot design. All 25 source URLs were reopened on the audit date; key numerical, eligibility and pricing claims were checked against the relevant sections. This is desk research, not customer validation or a regulated suitability assessment.

### Confirmed and recalculated

- DBT 2025 Table C: 1,150,875 plus 220,085 equals **1,370,960** businesses in the published 1–49 size bands. This is not an eligible/reachable agency market count.
- ONS 2026: approximately **2.79 million** VAT/PAYE businesses; professional/scientific/technical share **15.3%**. Its population/period differs from DBT's baseline.
- Survey export/import/software-use observations retain the 1–249 employee scope; percentages must not be multiplied into an unsupported agency estimate.
- The current UK consolidated Revolut schedule supports the stated monthly plan basis and domestic allowance calculation; the Basic domestic example is **GBP12**, with stated exclusions. Annual equivalents are not monthly billing offers.
- Weighted segment scores recalculate to **3.80, 3.05 and 3.45**; lowering agency access/simplicity assumptions ties agencies at **3.45**.
- Resources total **75 hours**, **GBP150 cash**, **GBP2,400 economic cost** at the assumed GBP30 hourly value.
- Expected activations recalculate to **0.320 / 2.000 / 6.480**. Base cash/economic costs per expected activation are **GBP75 / GBP1,200**. These are model outputs, not measured CAC.
- The illustrative GBP840 annual subscription billings are not 90-day revenue, profit or income to SkynetAI-Labs.
- Provider eligibility, client-money restrictions, account-entity distinctions and protection qualifications remain explicit. A dated Bank of England list is not a current Financial Services Register permissions check.

### Documentation corrections

Removed stale statements that research was unstarted, pricing calculations were entirely pending or the published GTM work remained planned. Linked staged analyses to later scoring, pricing, budget and protection work. Updated the prepared portfolio-entry link to the current repository. Original source-register access dates were preserved.

### Open research requirements

- **P1 before a cost recommendation:** Obtain comparable timestamped cross-border quotes for the same receipt, conversion, supplier-payment route and funding method. Unknown charges are not zero.
- **P1 before a real pilot:** Validate customer needs, buyer access, willingness to evaluate and channel capacity. Agencies remain a provisional hypothesis.
- **P2:** Check specific applicant eligibility, current register permissions, contractual account entity, protection applicability and actual integration functions. No provider approval is implied.
- **P2:** Recheck effective dates before later use; HSBC's announced December 2026 fee changes are not current October charges.
- **P2:** Collect observed funnel denominators, time, costs, outcomes and negative findings only in a separately authorized future exercise. No outreach or expenditure was conducted here.

### Primary sources rechecked

The original [source register](docs/gtm/sources.csv) retains detailed titles, dates, claims and qualifications. Rechecks covered S001–S025: DBT/ONS market statistics and schedule; SME survey; historical FCA review; Revolut product/pricing/terms/eligibility/onboarding/transition/protection and receipt guidance; Bank of England and FSCS; Wise product/pricing/verification/integrations; Starling and HSBC product/fee information. Research scope and gaps remain as important as numerical consistency.

## Banners and publication

Five matching banners were prepared for portfolio Labs 08–12 using the built-in image-generation tool. Each visibly includes **REVOLUT BUSINESS**, SkynetAI-Labs, its correct lab number and an independent-portfolio label. They use the established purple/black/white style and phase-relevant technologies or research methods. They do not imply Revolut endorsement.

Banners are linked beside the corresponding root README sections; the Lab 12 case-study README also links its banner. GitHub profile text and pinned projects are deliberately outside this stage.

## Completion boundary

The audit covers the reviewed repository and documented evidence. Fixed defects, remaining recommendations, historical scans, new CI verification and unvalidated commercial assumptions must not be conflated. A passing workflow does not establish production readiness or commercial viability.
