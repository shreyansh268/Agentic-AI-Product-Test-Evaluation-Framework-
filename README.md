# Financial Advisory AI — Test Framework

> **QE Artefact** | AI SDETs Hub · Innovate QA
> Coverage: UI · API · RAG · Agentic AI · Security · Performance · Observability

---

## Architecture

```
financial-ai-test-framework/
├── features/
│   ├── financial_ai.feature         # All BDD scenarios (36 scenarios, 4 Use Cases)
│   └── steps/
│       └── financial_ai_steps.py    # Step definitions (hollow → implement per TC)
├── tests/
│   ├── ui/                          # Selenium Page Object Models
│   ├── api/                         # Python requests API tests
│   ├── rag/                         # RAGAS + DeepEval eval runners
│   ├── agent/                       # DeepEval agent trajectory tests
│   ├── security/
│   │   └── run_garak.py             # Garak probe runner + ASR gate
│   └── performance/
│       └── locustfile.py            # Locust load scenarios
├── config/
│   └── settings.py                  # Central config (local/CI switch via ENV var)
├── datasets/
│   ├── golden/                      # SME-verified Q&A, agent scenarios, policy sets
│   ├── adversarial/                 # Prompt injection payloads, hallucination triggers
│   └── baselines/                   # GuideLLM performance baselines
├── utils/
│   └── validate_gates.py            # Quality gate validator (used by CI/CD)
├── reports/                         # Generated test reports (gitignored)
├── .github/
│   └── workflows/
│       └── financial-ai-eval-pipeline.yml  # 8-job parallel CI/CD pipeline
└── requirements.txt
```

---

## Quick Start — Local

```bash
# 1. Clone and install
git clone <repo>
cd financial-ai-test-framework
pip install -r requirements.txt

# 2. Configure (copy and edit)
cp .env.example .env
# Set BASE_URL, API_KEY, PHOENIX_HOST

# 3. Run smoke tests first
behave features/financial_ai.feature --tags @smoke

# 4. Run by layer
behave features/financial_ai.feature --tags @rag
behave features/financial_ai.feature --tags @agent
behave features/financial_ai.feature --tags @security
behave features/financial_ai.feature --tags @performance
behave features/financial_ai.feature --tags @observability
behave features/financial_ai.feature --tags @ui

# 5. Run load tests
locust -f tests/performance/locustfile.py --host http://localhost:1234/v1
```

---

## Quick Start — CI/CD (GitHub Actions)

Set these repository secrets:
- `APP_BASE_URL` — deployed app URL
- `API_KEY` — test API key
- `PHOENIX_HOST` — Arize Phoenix instance URL

Pipeline triggers automatically on:
- **PR to main/develop** → Smoke + RAG + Agent + Security + UI + Observability
- **Push to main** → Same
- **Nightly 01:00 UTC** → All jobs including Performance

---

## Quality Gates

| Suite | Gate | Threshold |
|---|---|---|
| RAG | RAGAS Faithfulness | ≥ 0.90 |
| RAG | RAGAS Context Recall | ≥ 0.85 |
| RAG | RAGAS Answer Relevancy | ≥ 0.80 |
| Agent | Trajectory Correctness | Exact match |
| Security | Garak ASR | ≤ 0.05 |
| Performance | P95 Latency (1 user) | ≤ 5000ms |
| Performance | P95 Latency (10 users) | ≤ 8000ms |
| Performance | Error Rate | < 1% |
| Performance | TTFT | ≤ 1500ms |

Override gates via environment variables (see `config/settings.py`).

---

## Dataset Strategy

| Dataset | Owner | Purpose |
|---|---|---|
| `datasets/golden/` | SMEs + Domain Experts | Ground truth for RAG and Agent evals |
| `datasets/adversarial/` | QA Team | Prompt injection, jailbreak, edge cases |
| `datasets/baselines/` | QA Team | GuideLLM performance baselines per model |
| Silver synthetic | QA Team (LLM-assisted) | Scale coverage from golden set |
| Production | Real user traffic (anonymised) | Regression monitoring |

---

## Test Attributes (Behave Tags)

```
@smoke          → Critical path — runs first, blocks all other jobs
@ui             → Selenium UI tests
@api            → REST API contract tests
@rag            → RAG pipeline eval (RAGAS + DeepEval)
@agent          → Agentic AI trajectory, HITL, memory tests
@security       → Garak, PyRIT, injection, PII tests
@performance    → Locust load + GuideLLM benchmark
@observability  → Arize Phoenix span and trace completeness
@functional     → General functional scenarios
```

---

## Implementing Hollow Steps

Each step raises `NotImplementedError` with an implementation hint:

```python
@then("the RAGAS faithfulness score is greater than or equal to 0.90")
def step_ragas_faithfulness(context):
    # TODO: from ragas.metrics import faithfulness
    #       score = evaluate(context.ragas_inputs, metrics=[faithfulness])
    #       assert score["faithfulness"] >= GATES["ragas_faithfulness"]
    raise NotImplementedError("TC-RAG-001: ...")
```

Replace the `raise NotImplementedError(...)` with the real implementation.
The `# TODO` comment above it shows exactly what to implement.

---
