"""
Generate self-signed SSL certificates for SRT2Web development.

Usage:
    python scripts/generate_ssl_certs.py [--cert-dir CERT_DIR]

    Default cert_dir: ./certs
"""

import argparse
import sys
from pathlib import Path


def generate_certs(cert_dir: str = "certs") -> None:
    """Generate self-signed SSL certificate and key using openssl."""
    cert_path = Path(cert_dir)
    cert_path.mkdir(parents=True, exist_ok=True)

    cert_file = cert_path / "cert.pem"
    key_file = cert_path / "key.pem"

    if cert_file.exists() and key_file.exists():
        print(f"Certificates already exist: {cert_file}, {key_file}")
        return

    # Check openssl is available
    import subprocess

    try:
        subprocess.run(
            ["openssl", "version"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("openssl not found. Install openssl or manually create certs.")
        print("On Windows: https://slproweb.com/products/Win32OpenSSL.html")
        print("On Mac: brew install openssl")
        print("On Ubuntu: sudo apt install openssl")
        sys.exit(1)

    # Generate self-signed certificate
    cmd = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:4096",
        "-nodes",
        "-out",
        str(cert_file),
        "-keyout",
        str(key_file),
        "-days",
        "365",
        "-subj",
        "/CN=localhost",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print("Generated SSL certificates:")
        print(f"  Cert: {cert_file}")
        print(f"  Key:  {key_file}")
        print("\nWARNING: These are self-signed certificates for development only!")
        print("   For production, use Let's Encrypt with Nginx/Caddy.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to generate certificates: {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SSL certificates for SRT2Web")
    parser.add_argument(
        "--cert-dir",
        default="certs",
        help="Directory to store certificates (default: certs)",
    )
    args = parser.parse_args()

    generate_certs(args.cert_dir)


if __name__ == "__main__":
    main()
