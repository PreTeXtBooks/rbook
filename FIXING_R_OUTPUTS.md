# Fixing R Output Rendering in PreTeXt Book

## Problem

R code outputs (console outputs starting with `##`) were not rendering in the PreTeXt book, even though they appeared correctly in the HTML version of the book. This was particularly noticeable in the Bayesian Statistics chapter, where outputs like "Bayes factor analysis" results were missing.

## Root Cause

The issue occurred because:

1. **HTML Generation**: When the bookdown HTML files are generated, knitr/bookdown executes R code blocks and captures their console output automatically.

2. **PreTeXt Conversion**: The conversion scripts (`convert_ch*.py`) were designed to process the R Markdown (`.Rmd`) source files, which contain:
   - R code blocks (````{r}`)
   - Simplified/edited output blocks (plain `````)
   
   However, they did NOT contain the full console output that R produces when the code is executed.

3. **Missing Full Outputs**: The full R console outputs (with headers like `## Bayes factor analysis`) only appeared in the HTML files after execution, not in the source `.Rmd` files.

## Solution

The solution involved two key changes:

### 1. Update Conversion Scripts to Use `<console>` Elements

Modified the conversion scripts to generate proper PreTeXt `<console>` elements for output blocks instead of plain `<pre>` tags:

```python
# Before:
if is_output:
    self.output.append('    <pre>')
    self.output.append(code_content)
    self.output.append('    </pre>')

# After:
if is_output:
    self.output.append('    <console>')
    self.output.append('      <output><![CDATA[')
    self.output.append(code_content)
    self.output.append(']]></output>')
    self.output.append('    </console>')
```

### 2. Extract R Outputs from HTML and Add to PTX

Created a Python script (`add_r_outputs.py`) that:

1. Parses the HTML files to find R code blocks and their console outputs
2. Extracts outputs that start with `##` (indicating console output)
3. Matches them to corresponding R code blocks in PTX files
4. Inserts `<console><output>` elements after the `<program>` elements

## Files Modified

### Conversion Scripts
- `convert_ch6_bayes.py`: Updated to use `<console>` elements

### PTX Files Updated with Console Outputs
- `ch6-bayesian-statistics.ptx`: 29 console elements added
- `ch5-factorial-anova.ptx`: 80 console elements added
- `ch-regression.ptx`: 28 console elements added
- `ch-anova.ptx`: 32 console elements added
- `ch-hypothesistesting.ptx`: 10 console elements added
- `ch-probability.ptx`: 25 console elements added
- `ch-estimation.ptx`: 26 console elements added

### New Tools Created
- `add_r_outputs.py`: Script to extract and add R outputs from HTML to PTX files

## Usage

### To Process All Chapters

Simply run the script without arguments:

```bash
cd /home/runner/work/rbook/rbook
python3 add_r_outputs.py
```

This will automatically process all mapped HTML→PTX chapter pairs.

### To Process a Single Chapter

Specify the HTML and PTX files:

```bash
python3 add_r_outputs.py docs/book/bayes.html pretext/source/ch6-bayesian-statistics.ptx
```

## PreTeXt Console Element Structure

The console elements added follow this structure:

```xml
<program language="r">
  <input><![CDATA[
library( BayesFactor )
contingencyTableBF( crosstab, sampleType = "jointMulti" )
]]></input>
</program>
<console>
  <output><![CDATA[
## Bayes factor analysis
## --------------
## [1] Non-indep. (a=1) : 15.92684 ±0%
## 
## Against denominator:
##   Null, independence, a = 1 
## ---
## Bayes factor type: BFcontingencyTable, joint multinomial
]]></output>
</console>
```

This properly renders both the R code and its console output in the PreTeXt book.

## Dependencies

The `add_r_outputs.py` script requires:
- Python 3
- BeautifulSoup4: `pip install beautifulsoup4`

## Future Maintenance

When adding new chapters or updating existing ones:

1. Run the conversion script for that chapter (e.g., `python3 convert_ch6_bayes.py`)
2. Run `add_r_outputs.py` to add console outputs from the HTML
3. Verify the PTX file is valid XML
4. Build and test the PreTeXt book

## Verification

All updated PTX files have been validated as well-formed XML using Python's `xml.etree.ElementTree` parser.
