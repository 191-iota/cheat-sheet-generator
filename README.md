# Cheat Sheet Generator

I came up with the concept of breaking "creating a cheatsheet with ai" down in multiple steps and vibecoded this. Still lazy but better.

## Structure

```
cheatsheet_generator/
├── prompt_template.py   # Failsafe prompt for AI
├── parser.py            # Parse [BOX] format from AI output
├── renderer.py          # Generate PDF with colored boxes
└── main.py              # Entry point + demo
```

## Workflow

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────┐
│  Lecture docs   │ ──►  │  Claude API      │ ──►  │  PDF        │
│  + Topics       │      │  (with prompt)   │      │  2-page A4  │
└─────────────────┘      └──────────────────┘      └─────────────┘
                               │
                               ▼
                    [BOX:A5]
                    [TITLE:...]
                    content...
                    [/BOX]
```

## AI Output Format

The prompt instructs AI to output this exact format:

```
[BOX:A5]
[TITLE:Full title of the topic]
**Bold term**: explanation

Subheading:
• Bullet point one
• Bullet point two

1. Numbered step
2. Another step
[/BOX]
```

## Usage

### Option 1: Demo
```bash
cd cheatsheet_generator
pip install reportlab
python main.py
# Creates demo_cheatsheet.pdf
```

### Option 2: From AI output file
```bash
python main.py --ai-output my_ai_output.txt --output cheatsheet.pdf
```

### Option 3: Full pipeline with API
```python
from main import generate_with_api

generate_with_api(
    lecture_content="... your lecture text ...",
    topics=["A1: Introduction to Project Management", "A2: Agile Methodologies", "B1: Risk Assessment"],
    api_key="sk-...",
    output_path="my_cheatsheet.pdf"
)
```

## Prompt Template

The key is the **failsafe prompt** in `prompt_template.py`. It:
- Forces structured output with clear delimiters
- Allows flexible content inside each box
- Specifies exactly how to format bullets, numbers, bold terms
- Maps to topic IDs (A1, A2, B1, etc.)

Copy `SYSTEM_PROMPT` and use it with any AI (Claude, ChatGPT, etc.).
