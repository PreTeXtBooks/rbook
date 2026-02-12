#!/usr/bin/env python3
"""
Convert 03.05-descriptives.Rmd to PreTeXt XML format
"""

import re
import sys

def escape_xml(text):
    """Escape XML special characters in text (not in code/math)"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text

def convert_inline_formatting(text):
    """Convert inline formatting like bold, term, code"""
    # First protect math expressions
    math_parts = []
    def save_math(match):
        math_parts.append(match.group(0))
        return f"__MATH_{len(math_parts)-1}__"
    text = re.sub(r'\$[^$]+\$', save_math, text)
    
    # Convert ***term*** and **_term_** to <term>
    text = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<term>\1</term>', text)
    text = re.sub(r'\*\*_([^_]+)_\*\*', r'<term>\1</term>', text)
    
    # Convert **bold** to <em>
    text = re.sub(r'\*\*([^*]+)\*\*', r'<em>\1</em>', text)
    
    # Convert `code` to <c>code</c> (but not in code blocks)
    text = re.sub(r'`([^`]+)`', r'<c>\1</c>', text)
    
    # Convert -- to <mdash />
    text = text.replace(' -- ', ' <mdash /> ')
    
    # Restore math
    for i, math in enumerate(math_parts):
        text = text.replace(f"__MATH_{i}__", math)
    
    return text

def convert_math(text):
    """Convert inline and display math"""
    # Display math: $$...$$ to <me>...</me>
    text = re.sub(r'\$\$(.*?)\$\$', r'<me>\1</me>', text, flags=re.DOTALL)
    # Inline math: $...$ to <m>...</m>
    text = re.sub(r'\$([^$]+)\$', r'<m>\1</m>', text)
    return text

def convert_cross_refs(text):
    """Convert cross-references"""
    # \@ref(fig:name) to <xref ref="fig-name" />
    text = re.sub(r'\\@ref\(fig:([^)]+)\)', lambda m: f'<xref ref="fig-{m.group(1).replace("_", "-")}" />', text)
    # \@ref(tab:name) to <xref ref="table-name" />
    text = re.sub(r'\\@ref\(tab:([^)]+)\)', lambda m: f'<xref ref="table-{m.group(1).replace("_", "-")}" />', text)
    # \@ref(section) to <xref ref="section" />
    text = re.sub(r'\\@ref\(([^)]+)\)', lambda m: f'<xref ref="{m.group(1).replace("_", "-")}" />', text)
    # Chapter references
    text = re.sub(r'Chapter \\@ref\(([^)]+)\)', lambda m: f'<xref ref="{m.group(1).replace("_", "-")}" />', text)
    text = re.sub(r'Section \\@ref\(([^)]+)\)', lambda m: f'<xref ref="{m.group(1).replace("_", "-")}" />', text)
    return text

def convert_footnotes(text):
    """Convert footnotes ^[text] to <fn>text</fn>"""
    text = re.sub(r'\^\[([^\]]+)\]', r'<fn>\1</fn>', text)
    return text

def process_line(line, in_code_block, in_list, in_blockquote, indent_level):
    """Process a single line"""
    result = []
    
    # Check for code block markers
    if line.strip().startswith('```'):
        return result, not in_code_block, in_list, in_blockquote
    
    # Skip YAML header
    if line.strip() == '---':
        return result, in_code_block, in_list, in_blockquote
    
    # In code block, preserve as is
    if in_code_block:
        return result, in_code_block, in_list, in_blockquote
    
    # Handle headings
    if line.startswith('#'):
        # Close any open lists or blockquotes
        if in_list:
            result.append('  ' * indent_level + '</ul>')
            in_list = False
        if in_blockquote:
            result.append('  ' * indent_level + '</blockquote>')
            in_blockquote = False
            
        match = re.match(r'^(#{1,4})\s+(.+?)(?:\{#([^}]+)\})?$', line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            xml_id = match.group(3) if match.group(3) else None
            
            # Convert title
            title = convert_inline_formatting(title)
            title = convert_math(title)
            title = convert_cross_refs(title)
            
            if level == 1:
                # This shouldn't happen in this file
                pass
            elif level == 2:
                if xml_id:
                    xml_id = xml_id.replace('_', '-')
                    result.append(f'  <section xml:id="{xml_id}">')
                else:
                    result.append('  <section>')
                result.append(f'    <title>{title}</title>')
            elif level == 3:
                if xml_id:
                    xml_id = xml_id.replace('_', '-')
                    result.append(f'    <subsection xml:id="{xml_id}">')
                else:
                    result.append('    <subsection>')
                result.append(f'      <title>{title}</title>')
            elif level == 4:
                if xml_id:
                    xml_id = xml_id.replace('_', '-')
                    result.append(f'      <subsubsection xml:id="{xml_id}">')
                else:
                    result.append('      <subsubsection>')
                result.append(f'        <title>{title}</title>')
    
    return result, in_code_block, in_list, in_blockquote

def main():
    input_file = '/home/runner/work/rbook/rbook/bookdown/03.05-descriptives.Rmd'
    output_file = '/home/runner/work/rbook/rbook/pretext/source/ch5-descriptive-statistics.ptx'
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Start with XML header
    output = ['<?xml version="1.0" encoding="UTF-8" ?>', '']
    output.append('<chapter xml:id="ch5-descriptive-statistics">')
    
    # Process content line by line
    lines = content.split('\n')
    in_code_block = False
    in_list = False
    in_blockquote = False
    in_paragraph = False
    code_block = []
    paragraph = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Handle code blocks
        if line.strip().startswith('```'):
            if not in_code_block:
                # Starting code block
                in_code_block = True
                code_block = []
                code_match = re.match(r'```\{r([^}]*)\}', line)
                if code_match:
                    code_params = code_match.group(1).strip()
                else:
                    code_params = ''
            else:
                # Ending code block
                in_code_block = False
                # Process the code block
                # ... (will implement full code block handling)
            i += 1
            continue
        
        if in_code_block:
            code_block.append(line)
            i += 1
            continue
        
        # Process regular lines
        # (simplified for now - full implementation needed)
        i += 1
    
    output.append('</chapter>')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print(f"Conversion complete: {output_file}")

if __name__ == '__main__':
    main()
