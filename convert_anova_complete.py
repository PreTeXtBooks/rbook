#!/usr/bin/env python3
"""
Complete conversion of 05.14-anova.Rmd to PreTeXt XML format.
Handles all markdown elements systematically.
"""

import re
import sys

def escape_xml(text):
    """Escape special XML characters, but preserve already-escaped entities."""
    # Don't escape if it's already an entity
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    # Fix double-escaping
    text = text.replace('&amp;lt;', '&lt;')
    text = text.replace('&amp;gt;', '&gt;')
    return text

def process_inline_formatting(text):
    """Convert inline markdown formatting to PreTeXt."""
    # Handle inline code first (before other formatting)
    text = re.sub(r'`([^`]+)`', r'<c>\1</c>', text)
    
    # Handle cross-references: \@ref(id) or Section \@ref(id)
    text = re.sub(r'\\@ref\(([^)]+)\)', r'<xref ref="\1"/>', text)
    
    # Handle footnotes: ^[text]
    def convert_footnote(match):
        content = match.group(1)
        content = process_inline_formatting(content)
        return f'<fn>{content}</fn>'
    text = re.sub(r'\^\[([^\]]+)\]', convert_footnote, text)
    
    # Handle bold+italic: ***text*** or ___text___
    text = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<em>\1</em>', text)
    text = re.sub(r'___([^_]+)___', r'<em>\1</em>', text)
    
    # Handle bold: **text** or __text__
    text = re.sub(r'\*\*([^*]+)\*\*', r'<em>\1</em>', text)
    text = re.sub(r'__([^_]+)__', r'<em>\1</em>', text)
    
    # Handle italic: *text* or _text_ (but not in math or already processed)
    text = re.sub(r'(?<![*_])\*([^*\n]+)\*(?![*_])', r'<em>\1</em>', text)
    text = re.sub(r'(?<![*_])_([^_\s][^_\n]*[^_\s])_(?![*_])', r'<em>\1</em>', text)
    
    return text

def process_inline_math(text):
    """Convert inline math $...$ to <m><![CDATA[...]]></m>."""
    # Match $...$ but not $$...$$
    def replace_math(match):
        math_content = match.group(1)
        return f'<m><![CDATA[{math_content}]]></m>'
    
    # Use negative lookbehind/ahead to avoid matching display math
    text = re.sub(r'(?<!\$)\$(?!\$)([^\$]+?)\$(?!\$)', replace_math, text)
    return text

def convert_display_math(text):
    """Convert display math $$...$$ to <me><![CDATA[...]]></me>."""
    return '<me><![CDATA[' + text + ']]></me>'

def convert_code_block(code):
    """Convert R code block to PreTeXt program."""
    return f'<program language="r">\n  <input><![CDATA[\n{code}]]></input>\n</program>'

def process_paragraph(text):
    """Process a paragraph with inline formatting and math."""
    text = text.strip()
    if not text:
        return ''
    
    # First handle inline math
    text = process_inline_math(text)
    
    # Then handle inline formatting
    text = process_inline_formatting(text)
    
    return f'<p>{text}</p>'

