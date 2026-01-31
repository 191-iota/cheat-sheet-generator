"""
Cheat Sheet PDF Renderer
Renders parsed boxes into a dense 2-column A4 landscape layout.
Matches the visual style: colored header bars, compact text, variable box heights.
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
import re
from typing import List

# Import Box from parser
try:
    from .parser import Box
except ImportError:
    from parser import Box

# Category colors
CATEGORY_COLORS = {
    "A": "#0d7377",  # Teal
    "B": "#1a5276",  # Blue  
    "C": "#7d6608",  # Gold/olive
    "D": "#6c3483",  # Purple
    "E": "#922b21",  # Red
}


class CheatSheetRenderer:
    def __init__(self, output_path: str, num_columns: int = 3):
        self.output_path = output_path
        self.page_width, self.page_height = landscape(A4)
        self.margin = 4 * mm
        self.column_gap = 2 * mm
        self.box_spacing = 1.5 * mm
        self.box_padding = 1 * mm
        self.header_height = 3 * mm
        self.num_columns = num_columns
        
        # Calculate column width for N columns
        usable_width = self.page_width - 2 * self.margin - (num_columns - 1) * self.column_gap
        self.column_width = usable_width / num_columns
        
        # Font sizes (small for density)
        self.header_font_size = 5
        self.content_font_size = 4.5
        self.code_font_size = 4
        self.line_height = 1.6 * mm
        
        self.c = None  # canvas
        
    def _get_color(self, category: str) -> str:
        return CATEGORY_COLORS.get(category, CATEGORY_COLORS["A"])
    
    def _wrap_text(self, text: str, max_width: float, font_name: str, font_size: float) -> List[str]:
        """Simple word wrapping."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            width = self.c.stringWidth(test_line, font_name, font_size)
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else ['']
    
    def _estimate_content_height(self, content: str, available_width: float) -> float:
        """Estimate height needed for content."""
        lines = content.split('\n')
        total_height = 0
        in_code_block = False
        
        for line in lines:
            # Skip code fence markers but track state
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if not line.strip():
                total_height += 0.8 * mm  # minimal blank line spacing
                continue
            
            # Calculate indent
            stripped = line.lstrip()
            indent = min((len(line) - len(stripped)) * 1 * mm, 8 * mm)  # cap indent
            
            # Check for bullet/number prefix
            prefix_width = 0
            if stripped.startswith('• ') or stripped.startswith('- '):
                prefix_width = 3 * mm
            elif re.match(r'^\d+\. ', stripped):
                prefix_width = 4 * mm
            
            # Wrap calculation
            text_width = available_width - self.box_padding * 2 - indent - prefix_width
            # Remove bold markers for width calculation
            clean_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', stripped)
            wrapped = self._wrap_text(clean_text, text_width, "Helvetica", self.content_font_size)
            total_height += len(wrapped) * self.line_height
        
        return total_height
    
    def _estimate_box_height(self, box: Box, width: float = None) -> float:
        """Estimate total box height."""
        if width is None:
            width = self.column_width
        content_height = self._estimate_content_height(box.content, width)
        return self.header_height + content_height + self.box_padding * 2
    
    def _calculate_box_width(self, box: Box) -> float:
        """Calculate width needed for box based on longest line."""
        max_width = 0
        
        # Check title width
        title_text = f"{box.id} {box.title}"
        title_width = self.c.stringWidth(title_text, "Helvetica-Bold", self.header_font_size) + 3 * mm
        max_width = max(max_width, title_width)
        
        # Check content lines
        for line in box.content.split('\n'):
            if line.strip().startswith('```'):
                continue
            stripped = line.strip()
            if not stripped:
                continue
            
            # Remove bold markers for width calculation
            clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', stripped)
            
            # Calculate indent contribution
            indent = min((len(line) - len(line.lstrip())) * 1 * mm, 8 * mm)
            
            # Check for bullet prefix
            prefix_width = 0
            if clean.startswith('• ') or clean.startswith('- '):
                prefix_width = 2 * mm
                clean = clean[2:]
            elif re.match(r'^\d+\. ', clean):
                prefix_width = 2.5 * mm
                clean = re.sub(r'^\d+\. ', '', clean)
            
            line_width = self.c.stringWidth(clean, "Helvetica", self.content_font_size)
            total_line_width = indent + prefix_width + line_width + self.box_padding * 2
            max_width = max(max_width, total_line_width)
        
        # Clamp to reasonable bounds
        min_width = 25 * mm
        max_allowed = (self.page_width - 2 * self.margin) / 2  # Max half page
        return max(min_width, min(max_width + 2 * mm, max_allowed))
    
    def _draw_text_with_bold(self, text: str, x: float, y: float, max_width: float) -> float:
        """Draw text with **bold** support. Returns lines used."""
        # Split by bold markers
        parts = re.split(r'(\*\*[^*]+\*\*)', text)
        current_x = x
        
        for part in parts:
            if not part:
                continue
            if part.startswith('**') and part.endswith('**'):
                self.c.setFont("Helvetica-Bold", self.content_font_size)
                clean = part[2:-2]
            else:
                self.c.setFont("Helvetica", self.content_font_size)
                clean = part
            
            self.c.drawString(current_x, y, clean)
            current_x += self.c.stringWidth(clean, self.c._fontname, self.content_font_size)
        
        return 1
    
    def _draw_box(self, box: Box, x: float, y: float, width: float = None) -> float:
        """Draw a single box. Returns actual height used."""
        c = self.c
        color = self._get_color(box.category)
        if width is None:
            width = self.column_width
        
        # Calculate height
        height = self._estimate_box_height(box, width)
        
        # Header background
        c.setFillColor(HexColor(color))
        c.rect(x, y - self.header_height, width, self.header_height, fill=True, stroke=False)
        
        # Header text
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Helvetica-Bold", self.header_font_size)
        header = f"{box.id} {box.title}"
        # Truncate if needed
        max_header_width = width - 2 * mm
        while c.stringWidth(header, "Helvetica-Bold", self.header_font_size) > max_header_width and len(header) > 20:
            header = header[:-4] + "..."
        c.drawString(x + 1 * mm, y - self.header_height + 0.9 * mm, header)
        
        # Box border
        c.setStrokeColor(HexColor(color))
        c.setLineWidth(0.4)
        c.rect(x, y - height, width, height, fill=False, stroke=True)
        
        # Content
        c.setFillColor(HexColor("#000000"))
        content_y = y - self.header_height - self.box_padding - self.line_height * 0.7
        in_code_block = False
        
        for line in box.content.split('\n'):
            # Handle code fence markers
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if not line.strip():
                content_y -= 0.6 * mm
                continue
            
            stripped = line.lstrip()
            indent = min((len(line) - len(stripped)) * 1 * mm, 8 * mm)
            text_x = x + self.box_padding + indent
            
            # Code block styling
            if in_code_block:
                c.setFont("Courier", self.code_font_size)
                c.drawString(text_x, content_y, stripped)
                content_y -= self.line_height
                continue
            
            # Handle bullets
            if stripped.startswith('• ') or stripped.startswith('- '):
                c.setFont("Helvetica", self.content_font_size)
                c.drawString(text_x, content_y, "•")
                text_x += 2 * mm
                stripped = stripped[2:]
            elif re.match(r'^(\d+)\. ', stripped):
                match = re.match(r'^(\d+)\. ', stripped)
                c.setFont("Helvetica", self.content_font_size)
                c.drawString(text_x, content_y, f"{match.group(1)}.")
                text_x += 2.5 * mm
                stripped = stripped[match.end():]
            
            # Draw text (simple, single line for now)
            self._draw_text_with_bold(stripped, text_x, content_y, width - self.box_padding * 2 - indent)
            content_y -= self.line_height
        
        return height
    
    def _calculate_optimal_columns(self, boxes: List[Box]) -> int:
        """Calculate optimal column count based on average line length."""
        if not boxes:
            return self.num_columns
        
        # Sample line lengths from content
        all_lines = []
        for box in boxes:
            for line in box.content.split('\n'):
                stripped = line.strip()
                if stripped:
                    # Remove formatting markers for length calc
                    clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', stripped)
                    all_lines.append(len(clean))
        
        if not all_lines:
            return self.num_columns
        
        avg_len = sum(all_lines) / len(all_lines)
        
        # Heuristic: shorter lines = more columns
        # avg ~20 chars -> 4 cols, ~40 chars -> 3 cols, ~60+ chars -> 2 cols
        if avg_len < 25:
            return 4
        elif avg_len < 45:
            return 3
        else:
            return 2
    
    def render(self, boxes: List[Box], sort_by_category: bool = True, auto_columns: bool = True):
        """Render all boxes to PDF with greedy bin-packing layout."""
        self.c = canvas.Canvas(self.output_path, pagesize=landscape(A4))
        
        if sort_by_category:
            boxes = sorted(boxes, key=lambda b: (b.category, b.id))
        
        page_top = self.page_height - self.margin
        page_bottom = self.margin
        page_right = self.page_width - self.margin
        
        # Track placed boxes as rectangles: (x, y_top, width, height)
        placed = []
        
        def find_best_position(box_w, box_h):
            """Find best position (highest Y, then leftmost X) for a box."""
            best_x, best_y = None, None
            
            # Try positions: start from top, scan left to right
            # Check Y levels from top down
            y_levels = [page_top]
            for (px, py, pw, ph) in placed:
                y_levels.append(py - ph)  # bottom of each placed box
            y_levels = sorted(set(y_levels), reverse=True)
            
            for y in y_levels:
                if y - box_h < page_bottom:
                    continue
                
                # Try X positions from left
                x_positions = [self.margin]
                for (px, py, pw, ph) in placed:
                    x_positions.append(px + pw + self.column_gap)
                x_positions = sorted(set(x_positions))
                
                for x in x_positions:
                    if x + box_w > page_right:
                        continue
                    
                    # Check if this position overlaps any placed box
                    overlaps = False
                    for (px, py, pw, ph) in placed:
                        # Check overlap: box at (x, y-box_h to y) vs placed at (px, py-ph to py)
                        if not (x + box_w + self.column_gap <= px or x >= px + pw + self.column_gap or
                                y - box_h >= py or y <= py - ph):
                            overlaps = True
                            break
                    
                    if not overlaps:
                        if best_y is None or y > best_y or (y == best_y and x < best_x):
                            best_x, best_y = x, y
                
                if best_x is not None:
                    break
            
            return best_x, best_y
        
        for box in boxes:
            box_width = self._calculate_box_width(box)
            box_height = self._estimate_box_height(box, box_width)
            
            x, y = find_best_position(box_width, box_height)
            
            if x is None:
                # New page
                self.c.showPage()
                placed = []
                x, y = self.margin, page_top
            
            self._draw_box(box, x, y, box_width)
            placed.append((x, y, box_width, box_height))
        
        self.c.save()
        print(f"✓ PDF saved: {self.output_path}")

    def calculate_layout(self, boxes: List[Box], sort_by_category: bool = True) -> list:
        """Calculate box positions and sizes without rendering - for editor preview."""
        # Need a temporary canvas for string width calculations
        import io
        temp_buffer = io.BytesIO()
        self.c = canvas.Canvas(temp_buffer, pagesize=landscape(A4))
        
        if sort_by_category:
            boxes = sorted(boxes, key=lambda b: (b.category, b.id))
        
        page_top = self.page_height - self.margin
        page_bottom = self.margin
        page_right = self.page_width - self.margin
        
        placed = []
        layout_result = []
        current_page = 0
        
        def find_best_position(box_w, box_h):
            best_x, best_y = None, None
            y_levels = [page_top]
            for (px, py, pw, ph, _) in placed:
                y_levels.append(py - ph)
            y_levels = sorted(set(y_levels), reverse=True)
            
            for y in y_levels:
                if y - box_h < page_bottom:
                    continue
                x_positions = [self.margin]
                for (px, py, pw, ph, _) in placed:
                    x_positions.append(px + pw + self.column_gap)
                x_positions = sorted(set(x_positions))
                
                for x in x_positions:
                    if x + box_w > page_right:
                        continue
                    overlaps = False
                    for (px, py, pw, ph, _) in placed:
                        if not (x + box_w + self.column_gap <= px or x >= px + pw + self.column_gap or
                                y - box_h >= py or y <= py - ph):
                            overlaps = True
                            break
                    if not overlaps:
                        if best_y is None or y > best_y or (y == best_y and x < best_x):
                            best_x, best_y = x, y
                if best_x is not None:
                    break
            return best_x, best_y
        
        for box in boxes:
            box_width = self._calculate_box_width(box)
            box_height = self._estimate_box_height(box, box_width)
            
            x, y = find_best_position(box_width, box_height)
            
            if x is None:
                current_page += 1
                placed = []
                x, y = self.margin, page_top
            
            placed.append((x, y, box_width, box_height, box.id))
            
            # Convert PDF coordinates to editor coordinates
            # PDF: bottom-left origin, Y up. Editor: top-left origin, Y down
            scale_x = 1123 / self.page_width
            scale_y = 794 / self.page_height
            
            editor_x = x * scale_x
            # Convert Y: PDF y is from bottom, editor y is from top
            editor_y = (self.page_height - y) * scale_y + (current_page * 794)
            editor_width = box_width * scale_x
            editor_height = box_height * scale_y
            
            layout_result.append({
                'id': box.id,
                'x': editor_x,
                'y': editor_y,
                'width': editor_width,
                'height': editor_height,
                'page': current_page
            })
        
        self.c = None
        return layout_result

    def render_with_layout(self, boxes: List[Box], layout: list):
        """
        Render boxes using positions from the editor (which match calculate_layout exactly).
        """
        self.c = canvas.Canvas(self.output_path, pagesize=landscape(A4))
        
        # Create lookup for layout data
        layout_lookup = {item['id']: item for item in layout}
        
        # Editor coordinates are scaled versions of PDF coordinates
        # Editor: 1123x794, PDF: 842x595 points
        scale_x = self.page_width / 1123
        scale_y = self.page_height / 794
        
        # Group boxes by page based on Y position
        EDITOR_PAGE_HEIGHT = 794
        pages = {}
        
        for box in boxes:
            if box.id not in layout_lookup:
                continue
                
            layout_info = layout_lookup[box.id]
            page_num = int(layout_info['y'] // EDITOR_PAGE_HEIGHT)
            
            if page_num not in pages:
                pages[page_num] = []
            
            pages[page_num].append((box, layout_info))
        
        # Render each page
        for page_num in sorted(pages.keys()):
            if page_num > 0:
                self.c.showPage()
            
            for box, layout_info in pages[page_num]:
                # Convert editor coordinates back to PDF coordinates
                x = layout_info['x'] * scale_x
                width = layout_info['width'] * scale_x
                
                # Y conversion: editor Y is from top-down, PDF Y is bottom-up
                editor_y = layout_info['y'] - (page_num * EDITOR_PAGE_HEIGHT)
                y = self.page_height - (editor_y * scale_y)
                
                # Draw the box (height auto-calculated by _draw_box)
                self._draw_box(box, x, y, width)
        
        self.c.save()
        print(f"✓ PDF saved with custom layout: {self.output_path}")

    def _draw_box_fixed_size(self, box: Box, x: float, y: float, width: float, height: float) -> float:
        """Draw a box with fixed dimensions (from editor)."""
        c = self.c
        color = self._get_color(box.category)
        
        # Header background
        c.setFillColor(HexColor(color))
        c.rect(x, y - self.header_height, width, self.header_height, fill=True, stroke=False)
        
        # Header text
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Helvetica-Bold", self.header_font_size)
        header = f"{box.id} {box.title}"
        # Truncate if needed
        max_header_width = width - 2 * mm
        while c.stringWidth(header, "Helvetica-Bold", self.header_font_size) > max_header_width and len(header) > 20:
            header = header[:-4] + "..."
        c.drawString(x + 1 * mm, y - self.header_height + 0.9 * mm, header)
        
        # Box border
        c.setStrokeColor(HexColor(color))
        c.setLineWidth(0.4)
        c.rect(x, y - height, width, height, fill=False, stroke=True)
        
        # Content - clip to available space
        c.setFillColor(HexColor("#000000"))
        content_y = y - self.header_height - self.box_padding - self.line_height * 0.7
        content_bottom = y - height + self.box_padding
        in_code_block = False
        
        for line in box.content.split('\n'):
            # Stop if we've exceeded the box height
            if content_y < content_bottom:
                break
            
            # Handle code fence markers
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if not line.strip():
                content_y -= 0.6 * mm
                continue
            
            stripped = line.lstrip()
            indent = min((len(line) - len(stripped)) * 1 * mm, 8 * mm)
            text_x = x + self.box_padding + indent
            
            # Code block styling
            if in_code_block:
                c.setFont("Courier", self.code_font_size)
                c.drawString(text_x, content_y, stripped)
                content_y -= self.line_height
                continue
            
            # Handle bullets
            if stripped.startswith('• ') or stripped.startswith('- '):
                c.setFont("Helvetica", self.content_font_size)
                c.drawString(text_x, content_y, "•")
                text_x += 2 * mm
                stripped = stripped[2:]
            elif re.match(r'^(\d+)\. ', stripped):
                match = re.match(r'^(\d+)\. ', stripped)
                c.setFont("Helvetica", self.content_font_size)
                c.drawString(text_x, content_y, f"{match.group(1)}.")
                text_x += 2.5 * mm
                stripped = stripped[match.end():]
            
            # Draw text
            self._draw_text_with_bold(stripped, text_x, content_y, width - self.box_padding * 2 - indent)
            content_y -= self.line_height
        
        return height


if __name__ == "__main__":
    # Test with sample boxes
    from parser import parse_ai_output
    
    sample = """
[BOX:A1]
[TITLE:Introduction to Project Management]
**Project Management** means: Applying knowledge, skills, and tools to meet project requirements.

**Project** means: Temporary endeavor creating unique deliverables.

What characterizes projects:
• **Scope** (defined boundaries)
• **Time-bound** (specific dates)
• **Unique Output** (not repetitive)
• **Progressive** (details refined over time)

Why Projects: Enable strategic objectives and respond to market changes.
[/BOX]

[BOX:A2]
[TITLE:Agile vs Waterfall Methodologies]
Waterfall goals:
• Sequential phase-based approach
• Clear structure and documentation
• Fixed requirements upfront
• Predictable timeline and budget

Agile approach:
1. **Iterative**
2. **Sprints** (1-4 week cycles)
3. **Collaboration** (team and customer)
4. **Adaptability** (embrace changes)
5. **Continuous delivery** (working software)
6. **Feedback loops** (improve continuously)

When to use:
1. Starting point: Assess requirements stability
2. Waterfall: Use for well-defined, stable projects
3. Agile: Use for evolving requirements
4. Hybrid: Combine approaches when needed
5. Context matters: Industry regulations, team experience
6. Measure and adjust: Track metrics and adapt
7. Implement and learn: Start small, scale gradually
[/BOX]

[BOX:A3]
[TITLE:Project Scope Management]
Fundamental principle: Not every idea should be in scope – focus on value.

Scope criteria:
• **Deliverables**: What outputs are required?
• **Boundaries**: What is explicitly excluded?
• **Acceptance Criteria**: How will success be measured?

Triggers:
• **Stakeholder requests**: Customer needs drive scope
• **Regulatory requirements**: Compliance mandates

Scope change patterns:
• Requirements clarification
• Feature additions
• Technology constraints
• Stakeholder alignment

Best practices:
• Clear requirements documentation
• Change control process
• Regular scope validation
• Formal approval for changes
[/BOX]

[BOX:B1]
[TITLE:Risk Assessment Techniques]
**Risk Assessment** = systematic process to identify and analyze project risks.

Benefits:
• Structures risk identification
• Creates common risk language
• Enables proactive management
[/BOX]

[BOX:B2]
[TITLE:Stakeholder Communication]
• **Identify**: Who are the stakeholders?
• **Analyze**: What are their interests and influence?
• **Plan**: How and when to communicate?
• **Execute**: Deliver appropriate information
• **Monitor**: Track engagement and adjust
• **Adjust**: Refine approach based on feedback
[/BOX]

[BOX:C1]
[TITLE:Budget Planning: Purpose]
Budget planning ensures **alignment** between project costs and available resources.
Goal: Clear financial control, not just estimation.
[/BOX]

[BOX:C2]
[TITLE:Budget Planning: Structure]
Cost categories:
• **Labor**: Team member time and rates
  • direct labor (project team)
  • indirect labor (support staff)
  • consultant fees
• **Materials**: Physical goods and supplies
• **Equipment**: Tools, software licenses, hardware

Financial baseline:
• **Planned costs**: Budget allocation
• **Actual costs**: What is spent
• **Variance**: Difference between plan and actual
[/BOX]

[BOX:C3]
[TITLE:Best Budget Planning Practices]
Best approach:
• Bottom-up estimation with work packages
• Include contingency reserves (5-10%)
• Regular cost tracking and variance analysis

Weaker approach:
• Top-down guesswork without detailed breakdown
[/BOX]
"""
    
    boxes = parse_ai_output(sample)
    renderer = CheatSheetRenderer("test_cheatsheet.pdf")
    renderer.render(boxes)
