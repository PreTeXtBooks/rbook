#!/usr/bin/env python3
"""
Conversion of 05.15-regression.Rmd to PreTeXt XML format (ch-regression.ptx)
Handles all 861 lines with proper structure
"""

import re
import sys

class RmdToPreTeXt:
    def __init__(self):
        self.output = []
        self.in_code_block = False
        self.code_block_lines = []
        self.code_block_params = {}
        self.in_paragraph = False
        self.paragraph_lines = []
        self.in_list = False
        self.list_lines = []
        self.list_type = None
        self.in_blockquote = False
        self.blockquote_lines = []
        self.section_stack = []
        
    def escape_xml_text(self, text):
        """Escape XML special characters in regular text"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text
    
    def convert_inline_formatting(self, text, escape=True):
        """Convert inline formatting - call BEFORE escaping XML"""
        # Protect escaped dollar signs (literal currency) FIRST
        text = text.replace(r'\$', '___LITERAL_DOLLAR___')
        
        # Protect code blocks temporarily
        code_parts = []
        def save_code(match):
            code_parts.append(match.group(1))
            return f"~~~CODE{len(code_parts)-1}~~~"
        text = re.sub(r'`([^`]+)`', save_code, text)
        
        # Convert display math $$...$$ to <me>...</me>
        math_display_parts = []
        def save_display_math(match):
            content = match.group(1).strip()
            # Use CDATA for LaTeX content to avoid XML parsing issues
            if '&' in content or '<' in content or '>' in content or '\\begin' in content or '\\array' in content:
                math_display_parts.append(f'<me><![CDATA[{content}]]></me>')
            else:
                math_display_parts.append(f'<me>{content}</me>')
            return f"~~~DISPMATH{len(math_display_parts)-1}~~~"
        text = re.sub(r'\$\$(.+?)\$\$', save_display_math, text, flags=re.DOTALL)
        
        # Convert inline math $...$ to <m>...</m>
        math_parts = []
        def save_inline_math(match):
            content = match.group(1)
            # Use CDATA for complex LaTeX
            if '&' in content or '<' in content or '>' in content:
                math_parts.append(f'<m><![CDATA[{content}]]></m>')
            else:
                math_parts.append(f'<m>{content}</m>')
            return f"~~~MATH{len(math_parts)-1}~~~"
        text = re.sub(r'\$([^\$]+?)\$', save_inline_math, text)
        
        # Escape XML AFTER protecting math and code
        if escape:
            text = self.escape_xml_text(text)
        
        # Convert markdown formatting
        # Bold + italic: ***text*** or **_text_** or _**text**_ 
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<em>\1</em>', text)
        text = re.sub(r'\*\*_(.+?)_\*\*', r'<em>\1</em>', text)
        text = re.sub(r'_\*\*(.+?)\*\*_', r'<em>\1</em>', text)
        
        # Bold: **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'<em>\1</em>', text)
        text = re.sub(r'__(.+?)__', r'<em>\1</em>', text)
        
        # Italic: *text* or _text_
        text = re.sub(r'\*([^\*]+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'(?<![_\w])_([^_]+?)_(?![_\w])', r'<em>\1</em>', text)
        
        # Cross-references: \@ref(id) -> <xref ref="id"/>
        text = re.sub(r'\\@ref\(([^)]+)\)', r'<xref ref="\1"/>', text)
        
        # Footnotes: ^[text] -> <fn>text</fn>
        def convert_footnote(match):
            content = match.group(1)
            content = self.convert_inline_formatting(content, escape=False)
            return f'<fn>{content}</fn>'
        text = re.sub(r'\^\[([^\]]+)\]', convert_footnote, text)
        
        # Restore display math
        for i, math in enumerate(math_display_parts):
            text = text.replace(f"~~~DISPMATH{i}~~~", math)
        
        # Restore inline math
        for i, math in enumerate(math_parts):
            text = text.replace(f"~~~MATH{i}~~~", math)
        
        # Restore code (escape XML chars in code content)
        for i, code in enumerate(code_parts):
            # Escape XML special characters in inline code
            code_escaped = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            text = text.replace(f"~~~CODE{i}~~~", f'<c>{code_escaped}</c>')
        
        # Restore literal dollar signs
        text = text.replace('___LITERAL_DOLLAR___', '$')
        
        return text
    
    def flush_paragraph(self):
        """Flush accumulated paragraph lines"""
        if self.paragraph_lines:
            content = ' '.join(self.paragraph_lines)
            content = self.convert_inline_formatting(content)
            self.output.append(f"    <p>{content}</p>")
            self.paragraph_lines = []
            self.in_paragraph = False
    
    def flush_blockquote(self):
        """Flush accumulated blockquote lines"""
        if self.blockquote_lines:
            # Join lines and process
            content = ' '.join(self.blockquote_lines)
            content = self.convert_inline_formatting(content)
            
            # Check if there's an attribution (-- Author pattern)
            if ' -- ' in content or ' <mdash/> ' in content:
                parts = content.split(' -- ') if ' -- ' in content else content.split(' <mdash/> ')
                if len(parts) == 2:
                    text_part = parts[0].strip()
                    author_part = parts[1].strip()
                    self.output.append(f'    <blockquote>')
                    self.output.append(f'      <p>{text_part}</p>')
                    self.output.append(f'    </blockquote>')
                else:
                    self.output.append(f'    <blockquote>')
                    self.output.append(f'      <p>{content}</p>')
                    self.output.append(f'    </blockquote>')
            else:
                self.output.append(f'    <blockquote>')
                self.output.append(f'      <p>{content}</p>')
                self.output.append(f'    </blockquote>')
            
            self.blockquote_lines = []
            self.in_blockquote = False
    
    def flush_list(self):
        """Flush accumulated list lines"""
        if not self.list_lines:
            return
        
        list_tag = 'ul' if self.list_type == 'unordered' else 'ol'
        self.output.append(f"    <{list_tag}>")
        
        for item in self.list_lines:
            content = self.convert_inline_formatting(item)
            self.output.append(f"      <li><p>{content}</p></li>")
        
        self.output.append(f"    </{list_tag}>")
        self.list_lines = []
        self.in_list = False
        self.list_type = None
    
    def flush_code_block(self):
        """Flush accumulated code block"""
        if self.code_block_lines:
            # Check if it's an output block
            is_output = self.code_block_params.get('output', False)
            
            # Join code lines
            code_content = '\n'.join(self.code_block_lines)
            
            if is_output:
                # Output blocks need XML escaping or CDATA
                # Use CDATA for output blocks to preserve formatting
                self.output.append('    <pre><![CDATA[')
                self.output.append(code_content)
                self.output.append(']]></pre>')
            else:
                # Use CDATA to avoid issues with < and & in code
                self.output.append('    <program language="r">')
                self.output.append('      <input><![CDATA[')
                self.output.append(code_content)
                self.output.append(']]></input>')
                self.output.append('    </program>')
            
            self.code_block_lines = []
            self.in_code_block = False
            self.code_block_params = {}
    
    def process_line(self, line):
        """Process a single line"""
        # Handle code blocks
        if line.startswith('```{r'):
            self.flush_paragraph()
            self.flush_blockquote()
            self.flush_list()
            self.in_code_block = True
            # Extract parameters
            params_match = re.search(r'```\{r\s+([^}]*)\}', line)
            if params_match:
                params = params_match.group(1)
                # Parse parameters
                for param in params.split(','):
                    param = param.strip()
                    if '=' in param:
                        key, val = param.split('=', 1)
                        self.code_block_params[key.strip()] = val.strip()
            return
        elif line.strip() == '```' and not self.in_code_block:
            # Start of plain code block (output block)
            self.flush_paragraph()
            self.flush_blockquote()
            self.flush_list()
            self.in_code_block = True
            self.code_block_params['output'] = True
            return
        elif line.strip() == '```' and self.in_code_block:
            self.flush_code_block()
            return
        elif self.in_code_block:
            self.code_block_lines.append(line)
            return
        
        # Handle blockquote
        if line.startswith('> '):
            self.flush_paragraph()
            self.flush_list()
            self.in_blockquote = True
            content = line[2:].strip()
            self.blockquote_lines.append(content)
            return
        elif self.in_blockquote and line.strip():
            if line.startswith('>'):
                content = line[1:].strip()
                self.blockquote_lines.append(content)
            else:
                self.blockquote_lines.append(line.strip())
            return
        elif self.in_blockquote and not line.strip():
            self.flush_blockquote()
            return
        
        # Handle headers
        if line.startswith('# '):
            self.flush_paragraph()
            self.flush_blockquote()
            self.flush_list()
            # Extract title and ID
            match = re.match(r'#\s+(.+?)\{#([^}]+)\}', line)
            if match:
                title = match.group(1).strip()
                xml_id = match.group(2)
                title = self.convert_inline_formatting(title)
                self.output.append(f'<chapter xml:id="{xml_id}">')
                self.output.append(f'  <title>{title}</title>')
                self.output.append('')
                self.section_stack = ['chapter']
            return
        
        elif line.startswith('## '):
            self.flush_paragraph()
            self.flush_blockquote()
            self.flush_list()
            match = re.match(r'##\s+(.+?)(?:\{#([^}]+)\})?$', line)
            if match:
                title = match.group(1).strip()
                xml_id = match.group(2) if match.group(2) else None
                title = self.convert_inline_formatting(title)
                
                # Close any open subsections first
                while len(self.section_stack) > 2:
                    level = self.section_stack.pop()
                    if level == 'subsection':
                        self.output.append('    </subsection>')
                
                # Close previous section if needed (but not chapter)
                if len(self.section_stack) > 1 and self.section_stack[-1] == 'section':
                    self.section_stack.pop()
                    self.output.append('  </section>')
                
                if xml_id:
                    self.output.append(f'  <section xml:id="{xml_id}">')
                else:
                    self.output.append(f'  <section>')
                self.output.append(f'    <title>{title}</title>')
                self.output.append('')
                
                self.section_stack.append('section')
            return
        
        elif line.startswith('### '):
            self.flush_paragraph()
            self.flush_blockquote()
            self.flush_list()
            match = re.match(r'###\s+(.+?)(?:\{#([^}]+)\})?$', line)
            if match:
                title = match.group(1).strip()
                xml_id = match.group(2) if match.group(2) else None
                title = self.convert_inline_formatting(title)
                
                # Close any existing subsection (but not section or chapter)
                if len(self.section_stack) > 2 and self.section_stack[-1] == 'subsection':
                    self.section_stack.pop()
                    self.output.append('    </subsection>')
                
                if xml_id:
                    self.output.append(f'    <subsection xml:id="{xml_id}">')
                else:
                    self.output.append(f'    <subsection>')
                self.output.append(f'      <title>{title}</title>')
                self.output.append('')
                
                self.section_stack.append('subsection')
            return
        
        # Handle lists
        if re.match(r'^[-*]\s+', line):
            if not self.in_list:
                self.flush_paragraph()
                self.flush_blockquote()
                self.in_list = True
                self.list_type = 'unordered'
            item = re.sub(r'^[-*]\s+', '', line).strip()
            self.list_lines.append(item)
            return
        elif re.match(r'^\d+\.\s+', line):
            if not self.in_list:
                self.flush_paragraph()
                self.flush_blockquote()
                self.in_list = True
                self.list_type = 'ordered'
            item = re.sub(r'^\d+\.\s+', '', line).strip()
            self.list_lines.append(item)
            return
        elif self.in_list and line.strip() and not line.startswith(' '):
            # Continue list item on next line
            if self.list_lines:
                self.list_lines[-1] += ' ' + line.strip()
            return
        elif self.in_list and not line.strip():
            self.flush_list()
            return
        
        # Handle empty lines
        if not line.strip():
            self.flush_paragraph()
            self.flush_blockquote()
            self.flush_list()
            return
        
        # Handle regular paragraph text
        if not self.in_paragraph:
            self.in_paragraph = True
        self.paragraph_lines.append(line.strip())
    
    def finalize(self):
        """Finalize conversion and close all open tags"""
        self.flush_paragraph()
        self.flush_blockquote()
        self.flush_list()
        self.flush_code_block()
        
        # Close all open sections
        while len(self.section_stack) > 0:
            level = self.section_stack.pop()
            if level == 'subsection':
                self.output.append('    </subsection>')
            elif level == 'section':
                self.output.append('  </section>')
            elif level == 'chapter':
                self.output.append('</chapter>')
    
    def convert(self, input_file, output_file):
        """Main conversion method"""
        # Add XML header
        self.output.append('<?xml version="1.0" encoding="UTF-8" ?>')
        self.output.append('')
        
        # Read and process input file
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                self.process_line(line)
        
        # Finalize
        self.finalize()
        
        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.output))
        
        print(f"Conversion complete: {output_file}")
        print(f"Total lines: {len(self.output)}")

if __name__ == '__main__':
    converter = RmdToPreTeXt()
    input_file = 'bookdown/05.15-regression.Rmd'
    output_file = 'pretext/source/ch-regression.ptx'
    converter.convert(input_file, output_file)
