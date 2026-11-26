import logging
import os
from typing import Iterable, Optional

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
            cls._instance._pid = None
        return cls._instance

    async def initialize(self, providers: Optional[Iterable] = None, force_reinit: bool = False):
        """
        Initialize the engine: load providers, decrypt credentials, and start the engine.
        Decoupled from ModelProvider model.
        """
        current_pid = os.getpid()

        # Reset initialized state if we are passing new providers (for testing)
        if providers is not None:
            self._initialized = False

        if not force_reinit and self._initialized and self._pid == current_pid:
            logger.info(f"AurafluxEngine is already initialized in pid {current_pid}.")
            return None

        logger.info(f"Initializing AurafluxEngine in pid {current_pid}...")

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
            config = EngineConfig(client_config=ClientConfig(providers=provider_configs, initialize_mode='run_forever'))
            self._engine = AurafluxEngine(config=config)
            await self._engine.initialize()
            self._initialized = True
            self._pid = current_pid
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
        if not self._initialized or self._pid != os.getpid():
            raise EngineInitializationError("Engine not initialized.")
        return self._engine

    @property
    def initialized(self):
        return self._initialized

    @property
    def pid(self):
        return self._pid
