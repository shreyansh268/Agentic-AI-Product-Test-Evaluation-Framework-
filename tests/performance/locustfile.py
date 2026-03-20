# tests/performance/locustfile.py
"""
Locust load test — Financial AI Application
Scenarios: Single user latency SLA | 10-user concurrent multi-country | Agent throughput

Run locally:
  locust -f tests/performance/locustfile.py --host http://localhost:1234/v1
  locust -f tests/performance/locustfile.py --headless -u 1 -r 1 --run-time 60s --host $BASE_URL

CI: invoked by GitHub Actions job 'performance'
"""

import json
import time
import random
from locust import HttpUser, task, between, events
from config.settings import GATES

# ── Sample query payloads per country ─────────────────
COUNTRY_QUERIES = {
    "UK":  "What is the corporate tax rate for UK financial services companies?",
    "DE":  "What are the VAT regulations for digital services in Germany?",
    "FR":  "What are the French tax obligations for cross-border mergers?",
    "US":  "What SEC filing requirements apply to mid-cap investment firms?",
    "SG":  "What are GST rules for Singapore fintech companies?",
    "AU":  "What are ASIC compliance requirements for Australian fund managers?",
    "JP":  "What are Japanese FSA regulations for foreign asset managers?",
    "IN":  "What are SEBI regulations for foreign portfolio investors in India?",
    "CA":  "What are CRA tax obligations for Canadian holding companies?",
    "NL":  "What are Netherlands thin capitalisation rules for multinationals?",
}

COUNTRIES = list(COUNTRY_QUERIES.keys())


class FinancialAIUser(HttpUser):
    """Simulates a financial analyst querying regulations."""
    wait_time = between(1, 3)
    country = None

    def on_start(self):
        """Assign a random country to each simulated user."""
        self.country = random.choice(COUNTRIES)
        self.client.headers.update({"Authorization": f"Bearer {__import__('os').getenv('API_KEY', 'dev')}"})

    @task(5)
    def query_regulation(self):
        """Primary task: submit a regulatory query. Measures E2E response time."""
        payload = {
            "query":   COUNTRY_QUERIES[self.country],
            "country": self.country,
        }
        start = time.time()
        with self.client.post(
            "/api/v1/query",
            json=payload,
            name="POST /api/v1/query",
            catch_response=True
        ) as resp:
            elapsed_ms = (time.time() - start) * 1000
            if resp.status_code != 200:
                resp.failure(f"Non-200 status: {resp.status_code}")
            elif elapsed_ms > GATES["latency_p95_ms"] * 1.5:   # Hard fail at 1.5× gate
                resp.failure(f"Response too slow: {elapsed_ms:.0f}ms > {GATES['latency_p95_ms'] * 1.5:.0f}ms hard limit")
            else:
                body = resp.json()
                # Validate response structure
                if "answer" not in body or "sources" not in body:
                    resp.failure("Missing required fields in response")
                elif not body.get("sources"):
                    resp.failure("Empty sources list — possible hallucination, no citations")
                else:
                    resp.success()

    @task(2)
    def query_different_country(self):
        """Simulate user switching country context — tests session isolation."""
        other_country = random.choice([c for c in COUNTRIES if c != self.country])
        payload = {
            "query":   COUNTRY_QUERIES[other_country],
            "country": other_country,
        }
        with self.client.post(
            "/api/v1/query",
            json=payload,
            name="POST /api/v1/query [country-switch]",
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                body = resp.json()
                # CRITICAL: ensure country in response matches what we asked for
                if body.get("country") != other_country:
                    resp.failure(f"Context mixing! Asked {other_country}, got {body.get('country')}")
                else:
                    resp.success()
            else:
                resp.failure(f"Non-200: {resp.status_code}")

    @task(1)
    def health_check(self):
        """Lightweight health ping — ensures app stays up during load."""
        with self.client.get("/health", name="GET /health", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Health check failed: {resp.status_code}")
            else:
                resp.success()


class TaxFilingAgentUser(HttpUser):
    """Simulates concurrent tax filing agent sessions — for throughput tests."""
    wait_time = between(2, 5)
    # Separate user class with lower weight — typically 5 concurrent agent users

    @task
    def run_agent_filing(self):
        """Submit a tax filing agent task and wait for completion."""
        # TODO: Replace with real agent payload from datasets/golden/agent_scenarios.json
        payload = {
            "task":       "tax_filing",
            "entity_id":  f"test-entity-{random.randint(1000, 9999)}",
            "tax_year":   2024,
            "country":    random.choice(["UK", "DE", "US"]),
            "dry_run":    True,    # Safety: never submit real filings in tests
        }
        with self.client.post(
            "/api/v1/agent/run",
            json=payload,
            name="POST /api/v1/agent/run [tax-filing]",
            catch_response=True,
            timeout=60,
        ) as resp:
            if resp.status_code == 200:
                body = resp.json()
                if body.get("status") not in ("completed", "awaiting_approval"):
                    resp.failure(f"Unexpected agent status: {body.get('status')}")
                else:
                    resp.success()
            else:
                resp.failure(f"Agent run failed: {resp.status_code}")


# ── Custom event hooks for gate reporting ─────────────
@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Print gate summary on test completion."""
    stats = environment.stats.total
    p95 = stats.get_response_time_percentile(0.95)
    fail_ratio = stats.fail_ratio * 100
    print("\n" + "═" * 60)
    print("LOCUST QUALITY GATE SUMMARY")
    print("═" * 60)
    print(f"  P95 Response Time : {p95:.0f}ms  (gate: {GATES['latency_p95_ms']}ms)")
    print(f"  Error Rate        : {fail_ratio:.2f}%   (gate: < 1%)")
    print(f"  Total Requests    : {stats.num_requests}")
    print(f"  Total Failures    : {stats.num_failures}")
    if p95 > GATES["latency_p95_ms"] or fail_ratio > 1.0:
        print("\n  ❌ ONE OR MORE GATES FAILED — CHECK PIPELINE")
        environment.process_exit_code = 1
    else:
        print("\n  ✅ ALL LOCUST GATES PASSED")
    print("═" * 60 + "\n")
