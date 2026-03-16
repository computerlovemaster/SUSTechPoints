#!/usr/bin/env bash
set -euo pipefail

cd /app

exec uwsgi --ini ./uwsgi.ini
