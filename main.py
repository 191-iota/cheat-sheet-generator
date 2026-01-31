"""
Main entry point for the Cheat Sheet Generator.

Workflow:
1. Provide lecture content + topics
2. Use prompt template to query AI (Claude/GPT)
3. Parse AI output into boxes
4. Render to PDF

Usage:
    python main.py --input lecture.txt --topics topics.txt --output cheatsheet.pdf
    
Or use the generate() function programmatically.
"""

import argparse
from pathlib import Path

from prompt_template import build_prompt, SYSTEM_PROMPT
from parser import parse_ai_output, validate_boxes, Box
from renderer import CheatSheetRenderer


def generate_from_ai_output(ai_output: str, output_path: str = "cheatsheet.pdf") -> str:
    """
    Generate PDF from already-obtained AI output.
    
    Args:
        ai_output: Raw AI output with [BOX] delimiters
        output_path: Where to save the PDF
        
    Returns:
        Path to generated PDF
    """
    boxes = parse_ai_output(ai_output)
    
    if not boxes:
        raise ValueError("No boxes found in AI output. Check the format.")
    
    print(f"Parsed {len(boxes)} boxes:")
    for box in boxes:
        print(f"  [{box.id}] {box.title[:50]}...")
    
    renderer = CheatSheetRenderer(output_path)
    renderer.render(boxes)
    
    return output_path


def generate_with_api(
    lecture_content: str,
    topics: list[str],
    api_key: str,
    output_path: str = "cheatsheet.pdf",
    model: str = "claude-sonnet-4-20250514"
) -> str:
    """
    Full pipeline: lecture content → AI → PDF
    
    Args:
        lecture_content: Raw lecture text
        topics: List of learning objectives/topics
        api_key: Anthropic API key
        output_path: Where to save PDF
        model: Which Claude model to use
        
    Returns:
        Path to generated PDF
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError("Install anthropic: pip install anthropic")
    
    # Build prompts
    system_prompt, user_prompt = build_prompt(topics, lecture_content)
    
    # Call Claude
    client = anthropic.Anthropic(api_key=api_key)
    
    print("Calling Claude API...")
    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    ai_output = response.content[0].text
    print(f"Received {len(ai_output)} characters from AI")
    
    # Parse and render
    return generate_from_ai_output(ai_output, output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate cheat sheet PDF from AI output")
    parser.add_argument("--ai-output", type=str, help="File containing AI output with [BOX] format")
    parser.add_argument("--output", "-o", type=str, default="cheatsheet.pdf", help="Output PDF path")
    
    args = parser.parse_args()
    
    if args.ai_output:
        ai_text = Path(args.ai_output).read_text(encoding="utf-8")
        generate_from_ai_output(ai_text, args.output)
    else:
        # Demo mode with sample data
        print("No input provided. Running demo...")
        demo()


def demo():
    """Run demo with sample AI output."""
    sample_ai_output = """
[BOX:A1]
[TITLE:Introduction to Project Management]
**Project Management** = Applying knowledge, skills, tools, and techniques to meet project requirements and objectives.

Core Knowledge Areas:
• **Scope** (what work is included/excluded)
• **Time** (scheduling and deadlines)
• **Cost** (budgeting and financial control)
• **Quality** (standards and deliverables)
• **Risk** (identifying and mitigating threats)

Key Principles:
• Projects are temporary (defined start and end)
• Projects create unique products/services
• Progressive elaboration (details refined over time)
• Stakeholder engagement is critical

Project vs. Operations:
• Projects → temporary, unique deliverables
• Operations → ongoing, repetitive activities
[/BOX]

[BOX:A2]
[TITLE:Agile vs Waterfall Methodologies]
**Waterfall** = Sequential, phase-based approach:
1. Requirements gathering
2. Design
3. Implementation
4. Testing
5. Deployment
6. Maintenance

Pros: Clear structure, easy to understand, good for stable requirements
Cons: Inflexible, late testing, difficulty adapting to changes

**Agile** = Iterative, incremental approach:
• Work in sprints (1-4 weeks)
• Continuous feedback and adaptation
• Regular delivery of working software
• Collaboration over documentation

Pros: Flexible, fast feedback, customer satisfaction
Cons: Less predictability, requires discipline, scope creep risk

When to use:
• Waterfall: Fixed requirements, regulated industries
• Agile: Evolving requirements, innovation projects
[/BOX]

[BOX:A3]
[TITLE:Project Scope Management]
**Scope** = The work that must be performed to deliver a product/service with specified features.

Scope Definition Process:
1. **Collect Requirements**: Stakeholder interviews, surveys, workshops
2. **Define Scope**: Create scope statement (deliverables, boundaries, assumptions)
3. **Create WBS**: Work Breakdown Structure (hierarchical decomposition)
4. **Validate Scope**: Formal acceptance of deliverables
5. **Control Scope**: Monitor and manage changes

**Scope Creep** = Uncontrolled expansion of scope without adjusting time/cost/resources.

Prevention techniques:
• Clear requirements documentation
• Change control process
• Regular stakeholder communication
• Formal approval for changes
[/BOX]

[BOX:B1]
[TITLE:Risk Assessment Techniques]
**Risk** = Uncertain event that could impact project objectives (positive or negative).

Risk Assessment Process:
1. **Identify**: Brainstorming, checklist, SWOT analysis
2. **Analyze**: Probability × Impact matrix
3. **Prioritize**: Focus on high-probability, high-impact risks
4. **Plan Response**: Avoid, transfer, mitigate, accept
5. **Monitor**: Track and review throughout project

