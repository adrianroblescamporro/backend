import os
from .base import Analyzer
import httpx

API_KEY = os.environ.get("OTX_API_KEY")  # Reemplaza esto o cárgalo con os.environ

class AlienVaultOTXAnalyzer(Analyzer):
    async def analyze(self):
        try:
            headers = {"X-OTX-API-KEY": API_KEY}
            url = f"https://otx.alienvault.com/api/v1/indicators/IPv4/{self.ioc}/general"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            return {
                "source": "AlienVault OTX",
                "summary": f"Detectado en {data.get('pulse_info', {}).get('count', 0)} pulsos",
                "full": data
            }
        except Exception as e:
            return {"source": "AlienVault OTX", "error": str(e)}
