from .analyzers.alienvault_otx import AlienVaultOTXAnalyzer
from .analyzers.abuseipdb import AbuseIPDBAnalyzer
from .analyzers.ipinfo import IPInfoAnalyzer
from .schemas import AnalyzerResult

async def enrich_ioc(ioc: str) -> list[AnalyzerResult]:
    """
    Ejecuta todos los analizadores sobre un IoC y devuelve la lista de resultados estandarizados.
    """
    analyzers = [
        AlienVaultOTXAnalyzer(ioc),
        AbuseIPDBAnalyzer(ioc),
        IPInfoAnalyzer(ioc)
    ]

    results = []
    for analyzer in analyzers:
        result = await analyzer.analyze()
        results.append(AnalyzerResult(**result))

    return results
