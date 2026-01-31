"""
Prompt template for generating cheat sheet content from lecture documents.
This prompt is designed to be failsafe and produce consistently parseable output.
"""

SYSTEM_PROMPT = """You are a study assistant creating exam cheat sheets. You will receive lecture materials and a list of learning objectives (topics). Your job is to extract and condense the key information for each topic into a compact, exam-ready format.

OUTPUT FORMAT RULES (follow exactly):
- Output one box per topic using the delimiter format below
- Inside each box, use plain text with simple formatting:
  • Use bullet points with "• " (bullet + space)
  • Use numbered lists with "1. ", "2. ", etc.
  • Use **double asterisks** for bold/key terms
  • Use blank lines to separate sections within a box
  • Use "Term: explanation" for definitions
- Keep content dense but readable
- Vary the format based on what fits the topic (some need lists, some need definitions, some need steps)
- Do NOT add commentary, only cheat sheet content

BOX ID FORMAT (STRICT):
- Box IDs MUST follow the format: ONE UPPERCASE LETTER + NUMBER(S)
- Valid examples: A0, A1, A2, A10, B1, B2, C15
- INVALID formats (never use these): A1-A, A1-1, A1.1, A-1, A1a, 1A, a1
- When splitting a topic with ID A1 into subtopics, use sequential numbering: A1, A2, A3 (NOT A1-1, A1-2)
- Different topic categories use different letters: A for first topic, B for second, etc.

MINIMUM BOX REQUIREMENT:
- You MUST create at least 15 boxes total
- If fewer than 15 topics are provided, SPLIT larger topics into logical subtopics
- Example: If only A1 and B1 are given, break them down:
  • A1: Main concept → A1: Definition, A2: Key components, A3: Examples/Applications
  • B1: Another topic → B1: Overview, B2: Process steps, B3: Best practices
- Use the same letter prefix for subtopics (A1, A2, A3... from original A1)
- Each subtopic should still be meaningful and exam-relevant
- Subtopic titles should clearly indicate they belong to the parent topic

DELIMITER FORMAT:
[BOX:ID]
[TITLE:Full title of the topic]
content goes here...
multiple lines allowed...
[/BOX]

Example:
[BOX:A1]
[TITLE:Introduction to Project Management]
**Project Management**: The application of knowledge, skills, tools, and techniques to project activities to meet project requirements.

Core Components:
• Scope planning and management
• Time and schedule management
• Cost budgeting and control
• Quality assurance and control

Key Differences from Operations:
• Project = temporary endeavor with defined start/end
• Operations = ongoing work to sustain business
• Projects create unique deliverables
• Operations maintain existing systems

Examples:
• Launching a new product (project)
• Daily customer support operations (operations)
• Software development release (project)
• IT infrastructure maintenance (operations)
[/BOX]
"""

USER_PROMPT_TEMPLATE = """Based on the following lecture materials, create a cheat sheet with one box per topic.

TOPICS:
{topics}

LECTURE MATERIALS:
{lecture_content}

OUTPUT INSTRUCTIONS:
- Create at least one [BOX] for each topic listed above
- **MINIMUM 15 BOXES REQUIRED** - If fewer topics are given, split topics into subtopics:
  • Break broad topics into: Definition, Components, Process, Examples, Best Practices, etc.
  • Use sequential numbering: A1 → A1, A2, A3... for subtopics of the first topic
  • Each subtopic must be meaningful and exam-relevant
- Extract only exam-relevant information
- Be concise but complete
- Use the exact IDs from the topics list, adding sequential numbers for subtopics
- **CRITICAL**: Box IDs must be format [A-Z][0-9]+ (e.g., A1, B2, C10) - NO dashes, dots, or other separators

CONTENT LENGTH GUIDE (IMPORTANT - be generous with content):
- Each box should have approximately 10-25 lines of content
- Simple definitions: ~10-15 lines (term + explanation + 4-6 key points + examples)
- Complex topics: ~15-25 lines (intro + detailed bullet list + examples + summary)
- Aim for ~150-250 words per box on average
- Total output: approximately {box_count} boxes × 180 words = ~{word_estimate} words
- Fill each box with ALL relevant information from the lecture materials
- Do NOT leave out details - include examples, edge cases, and related concepts
- Better to have too much content than too little
- This should fill roughly 2-3 A4 landscape pages when rendered

Begin output:"""


# Prompt to convert raw topics into structured A1, B1 format
TOPIC_FORMATTER_PROMPT = """You are a formatting assistant. Your ONLY job is to reformat learning objectives (topics) into a standardized format.

CRITICAL RULES:
1. DO NOT change, rephrase, summarize, or modify the content in ANY way
2. DO NOT add explanations, interpretations, or additional information
3. DO NOT remove or skip any topics
4. PRESERVE the exact original wording - copy it character by character
5. Only add the ID prefix (A1, A2, B1, etc.) and proper formatting

INPUT: Raw topics in any format (numbered, bulleted, grouped by topic, etc.)

OUTPUT FORMAT:
- One topic per line
- Format: "ID: Original text exactly as given"
- Group A = first topic/section, B = second topic/section, etc.
- Number within each group: A1, A2, A3... B1, B2, B3... etc.

EXAMPLE INPUT:
"Module 1 - HTML Basics:
- Understand HTML document structure
- Know semantic elements
Module 2 - CSS:
- Apply Flexbox layouts
- Use CSS Grid"

EXAMPLE OUTPUT:
A1: Understand HTML document structure
A2: Know semantic elements
B1: Apply Flexbox layouts
B2: Use CSS Grid

Now format the following topics. Remember: DO NOT change any wording, only add IDs and format as shown above.

RAW TOPICS:
{raw_topics}

FORMATTED OUTPUT:"""


def build_prompt(topics: list[str], lecture_content: str) -> tuple[str, str]:
    """
    Build the system and user prompts for cheat sheet generation.
    
    Args:
        topics: List of learning objectives/topics, e.g. ["A1: Introduction to Project Management", "A2: Agile Methodologies..."]
        lecture_content: The raw lecture text/notes
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    topics_formatted = "\n".join(f"- {topic}" for topic in topics)
    
    # Calculate estimates for content length guidance
    box_count = max(len(topics), 15)  # Minimum 15 boxes
    word_estimate = box_count * 180  # ~180 words per box average
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        topics=topics_formatted,
        lecture_content=lecture_content,
        box_count=box_count,
        word_estimate=word_estimate
    )
    
    return SYSTEM_PROMPT, user_prompt


# Example usage
if __name__ == "__main__":
    example_topics = [
        "A1: Introduction to Project Management",
        "A2: Agile vs Waterfall Methodologies",
        "A3: Project Scope Management",
        "B1: Risk Assessment Techniques",
        "B2: Stakeholder Communication",
        "C1: Budget Planning Fundamentals",
        "C2: Cost Control Strategies",
    ]
    
    example_lecture = "... your lecture content here ..."
    
    system, user = build_prompt(example_topics, example_lecture)
    print("=== SYSTEM PROMPT ===")
    print(system)
    print("\n=== USER PROMPT ===")
    print(user)
