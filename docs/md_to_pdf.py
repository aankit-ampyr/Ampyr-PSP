"""
Markdown-to-PDF converter for PSP Technical Reference.
Uses ReportLab Platypus for professional PDF generation.
"""
import re
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white, Color
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Preformatted, KeepTogether, HRFlowable, ListFlowable, ListItem,
    NextPageTemplate, PageTemplate, Frame, BaseDocTemplate
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ── Colour palette ──────────────────────────────────────────────
AMPYR_DARK   = HexColor('#1a1a2e')
AMPYR_BLUE   = HexColor('#16213e')
AMPYR_ACCENT = HexColor('#0f3460')
AMPYR_TEAL   = HexColor('#00a8cc')
AMPYR_ORANGE = HexColor('#e94560')
GREY_BG      = HexColor('#f4f4f8')
CODE_BG      = HexColor('#282c34')
TABLE_HEADER = HexColor('#16213e')
TABLE_ALT    = HexColor('#f0f4f8')
LINK_BLUE    = HexColor('#0066cc')


def build_styles():
    """Create all paragraph styles used in the document."""
    styles = getSampleStyleSheet()

    # Override defaults
    styles['Normal'].fontSize = 9.5
    styles['Normal'].leading = 13
    styles['Normal'].alignment = TA_JUSTIFY
    styles['Normal'].spaceAfter = 4

    # Title page
    styles.add(ParagraphStyle(
        'DocTitle', parent=styles['Title'],
        fontSize=28, leading=34, textColor=AMPYR_DARK,
        spaceAfter=6, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        'DocSubtitle', parent=styles['Normal'],
        fontSize=14, leading=18, textColor=AMPYR_ACCENT,
        spaceAfter=20, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        'MetaField', parent=styles['Normal'],
        fontSize=10, leading=14, textColor=HexColor('#555555'),
    ))

    # Headings
    styles.add(ParagraphStyle(
        'H1', parent=styles['Heading1'],
        fontSize=20, leading=26, textColor=AMPYR_DARK,
        spaceBefore=24, spaceAfter=10,
        borderWidth=0, borderPadding=0,
    ))
    styles.add(ParagraphStyle(
        'H2', parent=styles['Heading2'],
        fontSize=16, leading=21, textColor=AMPYR_BLUE,
        spaceBefore=18, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        'H3', parent=styles['Heading3'],
        fontSize=13, leading=17, textColor=AMPYR_ACCENT,
        spaceBefore=12, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'H4', parent=styles['Heading4'],
        fontSize=11, leading=15, textColor=HexColor('#333344'),
        spaceBefore=10, spaceAfter=4,
    ))

    # Code block
    styles.add(ParagraphStyle(
        'CodeBlock', parent=styles['Code'],
        fontSize=7.5, leading=10,
        fontName='Courier', textColor=HexColor('#abb2bf'),
        backColor=CODE_BG, borderWidth=0.5,
        borderColor=HexColor('#3e4451'), borderPadding=6,
        spaceBefore=4, spaceAfter=6,
        leftIndent=8, rightIndent=8,
    ))

    # Inline code within paragraph
    styles.add(ParagraphStyle(
        'InlineCode', parent=styles['Normal'],
        fontName='Courier', fontSize=8.5,
        backColor=GREY_BG,
    ))

    # Bullet / list items
    styles.add(ParagraphStyle(
        'BulletItem', parent=styles['Normal'],
        fontSize=9.5, leading=13,
        leftIndent=16, bulletIndent=6,
        spaceBefore=1, spaceAfter=1,
    ))
    styles.add(ParagraphStyle(
        'BulletItem2', parent=styles['Normal'],
        fontSize=9.5, leading=13,
        leftIndent=32, bulletIndent=22,
        spaceBefore=1, spaceAfter=1,
    ))
    styles.add(ParagraphStyle(
        'BulletItem3', parent=styles['Normal'],
        fontSize=9.5, leading=13,
        leftIndent=48, bulletIndent=38,
        spaceBefore=1, spaceAfter=1,
    ))

    # Table cells
    styles.add(ParagraphStyle(
        'TableHeader', parent=styles['Normal'],
        fontSize=8.5, leading=11, fontName='Helvetica-Bold',
        textColor=white, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontSize=8.5, leading=11, alignment=TA_LEFT,
        spaceBefore=0, spaceAfter=0,
    ))

    # Footer
    styles.add(ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=7.5, textColor=HexColor('#888888'),
        alignment=TA_CENTER,
    ))

    return styles


