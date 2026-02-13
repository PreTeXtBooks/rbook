#!/usr/bin/env python3
"""
Convert RMarkdown file to PreTeXt XML format.
Converts bookdown/05.16-anova2.Rmd to PreTeXt XML.
"""

import re
import sys

def process_inline_formatting(text, in_code=False):
    """Convert markdown inline formatting to PreTeXt."""
    if in_code:
        return text
    
    # Handle cross-references \@ref(id) -> <xref ref="id"/>
    text = re.sub(r'\\@ref\(([^)]+)\)', r'<xref ref="\1"/>', text)
    
    # Handle inline math $...$ -> <m>...</m>
    # But be careful not to match display math
    parts = []
    i = 0
    while i < len(text):
        if text[i] == '$' and (i == 0 or text[i-1] != '$') and (i+1 < len(text) and text[i+1] != '$'):
            # Find closing $
            j = i + 1
            while j < len(text) and text[j] != '$':
                j += 1
            if j < len(text):
                math_content = text[i+1:j]
                parts.append('<m>' + math_content + '</m>')
                i = j + 1
                continue
        parts.append(text[i])
        i += 1
    text = ''.join(parts)
    
    # Handle **bold** and _text_ first (including **_text_**)
    text = re.sub(r'\*\*_([^*_]+)_\*\*', r'<em>\1</em>', text)
    # Handle **text** 
    text = re.sub(r'\*\*([^*]+)\*\*', r'<em>\1</em>', text)
    # Handle _text_
    text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
    # Handle *text*
    text = re.sub(r'\*([^*\s][^*]*)\*', r'<em>\1</em>', text)
    
    # Handle footnotes ^[...] -> <fn>...</fn>
    def replace_footnote(match):
        content = match.group(1)
        content = process_inline_formatting(content, in_code=False)
        return f'<fn>{content}</fn>'
    text = re.sub(r'\^\[([^\]]+)\]', replace_footnote, text)
    
    return text

def convert_rmd_to_pretext(input_file, output_file):
    """Main conversion function."""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    output = []
    output.append('<?xml version="1.0" encoding="UTF-8" ?>\n\n')
    
    i = 0
    in_r_code = False
    r_code_buffer = []
    para_buffer = []
    
    # Track section depth
    section_stack = []
    
    def get_indent():
        return '  ' * (len(section_stack) + 1)
    
    def flush_paragraph():
        """Flush the paragraph buffer to output."""
        nonlocal para_buffer
        if para_buffer:
            content = ' '.join(para_buffer)
            content = process_inline_formatting(content)
            indent = get_indent()
            output.append(f'{indent}  <p>{content}</p>\n')
            para_buffer = []
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Handle chapter title
        if stripped.startswith('# ') and i == 0:
            match = re.match(r'#\s+([^{]+)\{#([^}]+)\}', stripped)
            if match:
                title = match.group(1).strip()
                xml_id = match.group(2)
                output.append(f'<chapter xml:id="{xml_id}">\n')
                output.append(f'  <title>{title}</title>\n\n')
            i += 1
            continue
        
        # Handle section headers
        if stripped.startswith('##'):
            flush_paragraph()
            
            # Close previous sections as needed
            level = len(re.match(r'^#+', stripped).group(0))
            
            while section_stack and section_stack[-1] >= level:
                section_stack.pop()
                indent = get_indent()
                if section_stack or level > 2:
                    output.append(f'{indent}</subsection>\n')
                else:
                    output.append(f'{indent}</section>\n')
            
            # Open new section
            match = re.match(r'#+\s+([^{]+)\{#([^}]+)\}', stripped)
            if not match:
                match = re.match(r'#+\s+(.+)$', stripped)
                if match:
                    title = match.group(1).strip()
                    # Process title for inline formatting  
                    title = process_inline_formatting(title)
                    xml_id = None
                else:
                    i += 1
                    continue
            else:
                title = match.group(1).strip()
                title = process_inline_formatting(title)
                xml_id = match.group(2)
            
            indent = get_indent()
            if level == 2:
                if xml_id:
                    output.append(f'{indent}<section xml:id="{xml_id}">\n')
                else:
                    output.append(f'{indent}<section>\n')
                output.append(f'{indent}  <title>{title}</title>\n\n')
            else:
                if xml_id:
                    output.append(f'{indent}<subsection xml:id="{xml_id}">\n')
                else:
                    output.append(f'{indent}<subsection>\n')
                output.append(f'{indent}  <title>{title}</title>\n\n')
            section_stack.append(level)
            i += 1
            continue
        
        # Handle R code blocks
        if stripped.startswith('```{r') or stripped == '```{r}':
            flush_paragraph()
            in_r_code = True
            r_code_buffer = []
            i += 1
            continue
        
        if in_r_code:
            if stripped == '```':
                # End of R code block
                in_r_code = False
                code_content = ''.join(r_code_buffer)
                indent = get_indent()
                output.append(f'{indent}  <program language="r">\n')
                output.append(f'{indent}    <input><![CDATA[\n')
                output.append(code_content)
                if not code_content.endswith('\n'):
                    output.append('\n')
                output.append(f'{indent}    ]]></input>\n')
                output.append(f'{indent}  </program>\n')
                r_code_buffer = []
            else:
                r_code_buffer.append(line)
            i += 1
            continue
        
        # Handle LaTeX environments like \begin{center}
        if stripped.startswith('\\begin{'):
            flush_paragraph()
            # Skip these environments - they're typically for formatting
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('\\end{'):
                # Capture the content
                content_line = lines[i].strip()
                if content_line and not content_line.startswith('\\'):
                    # It's code or content, keep it in paragraph
                    para_buffer.append(content_line)
                i += 1
            i += 1  # Skip the \end{} line
            continue
        
        # Handle display math $$...$$ on single line
        if stripped.startswith('$$') and stripped.endswith('$$') and len(stripped) > 4:
            flush_paragraph()
            math_content = stripped[2:-2].strip()
            indent = get_indent()
            output.append(f'{indent}  <me><![CDATA[{math_content}]]></me>\n')
            i += 1
            continue
        
        # Handle multi-line display math
        if stripped == '$$':
            flush_paragraph()
            # Collect math content
            i += 1
            math_lines = []
            while i < len(lines) and lines[i].strip() != '$$':
                math_lines.append(lines[i].rstrip())
                i += 1
            
            math_content = '\n'.join(math_lines)
            indent = get_indent()
            output.append(f'{indent}  <me><![CDATA[\n{math_content}\n{indent}  ]]></me>\n')
            i += 1
            continue
        
        # Handle empty lines
        if not stripped:
            flush_paragraph()
            i += 1
            continue
        
        # Regular paragraph text
        para_buffer.append(stripped)
        i += 1
    
    # Close any remaining paragraph
    flush_paragraph()
    
    # Close all open sections
    while section_stack:
        level = section_stack.pop()
        indent = get_indent()
        if level == 2:
            output.append(f'{indent}</section>\n')
        else:
            output.append(f'{indent}</subsection>\n')
    
    output.append('</chapter>\n')
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(output)
    
    print(f"Conversion complete: {output_file}")
    print(f"Total lines in output: {len(output)}")

if __name__ == '__main__':
    input_file = '/home/runner/work/rbook/rbook/bookdown/05.16-anova2.Rmd'
    output_file = '/home/runner/work/rbook/rbook/pretext/source/ch5-factorial-anova.ptx'
    
    convert_rmd_to_pretext(input_file, output_file)
