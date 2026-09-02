#!/usr/bin/env bash
# Render build script: installs deps, collects static files, and applies migrations.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