# ── Markdown inline formatting ──────────────────────────────────

def escape_xml(text):
    """Escape XML special characters but preserve our tags."""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def format_inline(text):
    """Convert markdown inline formatting to ReportLab XML tags."""
    # Escape XML first
    text = escape_xml(text)

    # Bold+Italic (***text*** or ___text___)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)

    # Bold (**text** or __text__)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Italic (*text* or _text_) — avoid matching inside words with underscores
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'<i>\1</i>', text)

    # Inline code (`text`) — use courier font
    text = re.sub(r'`([^`]+)`', r'<font face="Courier" size="8">\1</font>', text)

    # Links [text](url) — just show text in blue
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'<font color="#0066cc">\1</font>', text)

    # Em dash
    text = text.replace(' --- ', ' -- ')

    return text


# ── Markdown parser ─────────────────────────────────────────────

class MarkdownToPDF:
    def __init__(self, md_path, pdf_path):
        self.md_path = Path(md_path)
        self.pdf_path = Path(pdf_path)
        self.styles = build_styles()
        self.story = []
        self.lines = []
        self.idx = 0

    def parse(self):
        """Read markdown and convert to ReportLab flowables."""
        raw = self.md_path.read_text(encoding='utf-8')
        self.lines = raw.split('\n')
        self.idx = 0

        # Build title page
        self._build_title_page()

        # Parse body
        while self.idx < len(self.lines):
            line = self.lines[self.idx]

            # Horizontal rule
            if re.match(r'^---+\s*$', line):
                self.story.append(Spacer(1, 4))
                self.story.append(HRFlowable(
                    width="100%", thickness=0.5,
                    color=HexColor('#cccccc'), spaceBefore=4, spaceAfter=8
                ))
                self.idx += 1
                continue

            # Code block
            if line.strip().startswith('```'):
                self._parse_code_block()
                continue

            # Table
            if '|' in line and self.idx + 1 < len(self.lines) and '---' in self.lines[self.idx + 1]:
                self._parse_table()
                continue

            # Headings
            heading_match = re.match(r'^(#{1,4})\s+(.*)', line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                style_name = f'H{level}'
                formatted = format_inline(text)

                if level == 1:
                    self.story.append(PageBreak())

                self.story.append(Paragraph(formatted, self.styles[style_name]))

                # Add accent line under H1
                if level == 1:
                    self.story.append(HRFlowable(
                        width="30%", thickness=2,
                        color=AMPYR_TEAL, spaceBefore=2, spaceAfter=8,
                        hAlign='LEFT'
                    ))

                self.idx += 1
                continue

            # Bullet / list items
            bullet_match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)', line)
            if bullet_match:
                self._parse_list_item(bullet_match)
                continue

            # Empty line
            if not line.strip():
                self.story.append(Spacer(1, 4))
                self.idx += 1
                continue

            # Normal paragraph — collect consecutive lines
            self._parse_paragraph()

    def _build_title_page(self):
        """Create a professional title page."""
        self.story.append(Spacer(1, 60))
        self.story.append(Paragraph(
            "Ampyr-PSP Technical Reference",
            self.styles['DocTitle']
        ))
        self.story.append(Paragraph(
            "Project Sizing Platform -- BESS &amp; DG Sizing Tool",
            self.styles['DocSubtitle']
        ))
        self.story.append(Spacer(1, 20))

        # Metadata table
        meta = [
            ('Version', '1.2.0'),
            ('Author', 'Ankit Agarwal, GM -- Product &amp; Technology, Ampyr GTC'),
            ('Audience', 'DoublU Development Team (React + FastAPI rebuild)'),
            ('Last Updated', '2026-03-17'),
            ('Prototype Stack', 'Python 3.11+, Streamlit 1.41, Pandas 2.2, NumPy 2.1, Plotly 5.24'),
            ('Production Stack', 'React + TypeScript, MUI, FastAPI, PostgreSQL, Docker'),
        ]
        table_data = []
        for field, value in meta:
            table_data.append([
                Paragraph(f'<b>{field}</b>', self.styles['TableCell']),
                Paragraph(value, self.styles['TableCell']),
            ])
        t = Table(table_data, colWidths=[120, 350])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), GREY_BG),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ]))
        self.story.append(t)

        self.story.append(Spacer(1, 40))
        self.story.append(Paragraph(
            '<font color="#888888">CONFIDENTIAL -- AMPYR Energy / DoublU India Pvt Ltd</font>',
            self.styles['Normal']
        ))
        self.story.append(PageBreak())

        # Skip the title and metadata lines in the markdown
        # Find where the actual content starts (after first ---)
        while self.idx < len(self.lines):
            if self.lines[self.idx].strip().startswith('## Table of Contents'):
                # Build a simple TOC note
                self.story.append(Paragraph("Table of Contents", self.styles['H1']))
                self.story.append(HRFlowable(
                    width="30%", thickness=2,
                    color=AMPYR_TEAL, spaceBefore=2, spaceAfter=8,
                    hAlign='LEFT'
                ))
                self.idx += 1
                # Collect TOC entries
                while self.idx < len(self.lines) and self.lines[self.idx].strip():
                    toc_match = re.match(r'^\d+\.\s+\[(.+?)\]', self.lines[self.idx])
                    if toc_match:
                        entry = toc_match.group(1)
                        self.story.append(Paragraph(
                            f'<font color="#0066cc">{escape_xml(entry)}</font>',
                            self.styles['BulletItem']
                        ))
                    self.idx += 1
                self.story.append(PageBreak())
                break
            self.idx += 1

    def _parse_code_block(self):
        """Parse a fenced code block."""
        self.idx += 1  # Skip opening ```
        code_lines = []
        while self.idx < len(self.lines):
            if self.lines[self.idx].strip().startswith('```'):
                self.idx += 1
                break
            code_lines.append(self.lines[self.idx])
            self.idx += 1

        code_text = '\n'.join(code_lines)
        # Escape XML in code
        code_text = code_text.replace('&', '&amp;')
        code_text = code_text.replace('<', '&lt;')
        code_text = code_text.replace('>', '&gt;')

        # Truncate very long lines to avoid overflow
        truncated_lines = []
        for cline in code_text.split('\n'):
            if len(cline) > 105:
                cline = cline[:102] + '...'
            truncated_lines.append(cline)
        code_text = '\n'.join(truncated_lines)

        self.story.append(Preformatted(code_text, self.styles['CodeBlock']))

    def _parse_table(self):
        """Parse a markdown table."""
        # Header row
        header_line = self.lines[self.idx].strip()
        self.idx += 1
        # Separator row (skip)
        self.idx += 1

        # Parse header cells
        headers = [c.strip() for c in header_line.split('|') if c.strip()]

        # Parse data rows
        data_rows = []
        while self.idx < len(self.lines):
            row_line = self.lines[self.idx].strip()
            if not row_line or not '|' in row_line:
                break
            cells = [c.strip() for c in row_line.split('|') if c.strip()]
            # Pad if needed
            while len(cells) < len(headers):
                cells.append('')
            data_rows.append(cells[:len(headers)])
            self.idx += 1

        if not headers:
            return

        # Build table
        num_cols = len(headers)
        page_width = A4[0] - 50 * mm
        col_width = page_width / num_cols

        # Adjust column widths based on content
        col_widths = [col_width] * num_cols
        if num_cols == 2:
            col_widths = [page_width * 0.3, page_width * 0.7]
        elif num_cols == 3:
            col_widths = [page_width * 0.2, page_width * 0.35, page_width * 0.45]
        elif num_cols >= 5:
            col_widths = [page_width / num_cols] * num_cols

        # Header row
        table_data = [[
            Paragraph(format_inline(h), self.styles['TableHeader'])
            for h in headers
        ]]
        # Data rows
        for row in data_rows:
            table_data.append([
                Paragraph(format_inline(c), self.styles['TableCell'])
                for c in row
            ])

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ]
        # Alternate row colours
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), TABLE_ALT))

        t.setStyle(TableStyle(style_cmds))
        self.story.append(Spacer(1, 4))
        self.story.append(t)
        self.story.append(Spacer(1, 6))

    def _parse_list_item(self, match):
        """Parse a bullet or numbered list item."""
        indent = len(match.group(1))
        marker = match.group(2)
        text = match.group(3).strip()

        if indent >= 4:
            style = self.styles['BulletItem3']
            bullet_char = '-'
        elif indent >= 2:
            style = self.styles['BulletItem2']
            bullet_char = '-'
        else:
            style = self.styles['BulletItem']
            if re.match(r'\d+\.', marker):
                bullet_char = marker
            else:
                bullet_char = '\u2022'

        formatted = format_inline(text)
        self.story.append(Paragraph(
            f'{bullet_char}  {formatted}', style
        ))
        self.idx += 1

    def _parse_paragraph(self):
        """Parse a normal paragraph (may span multiple lines)."""
        para_lines = []
        while self.idx < len(self.lines):
            line = self.lines[self.idx]
            # Stop at blank line, heading, code, table, list, or hr
            if not line.strip():
                break
            if re.match(r'^#{1,4}\s+', line):
                break
            if line.strip().startswith('```'):
                break
            if '|' in line and self.idx + 1 < len(self.lines) and '---' in self.lines[self.idx + 1]:
                break
            if re.match(r'^(\s*)([-*]|\d+\.)\s+', line):
                break
            if re.match(r'^---+\s*$', line):
                break
            para_lines.append(line.strip())
            self.idx += 1

        if para_lines:
            text = ' '.join(para_lines)
            formatted = format_inline(text)
            self.story.append(Paragraph(formatted, self.styles['Normal']))

    def _header_footer(self, canvas, doc):
        """Draw header and footer on each page."""
        canvas.saveState()

        # Header line
        canvas.setStrokeColor(AMPYR_TEAL)
        canvas.setLineWidth(1.5)
        canvas.line(25 * mm, A4[1] - 18 * mm, A4[0] - 25 * mm, A4[1] - 18 * mm)

        # Header text
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(HexColor('#888888'))
        canvas.drawString(25 * mm, A4[1] - 16 * mm, "Ampyr-PSP Technical Reference v1.2.0")
        canvas.drawRightString(A4[0] - 25 * mm, A4[1] - 16 * mm, "CONFIDENTIAL")

        # Footer line
        canvas.setStrokeColor(HexColor('#cccccc'))
        canvas.setLineWidth(0.5)
        canvas.line(25 * mm, 18 * mm, A4[0] - 25 * mm, 18 * mm)

        # Page number
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(HexColor('#888888'))
        canvas.drawCentredString(A4[0] / 2, 12 * mm, f"Page {doc.page}")

        # Footer text
        canvas.setFont('Helvetica', 6.5)
        canvas.drawString(25 * mm, 12 * mm, "Ampyr Energy Tech Solutions Pvt Ltd")
        canvas.drawRightString(A4[0] - 25 * mm, 12 * mm, "2026-03-17")

        canvas.restoreState()

    def _title_page_template(self, canvas, doc):
        """Minimal header/footer for title page."""
        canvas.saveState()
        canvas.setStrokeColor(AMPYR_TEAL)
        canvas.setLineWidth(2)
        canvas.line(25 * mm, A4[1] - 25 * mm, A4[0] - 25 * mm, A4[1] - 25 * mm)
        canvas.restoreState()

    def build(self):
        """Build the final PDF."""
        doc = SimpleDocTemplate(
            str(self.pdf_path),
            pagesize=A4,
            leftMargin=25 * mm,
            rightMargin=25 * mm,
            topMargin=25 * mm,
            bottomMargin=25 * mm,
            title="Ampyr-PSP Technical Reference",
            author="Ankit Agarwal",
            subject="BESS & DG Sizing Tool - Technical Documentation",
        )

        self.parse()

        # Use different callbacks for first page vs rest
        doc.build(
            self.story,
            onFirstPage=self._title_page_template,
            onLaterPages=self._header_footer,
        )
        print(f"PDF generated: {self.pdf_path}")
        print(f"  Pages: {doc.page}")


if __name__ == '__main__':
    md_file = Path(__file__).parent / 'PSP_Technical_Reference.md'
    pdf_file = Path(__file__).parent / 'PSP_Technical_Reference.pdf'

    if len(sys.argv) > 1:
        md_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        pdf_file = Path(sys.argv[2])

    converter = MarkdownToPDF(md_file, pdf_file)
    converter.build()
