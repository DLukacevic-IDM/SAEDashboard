#!/bin/bash
mkdir -p /data/indicators /data/uploads /data/tmp
exec uvicorn app:app --host 0.0.0.0 --port 5020
