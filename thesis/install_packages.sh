#!/bin/bash
# Install all required LaTeX packages for the thesis

echo "Installing required LaTeX packages..."
echo "You'll need to enter your password for sudo access."
echo ""

# Core packages for the thesis
sudo tlmgr install \
  babel-greek \
  greek-fontenc \
  cbfonts \
  hyphen-greek \
  multirow \
  booktabs \
  subfig \
  float \
  caption \
  xcolor \
  listings \
  algorithm2e \
  algorithmicx \
  biblatex \
  biber \
  logreq \
  xstring \
  fancyhdr \
  geometry \
  setspace \
  amsmath \
  amssymb \
  amsthm \
  hyperref \
  lm \
  collection-fontsrecommended

echo ""
echo "Updating tlmgr..."
sudo tlmgr update --self

echo ""
echo "✓ All packages installed!"
echo ""
echo "Now compile the thesis with:"
echo "  cd /Users/A200255476/projects/ChargingAlgorithm/thesis"
echo "  export PATH=\"/Library/TeX/texbin:\$PATH\""
echo "  make"
