# Fix Missing LaTeX Packages

## Issue
BasicTeX is a minimal LaTeX distribution and doesn't include many packages by default (Greek support, multirow, booktabs, etc.).

## Solution 1: Install All Required Packages (Recommended)

I've created a script that installs everything you need. Run this in your terminal:

```bash
cd /Users/A200255476/projects/ChargingAlgorithm/thesis
./install_packages.sh
```

You'll need to enter your password. This installs:
- Greek language support (babel-greek, greek-fontenc, cbfonts, hyphen-greek)
- Table packages (multirow, booktabs)
- Figure packages (subfig, float, caption)
- Code listing packages (listings, xcolor)
- Algorithm packages (algorithm2e, algorithmicx)
- Bibliography packages (biblatex, biber, logreq)
- Layout packages (fancyhdr, geometry, setspace)
- Math packages (amsmath, amssymb, amsthm)
- Other essentials (hyperref, lm, collection-fontsrecommended)

After installation:

```bash
# Make sure PATH is set (already added to your .zshrc)
export PATH="/Library/TeX/texbin:$PATH"

# Compile the thesis
make
```

## Solution 2: Use English-Only Version (Quick Fix)

I've created an English-only version that compiles without Greek support.

Use `main_en.tex` instead of `main.tex`:

```bash
cd /Users/A200255476/projects/ChargingAlgorithm/thesis
pdflatex main_en.tex
biber main_en
pdflatex main_en.tex
pdflatex main_en.tex
```

## Solution 3: Use Overleaf (No Installation Issues)

Overleaf has all language packages pre-installed:

1. Upload `thesis_overleaf.zip` to https://www.overleaf.com
2. Compile - it will work immediately!
3. Greek support works out of the box

## Recommended: Use Overleaf

Since you're having installation issues, Overleaf is the easiest path forward.
