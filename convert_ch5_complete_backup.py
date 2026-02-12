#!/usr/bin/env python3
"""
Complete conversion of 03.05-descriptives.Rmd to PreTeXt XML format
Handles all 1374 lines with proper structure
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
        self.list_type = None  # 'ul' or 'ol'
        self.in_blockquote = False
        self.blockquote_lines = []
        self.section_stack = []  # Track open sections
        
    def escape_xml_text(self, text):
        """Escape XML special characters in regular text"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text
    
    def convert_inline_formatting(self, text, escape=True):
        """Convert inline formatting - call BEFORE escaping XML"""
        # Protect code blocks temporarily
        code_parts = []
        def save_code(match):
            code_parts.append(match.group(1))
            return f"__CODE_{len(code_parts)-1}__"
        text = re.sub(r'`([^`]+)`', save_code, text)
        
        # Protect math temporarily
        math_parts = []
        def save_math(match):
            math_parts.append(match.group(0))
            return f"__MATH_{len(math_parts)-1}__"
        text = re.sub(r'\$\$[^$]+\$\$|\$[^$]+\$', save_math, text)
        
        # Now escape XML if needed
        if escape:
            text = self.escape_xml_text(text)
        
        # Convert ***term*** and **_term_** to <term>
        text = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<term>\1</term>', text)
        text = re.sub(r'\*\*_([^_]+)_\*\*', r'<term>\1</term>', text)
        
        # Convert **bold** to <em>
        text = re.sub(r'\*\*([^*]+)\*\*', r'<em>\1</em>', text)
        
        # Convert -- to <mdash />
        text = text.replace(' -- ', ' <mdash /> ')
        
        # Restore code as <c>code</c>
        for i, code in enumerate(code_parts):
            text = text.replace(f"__CODE_{i}__", f'<c>{code}</c>')
        
        # Restore math
        for i, math in enumerate(math_parts):
            text = text.replace(f"__MATH_{i}__", math)
        
        return text
    
    def convert_math(self, text):
        """Convert math notation"""
        # Display math: $$...$$ to <me>...</me>
        text = re.sub(r'\$\$(.*?)\$\$', r'<me>\1</me>', text, flags=re.DOTALL)
        # Inline math: $...$ to <m>...</m>
        text = re.sub(r'\$([^$]+)\$', r'<m>\1</m>', text)
        return text
    
    def convert_cross_refs(self, text):
        """Convert cross-references"""
        # Chapter/Section at start
        text = re.sub(r'Chapter \\@ref\(([^)]+)\)', 
                     lambda m: f'<xref ref="{m.group(1).replace("_", "-")}" />', text)
        text = re.sub(r'Section \\@ref\(([^)]+)\)', 
                     lambda m: f'<xref ref="{m.group(1).replace("_", "-")}" />', text)
        # Figure references
        text = re.sub(r'Figure \\@ref\(fig:([^)]+)\)', 
                     lambda m: f'<xref ref="fig-{m.group(1).replace("_", "-")}" />', text)
        text = re.sub(r'\\@ref\(fig:([^)]+)\)', 
                     lambda m: f'<xref ref="fig-{m.group(1).replace("_", "-")}" />', text)
        # Table references
        text = re.sub(r'Table \\@ref\(tab:([^)]+)\)', 
                     lambda m: f'<xref ref="table-{m.group(1).replace("_", "-")}" />', text)
        text = re.sub(r'\\@ref\(tab:([^)]+)\)', 
                     lambda m: f'<xref ref="table-{m.group(1).replace("_", "-")}" />', text)
        # Generic references
        text = re.sub(r'\\@ref\(([^)]+)\)', 
                     lambda m: f'<xref ref="{m.group(1).replace("_", "-")}" />', text)
        return text
    
    def convert_footnotes(self, text):
        """Convert footnotes"""
        text = re.sub(r'\^\[([^\]]+)\]', r'<fn>\1</fn>', text)
        return text
    
    def process_text_line(self, text):
        """Process all inline conversions"""
        text = self.convert_inline_formatting(text)
        text = self.convert_math(text)
        text = self.convert_cross_refs(text)
        text = self.convert_footnotes(text)
        return text
    
    def flush_paragraph(self):
        """Output accumulated paragraph"""
        if self.paragraph_lines:
            para_text = ' '.join(self.paragraph_lines)
            para_text = self.process_text_line(para_text)
            indent = '  ' * (len(self.section_stack) + 2)
            self.output.append(f'{indent}<p>')
            self.output.append(f'{indent}  {para_text}')
            self.output.append(f'{indent}</p>')
            self.paragraph_lines = []
        self.in_paragraph = False
    
    def flush_list(self):
        """Output accumulated list"""
        if self.list_lines:
            indent = '  ' * (len(self.section_stack) + 2)
            self.output.append(f'{indent}<{self.list_type}>')
            for item in self.list_lines:
                item_text = self.process_text_line(item)
                self.output.append(f'{indent}  <li>')
                self.output.append(f'{indent}    <p>{item_text}</p>')
                self.output.append(f'{indent}  </li>')
            self.output.append(f'{indent}</{self.list_type}>')
            self.list_lines = []
        self.in_list = False
        self.list_type = None
    
    def flush_blockquote(self):
        """Output accumulated blockquote"""
        if self.blockquote_lines:
            quote_text = ' '.join(self.blockquote_lines)
            quote_text = self.process_text_line(quote_text)
            indent = '  ' * (len(self.section_stack) + 2)
            self.output.append(f'{indent}<blockquote>')
            self.output.append(f'{indent}  <p>{quote_text}</p>')
            self.output.append(f'{indent}</blockquote>')
            self.blockquote_lines = []
        self.in_blockquote = False
    
    def close_sections_to_level(self, target_level):
        """Close sections down to target level"""
        while len(self.section_stack) > target_level:
            section_info = self.section_stack.pop()
            indent = '  ' * (len(self.section_stack) + 1)
            self.output.append(f'{indent}</{section_info["type"]}>')
    
    def process_heading(self, line):
        """Process markdown heading"""
        self.flush_paragraph()
        self.flush_list()
        self.flush_blockquote()
        
        match = re.match(r'^(#{1,4})\s+(.+?)(?:\{#([^}]+)\})?\s*$', line)
        if not match:
            return
        
        level = len(match.group(1))
        title = match.group(2).strip()
        xml_id = match.group(3) if match.group(3) else None
        
        # Process title formatting
        title = self.convert_inline_formatting(title, escape=False)
        title = self.convert_math(title)
        
        if level == 1:
            # Chapter title - already handled
            return
        elif level == 2:
            # Close subsections and subsubsections, but not the section itself
            self.close_sections_to_level(1)
            section_type = 'section'
            stack_level = 1
        elif level == 3:
            # Close subsubsections if any, keep section and possibly subsection
            self.close_sections_to_level(2)
            section_type = 'subsection'
            stack_level = 2
        elif level == 4:
            # Close previous subsubsection, keep section and subsection
            self.close_sections_to_level(3)
            section_type = 'subsubsection'
            stack_level = 3
        
        # Ensure we're at the right level
        self.close_sections_to_level(stack_level)
        
        # Add new section
        indent = '  ' * (len(self.section_stack) + 1)
        if xml_id:
            xml_id = xml_id.replace('_', '-')
            self.output.append(f'{indent}<{section_type} xml:id="{xml_id}">')
        else:
            self.output.append(f'{indent}<{section_type}>')
        self.output.append(f'{indent}  <title>{title}</title>')
        
        self.section_stack.append({'type': section_type, 'level': stack_level})
    
    def process_code_block(self):
        """Process accumulated code block"""
        if not self.code_block_lines:
            return
        
        params = self.code_block_params
        fig_cap = params.get('fig.cap', '')
        echo = params.get('echo', True)
        label = params.get('label', '')
        include_graphics = None
        
        # Check if this is an include_graphics call
        code_text = '\n'.join(self.code_block_lines)
        graphics_match = re.search(r'include_graphics\(["\']([^"\']+)["\']\)', code_text)
        if graphics_match:
            include_graphics = graphics_match.group(1)
        
        indent = '  ' * (len(self.section_stack) + 2)
        
        # If there's a figure caption, create a figure
        if fig_cap:
            fig_id = f'fig-{label}' if label else ''
            if fig_id:
                self.output.append(f'{indent}<figure xml:id="{fig_id}">')
            else:
                self.output.append(f'{indent}<figure>')
            
            caption = self.process_text_line(fig_cap.strip('"\''))
            self.output.append(f'{indent}  <caption>{caption}</caption>')
            
            # Determine image source
            if include_graphics:
                image_src = include_graphics.replace('./img/', 'images/')
            elif label:
                image_src = f'generated/{label}.png'
            else:
                image_src = 'generated/plot.png'
            
            self.output.append(f'{indent}  <image source="{image_src}"/>')
            self.output.append(f'{indent}</figure>')
            
            # Add R code in a remark if echo != FALSE
            if echo and echo != 'FALSE':
                self.output.append(f'{indent}<remark>')
                self.output.append(f'{indent}  <title>R Code</title>')
                self.output.append(f'{indent}  <program language="r">')
                self.output.append(f'{indent}    <input>')
                for line in self.code_block_lines:
                    self.output.append(f'{indent}      {line}')
                self.output.append(f'{indent}    </input>')
                self.output.append(f'{indent}  </program>')
                self.output.append(f'{indent}</remark>')
        else:
            # Regular code block
            self.output.append(f'{indent}<program language="r">')
            self.output.append(f'{indent}  <input>')
            for line in self.code_block_lines:
                self.output.append(f'{indent}    {line}')
            self.output.append(f'{indent}  </input>')
            self.output.append(f'{indent}</program>')
        
        self.code_block_lines = []
        self.code_block_params = {}
    
    def process_table(self, lines, start_idx):
        """Process a knitr::kable table"""
        # Find the end of the R code block
        end_idx = start_idx
        while end_idx < len(lines) and not lines[end_idx].strip().startswith('```'):
            end_idx += 1
        
        # Extract table parameters from knitr::kable call
        code_block = '\n'.join(lines[start_idx:end_idx])
        
        # Try to extract caption and data
        caption_match = re.search(r'col\.names\s*=\s*c\((.*?)\)', code_block, re.DOTALL)
        
        # For now, create a placeholder table structure
        indent = '  ' * (len(self.section_stack) + 2)
        self.output.append(f'{indent}<table>')
        self.output.append(f'{indent}  <title>Table</title>')
        self.output.append(f'{indent}  <tabular>')
        self.output.append(f'{indent}    <row>')
        self.output.append(f'{indent}      <cell>See R code for table contents</cell>')
        self.output.append(f'{indent}    </row>')
        self.output.append(f'{indent}  </tabular>')
        self.output.append(f'{indent}</table>')
        
        return end_idx + 1
    
    def convert(self, input_file, output_file):
        """Main conversion function"""
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Start XML document
        self.output.append('<?xml version="1.0" encoding="UTF-8" ?>')
        self.output.append('')
        self.output.append('<chapter xml:id="ch5-descriptive-statistics">')
        self.output.append('  <title>Descriptive statistics</title>')
        
        i = 0
        skip_yaml = False
        
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Skip YAML header
            if line.strip() == '---':
                if not skip_yaml:
                    skip_yaml = True
                    i += 1
                    continue
                else:
                    skip_yaml = False
                    i += 1
                    continue
            if skip_yaml:
                i += 1
                continue
            
            # Handle code blocks
            if line.strip().startswith('```'):
                if not self.in_code_block:
                    # Starting code block
                    self.flush_paragraph()
                    self.flush_list()
                    self.flush_blockquote()
                    
                    self.in_code_block = True
                    self.code_block_lines = []
                    
                    # Parse code block parameters
                    code_match = re.match(r'```\{r\s*([^}]*)\}', line)
                    if code_match:
                        params_str = code_match.group(1).strip()
                        # Parse parameters
                        self.code_block_params = {}
                        
                        # Get label (first unnamed parameter)
                        parts = re.split(r',\s*', params_str)
                        for j, part in enumerate(parts):
                            if '=' in part:
                                key, val = part.split('=', 1)
                                self.code_block_params[key.strip()] = val.strip()
                            elif j == 0 and part:
                                self.code_block_params['label'] = part.strip()
                else:
                    # Ending code block
                    self.in_code_block = False
                    self.process_code_block()
                
                i += 1
                continue
            
            if self.in_code_block:
                self.code_block_lines.append(line)
                i += 1
                continue
            
            # Handle headings
            if line.startswith('#'):
                self.process_heading(line)
                i += 1
                continue
            
            # Handle blockquotes
            if line.startswith('>'):
                self.flush_paragraph()
                self.flush_list()
                
                if not self.in_blockquote:
                    self.in_blockquote = True
                    self.blockquote_lines = []
                
                quote_text = line[1:].strip()
                if quote_text:
                    self.blockquote_lines.append(quote_text)
                i += 1
                continue
            else:
                if self.in_blockquote:
                    self.flush_blockquote()
            
            # Handle lists
            list_match = re.match(r'^(\s*)[-*]\s+(.+)$', line)
            if list_match:
                self.flush_paragraph()
                self.flush_blockquote()
                
                if not self.in_list:
                    self.in_list = True
                    self.list_type = 'ul'
                    self.list_lines = []
                
                item_text = list_match.group(2)
                self.list_lines.append(item_text)
                i += 1
                continue
            
            # Numbered lists
            num_list_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
            if num_list_match:
                self.flush_paragraph()
                self.flush_blockquote()
                
                if not self.in_list:
                    self.in_list = True
                    self.list_type = 'ol'
                    self.list_lines = []
                
                item_text = num_list_match.group(2)
                self.list_lines.append(item_text)
                i += 1
                continue
            
            # If we had a list, check if it continues
            if self.in_list and not line.strip():
                # Empty line might end list, but check next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1].rstrip()
                    if not re.match(r'^(\s*)[-*]\s+', next_line) and not re.match(r'^(\s*)\d+\.\s+', next_line):
                        self.flush_list()
                else:
                    self.flush_list()
            elif self.in_list and line.strip():
                # Non-empty, non-list line ends the list
                self.flush_list()
            
            # Handle blank lines
            if not line.strip():
                if self.in_paragraph:
                    self.flush_paragraph()
                i += 1
                continue
            
            # Regular paragraph text
            if not self.in_list and not self.in_blockquote:
                if not self.in_paragraph:
                    self.in_paragraph = True
                    self.paragraph_lines = []
                
                self.paragraph_lines.append(line.strip())
            
            i += 1
        
        # Flush any remaining content
        self.flush_paragraph()
        self.flush_list()
        self.flush_blockquote()
        
        # Close all remaining sections
        self.close_sections_to_level(0)
        
        # Close chapter
        self.output.append('</chapter>')
        
        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.output))
        
        print(f"Conversion complete: {output_file}")
        print(f"Generated {len(self.output)} lines of XML")

def main():
    input_file = '/home/runner/work/rbook/rbook/bookdown/03.05-descriptives.Rmd'
    output_file = '/home/runner/work/rbook/rbook/pretext/source/ch5-descriptive-statistics.ptx'
    
    converter = RmdToPreTeXt()
    converter.convert(input_file, output_file)

if __name__ == '__main__':
    main()
