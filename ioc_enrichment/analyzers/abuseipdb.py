import os
from .base import Analyzer
import httpx

API_KEY = os.environ.get("ABUSEIPDB_API_KEY")

class AbuseIPDBAnalyzer(Analyzer):
    async def analyze(self):
        try:
            url = f"https://api.abuseipdb.com/api/v2/check?ipAddress={self.ioc}&maxAgeInDays=90"
            headers = {
                "Accept": "application/json",
                "Key": API_KEY
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            summary = data["data"]
            return {
                "source": "AbuseIPDB",
                "summary": f"{summary['abuseConfidenceScore']}% confianza en abuso",
                "full": summary
            }
        except Exception as e:
            return {"source": "AbuseIPDB", "error": str(e)}
