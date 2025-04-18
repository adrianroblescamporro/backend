# backend/ioc_enrichment/analyzers/base.py

from abc import ABC, abstractmethod

class Analyzer(ABC):
    def __init__(self, ioc: str):
        self.ioc = ioc

    @abstractmethod
    async def analyze(self) -> dict:
        """
        Ejecuta el análisis y devuelve un dict con los resultados.
        """
        pass
