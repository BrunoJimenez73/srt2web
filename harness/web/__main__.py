"""Allow running as: python -m harness.web.server"""
from .server import run_server
import sys

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8500
run_server(port)
