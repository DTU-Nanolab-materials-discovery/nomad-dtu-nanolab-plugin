"""Resolve the Oasis API URL and access token for local machines and NORTH."""

from __future__ import annotations

import os

DEFAULT_API_URL = 'https://nomad.nanolab.dtu.dk/nomad-oasis/api/v1'


def api_base_url() -> str:
    """API URL: NOMAD_BASE_URL, else NORTH's NOMAD_CLIENT_URL, else the default."""
    explicit = os.environ.get('NOMAD_BASE_URL')
    if explicit:
        return explicit.rstrip('/')
    client_url = os.environ.get('NOMAD_CLIENT_URL')
    if client_url:
        client_url = client_url.rstrip('/')
        if client_url.endswith('/v1'):
            return client_url
        if client_url.endswith('/api'):
            return f'{client_url}/v1'
        return f'{client_url}/api/v1'
    return DEFAULT_API_URL


def get_token() -> str | None:
    """Token from the environment (NORTH/other runtimes), else the Windows DPAPI store."""
    token = os.environ.get('NOMAD_CLIENT_ACCESS_TOKEN')
    if token:
        return token
    if os.name == 'nt':
        from token_store import load_token

        return load_token()
    return None


def running_in_north() -> bool:
    return bool(os.environ.get('JUPYTERHUB_USER') or os.environ.get('NOMAD_CLIENT_URL'))
