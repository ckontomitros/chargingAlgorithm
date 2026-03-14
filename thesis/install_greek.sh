#!/bin/bash
# Install Greek language support for BasicTeX

echo "Installing Greek language packages..."
sudo tlmgr install babel-greek greek-fontenc cbfonts hyphen-greek

echo "Updating tlmgr..."
sudo tlmgr update --self

echo "Done! Greek support installed."
echo ""
echo "Now you can compile the thesis with:"
echo "  cd /Users/A200255476/projects/ChargingAlgorithm/thesis"
echo "  make"
