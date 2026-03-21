"""
Network utilities for SRT2Web.

Provides functions for detecting local and public IP addresses.
"""

import socket
import urllib.request
import logging

logger = logging.getLogger("srt2web.network")

_public_ip_logged = False


def get_local_ip() -> str:
    """
    Get the local network IP address of this machine.

    Returns:
        str: Local IP address (e.g., "192.168.1.100")
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.warning(f"Could not detect local IP: {e}")
        return "127.0.0.1"


def get_public_ip() -> tuple[str | None, bool]:
    """
    Get the public IP address of this machine using ipify.org.
    Only logs the IP once to avoid log spam.

    Returns:
        tuple: (ip_address, success)
            - ip_address: Public IP string or None if failed
            - success: True if IP was retrieved successfully
    """
    global _public_ip_logged
    try:
        with urllib.request.urlopen(
            "https://api.ipify.org?format=text", timeout=5
        ) as response:
            ip = response.read().decode("utf-8").strip()
            if ip:
                if not _public_ip_logged:
                    logger.info(f"Public IP detected: {ip}")
                    _public_ip_logged = True
                return ip, True
    except Exception as e:
        logger.warning(f"Could not detect public IP: {e}")

    return None, False


def get_network_info(
    srt_port: int = 9000, server_port: int = 9999, latency_ms: int = 1000
) -> dict:
    """
    Get comprehensive network information for external connections.

    Args:
        srt_port: SRT listener port
        server_port: Web server port
        latency_ms: SRT latency in milliseconds

    Returns:
        dict: Network information including IPs and connection URLs
    """
    local_ip = get_local_ip()
    public_ip, public_success = get_public_ip()

    latency_us = latency_ms * 1000

    info = {
        "local_ip": local_ip,
        "public_ip": public_ip,
        "public_ip_available": public_success,
        "server_port": server_port,
        "srt_port": srt_port,
        "latency_ms": latency_ms,
        "stream_url": None,
        "player_url": None,
        "srt_url_listener": None,
        "srt_url_caller_template": None,
    }

    if public_success:
        base_url = f"http://{public_ip}:{server_port}"
        info["stream_url"] = f"{base_url}/hls/stream.m3u8"
        info["player_url"] = f"{base_url}/player"
        info["srt_url_listener"] = (
            f"srt://{public_ip}:{srt_port}?mode=listener&latency={latency_us}"
        )
        info["srt_url_caller_template"] = (
            f"srt://EMITTER_IP:{srt_port}?mode=caller&latency={latency_us}"
        )
    else:
        base_url = f"http://{local_ip}:{server_port}"
        info["stream_url"] = f"{base_url}/hls/stream.m3u8"
        info["player_url"] = f"{base_url}/player"
        info["srt_url_listener"] = (
            f"srt://{local_ip}:{srt_port}?mode=listener&latency={latency_us}"
        )
        info["srt_url_caller_template"] = (
            f"srt://EMITTER_IP:{srt_port}?mode=caller&latency={latency_us}"
        )

    return info
