import logging
from typing import Iterable, Optional

from asgiref.sync import async_to_sync
# Auraflux engine imports
from auraflux_core.core.schemas.clients import ClientConfig, ProviderConfig
from auraflux_core.core.schemas.engine import EngineConfig
from auraflux_core.engine import AurafluxEngine

# Local exceptions
from .exceptions import EngineInitializationError

logger = logging.getLogger(__name__)

class AurafluxEngineSingleton:
    """
    Singleton class to manage AurafluxEngine lifecycle.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AurafluxEngineSingleton, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance._engine = None
        return cls._instance

    def initialize(self, providers: Optional[Iterable] = None):
        """
        Initialize the engine: load providers, decrypt credentials, and start the engine.
        Decoupled from ModelProvider model.
        """

        # Reset initialized state if we are passing new providers (for testing)
        if providers is not None:
            self._initialized = False

        if self._initialized:
            logger.info("AurafluxEngine is already initialized.")
            return None

        logger.info("Initializing AurafluxEngine...")

        if providers is None:
            raise EngineInitializationError("No providers provided for initialization.")

        provider_configs = []
        providers_status = []

        for provider in providers:
            try:
                # Handle provider as dict or object with get_api_key/attributes
                if isinstance(provider, dict):
                    raw_key = provider.get('api_key')
                    p_id = provider.get('id')
                    p_type = provider.get('provider_type', 'openai')
                    p_base_url = provider.get('base_url')
                    name = provider.get('name', 'unknown')
                else:
                    # Model instance fallback (using duck typing for attributes/methods)
                    raw_key = getattr(provider, 'get_api_key')()
                    p_id = provider.id
                    p_type = provider.provider_type
                    p_base_url = provider.base_url
                    name = provider.name

                # Check for decryption failure
                status = "ACTIVE"
                if raw_key == "DECRYPTION_ERROR" or raw_key == "DECRYPTION_ERROR_SIM":
                    logger.warning(f"Provider {p_id} decryption failed.")
                    status = "DECRYPTION_ERROR"

                providers_status.append({
                    "provider_id": p_id,
                    "name": name,
                    "status": status
                })

                if status == "ACTIVE":
                    provider_config = ProviderConfig(
                        id=str(p_id),
                        type=p_type.upper(),
                        api_key=raw_key,
                        base_url=p_base_url
                    )
                    provider_configs.append(provider_config)

            except Exception as e:
                logger.error(f"Failed to process provider: {e}")
                continue

        # Start the engine
        try:
            config = EngineConfig(client_config=ClientConfig(providers=provider_configs))
            self._engine = AurafluxEngine(config=config)
            async_to_sync(self._engine.initialize)()
            self._initialized = True
            logger.info(f"AurafluxEngine initialized with {len(provider_configs)} providers.")
        except Exception as e:
            logger.error(f"Critical error during engine initialization: {e}")
            raise EngineInitializationError(f"Initialization failed: {e}")

        return {
            "initialized": True,
            "loaded_providers_count": len(provider_configs),
            "providers_status": providers_status
        }

    @property
    def engine(self):
        if not self._initialized:
            raise EngineInitializationError("Engine not initialized.")
        return self._engine
