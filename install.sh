#!/bin/bash
# Install let-claude-code (cook command)
set -e

echo "Installing let-claude-code..."
pip install git+https://github.com/friday-james/let-claude-code.git

echo ""
echo "Done! Run 'cook --help' to get started."
