import logging
from typing import Any, Dict, List

from asgiref.sync import async_to_sync
from auraflux_core.core.schemas.clients import ClientConfig, ProviderConfig
from auraflux_core.core.schemas.engine import EngineConfig
from auraflux_core.engine import AurafluxEngine

from .exceptions import EngineInitializationError

logger = logging.getLogger(__name__)

class AurafluxEngineSingleton:
    _instance = None

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = False
            # Initialize without providers initially
            self.engine = AurafluxEngine(config=EngineConfig(client_config=ClientConfig(providers={})))
            self.providers_status = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AurafluxEngineSingleton, cls).__new__(cls)
        return cls._instance

    def initialize(self, providers: List[Dict[str, Any]]):
        """
        Initialize the core engine and handle provider credential decryption.
        """
        self.providers_status = []
        success_count = 0

        # Prepare providers config for EngineConfig
        provider_configs = []
        for provider in providers:
            provider_id = provider.get('id')
            provider_config = ProviderConfig(
                id=str(provider_id),
                type=provider.get('provider_type', 'openai').upper(),
                api_key=provider.get('api_key', 'dummy_key'),
                base_url=provider.get('base_url')
            )
            provider_configs.append(provider_config)

            self.providers_status.append({
                "provider_id": provider_id,
                "name": provider.get('name'),
                "status": "ACTIVE"
            })
            success_count += 1

        # Re-initialize engine with actual providers
        # ClientConfig expects a list of providers
        self.engine = AurafluxEngine(config=EngineConfig(client_config=ClientConfig(providers=provider_configs)))

        try:
            # Sync wrapper for async initialize
            async_to_sync(self.engine.initialize)()
            self.initialized = True
        except Exception as e:
            logger.error(f"Engine initialization failed: {e}")
            raise EngineInitializationError(f"Initialization failed: {e}")

        return {
            "initialized": True,
            "loaded_providers_count": success_count,
            "providers_status": self.providers_status
        }
