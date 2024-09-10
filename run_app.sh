#!/bin/bash
echo "Starting IDF tool..."
xdg-open "http://127.0.0.1:5000"  # For Linux
open "http://127.0.0.1:5000"      # For macOS
python3 idf_tool/app.py