Risk Matrix:
• **High Probability + High Impact** = Critical priority
• **Low Probability + Low Impact** = Monitor only
• **High Impact + Low Probability** = Contingency plan
• **High Probability + Low Impact** = Mitigate early

Common project risks:
• Resource availability
• Technical complexity
• Requirement changes
• Budget constraints
[/BOX]

[BOX:B2]
[TITLE:Stakeholder Communication]
**Stakeholder** = Individual/group affected by or can affect the project.

Communication Planning:
• **Who**: Identify all stakeholders (sponsor, team, customers, users)
• **What**: Information needs (status reports, decisions, issues)
• **When**: Frequency (daily, weekly, monthly)
• **How**: Method (email, meeting, dashboard, report)

Communication Methods:
• **Interactive**: Meetings, calls, video conferences
• **Push**: Email, memos, reports (one-way)
• **Pull**: Intranet, knowledge base (self-service)

Stakeholder Analysis:
• **High Power + High Interest** = Manage closely
• **High Power + Low Interest** = Keep satisfied
• **Low Power + High Interest** = Keep informed
• **Low Power + Low Interest** = Monitor

Best Practices:
• Tailor message to audience
• Use clear, concise language
• Document important decisions
• Follow up on action items
[/BOX]

[BOX:C1]
[TITLE:Budget Planning Fundamentals]
**Budget** = Financial plan allocating resources to project activities.

Cost Estimation Techniques:
1. **Analogous**: Use historical data from similar projects
2. **Parametric**: Mathematical model (e.g., cost per square foot)
3. **Bottom-up**: Estimate each work package, roll up
4. **Three-point**: (Optimistic + 4×Most Likely + Pessimistic) / 6

Budget Components:
• **Direct Costs**: Labor, materials, equipment
• **Indirect Costs**: Overhead, admin, facilities
• **Contingency Reserve**: Known risks (5-10% typical)
• **Management Reserve**: Unknown risks (5-15% typical)

Cost Baseline:
• Time-phased budget used to measure performance
• Approved version of the budget
• Only changed through formal change control
[/BOX]

[BOX:C2]
[TITLE:Cost Control Strategies]
**Cost Control** = Monitoring budget vs. actual spending to prevent overruns.

Earned Value Management (EVM):
• **Planned Value (PV)**: Budgeted cost of scheduled work
• **Earned Value (EV)**: Budgeted cost of completed work
• **Actual Cost (AC)**: Actual cost of completed work

Key Metrics:
• **Cost Variance (CV)** = EV - AC (positive = under budget)
• **Schedule Variance (SV)** = EV - PV (positive = ahead of schedule)
• **Cost Performance Index (CPI)** = EV / AC (>1.0 = efficient)
• **Schedule Performance Index (SPI)** = EV / PV (>1.0 = on track)

Corrective Actions:
• Review spending patterns weekly
• Identify cost drivers
• Negotiate with vendors
• Optimize resource allocation
• Consider scope reduction if needed
• Fast-track or crash critical path (if schedule is the issue)
[/BOX]

[BOX:A4]
[TITLE:Project Charter and Initiation]
**Project Charter** = Formal document that authorizes a project.

Key Contents:
• Project purpose and justification
• High-level requirements
• Summary budget
• Success criteria
• Assigned project manager and authority level
• Sponsor signature

Project Initiation Steps:
1. Develop business case
2. Conduct feasibility study
3. Create project charter
4. Identify stakeholders
5. Hold kickoff meeting

Why it matters:
• Establishes project authority
• Secures resources and budget
• Aligns stakeholders on goals
• Provides clear mandate to PM
[/BOX]

[BOX:B3]
[TITLE:Quality Management Principles]
**Quality** = Degree to which deliverables meet requirements and satisfy customers.

Quality Planning:
• Define quality standards (industry, organizational, regulatory)
• Identify quality metrics (defect rate, customer satisfaction)
• Plan quality assurance and control activities

Quality Assurance (QA) vs. Quality Control (QC):
• **QA** = Process-focused, preventive (audits, process improvement)
• **QC** = Product-focused, detective (testing, inspections)

Cost of Quality:
• **Prevention Costs**: Training, process documentation
• **Appraisal Costs**: Testing, inspections, reviews
• **Failure Costs**: Rework, warranty, customer complaints
• Principle: Invest in prevention to reduce failure costs

Continuous Improvement:
• Plan-Do-Check-Act (PDCA) cycle
• Root cause analysis
• Lessons learned documentation
[/BOX]

[BOX:C3]
[TITLE:Resource Allocation and Management]
**Resource** = People, equipment, materials, or facilities needed to complete project activities.

Resource Planning:
1. **Estimate**: Determine types and quantities needed
2. **Acquire**: Obtain resources (hire, procure, contract)
3. **Assign**: Allocate to specific activities
4. **Level**: Optimize to avoid overallocation
5. **Control**: Monitor utilization and adjust

Resource Optimization Techniques:
• **Resource Leveling**: Extend schedule to avoid overallocation
• **Resource Smoothing**: Optimize within fixed schedule
• **Fast Tracking**: Parallel activities to compress schedule
• **Crashing**: Add resources to critical path

Common Challenges:
• Limited availability of skilled resources
• Competing priorities across projects
• Resource conflicts and bottlenecks
• Underestimating effort required

Solutions:
• Cross-training team members
• Flexible resource pools
• Clear prioritization criteria
• Regular capacity planning
[/BOX]
"""
    
    generate_from_ai_output(sample_ai_output, "demo_cheatsheet.pdf")
    print("\n✓ Demo complete! Check demo_cheatsheet.pdf")


if __name__ == "__main__":
    main()
