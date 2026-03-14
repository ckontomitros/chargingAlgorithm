# Makefile for LaTeX thesis compilation

# Main document name (without .tex extension)
MAIN = main

# LaTeX compiler
LATEX = xelatex
BIBTEX = biber

# Compilation flags
LATEX_FLAGS = -interaction=nonstopmode -halt-on-error

# Default target
.PHONY: all
all: $(MAIN).pdf

# Compile the main document
$(MAIN).pdf: $(MAIN).tex chapters/*.tex references.bib
	@echo "First LaTeX pass..."
	$(LATEX) $(LATEX_FLAGS) $(MAIN).tex
	@echo "Running biber for bibliography..."
	$(BIBTEX) $(MAIN)
	@echo "Second LaTeX pass..."
	$(LATEX) $(LATEX_FLAGS) $(MAIN).tex
	@echo "Third LaTeX pass..."
	$(LATEX) $(LATEX_FLAGS) $(MAIN).tex
	@echo "Compilation complete: $(MAIN).pdf"

# Quick compile (single pass, for draft viewing)
.PHONY: quick
quick:
	$(LATEX) $(LATEX_FLAGS) $(MAIN).tex

# Clean auxiliary files
.PHONY: clean
clean:
	@echo "Cleaning auxiliary files..."
	rm -f $(MAIN).aux $(MAIN).log $(MAIN).out $(MAIN).toc $(MAIN).lof $(MAIN).lot
	rm -f $(MAIN).bbl $(MAIN).bcf $(MAIN).blg $(MAIN).run.xml
	rm -f chapters/*.aux
	@echo "Clean complete."

# Clean everything including PDF
.PHONY: cleanall
cleanall: clean
	rm -f $(MAIN).pdf
	@echo "All files cleaned."

# Watch for changes and recompile (requires latexmk)
.PHONY: watch
watch:
	latexmk -pdf -pvc $(MAIN).tex

# Count words (approximate)
.PHONY: wordcount
wordcount:
	@echo "Approximate word count:"
	@texcount -inc -incbib -sum $(MAIN).tex

# Spell check (requires aspell)
.PHONY: spell
spell:
	@echo "Spell checking..."
	@for file in chapters/*.tex; do \
		echo "Checking $$file..."; \
		aspell --lang=en --mode=tex check $$file; \
	done

# Create figures directory if it doesn't exist
.PHONY: setup
setup:
	@mkdir -p figures
	@echo "Created figures/ directory"
	@echo "Copy your simulation results:"
	@echo "  cp ../scripts/simulation_results_multi.png figures/"
	@echo "  cp ../scripts/simulation_results_multi_v2g.png figures/"

# Help
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  make          - Compile thesis (full compilation with bibliography)"
	@echo "  make quick    - Quick compile (single pass, no bibliography)"
	@echo "  make clean    - Remove auxiliary files"
	@echo "  make cleanall - Remove all generated files including PDF"
	@echo "  make watch    - Watch for changes and auto-recompile (requires latexmk)"
	@echo "  make wordcount- Count words in document"
	@echo "  make spell    - Run spell checker (requires aspell)"
	@echo "  make setup    - Create figures directory"
	@echo "  make help     - Show this help message"
