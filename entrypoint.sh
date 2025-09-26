#!/bin/sh
# This script checks for the 'share' environment variable and launches the application accordingly.

# Default to not sharing
SHARE_FLAG=""

# Check if the 'share' environment variable is set to "True"
if [ "$share" = "True" ]; then
  echo "INFO:     Launching with Gradio share link enabled."
  SHARE_FLAG="--share"
fi

# Launch the application using exec to replace the shell process.
# This ensures that signals are passed correctly to the Python application.
exec python -m app.main --host 0.0.0.0 --port 8000 $SHARE_FLAG

