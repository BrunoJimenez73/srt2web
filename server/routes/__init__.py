"""
Routes package for SRT2Web API.

Contains separated route modules:
- pipeline.py: Pipeline control routes
- config.py: Configuration routes
- modules.py: Module management routes
- outputs.py: Output management routes
"""

from server.routes import pipeline, config, modules, outputs

__all__ = ["pipeline", "config", "modules", "outputs"]
