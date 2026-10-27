"""Prompt for an existing NOMAD API token and store it with Windows DPAPI."""

from __future__ import annotations

import argparse
import getpass
import os
import webbrowser
from urllib.parse import urlsplit

from token_store import save_token, token_path


DEFAULT_GUI_URL = 'https://nomad.nanolab.dtu.dk/nomad-oasis/gui/'


def oasis_gui_url() -> str:
    base_url = os.environ.get(
        'NOMAD_BASE_URL',
        'https://nomad.nanolab.dtu.dk/nomad-oasis/api/v1',
    )
    parsed = urlsplit(base_url)
    if parsed.scheme != 'https' or not parsed.netloc:
        raise ValueError(
            'NOMAD_BASE_URL must be an HTTPS Oasis URL so authentication is protected.'
        )
    prefix = parsed.path.split('/api/', 1)[0].rstrip('/')
    return f'{parsed.scheme}://{parsed.netloc}{prefix}/gui/'


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            'Open the Oasis sign-in page, then securely store a token you create '
            'in your account settings. This tool never asks for your password.'
        )
    )
    parser.add_argument(
        '--skip-browser',
        action='store_true',
        help='Do not open the Oasis sign-in page automatically.',
    )
    args = parser.parse_args()

    gui_url = oasis_gui_url() if os.environ.get('NOMAD_BASE_URL') else DEFAULT_GUI_URL
    print(f'1. Sign in to the Oasis in your browser: {gui_url}')
    print(
        '2. In your account settings, create/copy an API access token with '
        'read access. Do not enter your password here.'
    )
    if not args.skip_browser:
        webbrowser.open(gui_url)

    token = getpass.getpass('Paste the API token (input is hidden): ').strip()
    if not token:
        parser.error('The token cannot be empty.')
    confirmation = getpass.getpass('Paste it again to confirm (input is hidden): ').strip()
    if token != confirmation:
        parser.error('The two token entries did not match; nothing was saved.')

    path = save_token(token)
    del token, confirmation
    print(f'Token encrypted for this Windows user and saved outside the repository: {path}')
    print(
        'Restart the Jupyter kernel before running the analysis notebook. '
        'The notebook reads the token from this encrypted file and never displays it.'
    )


if __name__ == '__main__':
    main()
