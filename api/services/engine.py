import logging
from typing import Any, Dict, List
from auraflux_core.engine import AurafluxEngine
from auraflux_core.core.schemas.engine import EngineConfig
from auraflux_core.core.schemas.clients import ClientConfig

from .exceptions import EngineInitializationError

logger = logging.getLogger(__name__)

class AurafluxCoreService:
    _instance = None

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.engine = AurafluxEngine(config=EngineConfig(client_config=ClientConfig(providers={})))
            self.initialized = False
            self.providers_status = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AurafluxCoreService, cls).__new__(cls)
        return cls._instance

    def initialize(self, providers: List[Dict[str, Any]]):
        """
        Initialize the core engine and handle provider credential decryption.
        providers: List of dictionaries containing ModelProvider data.
        """
        self.providers_status = []
        success_count = 0

        for provider in providers:
            provider_id = provider.get('id')
            name = provider.get('name')

            try:
                # Simulate core engine initialization
                self.providers_status.append({
                    "provider_id": provider_id,
                    "name": name,
                    "status": "ACTIVE"
                })
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to process provider {provider_id}: {e}")
                self.providers_status.append({
                    "provider_id": provider_id,
                    "name": name,
                    "status": "DECRYPTION_ERROR"
                })

        self.initialized = True
        return {
            "initialized": True,
            "loaded_providers_count": success_count,
            "providers_status": self.providers_status
        }
