import os
from .base import Analyzer
import httpx

API_TOKEN = os.environ.get("IPINFO_TOKEN")

class IPInfoAnalyzer(Analyzer):
    async def analyze(self):
        try:
            url = f"https://ipinfo.io/{self.ioc}/json?token={API_TOKEN}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            return {
                "source": "IPInfo",
                "summary": f"{data.get('org')} ({data.get('country')})",
                "full": data
            }
        except Exception as e:
            return {"source": "IPInfo", "error": str(e)}
