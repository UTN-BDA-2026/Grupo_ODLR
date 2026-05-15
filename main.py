"""
Application entry point.

Este archivo sirve como punto de entrada principal para levantar la aplicación.
Importa y exporta la app de FastAPI desde app.main
"""

from app.main import app, create_application

__all__ = ["app", "create_application"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    
