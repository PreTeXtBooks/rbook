#!/usr/bin/env python3
"""
Convert the ANOVA chapter (05.14-anova.Rmd) from R Markdown to PreTeXt XML format.
"""

import re
import sys

def process_math_inline(text):
    """Convert inline math $...$ to <m>...</m>"""
    # Handle inline math with CDATA for complex expressions
    def replace_inline_math(match):
        content = match.group(1)
        # Check if we need CDATA (has special chars like <, >, &, {, }, etc.)
        if any(c in content for c in ['<', '>', '&', '{', '}', '_', '^', '\\']):
            return f'<m><![CDATA[{content}]]></m>'
        else:
            return f'<m>{content}</m>'
    
    text = re.sub(r'\$([^\$]+)\$', replace_inline_math, text)
    return text

def process_math_display(text):
    """Convert display math $$...$$ to <me>...</me>"""
    def replace_display_math(match):
        content = match.group(1).strip()
        # Always use CDATA for display math
        return f'\n<me><![CDATA[{content}]]></me>\n'
    
    text = re.sub(r'\$\$([^\$]+)\$\$', replace_display_math, text, flags=re.DOTALL)
    return text

def process_emphasis(text):
    """Convert **bold** and *italic* to <em>"""
    # Handle bold
    text = re.sub(r'\*\*([^\*]+)\*\*', r'<em>\1</em>', text)
    text = re.sub(r'__([^_]+)__', r'<em>\1</em>', text)
    # Handle italic (but not already processed)
    text = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'<em>\1</em>', text)
    return text

def process_code_inline(text):
    """Convert `code` to <c>code</c>"""
    text = re.sub(r'`([^`]+)`', r'<c>\1</c>', text)
    return text

def process_references(text):
    """Convert \@ref(id) to <xref ref="id"/>"""
    text = re.sub(r'\\@ref\(([^)]+)\)', r'<xref ref="\1"/>', text)
    return text

def process_footnotes(text):
    """Convert ^[...] to <fn>...</fn>"""
    def replace_footnote(match):
        content = match.group(1)
        # Process the content
        content = process_inline_formatting(content)
        return f'<fn>{content}</fn>'
    
    text = re.sub(r'\^\[([^\]]+)\]', replace_footnote, text)
    return text

def process_inline_formatting(text):
    """Apply all inline formatting conversions"""
    text = process_emphasis(text)
    text = process_code_inline(text)
    text = process_math_inline(text)
    text = process_references(text)
    text = process_footnotes(text)
    return text

def escape_xml(text):
    """Escape special XML characters (but not in CDATA sections)"""
    # Don't escape if we're in a CDATA section
    if '<![CDATA[' in text:
        return text
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text

