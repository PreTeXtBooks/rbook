#!/usr/bin/env python3
"""
Conversion of Part IV (Statistical theory) chapters from RMD to PreTeXt XML format:
- 04.09-probability.Rmd (660 lines) → ch-probability.ptx
- 04.10-estimation.Rmd (553 lines) → ch-estimation.ptx  
- 04.11-hypothesistesting.Rmd (508 lines) → ch-hypothesistesting.ptx
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
        text = text.replace(r'\$', '~~~LITERALDOLLAR~~~')
        
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
            if '&' in content or '<' in content or '>' in content or '\\begin' in content:
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
        
        # Restore code blocks
        for i, code in enumerate(code_parts):
            text = text.replace(f"~~~CODE{i}~~~", f'<c>{self.escape_xml_text(code)}</c>')
        
        # Restore literal dollar signs
        text = text.replace('~~~LITERALDOLLAR~~~', '$')
        
        return text
    
    def flush_paragraph(self):
        """Output accumulated paragraph"""
        if self.paragraph_lines:
            content = ' '.join(self.paragraph_lines).strip()
            if content:
                content = self.convert_inline_formatting(content)
                self.output.append(f'<p>{content}</p>')
            self.paragraph_lines = []
            self.in_paragraph = False
    
    def flush_list(self):
        """Output accumulated list"""
        if self.list_lines:
            tag = 'ul' if self.list_type == 'ul' else 'ol'
            self.output.append(f'<{tag}>')
            for item in self.list_lines:
                item = self.convert_inline_formatting(item)
                self.output.append(f'<li><p>{item}</p></li>')
            self.output.append(f'</{tag}>')
            self.list_lines = []
            self.list_type = None
            self.in_list = False
    
    def flush_blockquote(self):
        """Output accumulated blockquote"""
        if self.blockquote_lines:
            self.output.append('<blockquote>')
            content = ' '.join(self.blockquote_lines).strip()
            content = self.convert_inline_formatting(content)
            self.output.append(f'<p>{content}</p>')
            self.output.append('</blockquote>')
            self.blockquote_lines = []
            self.in_blockquote = False
    
    def flush_code_block(self):
        """Output accumulated code block"""
        if self.code_block_lines:
            code = '\n'.join(self.code_block_lines)
            
            # Check if it's R code
            if self.code_block_params.get('lang') == 'r':
                # Check for special output blocks
                echo = self.code_block_params.get('echo', 'TRUE').upper()
                eval_param = self.code_block_params.get('eval', 'TRUE').upper()
                
                if echo == 'FALSE' or eval_param == 'FALSE':
                    # This is output or a table
                    self.output.append('<console>')
                    self.output.append(f'<output><![CDATA[{code}]]></output>')
                    self.output.append('</console>')
                else:
                    # Regular R code
                    self.output.append('<program language="r">')
                    self.output.append(f'<input><![CDATA[{code}]]></input>')
                    self.output.append('</program>')
            else:
                # Plain text or other language
                self.output.append('<console>')
                self.output.append(f'<output><![CDATA[{code}]]></output>')
                self.output.append('</console>')
            
            self.code_block_lines = []
            self.code_block_params = {}
            self.in_code_block = False
    
    def close_sections(self, target_level):
        """Close sections down to target level"""
        while self.section_stack and self.section_stack[-1][0] >= target_level:
            _, tag = self.section_stack.pop()
            self.output.append(f'</{tag}>')
    
    def process_line(self, line):
        """Process a single line"""
        # Handle code blocks
        if line.startswith('```'):
            if self.in_code_block:
                self.flush_code_block()
            else:
                self.flush_paragraph()
                self.flush_list()
                self.flush_blockquote()
                
                # Parse code block parameters
                params_str = line[3:].strip()
                if params_str.startswith('{'):
                    # R code block with parameters
                    params_str = params_str[1:-1] if params_str.endswith('}') else params_str[1:]
                    parts = params_str.split(',')
                    self.code_block_params['lang'] = 'r'
                    for part in parts[1:]:
                        part = part.strip()
                        if '=' in part:
                            key, val = part.split('=', 1)
                            self.code_block_params[key.strip()] = val.strip()
                elif params_str:
                    self.code_block_params['lang'] = params_str
                
                self.in_code_block = True
            return
        
        if self.in_code_block:
            self.code_block_lines.append(line)
            return
        
        # Handle chapter/section headings
        heading_match = re.match(r'^(#{1,4})\s+(.+?)(?:\{#([^}]+)\})?\s*$', line)
        if heading_match:
            self.flush_paragraph()
            self.flush_list()
            self.flush_blockquote()
            
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            xml_id = heading_match.group(3)
            
            # Convert inline formatting in title
            title = self.convert_inline_formatting(title)
            
            # Close deeper sections
            self.close_sections(level)
            
            # Determine tag
            if level == 1:
                tag = 'chapter'
            elif level == 2:
                tag = 'section'
            elif level == 3:
                tag = 'subsection'
            else:
                tag = 'subsubsection'
            
            # Open new section
            if xml_id:
                self.output.append(f'<{tag} xml:id="{xml_id}">')
            else:
                self.output.append(f'<{tag}>')
            self.output.append(f'<title>{title}</title>')
            self.section_stack.append((level, tag))
            return
        
        # Handle blockquotes
        if line.startswith('>'):
            self.flush_paragraph()
            self.flush_list()
            
            content = line[1:].strip()
            if content:
                self.blockquote_lines.append(content)
            self.in_blockquote = True
            return
        elif self.in_blockquote and line.strip():
            # Continuation of blockquote content
            self.blockquote_lines.append(line.strip())
            return
        elif self.in_blockquote and not line.strip():
            self.flush_blockquote()
            return
        
        # Handle lists
        list_match = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.+)$', line)
        if list_match:
            self.flush_paragraph()
            
            indent = list_match.group(1)
            marker = list_match.group(2)
            content = list_match.group(3)
            
            # Determine list type
            new_list_type = 'ol' if marker[0].isdigit() else 'ul'
            
            # If switching list types, flush old list
            if self.in_list and self.list_type != new_list_type:
                self.flush_list()
            
            self.list_type = new_list_type
            self.list_lines.append(content)
            self.in_list = True
            return
        
        # Empty line - flush current paragraph/list/blockquote
        if not line.strip():
            self.flush_paragraph()
            self.flush_list()
            self.flush_blockquote()
            return
        
        # Regular paragraph text
        self.flush_list()
        self.flush_blockquote()
        
        self.paragraph_lines.append(line.strip())
        self.in_paragraph = True
    
    def convert(self, input_file, output_file):
        """Convert RMD file to PreTeXt XML"""
        print(f"Converting {input_file} to {output_file}...")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Add XML declaration
        self.output.append('<?xml version="1.0" encoding="UTF-8"?>')
        self.output.append('')
        
        # Process each line
        for line in lines:
            line = line.rstrip('\n')
            self.process_line(line)
        
        # Flush any remaining content
        self.flush_paragraph()
        self.flush_list()
        self.flush_blockquote()
        self.flush_code_block()
        
        # Close all open sections
        self.close_sections(0)
        
        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.output))
        
        print(f"✓ Converted {len(lines)} lines to {output_file}")
        return len(self.output)

def main():
    converter = RmdToPreTeXt()
    
    chapters = [
        ('bookdown/04.09-probability.Rmd', 'pretext/source/ch-probability.ptx'),
        ('bookdown/04.10-estimation.Rmd', 'pretext/source/ch-estimation.ptx'),
        ('bookdown/04.11-hypothesistesting.Rmd', 'pretext/source/ch-hypothesistesting.ptx'),
    ]
    
    print("=" * 70)
    print("Converting Part IV (Statistical theory) chapters to PreTeXt XML")
    print("=" * 70)
    print()
    
    for input_file, output_file in chapters:
        converter = RmdToPreTeXt()  # Fresh converter for each file
        lines = converter.convert(input_file, output_file)
        print()
    
    print("=" * 70)
    print("All conversions complete!")
    print("=" * 70)

if __name__ == '__main__':
    main()
