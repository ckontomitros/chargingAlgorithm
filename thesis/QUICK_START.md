# Quick Start Guide

## Getting Started with Your Thesis

This guide will help you quickly set up and start working on your thesis.

## Step 1: Setup (5 minutes)

```bash
# Navigate to thesis directory
cd /Users/A200255476/projects/ChargingAlgorithm/thesis

# Create figures directory
mkdir -p figures

# Copy simulation results
cp ../scripts/simulation_results_multi.png figures/
cp ../scripts/simulation_results_multi_v2g.png figures/
```

## Step 2: Install LaTeX Packages (5-10 minutes)

BasicTeX is minimal and needs additional packages. Run the installation script:

```bash
# Install all required packages (you'll need to enter your password)
./install_packages.sh
```

This installs Greek support, table packages, figure packages, bibliography tools, and more.

**Alternative:** If you prefer to skip local installation, use **Overleaf** instead (see `OVERLEAF_INSTRUCTIONS.md`). Overleaf has all packages pre-installed!

## Step 3: Test Compilation (5 minutes)

After installing packages:

```bash
# Make sure LaTeX is in your PATH (already added to .zshrc)
export PATH="/Library/TeX/texbin:$PATH"

# Compile the thesis
make

# Or manually:
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex

# View the PDF
open main.pdf  # macOS
# or
xdg-open main.pdf  # Linux
```

If compilation succeeds, you should see a PDF with the complete structure but with placeholder data.

**Troubleshooting:** If you get package errors, see `FIX_GREEK_SUPPORT.md` for detailed solutions.

## Step 4: Fill in Personal Information (10 minutes)

Edit `chapters/00_frontmatter.tex`:

1. Replace `[YOUR UNIVERSITY NAME]` with your university
2. Replace `[DEPARTMENT/SCHOOL NAME]` with your department
3. Replace `[YOUR NAME]` with your name
4. Replace `[SUPERVISOR NAME]` with your advisor's name
5. Replace `[CITY]` and `[MONTH]` with appropriate values
6. Write your abstracts (Greek and English)
7. Write acknowledgments

## Step 5: Extract Simulation Data (30 minutes)

You need to run your simulations and extract numerical results to fill in the `[XX.XX]` placeholders.

### Run Simulations

```bash
cd /Users/A200255476/projects/ChargingAlgorithm

# Run charge-only simulation
# Edit scripts/run_simulation.py: Set SIMULATION_TYPE = "multi_ev"
python scripts/run_simulation.py > results_charge_only.txt

# Run V2G simulation  
# Edit scripts/run_simulation.py: Set SIMULATION_TYPE = "multi_ev_v2g"
python scripts/run_simulation.py > results_v2g.txt
```

### Extract Data

From the output, extract:
- Total costs/benefits for each method
- Grid energy consumption
- Solar energy utilization
- Final SoC values
- Constraint violations

Create a spreadsheet or text file with all values, then systematically replace placeholders in Chapter 4.

## Step 6: Priority Writing Order

Don't write sequentially! Use this order for efficiency:

### Week 1: Methodology (Chapter 2)
- **Why first?** Most technical, based on your code
- **What to do:** Document your mathematical models and algorithms
- **Tip:** Copy equations from your code comments

### Week 2: Results (Chapter 4)
- **Why second?** You have fresh simulation data
- **What to do:** Present results with tables and figures
- **Tip:** Create all figures first, then write analysis around them

### Week 3: Case Study (Chapter 3)
- **Why third?** Describes your data sources
- **What to do:** Document where data came from and why you chose it
- **Tip:** Justify every parameter choice

### Week 4: Introduction (Chapter 1)
- **Why fourth?** Easier to write intro after you know your results
- **What to do:** Motivate the problem, review literature, state objectives
- **Tip:** Start with literature review (cite 30-50 papers)

### Week 5: Conclusions (Chapter 5)
- **Why last?** Synthesizes everything
- **What to do:** Summarize findings, make recommendations, discuss future work
- **Tip:** Answer the research questions directly

### Week 6: Polish and Appendices
- Complete appendices
- Proofread everything
- Check all references
- Format consistently

## Step 7: Daily Writing Routine

### Morning Session (2-3 hours)
- Write new content
- Focus on one section at a time
- Don't worry about perfection

### Afternoon Session (1-2 hours)
- Revise morning's work
- Add figures and tables
- Check citations

### Evening (30 minutes)
- Read what you wrote
- Plan tomorrow's section
- Update progress tracker

## Step 8: Using the Makefile

```bash
# Full compilation (use when you've made significant changes)
make

# Quick preview (faster, use during writing)
make quick

# Clean up auxiliary files
make clean

# Auto-recompile on changes (requires latexmk)
make watch

# Count words
make wordcount

# Get help
make help
```

## Step 9: Working with Figures

### Creating New Figures

If you need additional figures beyond the simulation results:

```python
# In a Python script or notebook
import matplotlib.pyplot as plt
import numpy as np

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))
# ... plot your data ...
ax.set_xlabel('Hour', fontsize=12)
ax.set_ylabel('Cost (€)', fontsize=12)
ax.set_title('Cost Comparison', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)

# Save as high-resolution PNG or PDF
plt.savefig('thesis/figures/cost_comparison.png', dpi=300, bbox_inches='tight')
# Or PDF for vector graphics:
plt.savefig('thesis/figures/cost_comparison.pdf', bbox_inches='tight')
```

