"""
Script load testing menggunakan Locust.

Cara menjalankan:
1. Pastikan backend uvicorn sedang berjalan (misal: localhost:8000)
2. Jalankan perintah: locust -f backend/scripts/load_test.py
3. Buka browser di http://localhost:8089 untuk melihat antarmuka Locust
"""

import json
import uuid

from locust import HttpUser, between, task


class EnterpriseMindUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def test_query_endpoint(self):
        """Simulasi user mengirimkan kueri ke sistem multi-agent"""
        payload = {
            "query": "Apa itu Supabase?",
            "session_id": str(uuid.uuid4()),
        }
        headers = {"Content-Type": "application/json"}
        self.client.post(
            "/api/query",
            data=json.dumps(payload),
            headers=headers,
            timeout=20,
        )

    @task(1)
    def test_health_check(self):
        """Simulasi pengecekan status server"""
        self.client.get("/health")

    @task(1)
    def test_documents_list(self):
        """Simulasi user membuka daftar dokumen"""
        self.client.get("/api/documents")

    @task(1)
    def test_metrics(self):
        """Simulasi user membuka dashboard metrik"""
        self.client.get("/api/metrics")
