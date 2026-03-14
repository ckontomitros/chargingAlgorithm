# Diploma Thesis: Smart EV Charging in Office Buildings

## LaTeX Document Structure

This directory contains the LaTeX source files for the diploma thesis.

### Files and Directories

```
thesis/
├── main.tex                          # Main document file
├── references.bib                    # Bibliography database
├── README.md                         # This file
├── chapters/
│   ├── 00_frontmatter.tex           # Title page, abstract, acknowledgments
│   ├── 01_introduction.tex          # Chapter 1: Introduction
│   ├── 02_methodology.tex           # Chapter 2: Methodology
│   ├── 03_case_study.tex            # Chapter 3: Case Study
│   ├── 04_results.tex               # Chapter 4: Results
│   ├── 05_conclusions.tex           # Chapter 5: Conclusions
│   ├── appendix_a_code.tex          # Appendix A: Code
│   └── appendix_b_data.tex          # Appendix B: Data
└── figures/                          # Directory for figures (create this)
```

## Compilation Instructions

### Prerequisites

Install a LaTeX distribution:
- **macOS**: MacTeX (`brew install --cask mactex`)
- **Linux**: TeX Live (`sudo apt-get install texlive-full`)
- **Windows**: MiKTeX or TeX Live

### Compiling the Document

```bash
# Navigate to thesis directory
cd thesis/

# Compile with biber for bibliography
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex

# Or use latexmk for automatic compilation
latexmk -pdf -pvc main.tex
```

### Using Overleaf

Alternatively, upload all files to Overleaf for online compilation:
1. Create new project on Overleaf
2. Upload all `.tex` files and `references.bib`
3. Set main document to `main.tex`
4. Compile

## Next Steps

### 1. Fill in Placeholders

The template contains placeholders marked with `[...]` that need to be filled:

- `[YOUR UNIVERSITY NAME]`
- `[YOUR NAME]`
- `[SUPERVISOR NAME]`
- Data values: `[XX.XX]`, `[XXX.X]`, etc.

### 2. Add Figures

Create a `figures/` directory and add:

- `university_logo.png` (if applicable)
- `building_consumption_profile.png`
- `solar_production_profile.png`
- `electricity_price_profile.png`
- Other visualization figures

You can copy the simulation result images from `../scripts/`:
```bash
mkdir -p figures
cp ../scripts/simulation_results_multi.png figures/
cp ../scripts/simulation_results_multi_v2g.png figures/
```

### 3. Run Simulations and Extract Data

Run your simulations to get actual numerical results:

```bash
cd ..
python scripts/run_simulation.py
```

Then fill in the data tables in Chapter 4 with actual values.

### 4. Complete Literature Review

Add relevant citations to `references.bib` and reference them in Chapter 1 (Introduction).

### 5. Write Abstracts

Complete the Greek and English abstracts in `00_frontmatter.tex`.

## Document Structure Overview

### Chapter 1: Introduction (15-20 pages)
- Background and motivation
- Smart charging levels (0-3)
- Literature review
- Research objectives

### Chapter 2: Methodology (25-30 pages)
- System components (building, EVs, grid)
- Mathematical models for each level
- Algorithm descriptions (RL, MPC, PSO, MILP, DQN)
- Assumptions and limitations

### Chapter 3: Case Study (15-20 pages)
- Office building characteristics
- Data sources and validation
- EV fleet scenario
- Grid parameters
- Simulation setup

### Chapter 4: Results (25-30 pages)
- Performance comparison across levels
- Economic analysis
- Energy metrics
- V2G impact assessment
- Sensitivity analysis

### Chapter 5: Conclusions (10-15 pages)
- Summary of findings
- Practical recommendations
- Challenges and limitations
- Future research directions

### Appendices (10-15 pages)
- Appendix A: Code implementation
- Appendix B: Data tables

**Total estimated length: 100-140 pages**

## Tips for Writing

1. **Use consistent notation**: Define all symbols when first introduced
2. **Reference figures and tables**: Use `\ref{}` and `\label{}`
3. **Cite sources**: Use `\cite{}` for all references
4. **Explain equations**: Don't just present math, explain the meaning
5. **Use active voice**: "We implement..." rather than "It is implemented..."
6. **Proofread**: Check for typos, grammar, and formatting consistency

## Greek Language Support

The document is configured for both Greek and English text. To write in Greek:

```latex
\textgreek{Κείμενο στα ελληνικά}
```

Or switch language for entire sections:

```latex
\begin{otherlanguage}{greek}
Μεγάλο κείμενο στα ελληνικά...
\end{otherlanguage}
```

## Common LaTeX Commands

```latex
% Figures
\begin{figure}[H]
    \centering
    \includegraphics[width=0.8\textwidth]{figures/filename.png}
    \caption{Figure caption}
    \label{fig:label}
\end{figure}

% Tables
\begin{table}[H]
    \centering
    \caption{Table caption}
    \label{tab:label}
    \begin{tabular}{@{}lcc@{}}
        \toprule
        Column 1 & Column 2 & Column 3 \\
        \midrule
        Data & Data & Data \\
        \bottomrule
    \end{tabular}
\end{table}

% Equations
\begin{equation}
    E = mc^2
    \label{eq:einstein}
\end{equation}

% References
See Figure~\ref{fig:label}, Table~\ref{tab:label}, and Equation~\eqref{eq:einstein}.
```

## Troubleshooting

### Common Issues

1. **Bibliography not showing**: Run `biber main` then `pdflatex main.tex` twice
2. **Greek characters not displaying**: Ensure `\usepackage[greek,english]{babel}` is loaded
3. **Figures not found**: Check file paths and ensure `figures/` directory exists
4. **Undefined references**: Compile multiple times (references need 2-3 passes)

### Getting Help

- LaTeX Stack Exchange: https://tex.stackexchange.com/
- Overleaf Documentation: https://www.overleaf.com/learn

## License

[Specify license for your thesis document]