### Including Figures in LaTeX

```latex
\begin{figure}[H]
    \centering
    \includegraphics[width=0.8\textwidth]{figures/cost_comparison.png}
    \caption{Cost comparison across intelligence levels}
    \label{fig:cost_comparison}
\end{figure}
```

## Step 10: Managing References

### Adding References

1. Find paper on Google Scholar
2. Click "Cite" → "BibTeX"
3. Copy BibTeX entry to `references.bib`
4. Cite in text: `\cite{author2023}`

### Example

```bibtex
@article{smith2023smart,
    author = {Smith, John and Doe, Jane},
    title = {Smart EV Charging Optimization},
    journal = {IEEE Transactions on Smart Grid},
    year = {2023},
    volume = {14},
    pages = {1234--1245},
    doi = {10.1109/TSG.2023.1234567}
}
```

Then in your text:
```latex
Recent research by Smith and Doe \cite{smith2023smart} demonstrates...
```

## Step 11: Common LaTeX Issues and Solutions

### Issue: Bibliography not showing

**Solution:**
```bash
pdflatex main.tex
biber main        # Not bibtex!
pdflatex main.tex
pdflatex main.tex
```

### Issue: Figure not found

**Solution:**
- Check file path: `figures/filename.png`
- Ensure file exists
- Check file extension (case-sensitive on Linux)

### Issue: Undefined reference

**Solution:**
- Compile multiple times (references need 2-3 passes)
- Check that `\label{}` exists for the reference

### Issue: Greek text not displaying

**Solution:**
```latex
% Use textgreek command
\textgreek{Ελληνικό κείμενο}

% Or switch language
\begin{otherlanguage}{greek}
Μεγάλο κείμενο στα ελληνικά...
\end{otherlanguage}
```

## Step 12: Version Control (Recommended)

Track your thesis with Git:

```bash
cd /Users/A200255476/projects/ChargingAlgorithm/thesis

# Initialize git (if not already in main repo)
git init

# Add files
git add main.tex chapters/*.tex references.bib

# Commit regularly
git commit -m "Initial thesis structure"

# After each writing session
git add -A
git commit -m "Completed Section 2.3: RL algorithm"
```

**Benefits:**
- Track changes over time
- Revert if you delete something important
- See your progress
- Backup your work

## Step 13: Productivity Tips

### Focus Techniques

1. **Pomodoro Technique:**
   - Write for 25 minutes
   - Break for 5 minutes
   - Repeat 4 times, then longer break

2. **Section-by-Section:**
   - Complete one section before moving to next
   - Don't jump around too much

3. **Separate Writing and Editing:**
   - Morning: Write new content (don't edit)
   - Afternoon: Edit and refine

### Overcoming Writer's Block

1. **Start with easy sections:**
   - Write methodology first (you know your code)
   - Save introduction for later

2. **Use bullet points:**
   - Write key points as bullets first
   - Expand into paragraphs later

3. **Talk it out:**
   - Explain to a friend
   - Record yourself explaining
   - Transcribe and edit

### Staying Motivated

1. **Set daily goals:**
   - "Write 2 pages today"
   - "Complete Section 2.3"
   - Track progress

2. **Celebrate milestones:**
   - Finished a chapter? Take a break!
   - Reward yourself for progress

3. **Visualize completion:**
   - Imagine holding your finished thesis
   - Remember why this matters

## Step 14: Getting Feedback

### From Your Advisor

- Send chapter drafts as you complete them
- Don't wait until everything is done
- Be open to criticism
- Ask specific questions

### From Peers

- Exchange chapters with classmates
- Fresh eyes catch errors
- Learn from their writing

### Self-Review Checklist

Before sending to advisor:
- [ ] Read aloud (catches awkward phrasing)
- [ ] Check all figures are referenced
- [ ] Verify all equations are explained
- [ ] Ensure logical flow between sections
- [ ] Spell check and grammar check

## Step 15: Final Submission Preparation

### Two Weeks Before Deadline

- [ ] Complete all chapters
- [ ] All figures and tables finalized
- [ ] Bibliography complete
- [ ] First full proofread

### One Week Before Deadline

- [ ] Incorporate advisor feedback
- [ ] Second proofread
- [ ] Check formatting requirements
- [ ] Print draft for review

### Three Days Before Deadline

- [ ] Final proofread
- [ ] Verify PDF quality
- [ ] Check page numbers
- [ ] Ensure all requirements met

### Submission Day

- [ ] Generate final PDF
- [ ] Verify file size and format
- [ ] Submit through required channel
- [ ] Keep backup copies
- [ ] Celebrate! 🎉

## Useful Resources

### LaTeX Help
- Overleaf Documentation: https://www.overleaf.com/learn
- LaTeX Wikibook: https://en.wikibooks.org/wiki/LaTeX
- TeX Stack Exchange: https://tex.stackexchange.com/

### Writing Help
- Academic Phrasebank: http://www.phrasebank.manchester.ac.uk/
- Purdue OWL: https://owl.purdue.edu/

### Research Tools
- Google Scholar: https://scholar.google.com/
- Connected Papers: https://www.connectedpapers.com/
- Research Rabbit: https://www.researchrabbit.ai/

## Questions?

If you encounter issues:
1. Check this guide first
2. Search online (most LaTeX issues are well-documented)
3. Ask your advisor
4. Consult with classmates

Good luck! You've got this! 💪