def main():
    input_file = '/home/runner/work/rbook/rbook/bookdown/05.14-anova.Rmd'
    output_file = '/home/runner/work/rbook/rbook/pretext/source/ch-anova.ptx'
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Start output
    output = ['<?xml version="1.0" encoding="UTF-8" ?>']
    output.append('')
    output.append('<chapter xml:id="anova">')
    output.append('  <title>Comparing several means (one-way ANOVA)</title>')
    output.append('')
    
    # Process content line by line
    lines = content.split('\n')
    i = 0
    in_code_block = False
    in_paragraph = False
    in_list = False
    code_block_lines = []
    paragraph_lines = []
    list_lines = []
    indent_level = 1
    
    while i < len(lines):
        line = lines[i]
        
        # Handle code blocks
        if line.startswith('```'):
            if not in_code_block:
                # Start code block
                in_code_block = True
                code_block_lines = []
                lang_match = re.search(r'```\{r([^}]*)\}', line)
                if lang_match:
                    # R code block
                    pass
                i += 1
                continue
            else:
                # End code block
                in_code_block = False
                # Output code block
                indent = '  ' * indent_level
                output.append(f'{indent}<program language="r">')
                output.append(f'{indent}  <input><![CDATA[')
                for code_line in code_block_lines:
                    output.append(code_line)
                output.append(f'{indent}]]></input>')
                output.append(f'{indent}</program>')
                code_block_lines = []
                i += 1
                continue
        
        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue
        
        # Skip YAML header and setup chunks
        if i < 10 and (line.startswith('---') or line.startswith('```{r, echo=FALSE')):
            if line.startswith('```{r, echo=FALSE'):
                # Skip to end of block
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    i += 1
            i += 1
            continue
        
        # Handle section headers
        if line.startswith('# ') and '{#' in line:
            # Chapter title - already handled
            i += 1
            continue
        
        if line.startswith('## ') and '{#' in line:
            # Section
            if in_paragraph:
                # Close any open paragraph
                output.append(f'{"  " * indent_level}<p>{" ".join(paragraph_lines)}</p>')
                paragraph_lines = []
                in_paragraph = False
            
            title_match = re.search(r'##\s+(.+?)\{#([^}]+)\}', line)
            if title_match:
                title = title_match.group(1).strip()
                xml_id = title_match.group(2)
                output.append(f'  <section xml:id="{xml_id}">')
                output.append(f'    <title>{title}</title>')
                output.append('')
                indent_level = 2
            i += 1
            continue
        
        if line.startswith('### ') and '{#' in line:
            # Subsection
            if in_paragraph:
                output.append(f'{"  " * indent_level}<p>{" ".join(paragraph_lines)}</p>')
                paragraph_lines = []
                in_paragraph = False
            
            title_match = re.search(r'###\s+(.+?)\{#([^}]+)\}', line)
            if title_match:
                title = title_match.group(1).strip()
                # Process any inline formatting in title
                title = process_math_inline(title)
                xml_id = title_match.group(2)
                output.append(f'    <subsection xml:id="{xml_id}">')
                output.append(f'      <title>{title}</title>')
                output.append('')
                indent_level = 3
            i += 1
            continue
        
        if line.startswith('### ') and '{#' not in line:
            # Subsection without id
            if in_paragraph:
                output.append(f'{"  " * indent_level}<p>{" ".join(paragraph_lines)}</p>')
                paragraph_lines = []
                in_paragraph = False
            
            title = line[4:].strip()
            title = process_math_inline(title)
            output.append(f'    <subsection>')
            output.append(f'      <title>{title}</title>')
            output.append('')
            indent_level = 3
            i += 1
            continue
        
        # Handle blockquotes
        if line.strip().startswith('>'):
            if in_paragraph:
                output.append(f'{"  " * indent_level}<p>{" ".join(paragraph_lines)}</p>')
                paragraph_lines = []
                in_paragraph = False
            
            # Collect blockquote lines
            blockquote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                blockquote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            
            # Process blockquote content
            bq_content = ' '.join(blockquote_lines)
            bq_content = process_inline_formatting(bq_content)
            bq_content = process_math_display(bq_content)
            
            indent = '  ' * indent_level
            output.append(f'{indent}<blockquote>')
            output.append(f'{indent}  <p>{bq_content}</p>')
            output.append(f'{indent}</blockquote>')
            continue
        
        # Handle empty lines
        if not line.strip():
            if in_paragraph:
                # End paragraph
                para_text = ' '.join(paragraph_lines)
                para_text = process_inline_formatting(para_text)
                para_text = process_math_display(para_text)
                indent = '  ' * indent_level
                output.append(f'{indent}<p>{para_text}</p>')
                paragraph_lines = []
                in_paragraph = False
            i += 1
            continue
        
        # Regular paragraph text
        if not in_paragraph:
            in_paragraph = True
        paragraph_lines.append(line.strip())
        i += 1
    
    # Close any remaining paragraph
    if in_paragraph and paragraph_lines:
        para_text = ' '.join(paragraph_lines)
        para_text = process_inline_formatting(para_text)
        para_text = process_math_display(para_text)
        indent = '  ' * indent_level
        output.append(f'{indent}<p>{para_text}</p>')
    
    # Close all sections
    output.append('    </subsection>')
    output.append('  </section>')
    output.append('</chapter>')
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print(f"Conversion complete: {output_file}")
    print(f"Lines in input: {len(lines)}")
    print(f"Lines in output: {len(output)}")

if __name__ == '__main__':
    main()
