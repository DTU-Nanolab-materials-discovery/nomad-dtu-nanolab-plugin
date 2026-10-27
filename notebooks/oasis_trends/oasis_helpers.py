"""Small, read-only NOMAD Oasis helpers used by the trend notebooks."""

from __future__ import annotations

import os
from typing import Any
import requests

from oasis_auth import api_base_url, get_token

BASE_URL = api_base_url()
PAGE_SIZE = 100


def _session() -> requests.Session:
    token = get_token()
    if not token:
        raise RuntimeError(
            'No NOMAD token found. In NORTH, set NOMAD_CLIENT_ACCESS_TOKEN (see '
            'README); on Windows, run setup_nomad_token.py.'
        )
    session = requests.Session()
    session.headers.update(
        {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }
    )
    return session


def _raise_for_status(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text[:1000]
        raise requests.HTTPError(
            f'NOMAD API request failed ({response.status_code}): {detail}',
            response=response,
        ) from exc


def search_entries(schema: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return at most ``limit`` visible entry metadata records for a schema."""
    if limit < 1:
        raise ValueError('limit must be positive')

    session = _session()
    endpoint = f'{BASE_URL}/entries/query'
    body: dict[str, Any] = {
        'owner': 'visible',
        'query': {'section_defs.definition_qualified_name:all': [schema]},
        'pagination': {'page_size': min(PAGE_SIZE, limit)},
        'required': {
            'include': [
                'entry_id',
                'entry_name',
                'entry_create_time',
                'upload_id',
                'mainfile',
            ]
        },
    }
    entries: list[dict[str, Any]] = []
    while len(entries) < limit:
        body['pagination']['page_size'] = min(PAGE_SIZE, limit - len(entries))
        response = session.post(endpoint, json=body, timeout=60)
        _raise_for_status(response)
        payload = response.json()
        page = payload.get('data', [])
        if not page:
            break
        entries.extend(page)
        next_value = payload.get('pagination', {}).get('next_page_after_value')
        if not next_value:
            break
        body['pagination']['page_after_value'] = next_value
    return entries[:limit]


def fetch_archives(
    entries: list[dict[str, Any]], limit: int
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Fetch bounded archives in read-only batches, preserving their metadata."""
    if limit < 0:
        raise ValueError('limit cannot be negative')
    selected = entries[:limit]
    if not selected:
        return []

    session = _session()
    endpoint = f'{BASE_URL}/entries/archive/query'
    archives: dict[str, dict[str, Any]] = {}
    batch_size = 20
    for start in range(0, len(selected), batch_size):
        batch = selected[start : start + batch_size]
        entry_ids = [meta['entry_id'] for meta in batch]
        response = session.post(
            endpoint,
            json={
                'owner': 'visible',
                'query': {'entry_id:any': entry_ids},
                'pagination': {'page_size': len(entry_ids)},
                'required': {'include': ['entry_id'], 'data': '*'},
            },
            timeout=120,
        )
        _raise_for_status(response)
        payload = response.json()
        for item in payload.get('data', []):
            archive = item.get('archive') or {}
            data = archive.get('data') if isinstance(archive, dict) else None
            if isinstance(data, dict):
                archives[item['entry_id']] = data

    missing = set(meta['entry_id'] for meta in selected) - archives.keys()
    if missing:
        raise ValueError(
            f'NOMAD archive query returned {len(missing)} of '
            f'{len(selected)} requested entries; first missing ID: '
            f'{next(iter(missing))}'
        )
    return [(meta, archives[meta['entry_id']]) for meta in selected]


def reference_entry_id(value: Any) -> str | None:
    """Extract a NOMAD entry ID from common archive reference representations."""
    if isinstance(value, dict):
        for key in ('m_ref', 'reference', 'entry_id', 'target_entry_id'):
            if key in value:
                found = reference_entry_id(value[key])
                if found:
                    return found
    elif isinstance(value, str):
        marker = '/archive/'
        if marker in value:
            return value.split(marker, 1)[1].split('#', 1)[0].split('/', 1)[0]
    return None


def reference_ids(values: Any) -> set[str]:
    """Collect entry IDs from a reference or sequence of references."""
    if not isinstance(values, list):
        values = [values]
    return {
        entry_id
        for value in values
        if (entry_id := reference_entry_id(value)) is not None
    }
