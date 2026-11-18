#!/bin/sh
# Browser-Wrapper für kaleido auf Systemen ohne Chrome, aber mit Brave als
# Flatpak. kaleido nutzt diesen Wrapper, wenn BROWSER_PATH darauf zeigt
# (setzt scripts/export_figures.py, wenn kein Chrome/Chromium im PATH liegt).
# Der Dateisystemzugriff ist nötig, damit Brave kaleidos temporäre HTML-Seite
# lesen kann.
exec flatpak run --filesystem=host --filesystem=/tmp com.brave.Browser "$@"
