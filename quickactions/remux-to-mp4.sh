#!/bin/bash
# Quick Action wrapper for remux-to-mp4.

set -e

exec python3 -m video_file_management.remux.remux_quickaction "$@"
