"""
main.py
Application entrypoint – starts the Uvicorn server.
"""
import uvicorn
from core.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "api.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )
