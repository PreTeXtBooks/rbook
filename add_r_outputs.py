#!/usr/bin/env python3
"""
Extract R code outputs from HTML and add them to PreTeXt files.
This handles cases where knitr executed R code and generated output,
but the output is not explicitly in the Rmd source.
"""

import re
from bs4 import BeautifulSoup
import sys

def extract_r_outputs_from_html(html_file):
    """Extract R code blocks and their outputs from HTML"""
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all R code blocks (sourceCode r) followed by output blocks
    outputs = []
    
    # Find all divs with class sourceCode
    source_divs = soup.find_all('div', class_='sourceCode')
    
    for source_div in source_divs:
        # Get the R code
        code_elem = source_div.find('code', class_='sourceCode r')
        if not code_elem:
            continue
            
        # Extract the actual R code text
        r_code = code_elem.get_text()
        r_code = r_code.strip()
        
        # Look for the next sibling that's a <pre><code> (output)
        next_elem = source_div.find_next_sibling()
        if next_elem and next_elem.name == 'pre':
            code_elem = next_elem.find('code')
            if code_elem:
                output_text = code_elem.get_text()
                # Check if this looks like R console output (starts with ##)
                if output_text.strip().startswith('##'):
                    outputs.append({
                        'code': r_code,
                        'output': output_text
                    })
    
    return outputs

def add_outputs_to_ptx(ptx_file, outputs):
    """Add console outputs after matching program blocks in PTX file"""
    with open(ptx_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        new_lines.append(lines[i])
        
        # Check if this is a program closing tag
        if lines[i].strip() == '</program>':
            # Extract the R code from the previous program block
            # Go back to find the start of the program block
            j = i - 1
            program_lines = []
            while j >= 0:
                if '<program language="r">' in lines[j]:
                    # Found start, collect all lines between start and end
                    for k in range(j, i + 1):
                        program_lines.append(lines[k])
                    break
                j -= 1
            
            # Extract the actual R code content
            program_text = '\n'.join(program_lines)
            
            # Extract code from CDATA section
            code_match = re.search(r'<input><!\[CDATA\[(.*?)\]\]></input>', program_text, re.DOTALL)
            if code_match:
                r_code = code_match.group(1).strip()
                
                # Find matching output
                for output_info in outputs:
                    # Normalize code for comparison (remove extra whitespace)
                    output_code_normalized = ' '.join(output_info['code'].split())
                    r_code_normalized = ' '.join(r_code.split())
                    
                    if output_code_normalized in r_code_normalized or r_code_normalized in output_code_normalized:
                        # Check if next non-empty line is already a console block
                        k = i + 1
                        while k < len(lines) and not lines[k].strip():
                            k += 1
                        
                        if k < len(lines) and '<console>' in lines[k]:
                            # Already has output, skip
                            break
                        
                        # Add the console output
                        new_lines.append('    <console>')
                        new_lines.append('      <output><![CDATA[')
                        new_lines.append(output_info['output'])
                        new_lines.append(']]></output>')
                        new_lines.append('    </console>')
                        break
        
        i += 1
    
    # Write back
    with open(ptx_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

def main():
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python3 add_r_outputs.py <html_file> <ptx_file>")
        print("\nOr run with no arguments to process all chapters:")
        chapters = [
            ('bayes.html', 'ch6-bayesian-statistics.ptx'),
            ('anova2.html', 'ch5-factorial-anova.ptx'),
            ('regression.html', 'ch-regression.ptx'),
        ]
        for html_name, ptx_name in chapters:
            html_file = f'/home/runner/work/rbook/rbook/docs/book/{html_name}'
            ptx_file = f'/home/runner/work/rbook/rbook/pretext/source/{ptx_name}'
            
            print(f"\nProcessing {html_name}...")
            print(f"Extracting R outputs from {html_file}...")
            outputs = extract_r_outputs_from_html(html_file)
            print(f"Found {len(outputs)} R code outputs")
            
            print(f"Adding outputs to {ptx_file}...")
            add_outputs_to_ptx(ptx_file, outputs)
            print("Done!")
    else:
        html_file = sys.argv[1]
        ptx_file = sys.argv[2]
        
        print(f"Extracting R outputs from {html_file}...")
        outputs = extract_r_outputs_from_html(html_file)
        print(f"Found {len(outputs)} R code outputs")
        
        print(f"Adding outputs to {ptx_file}...")
        add_outputs_to_ptx(ptx_file, outputs)
        print("Done!")

if __name__ == '__main__':
    main()
