"""Allow running as: python -m harness.web.server"""

import sys

from .server import run_server

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8500
run_server(port)
