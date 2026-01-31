"""
Parser for AI-generated cheat sheet content.
Extracts boxes from the delimited format into structured data.
"""

import re
from dataclasses import dataclass


@dataclass
class Box:
    id: str
    title: str
    content: str
    
    @property
    def category(self) -> str:
        """Extract category letter from ID (e.g., 'A' from 'A5' or 'A0')"""
        match = re.match(r'^([A-Z])', self.id)
        return match.group(1) if match else 'A'


def parse_ai_output(raw_output: str) -> list[Box]:
    """
    Parse the AI output into Box objects.
    
    Expected format:
    [BOX:A5]
    [TITLE:Some title here]
    Content lines...
    More content...
    [/BOX]
    
    Args:
        raw_output: Raw text from AI containing [BOX] delimiters
        
    Returns:
        List of Box objects
    """
    boxes = []
    
    # Pattern to match each box block - permissive to capture various formats
    pattern = r'\[BOX:([A-Za-z0-9\-_.]+)\]\s*\[TITLE:([^\]]+)\]\s*(.*?)\[/BOX\]'
    
    matches = re.findall(pattern, raw_output, re.DOTALL)
    
    # Strict format pattern for validation
    strict_pattern = re.compile(r'^[A-Z]\d+$')
    
    for match in matches:
        box_id = match[0].strip()
        title = match[1].strip()
        content = match[2].strip()
        
        # Validate box ID format and warn if non-conforming
        if not strict_pattern.match(box_id):
            print(f"WARNING: Box ID '{box_id}' does not match the strict format [A-Z][0-9]+ (e.g., A1, B2, C10)")
            title_preview = title[:50] + ('...' if len(title) > 50 else '')
            print(f"         Title: {title_preview}")
        
        boxes.append(Box(id=box_id, title=title, content=content))
    
    return boxes


def validate_boxes(boxes: list[Box], expected_ids: list[str]) -> dict:
    """
    Validate that all expected topics are covered.
    
    Args:
        boxes: Parsed boxes from AI
        expected_ids: List of expected IDs like ['A1', 'A2', 'B1']
        
    Returns:
        Dict with 'missing', 'extra', and 'valid' keys
    """
    found_ids = {box.id for box in boxes}
    expected_set = set(expected_ids)
    
    return {
        'missing': expected_set - found_ids,
        'extra': found_ids - expected_set,
        'valid': found_ids & expected_set,
        'complete': found_ids >= expected_set
    }


# Test with sample AI output
if __name__ == "__main__":
    sample_output = """
[BOX:A1]
[TITLE:Introduction to Project Management]
**Project Management** means: Applying knowledge, skills, tools, and techniques to project activities to meet project requirements.

**Project** means: A temporary endeavor with a defined start and end, creating unique deliverables.

What characterizes projects:
• **Defined Scope** (clear boundaries and deliverables)
• **Time-bound** (specific start and end dates)
• **Unique Output** (not repetitive like operations)
• **Progressive Elaboration** (details refined over time)

Why Projects:
• Enable strategic objectives
• Respond to market changes
• Improve business processes
[/BOX]

[BOX:B1]
[TITLE:Risk Assessment Techniques]
**Risk Assessment** is a systematic process to identify and analyze potential project risks.

Benefits:
• Structures risk identification and analysis
• Creates common language in team
• Prevents surprises and enables proactive management
[/BOX]
"""
    
    boxes = parse_ai_output(sample_output)
    
    print(f"Parsed {len(boxes)} boxes:\n")
    for box in boxes:
        print(f"[{box.id}] {box.title}")
        print(f"Category: {box.category}")
        print(f"Content preview: {box.content[:100]}...")
        print("-" * 40)
    
    # Validate
    result = validate_boxes(boxes, ['A1', 'B1', 'B2'])
    print(f"\nValidation: {result}")