def convert_file(input_file, output_file):
    """Convert R Markdown file to PreTeXt XML."""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    output = []
    output.append('<?xml version="1.0" encoding="UTF-8" ?>\n')
    output.append('\n')
    
    i = 0
    in_code_block = False
    code_block = []
    in_display_math = False
    display_math = []
    in_list = False
    list_type = None
    list_items = []
    in_blockquote = False
    blockquote_lines = []
    paragraph_lines = []
    
    def flush_paragraph():
        """Flush accumulated paragraph lines."""
        nonlocal paragraph_lines
        if paragraph_lines:
            para_text = ' '.join(paragraph_lines).strip()
            if para_text:
                output.append('    ' + process_paragraph(para_text) + '\n')
            paragraph_lines = []
    
    def flush_list():
        """Flush accumulated list items."""
        nonlocal in_list, list_type, list_items
        if in_list and list_items:
            tag = 'ol' if list_type == 'ordered' else 'ul'
            output.append(f'    <{tag}>\n')
            for item in list_items:
                item_text = process_inline_math(item)
                item_text = process_inline_formatting(item_text)
                output.append(f'      <li><p>{item_text}</p></li>\n')
            output.append(f'    </{tag}>\n')
            in_list = False
            list_items = []
    
    def flush_blockquote():
        """Flush accumulated blockquote lines."""
        nonlocal in_blockquote, blockquote_lines
        if in_blockquote and blockquote_lines:
            output.append('    <blockquote>\n')
            bq_text = ' '.join(blockquote_lines).strip()
            bq_text = process_inline_math(bq_text)
            bq_text = process_inline_formatting(bq_text)
            output.append(f'      <p>{bq_text}</p>\n')
            output.append('    </blockquote>\n')
            in_blockquote = False
            blockquote_lines = []
    
    while i < len(lines):
        line = lines[i]
        
        # Handle chapter title (first line)
        if i == 0 and line.startswith('# '):
            match = re.match(r'# ([^{]+)\{#([^}]+)\}', line)
            if match:
                title = match.group(1).strip()
                xml_id = match.group(2)
                output.append(f'<chapter xml:id="{xml_id}">\n')
                output.append(f'  <title>{title}</title>\n\n')
            i += 1
            continue
        
        # Handle code blocks
        if line.startswith('```'):
            if not in_code_block:
                flush_paragraph()
                flush_list()
                flush_blockquote()
                in_code_block = True
                code_block = []
            else:
                in_code_block = False
                code_text = ''.join(code_block).rstrip()
                output.append('    ' + convert_code_block(code_text) + '\n')
                code_block = []
            i += 1
            continue
        
        if in_code_block:
            code_block.append(line)
            i += 1
            continue
        
        # Handle display math
        if line.strip().startswith('$$'):
            if not in_display_math:
                flush_paragraph()
                flush_list()
                flush_blockquote()
                in_display_math = True
                display_math = []
            else:
                in_display_math = False
                math_text = ''.join(display_math).strip()
                output.append('    ' + convert_display_math(math_text) + '\n')
                display_math = []
            i += 1
            continue
        
        if in_display_math:
            display_math.append(line)
            i += 1
            continue
        
        # Handle section headings
        section_match = re.match(r'^(#{2,})\s+(.+?)(?:\{#([^}]+)\})?\s*$', line)
        if section_match:
            flush_paragraph()
            flush_list()
            flush_blockquote()
            
            level = len(section_match.group(1))
            title = section_match.group(2).strip()
            section_id = section_match.group(3)
            
            # Process title formatting
            title = process_inline_math(title)
            title = process_inline_formatting(title)
            
            # Close previous sections as needed
            # (simplified - assumes proper nesting)
            
            if level == 2:
                tag = 'section'
            elif level == 3:
                tag = 'subsection'
            else:
                tag = 'subsubsection'
            
            if section_id:
                output.append(f'  <{tag} xml:id="{section_id}">\n')
            else:
                output.append(f'  <{tag}>\n')
            output.append(f'    <title>{title}</title>\n\n')
            
            i += 1
            continue
        
        # Handle blockquotes
        if line.startswith('> '):
            flush_paragraph()
            flush_list()
            if not in_blockquote:
                in_blockquote = True
                blockquote_lines = []
            blockquote_lines.append(line[2:].strip())
            i += 1
            continue
        elif in_blockquote and line.strip() == '':
            flush_blockquote()
            i += 1
            continue
        
        # Handle ordered lists
        if re.match(r'^\d+\.\s+', line):
            flush_paragraph()
            flush_blockquote()
            if not in_list or list_type != 'ordered':
                flush_list()
                in_list = True
                list_type = 'ordered'
                list_items = []
            item_text = re.sub(r'^\d+\.\s+', '', line).strip()
            list_items.append(item_text)
            i += 1
            continue
        
        # Handle unordered lists
        if re.match(r'^[\*\-]\s+', line):
            flush_paragraph()
            flush_blockquote()
            if not in_list or list_type != 'unordered':
                flush_list()
                in_list = True
                list_type = 'unordered'
                list_items = []
            item_text = re.sub(r'^[\*\-]\s+', '', line).strip()
            list_items.append(item_text)
            i += 1
            continue
        
        # Handle empty lines
        if line.strip() == '':
            flush_paragraph()
            flush_list()
            flush_blockquote()
            i += 1
            continue
        
        # Regular paragraph text
        flush_list()
        flush_blockquote()
        paragraph_lines.append(line.strip())
        i += 1
    
    # Flush any remaining content
    flush_paragraph()
    flush_list()
    flush_blockquote()
    
    # Close all open tags
    output.append('  </section>\n')
    output.append('</chapter>\n')
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(output)
    
    print(f"Conversion complete: {output_file}")

if __name__ == '__main__':
    input_file = '/home/runner/work/rbook/rbook/bookdown/05.14-anova.Rmd'
    output_file = '/home/runner/work/rbook/rbook/pretext/source/ch-anova.ptx'
    
    convert_file(input_file, output_file)
