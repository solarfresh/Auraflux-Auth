from typing import Any, Dict, Optional


class EngineInitializationError(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.error_code = "ENGINE_INITIALIZATION_FAILED"
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
