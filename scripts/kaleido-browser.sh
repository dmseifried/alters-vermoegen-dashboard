#!/bin/sh
# Browser-Wrapper für kaleido: Auf diesem Rechner gibt es kein Chrome, aber
# Brave als Flatpak. kaleido nutzt diesen Wrapper, wenn BROWSER_PATH darauf
# zeigt (setzt scripts/export_figures.py automatisch). Der Dateisystemzugriff
# ist nötig, damit Brave kaleidos temporäre HTML-Seite lesen kann.
exec flatpak run --filesystem=host --filesystem=/tmp com.brave.Browser "$@"
