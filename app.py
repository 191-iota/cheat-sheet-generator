"""
Simple web frontend for the Cheat Sheet Generator.
Upload documents, provide topics, get PDF.
"""

from flask import Flask, request, render_template_string, send_file, jsonify
from pathlib import Path
import tempfile
import os

from prompt_template import build_prompt, SYSTEM_PROMPT
from parser import parse_ai_output
from renderer import CheatSheetRenderer

# Document extractors
try:
    import fitz  # PyMuPDF
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

app = Flask(__name__)


def extract_text_from_file(file) -> str:
    """Extract text from uploaded file (PDF, DOCX, TXT)."""
    filename = file.filename.lower()
    content = file.read()
    
    if filename.endswith('.txt') or filename.endswith('.md'):
        return content.decode('utf-8', errors='ignore')
    
    elif filename.endswith('.pdf') and HAS_PDF:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            doc = fitz.open(temp_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        finally:
            os.unlink(temp_path)
    
    elif filename.endswith('.docx') and HAS_DOCX:
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            f.write(content)
            temp_path = f.name
        try:
            doc = docx.Document(temp_path)
            text = "\n".join([p.text for p in doc.paragraphs])
            return text
        finally:
            os.unlink(temp_path)
    
    else:
        # Try as plain text
        try:
            return content.decode('utf-8', errors='ignore')
        except:
            return f"[Could not extract text from {filename}]"


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cheat Sheet Generator</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 850px; 
            margin: 40px auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #333; margin-bottom: 30px; }
        .section { 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        label { 
            display: block; 
            font-weight: 600; 
            margin-bottom: 8px; 
            color: #444;
        }
        textarea, input[type="text"] { 
            width: 100%; 
            padding: 10px; 
            border: 1px solid #ddd; 
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
        }
        textarea { min-height: 150px; resize: vertical; }
        .small-textarea { min-height: 80px; }
        input[type="file"] {
            padding: 10px;
            border: 2px dashed #ddd;
            border-radius: 4px;
            width: 100%;
            cursor: pointer;
        }
        input[type="file"]:hover { border-color: #0d7377; }
        button { 
            background: #0d7377; 
            color: white; 
            border: none; 
            padding: 12px 24px; 
            border-radius: 4px; 
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
        }
        button:hover { background: #0a5c5f; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .help { font-size: 12px; color: #666; margin-top: 5px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 15px; }
        .tab { 
            padding: 8px 16px; 
            background: #eee; 
            border-radius: 4px; 
            cursor: pointer;
        }
        .tab.active { background: #0d7377; color: white; }
        .hidden { display: none; }
        #result { margin-top: 20px; }
        .error { color: #c44536; background: #fee; padding: 10px; border-radius: 4px; }
        .success { color: #0d7377; background: #e8f5f5; padding: 10px; border-radius: 4px; }
        .info { color: #1a5276; background: #e8f0f5; padding: 10px; border-radius: 4px; }
        .prompt-box { 
            background: #f8f8f8; 
            border: 1px solid #ddd; 
            padding: 15px; 
            border-radius: 4px;
            font-family: monospace;
            font-size: 11px;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }
        .columns { display: flex; gap: 10px; align-items: center; }
        .columns input { width: 60px; text-align: center; }
        .file-list { 
            margin-top: 8px; 
            font-size: 12px; 
            color: #666;
        }
        .file-list span {
            display: inline-block;
            background: #e8f5f5;
            padding: 2px 8px;
            border-radius: 3px;
            margin: 2px;
        }
        /* Editor View Styles */
        .editor-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: #2a2a2a;
            z-index: 1000;
            display: none;
        }
        .editor-container.visible { display: flex; flex-direction: column; }
        .editor-toolbar {
            background: #333;
            padding: 10px 20px;
            display: flex;
            gap: 15px;
            align-items: center;
            border-bottom: 1px solid #444;
        }
        .editor-toolbar button {
            padding: 8px 16px;
            font-size: 13px;
        }
        .editor-toolbar .btn-secondary {
            background: #555;
        }
        .editor-toolbar .btn-secondary:hover {
            background: #666;
        }
        .editor-toolbar span {
            color: #aaa;
            font-size: 13px;
        }
        .editor-canvas-wrapper {
            flex: 1;
            overflow: auto;
            padding: 20px;
            display: flex;
            justify-content: center;
        }
        .editor-canvas {
            background: white;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            position: relative;
            min-height: 100%;
        }
        .editor-box {
            position: absolute;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
            cursor: move;
            user-select: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: box-shadow 0.2s;
        }
        .editor-box:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .editor-box.selected {
            outline: 2px solid #0d7377;
            outline-offset: 2px;
        }
        .editor-box.dragging {
            opacity: 0.8;
            z-index: 100;
        }
        .editor-box-header {
            padding: 0.75mm 2.25mm;
            color: white;
            font-size: 3.75pt;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 2.25mm;
            min-height: 2.25mm;
            max-height: 2.25mm;
        }
        .editor-box-content {
            padding: 0.75mm;
            font-size: 3.37pt;
            line-height: 1.2mm;
            overflow: hidden;
            color: #333;
            white-space: pre-wrap;
            flex: 1;
            font-family: 'Helvetica', 'Arial', sans-serif;
        }
        .editor-box {
            display: flex;
            flex-direction: column;
        }
        .content-overflow {
            border: 2px solid #e74c3c !important;
        }
        .content-overflow::after {
            content: "⚠️";
            position: absolute;
            top: 2px;
            right: 2px;
            background: #e74c3c;
            color: white;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 10px;
            pointer-events: none;
            z-index: 10;
        }
        .content-fits {
            border: 2px solid #27ae60 !important;
        }
        .font-controls {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #ccc;
            font-size: 12px;
        }
        .font-controls input {
            width: 45px;
            padding: 3px 5px;
            border: 1px solid #555;
            border-radius: 3px;
            background: #444;
            color: white;
            font-size: 11px;
        }
        .font-controls label {
            font-size: 11px;
        }
        .resize-handle {
            position: absolute;
            width: 12px;
            height: 12px;
            bottom: 0;
            right: 0;
            cursor: se-resize;
            background: linear-gradient(135deg, transparent 50%, #0d7377 50%);
            border-radius: 0 0 3px 0;
        }
        .editor-zoom {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-left: auto;
        }
        .editor-zoom input {
            width: 80px;
        }
        .page-indicator {
            color: #fff;
            font-size: 12px;
            background: #555;
            padding: 4px 12px;
            border-radius: 4px;
        }
        .page-divider {
            position: absolute;
            left: 0;
            right: 0;
            height: 2px;
            background: repeating-linear-gradient(90deg, #e74c3c 0, #e74c3c 10px, transparent 10px, transparent 20px);
            pointer-events: none;
        }
        .page-divider::after {
            content: 'Page Break';
            position: absolute;
            right: 10px;
            top: -8px;
            font-size: 10px;
            color: #e74c3c;
            background: white;
            padding: 0 5px;
        }
        .grid-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
            opacity: 0.1;
            background-image: 
                linear-gradient(to right, #000 1px, transparent 1px),
                linear-gradient(to bottom, #000 1px, transparent 1px);
            background-size: 20px 20px;
        }
        .snap-guide {
            position: absolute;
            background: #0d7377;
            pointer-events: none;
            z-index: 50;
        }
        .snap-guide.horizontal {
            height: 1px;
            left: 0;
            right: 0;
        }
        .snap-guide.vertical {
            width: 1px;
            top: 0;
            bottom: 0;
        }
        /* Edit Modal Styles */
        .edit-modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0,0,0,0.7);
            z-index: 2000;
            display: none;
            justify-content: center;
            align-items: center;
        }
        .edit-modal-overlay.visible {
            display: flex;
        }
        .edit-modal {
            background: white;
            border-radius: 8px;
            width: 700px;
            max-width: 90vw;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        .edit-modal-header {
            padding: 15px 20px;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .edit-modal-header h3 {
            margin: 0;
            color: #333;
        }
        .edit-modal-close {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #666;
            padding: 0;
            line-height: 1;
        }
        .edit-modal-close:hover {
            color: #333;
        }
        .edit-modal-body {
            padding: 20px;
            overflow-y: auto;
            flex: 1;
        }
        .edit-modal-body label {
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
            color: #444;
        }
        .edit-modal-body input[type="text"],
        .edit-modal-body textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
            margin-bottom: 15px;
        }
        .edit-modal-body textarea {
            min-height: 300px;
            resize: vertical;
        }
        .edit-modal-footer {
            padding: 15px 20px;
            border-top: 1px solid #ddd;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }
        .edit-modal-footer .btn-cancel {
            background: #666;
        }
        .edit-modal-footer .btn-delete {
            background: #c44536;
            margin-right: auto;
        }
        .edit-modal-footer .btn-delete:hover {
            background: #a33;
        }
        .editor-box-edit-btn {
            background: rgba(255,255,255,0.3);
            border: none;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 9px;
        }
        .editor-box-edit-btn:hover {
            background: rgba(255,255,255,0.5);
        }
    </style>
</head>
<body>
    <h1>📄 Cheat Sheet Generator</h1>
    
    <div class="section">
        <div class="tabs">
            <div class="tab" onclick="showTab('format')">1. Format Topics</div>
            <div class="tab" onclick="showTab('prompt')">2. Generate Prompt</div>
            <div class="tab active" onclick="showTab('ai')">3. AI Output → PDF</div>
        </div>
        
        <!-- Tab 0: Format Topics -->
        <div id="tab-format" class="hidden">
            <label>Paste raw topics (any format)</label>
            <textarea id="raw-topics" placeholder="Paste your topics here in any format...

Example:
Module 1 - HTML Basics:
• Understand HTML document structure
• Know semantic elements

Module 2 - CSS:
• Apply Flexbox layouts
• Use CSS Grid"></textarea>
            <p class="help">The AI will convert these to "A1: ..., B1: ..." format WITHOUT changing any content</p>
            
            <button onclick="formatTopics()" style="margin-top: 15px;">Generate Formatter Prompt</button>
            
            <div id="format-result" class="hidden" style="margin-top: 15px;">
                <label>Copy this to Claude/ChatGPT:</label>
                <div class="prompt-box" id="format-output"></div>
                <button onclick="copyFormatPrompt()" style="margin-top: 10px;">📋 Copy to Clipboard</button>
                <p class="help" style="margin-top: 10px;">After AI responds, paste the formatted topics into the "Generate Prompt" tab</p>
            </div>
        </div>
        
        <!-- Tab 1: Direct AI Output -->
        <div id="tab-ai">
            <label>Paste AI Output (with [BOX]...[/BOX] format)</label>
            <textarea id="ai-output" placeholder="[BOX:A1]
[TITLE:Your Title]
Content here...
• Bullet points
• More content
[/BOX]

[BOX:A2]
..."></textarea>
            <p class="help">Paste the output from Claude/ChatGPT that uses the [BOX] format</p>
            
            <div style="display: flex; gap: 10px; margin-top: 15px;">
                <button onclick="generatePDF()">Generate PDF</button>
                <button onclick="openEditor()" class="btn-editor" style="background: #1a5276;">📐 Open Editor</button>
            </div>
        </div>
        
        <!-- Tab 2: Generate Prompt from Documents -->
        <div id="tab-prompt" class="hidden">
            <label>Topics (one per line)</label>
            <textarea id="topics" class="small-textarea" placeholder="A1: Introduction to Project Management
A2: Agile Methodologies
B1: Risk Assessment
..."></textarea>
            
            <label style="margin-top: 15px;">Upload Lecture Documents</label>
            <input type="file" id="lecture-files" multiple accept=".pdf,.docx,.txt,.md">
            <div class="file-list" id="file-list"></div>
            <p class="help">Upload PDF, DOCX, or TXT files. Multiple files supported.</p>
            
            <label style="margin-top: 15px;">Or paste lecture content directly</label>
            <textarea id="lecture-content" class="small-textarea" placeholder="(Optional) Paste additional notes here..."></textarea>
            
            <button onclick="generatePrompt()" style="margin-top: 15px;" id="prompt-btn">Generate Prompt for AI</button>
            
            <div id="prompt-result" class="hidden" style="margin-top: 15px;">
                <label>Copy this to Claude/ChatGPT:</label>
                <div class="prompt-box" id="prompt-output"></div>
                <button onclick="copyPrompt()" style="margin-top: 10px;">📋 Copy to Clipboard</button>
            </div>
        </div>
    </div>
    
    <div id="result"></div>
    
    <!-- Editor View -->
    <div id="editor-container" class="editor-container">
        <div class="editor-toolbar">
            <button onclick="closeEditor()" class="btn-secondary">← Back</button>
            <button onclick="addNewBox()">➕ Add Box</button>
            <button onclick="resetLayout()">🔄 Reset Layout</button>
            <button onclick="autoArrange()">📊 Auto Arrange</button>
            <span>|</span>
            <label style="color: #aaa; font-size: 13px;">
                <input type="checkbox" id="show-grid" onchange="toggleGrid()"> Show Grid
            </label>
            <label style="color: #aaa; font-size: 13px;">
                <input type="checkbox" id="snap-to-grid" checked> Snap to Grid
            </label>
            <span>|</span>
            <div class="editor-zoom">
                <span>Zoom:</span>
                <input type="range" id="zoom-slider" min="50" max="150" value="100" onchange="setZoom(this.value)">
                <span id="zoom-value">100%</span>
            </div>
            <span class="page-indicator" id="page-indicator">Page 1</span>
            <button onclick="exportFromEditor()" style="background: #0d7377;">📥 Export PDF</button>
        </div>
        <div class="editor-canvas-wrapper" id="canvas-wrapper">
            <div class="editor-canvas" id="editor-canvas">
                <div class="grid-overlay" id="grid-overlay" style="display: none;"></div>
            </div>
        </div>
    </div>
    
    <!-- Edit Box Modal -->
    <div id="edit-modal-overlay" class="edit-modal-overlay">
        <div class="edit-modal">
            <div class="edit-modal-header">
                <h3>✏️ Edit Box <span id="edit-box-id"></span></h3>
                <button class="edit-modal-close" onclick="closeEditModal()">&times;</button>
            </div>
            <div class="edit-modal-body">
                <label for="edit-box-id-input">ID (e.g., A1, B2)</label>
                <input type="text" id="edit-box-id-input" placeholder="Box ID..." style="width: 100px; margin-bottom: 15px;">
                
                <label for="edit-box-title">Title</label>
                <input type="text" id="edit-box-title" placeholder="Box title...">
                
                <label for="edit-box-content">Content</label>
                <textarea id="edit-box-content" placeholder="Box content...
• Use bullet points with '• '
• Use **bold** for emphasis
• Use numbered lists: 1. 2. 3."></textarea>
                
                <div id="height-info" style="margin-top: 10px; padding: 8px; background: #f0f0f0; border-radius: 4px; font-size: 13px; display: none;">
                    <div style="margin-bottom: 5px;">
                        <strong>Height Status:</strong> 
                        <span id="height-status-text"></span>
                    </div>
                    <button onclick="autoFitHeight()" style="padding: 5px 10px; font-size: 12px; cursor: pointer;">📏 Auto-fit Height to Content</button>
                </div>
            </div>
            <div class="edit-modal-footer">
                <button class="btn-delete" onclick="deleteBox()">🗑️ Delete</button>
                <button class="btn-cancel" onclick="closeEditModal()">Cancel</button>
                <button onclick="saveBoxEdit()">💾 Save</button>
            </div>
        </div>
    </div>
    
    <script>
        // Show selected files
        const lectureFilesInput = document.getElementById('lecture-files');
        if (lectureFilesInput) {
            lectureFilesInput.addEventListener('change', function(e) {
                const fileList = document.getElementById('file-list');
                const files = Array.from(e.target.files);
                if (files.length) {
                    fileList.innerHTML = 'Selected: ' + files.map(f => '<span>' + f.name + '</span>').join('');
                } else {
                    fileList.innerHTML = '';
                }
            });
        }
    
        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tabs .tab').forEach(t => {
                if (t.textContent.toLowerCase().includes(tab)) t.classList.add('active');
            });
            document.getElementById('tab-ai').classList.toggle('hidden', tab !== 'ai');
            document.getElementById('tab-prompt').classList.toggle('hidden', tab !== 'prompt');
            document.getElementById('tab-format').classList.toggle('hidden', tab !== 'format');
        }
        
        function formatTopics() {
            const raw = document.getElementById('raw-topics').value;
            const result = document.getElementById('result');
            
            if (!raw.trim()) {
                result.innerHTML = '<div class="error">Please paste raw topics first</div>';
                return;
            }
            
            // Build the prompt client-side (it's just string formatting)
            const prompt = `You are a formatting assistant. Your ONLY job is to reformat learning objectives (topics) into a standardized format.

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
${raw}

FORMATTED OUTPUT:`;
            
            document.getElementById('format-output').textContent = prompt;
            document.getElementById('format-result').classList.remove('hidden');
            result.innerHTML = '<div class="success">✓ Prompt generated! Copy it to Claude/ChatGPT.</div>';
        }
        
        function copyFormatPrompt() {
            const text = document.getElementById('format-output').textContent;
            navigator.clipboard.writeText(text);
            document.getElementById('result').innerHTML = '<div class="success">✓ Copied to clipboard!</div>';
        }
        
        async function generatePDF() {
            const aiOutput = document.getElementById('ai-output').value;
            const result = document.getElementById('result');
            
            if (!aiOutput.trim()) {
                result.innerHTML = '<div class="error">Please paste AI output first</div>';
                return;
            }
            
            result.innerHTML = '<div class="success">Generating PDF...</div>';
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ai_output: aiOutput })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'cheatsheet.pdf';
                    a.click();
                    result.innerHTML = '<div class="success">✓ PDF downloaded!</div>';
                } else {
                    const err = await response.json();
                    result.innerHTML = '<div class="error">Error: ' + err.error + '</div>';
                }
            } catch (e) {
                result.innerHTML = '<div class="error">Error: ' + e.message + '</div>';
            }
        }
        
        async function generatePrompt() {
            const topics = document.getElementById('topics').value;
            const manualContent = document.getElementById('lecture-content').value;
            const filesInput = document.getElementById('lecture-files');
            const result = document.getElementById('result');
            const btn = document.getElementById('prompt-btn');
            
            if (!topics.trim()) {
                result.innerHTML = '<div class="error">Please enter topics</div>';
                return;
            }
            
            btn.disabled = true;
            btn.textContent = 'Processing...';
            result.innerHTML = '<div class="info">Extracting text from documents...</div>';
            
            try {
                const formData = new FormData();
                formData.append('topics', topics);
                formData.append('manual_content', manualContent);
                
                // Add files
                for (const file of filesInput.files) {
                    formData.append('files', file);
                }
                
                const response = await fetch('/prompt', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.error) {
                    result.innerHTML = '<div class="error">' + data.error + '</div>';
                } else {
                    document.getElementById('prompt-output').textContent = data.prompt;
                    document.getElementById('prompt-result').classList.remove('hidden');
                    result.innerHTML = '<div class="success">✓ Prompt generated! Copy it to Claude/ChatGPT.</div>';
                }
            } catch (e) {
                result.innerHTML = '<div class="error">Error: ' + e.message + '</div>';
            } finally {
                btn.disabled = false;
                btn.textContent = 'Generate Prompt for AI';
            }
        }
        
        function copyPrompt() {
            const text = document.getElementById('prompt-output').textContent;
            navigator.clipboard.writeText(text);
            document.getElementById('result').innerHTML = '<div class="success">✓ Copied to clipboard!</div>';
        }
        
        // ========== Editor View ==========
        const CATEGORY_COLORS = {
            "A": "#0d7377",
            "B": "#1a5276",
            "C": "#7d6608",
            "D": "#6c3483",
            "E": "#922b21"
        };
        
        // Page dimensions (A4 Landscape in pixels at 96 DPI)
        const PAGE_WIDTH = 1123;  // 297mm
        const PAGE_HEIGHT = 794;  // 210mm
        const MARGIN = 15;
        const GRID_SIZE = 10;
        
        let editorBoxes = [];
        let selectedBox = null;
        let isDragging = false;
        let isResizing = false;
        let dragOffset = { x: 0, y: 0 };
        let currentZoom = 1;
        
        function getMinDimensionsForContent(box) {
            // Find the actual rendered box in the editor to measure its content
            const boxDiv = document.querySelector(`.editor-box[data-index="${editorBoxes.indexOf(box)}"]`);
            if (boxDiv) {
                const content = boxDiv.querySelector('.editor-box-content');
                if (content) {
                    // Measure the actual scroll dimensions needed
                    const headerHeight = boxDiv.querySelector('.editor-box-header').offsetHeight;
                    const minHeight = headerHeight + content.scrollHeight + 4;
                    const minWidth = Math.max(60, content.scrollWidth + 6);
                    return { width: minWidth, height: minHeight };
                }
            }
            
            // Fallback: create a hidden measurement div
            const measureDiv = document.createElement('div');
            measureDiv.style.cssText = `
                position: absolute;
                visibility: hidden;
                font-size: 4.75pt;
                line-height: 1.15;
                font-family: 'Helvetica', 'Arial', sans-serif;
                padding: 1px 1.5px;
                white-space: pre-wrap;
                width: ${box.width - 6}px;
            `;
            measureDiv.textContent = box.content;
            document.body.appendChild(measureDiv);
            
            const contentHeight = measureDiv.offsetHeight;
            document.body.removeChild(measureDiv);
            
            // Header height (3mm ≈ 11px in editor)
            const headerHeight = 11;
            const minHeight = headerHeight + contentHeight + 4;
            
            return { width: 60, height: minHeight };
        }
        
        async function checkContentOverflow(boxDiv) {
            const content = boxDiv.querySelector('.editor-box-content');
            if (!content) return;
            
            // First, do a quick client-side check
            const isOverflowing = content.scrollHeight > content.clientHeight + 2;
            boxDiv.classList.remove('content-overflow', 'content-fits');
            boxDiv.classList.add(isOverflowing ? 'content-overflow' : 'content-fits');
            
            // Then do server-side validation for more accuracy
            const boxIndex = parseInt(boxDiv.dataset.index);
            if (boxIndex !== undefined && boxIndex < editorBoxes.length) {
                const box = editorBoxes[boxIndex];
                try {
                    const estimatedHeight = await estimateServerHeight(box.content, box.width);
                    if (estimatedHeight > 0) {
                        const willOverflow = estimatedHeight > box.height + 5;
                        boxDiv.classList.remove('content-overflow', 'content-fits');
                        boxDiv.classList.add(willOverflow ? 'content-overflow' : 'content-fits');
                        
                        // Add tooltip showing overflow amount
                        if (willOverflow) {
                            const diff = Math.round(estimatedHeight - box.height);
                            boxDiv.setAttribute('title', `⚠️ Content will overflow by ~${diff}px in PDF`);
                        } else {
                            boxDiv.setAttribute('title', '✓ Content fits in PDF');
                        }
                    }
                } catch (error) {
                    // Fall back to client-side check on error
                    console.error('Error checking overflow:', error);
                }
            }
        }
        
        function checkAllOverflows() {
            document.querySelectorAll('.editor-box').forEach(checkContentOverflow);
        }
        
        function parseBoxes(aiOutput) {
            const pattern = /\\[BOX:([A-Za-z0-9\\-_]+)\\]\\s*\\[TITLE:([^\\]]+)\\]\\s*([\\s\\S]*?)\\[\\/BOX\\]/g;
            const boxes = [];
            let match;
            
            while ((match = pattern.exec(aiOutput)) !== null) {
                boxes.push({
                    id: match[1].trim(),
                    title: match[2].trim(),
                    content: match[3].trim(),
                    category: match[1].charAt(0).toUpperCase()
                });
            }
            return boxes;
        }
        
        function getColor(category) {
            return CATEGORY_COLORS[category] || CATEGORY_COLORS["A"];
        }
        
        function estimateBoxHeight(content) {
            const lines = content.split('\\n').filter(l => !l.trim().startsWith('```'));
            let totalLines = 0;
            lines.forEach(line => {
                if (!line.trim()) {
                    totalLines += 0.5;
                } else {
                    totalLines += Math.ceil(line.length / 40);
                }
            });
            return Math.max(60, Math.min(300, 30 + totalLines * 12));
        }
        
        async function openEditor() {
            const aiOutput = document.getElementById('ai-output').value;
            const result = document.getElementById('result');
            
            if (!aiOutput.trim()) {
                result.innerHTML = '<div class="error">Please paste AI output first</div>';
                return;
            }
            
            result.innerHTML = '<div class="info">Calculating layout...</div>';
            
            try {
                // Fetch the EXACT layout from the server (same as PDF generation)
                const response = await fetch('/calculate-layout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ai_output: aiOutput })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    result.innerHTML = '<div class="error">' + data.error + '</div>';
                    return;
                }
                
                // Use the server-calculated layout (matches PDF exactly)
                editorBoxes = data.boxes.map((box, i) => {
                    const layoutInfo = data.layout.find(l => l.id === box.id);
                    return {
                        ...box,
                        x: layoutInfo ? layoutInfo.x : 0,
                        y: layoutInfo ? layoutInfo.y : 0,
                        width: layoutInfo ? layoutInfo.width : 180,
                        height: layoutInfo ? layoutInfo.height : 100,
                        baseHeight: layoutInfo ? layoutInfo.height : 100  // Store original height for scaling
                    };
                });
                
                result.innerHTML = '';
                renderEditor();
                document.getElementById('editor-container').classList.add('visible');
                document.body.style.overflow = 'hidden';
            } catch (e) {
                result.innerHTML = '<div class="error">Error: ' + e.message + '</div>';
            }
        }
        
        function closeEditor() {
            document.getElementById('editor-container').classList.remove('visible');
            document.body.style.overflow = '';
        }
        
        function autoArrange() {
            // Re-fetch layout from server to match PDF exactly
            const aiOutput = document.getElementById('ai-output').value;
            if (!aiOutput.trim()) return;
            
            fetch('/calculate-layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ai_output: aiOutput })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) return;
                
                editorBoxes.forEach(box => {
                    const layoutInfo = data.layout.find(l => l.id === box.id);
                    if (layoutInfo) {
                        box.x = layoutInfo.x;
                        box.y = layoutInfo.y;
                        box.width = layoutInfo.width;
                        box.height = layoutInfo.height;
                    }
                });
                
                renderEditor();
            });
        }
        
        function resetLayout() {
            autoArrange();
        }
        
        function updateCanvasSize() {
            const maxY = Math.max(...editorBoxes.map(b => b.y + b.height)) + MARGIN;
            const numPages = Math.ceil(maxY / PAGE_HEIGHT);
            const canvas = document.getElementById('editor-canvas');
            canvas.style.width = PAGE_WIDTH + 'px';
            canvas.style.height = Math.max(PAGE_HEIGHT, numPages * PAGE_HEIGHT) + 'px';
            
            // Update page indicator
            document.getElementById('page-indicator').textContent = `${numPages} Page${numPages > 1 ? 's' : ''}`;
            
            // Add page dividers
            canvas.querySelectorAll('.page-divider').forEach(d => d.remove());
            for (let p = 1; p < numPages; p++) {
                const divider = document.createElement('div');
                divider.className = 'page-divider';
                divider.style.top = (p * PAGE_HEIGHT) + 'px';
                canvas.appendChild(divider);
            }
        }
        
        function renderEditor() {
            const canvas = document.getElementById('editor-canvas');
            
            // Remove existing boxes
            canvas.querySelectorAll('.editor-box').forEach(b => b.remove());
            canvas.querySelectorAll('.snap-guide').forEach(g => g.remove());
            
            editorBoxes.forEach((box, index) => {
                const div = document.createElement('div');
                div.className = 'editor-box';
                div.dataset.index = index;
                div.style.left = box.x + 'px';
                div.style.top = box.y + 'px';
                div.style.width = box.width + 'px';
                div.style.height = box.height + 'px';
                
                const color = getColor(box.category);
                
                div.innerHTML = `
                    <div class="editor-box-header" style="background: ${color};">
                        <span>${box.id} ${box.title}</span>
                        <button class="editor-box-edit-btn" onclick="openEditModal(${index}, event)">✏️ Edit</button>
                    </div>
                    <div class="editor-box-content">${escapeHtml(box.content)}</div>
                    <div class="resize-handle"></div>
                `;
                
                // Check if content overflows after rendering
                setTimeout(() => checkContentOverflow(div), 0);
                
                // Drag handlers
                div.addEventListener('mousedown', (e) => startDrag(e, index));
                div.querySelector('.resize-handle').addEventListener('mousedown', (e) => startResize(e, index));
                // Double-click to edit
                div.addEventListener('dblclick', (e) => openEditModal(index, e));
                
                canvas.appendChild(div);
            });
            
            updateCanvasSize();
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function startDrag(e, index) {
            if (e.target.classList.contains('resize-handle')) return;
            e.preventDefault();
            
            selectedBox = index;
            isDragging = true;
            
            const box = editorBoxes[index];
            const rect = e.target.closest('.editor-box').getBoundingClientRect();
            const canvasRect = document.getElementById('editor-canvas').getBoundingClientRect();
            
            dragOffset.x = e.clientX - rect.left;
            dragOffset.y = e.clientY - rect.top;
            
            document.querySelectorAll('.editor-box').forEach(b => b.classList.remove('selected'));
            e.target.closest('.editor-box').classList.add('selected', 'dragging');
        }
        
        function startResize(e, index) {
            e.preventDefault();
            e.stopPropagation();
            
            selectedBox = index;
            isResizing = true;
            
            document.querySelectorAll('.editor-box').forEach(b => b.classList.remove('selected'));
            e.target.closest('.editor-box').classList.add('selected');
        }
        
        document.addEventListener('mousemove', (e) => {
            if (selectedBox === null) return;
            
            const canvas = document.getElementById('editor-canvas');
            const canvasRect = canvas.getBoundingClientRect();
            const box = editorBoxes[selectedBox];
            const snapEnabled = document.getElementById('snap-to-grid').checked;
            
            if (isDragging) {
                let newX = (e.clientX - canvasRect.left) / currentZoom - dragOffset.x;
                let newY = (e.clientY - canvasRect.top) / currentZoom - dragOffset.y;
                
                if (snapEnabled) {
                    newX = Math.round(newX / GRID_SIZE) * GRID_SIZE;
                    newY = Math.round(newY / GRID_SIZE) * GRID_SIZE;
                }
                
                // Constrain to canvas
                newX = Math.max(MARGIN, Math.min(PAGE_WIDTH - box.width - MARGIN, newX));
                newY = Math.max(MARGIN, newY);
                
                box.x = newX;
                box.y = newY;
                
                const div = canvas.querySelector(`.editor-box[data-index="${selectedBox}"]`);
                div.style.left = box.x + 'px';
                div.style.top = box.y + 'px';
                
                updateCanvasSize();
            }
            
            if (isResizing) {
                let newWidth = (e.clientX - canvasRect.left) / currentZoom - box.x;
                let newHeight = (e.clientY - canvasRect.top) / currentZoom - box.y;
                
                if (snapEnabled) {
                    newWidth = Math.round(newWidth / GRID_SIZE) * GRID_SIZE;
                    newHeight = Math.round(newHeight / GRID_SIZE) * GRID_SIZE;
                }
                
                // Simple minimum constraints (allow user to resize freely)
                box.width = Math.max(50, Math.min(PAGE_WIDTH - box.x - MARGIN, newWidth));
                box.height = Math.max(30, newHeight);
                
                const div = canvas.querySelector(`.editor-box[data-index="${selectedBox}"]`);
                div.style.width = box.width + 'px';
                div.style.height = box.height + 'px';
                
                // Check overflow while resizing
                checkContentOverflow(div);
                
                updateCanvasSize();
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (selectedBox !== null) {
                const div = document.getElementById('editor-canvas')
                    .querySelector(`.editor-box[data-index="${selectedBox}"]`);
                if (div) div.classList.remove('dragging');
            }
            isDragging = false;
            isResizing = false;
        });
        
        function toggleGrid() {
            const grid = document.getElementById('grid-overlay');
            grid.style.display = document.getElementById('show-grid').checked ? 'block' : 'none';
        }
        
        function setZoom(value) {
            currentZoom = value / 100;
            document.getElementById('zoom-value').textContent = value + '%';
            const canvas = document.getElementById('editor-canvas');
            canvas.style.transform = `scale(${currentZoom})`;
            canvas.style.transformOrigin = 'top left';
        }
        
        function exportFromEditor() {
            // Build AI output format from editor boxes
            let output = '';
            editorBoxes.forEach(box => {
                output += `[BOX:${box.id}]\n[TITLE:${box.title}]\n${box.content}\n[/BOX]\n\n`;
            });
            
            // Build layout data
            const layoutData = editorBoxes.map(box => ({
                id: box.id,
                x: box.x,
                y: box.y,
                width: box.width,
                height: box.height
            }));
            
            // Send to server
            document.getElementById('result').innerHTML = '<div class="success">Generating PDF with custom layout...</div>';
            
            fetch('/generate-with-layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    ai_output: output,
                    layout: layoutData
                })
            })
            .then(response => {
                if (response.ok) return response.blob();
                return response.json().then(err => { throw new Error(err.error); });
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'cheatsheet.pdf';
                a.click();
                document.getElementById('result').innerHTML = '<div class="success">✓ PDF downloaded!</div>';
            })
            .catch(err => {
                document.getElementById('result').innerHTML = '<div class="error">Error: ' + err.message + '</div>';
            });
        }
        
        // ========== Edit Modal Functions ==========
        let editingBoxIndex = null;
        
        function addNewBox() {
            // Generate a new ID based on existing boxes
            const existingIds = editorBoxes.map(b => b.id);
            let newId = 'X1';
            let counter = 1;
            while (existingIds.includes(newId)) {
                counter++;
                newId = 'X' + counter;
            }
            
            const newBox = {
                id: newId,
                title: 'New Box',
                content: '• Add your content here\\n• Use bullet points\\n• Use **bold** for emphasis',
                category: 'A',
                x: MARGIN,
                y: MARGIN,
                width: 180,
                height: 80
            };
            
            editorBoxes.push(newBox);
            renderEditor();
            
            // Open edit modal for the new box
            openEditModal(editorBoxes.length - 1);
        }
        
        function openEditModal(index, event) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            editingBoxIndex = index;
            const box = editorBoxes[index];
            
            document.getElementById('edit-box-id').textContent = box.id;
            document.getElementById('edit-box-id-input').value = box.id;
            document.getElementById('edit-box-title').value = box.title;
            document.getElementById('edit-box-content').value = box.content;
            
            document.getElementById('edit-modal-overlay').classList.add('visible');
            document.getElementById('edit-box-title').focus();
            
            // Update height info when opening
            updateHeightInfo();
            
            // Add event listener for content changes
            const contentTextarea = document.getElementById('edit-box-content');
            contentTextarea.removeEventListener('input', updateHeightInfo);
            contentTextarea.addEventListener('input', updateHeightInfo);
        }
        
        function closeEditModal() {
            editingBoxIndex = null;
            document.getElementById('edit-modal-overlay').classList.remove('visible');
        }
        
        function saveBoxEdit() {
            if (editingBoxIndex === null) return;
            
            const box = editorBoxes[editingBoxIndex];
            const newId = document.getElementById('edit-box-id-input').value.trim() || box.id;
            
            box.id = newId;
            box.category = newId.charAt(0).toUpperCase();
            box.title = document.getElementById('edit-box-title').value;
            box.content = document.getElementById('edit-box-content').value;
            
            // Recalculate height based on new content
            box.height = estimateBoxHeight(box.content);
            
            closeEditModal();
            renderEditor();
        }
        
        async function estimateServerHeight(content, width) {
            try {
                const response = await fetch('/estimate-height', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content, width })
                });
                const data = await response.json();
                return data.estimated_height || 0;
            } catch (error) {
                console.error('Error estimating height:', error);
                return 0;
            }
        }
        
        async function updateHeightInfo() {
            if (editingBoxIndex === null) return;
            
            const box = editorBoxes[editingBoxIndex];
            const content = document.getElementById('edit-box-content').value;
            
            // Get estimated height from server
            const estimatedHeight = await estimateServerHeight(content, box.width);
            
            const heightInfo = document.getElementById('height-info');
            const statusText = document.getElementById('height-status-text');
            
            if (estimatedHeight > 0) {
                heightInfo.style.display = 'block';
                
                const currentHeight = box.height;
                const diff = Math.round(estimatedHeight - currentHeight);
                
                if (diff > 5) {
                    statusText.innerHTML = `<span style="color: #e74c3c;">⚠️ Content will overflow by ~${diff}px</span>`;
                } else if (diff < -20) {
                    statusText.innerHTML = `<span style="color: #3498db;">ℹ️ Box has ${-diff}px extra space</span>`;
                } else {
                    statusText.innerHTML = `<span style="color: #27ae60;">✓ Content fits well</span>`;
                }
            } else {
                heightInfo.style.display = 'none';
            }
        }
        
        async function autoFitHeight() {
            if (editingBoxIndex === null) return;
            
            const box = editorBoxes[editingBoxIndex];
            const content = document.getElementById('edit-box-content').value;
            
            // Get estimated height from server
            const estimatedHeight = await estimateServerHeight(content, box.width);
            
            if (estimatedHeight > 0) {
                box.height = Math.max(30, Math.round(estimatedHeight));
                await updateHeightInfo();
            }
        }
        
        function deleteBox() {
            if (editingBoxIndex === null) return;
            
            if (confirm('Are you sure you want to delete this box?')) {
                editorBoxes.splice(editingBoxIndex, 1);
                closeEditModal();
                renderEditor();
            }
        }
        
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && document.getElementById('edit-modal-overlay').classList.contains('visible')) {
                closeEditModal();
                e.stopPropagation();
                return;
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Skip if modal is open
            if (document.getElementById('edit-modal-overlay').classList.contains('visible')) return;
            if (!document.getElementById('editor-container').classList.contains('visible')) return;
            
            if (e.key === 'Escape') {
                closeEditor();
            }
            
            if (selectedBox !== null) {
                const box = editorBoxes[selectedBox];
                const step = e.shiftKey ? 10 : 1;
                
                if (e.key === 'ArrowLeft') { box.x -= step; e.preventDefault(); }
                if (e.key === 'ArrowRight') { box.x += step; e.preventDefault(); }
                if (e.key === 'ArrowUp') { box.y -= step; e.preventDefault(); }
                if (e.key === 'ArrowDown') { box.y += step; e.preventDefault(); }
                
                // Open edit on Enter key
                if (e.key === 'Enter') {
                    openEditModal(selectedBox, e);
                }
                
                renderEditor();
            }
        });
        
        // Close modal on overlay click
        const editModalOverlay = document.getElementById('edit-modal-overlay');
        if (editModalOverlay) {
            editModalOverlay.addEventListener('click', function(e) {
                if (e.target.id === 'edit-modal-overlay') {
                    closeEditModal();
                }
            });
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    ai_output = data.get('ai_output', '')
    
    if not ai_output:
        return jsonify({'error': 'No AI output provided'}), 400
    
    # Parse boxes
    boxes = parse_ai_output(ai_output)
    
    if not boxes:
        return jsonify({'error': 'No valid [BOX] blocks found in input'}), 400
    
    # Generate PDF to temp file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        output_path = f.name
    
    try:
        renderer = CheatSheetRenderer(output_path)
        renderer.render(boxes)
        
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='cheatsheet.pdf'
        )
    finally:
        if os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except:
                pass


@app.route('/calculate-layout', methods=['POST'])
def calculate_layout():
    """Calculate box positions and sizes for editor preview - matches PDF output exactly."""
    data = request.json
    ai_output = data.get('ai_output', '')
    
    if not ai_output:
        return jsonify({'error': 'No AI output provided'}), 400
    
    boxes = parse_ai_output(ai_output)
    
    if not boxes:
        return jsonify({'error': 'No valid [BOX] blocks found in input'}), 400
    
    # Calculate layout using same algorithm as PDF generation
    renderer = CheatSheetRenderer("dummy.pdf")
    layout = renderer.calculate_layout(boxes)
    
    return jsonify({'layout': layout, 'boxes': [{'id': b.id, 'title': b.title, 'content': b.content, 'category': b.category} for b in boxes]})


@app.route('/estimate-height', methods=['POST'])
def estimate_height():
    """Calculate the height needed for content using PDF renderer logic."""
    data = request.json
    content = data.get('content', '')
    width = data.get('width', 100)
    
    if not content:
        return jsonify({'estimated_height': 0})
    
    # Use renderer's height estimation
    # Need a temporary canvas for string width calculations
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    
    temp_buffer = io.BytesIO()
    renderer = CheatSheetRenderer("dummy.pdf")
    renderer.c = canvas.Canvas(temp_buffer, pagesize=landscape(A4))
    
    # Convert editor width to PDF width
    # Editor: 1123x794, PDF: 842x595 points
    pdf_width = width * (renderer.page_width / 1123)
    
    # Calculate PDF height needed for content
    pdf_height = renderer._estimate_content_height(content, pdf_width)
    
    # Add header and padding
    total_pdf_height = renderer.header_height + pdf_height + renderer.box_padding * 2
    
    # Convert back to editor height
    editor_height = total_pdf_height * (794 / renderer.page_height)
    
    # Clean up
    renderer.c = None
    
    return jsonify({'estimated_height': editor_height})


@app.route('/generate-with-layout', methods=['POST'])
def generate_with_layout():
    """Generate PDF with custom box positions and sizes from the editor."""
    data = request.json
    ai_output = data.get('ai_output', '')
    layout = data.get('layout', [])
    
    if not ai_output:
        return jsonify({'error': 'No AI output provided'}), 400
    
    # Parse boxes
    boxes = parse_ai_output(ai_output)
    
    if not boxes:
        return jsonify({'error': 'No valid [BOX] blocks found in input'}), 400
    
    # Generate PDF to temp file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        output_path = f.name
    
    try:
        renderer = CheatSheetRenderer(output_path)
        renderer.render_with_layout(boxes, layout)
        
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='cheatsheet.pdf'
        )
    finally:
        if os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except:
                pass


@app.route('/prompt', methods=['POST'])
def generate_prompt():
    topics_raw = request.form.get('topics', '')
    manual_content = request.form.get('manual_content', '')
    
    # Parse topics
    topics = [l.strip() for l in topics_raw.strip().split('\n') if l.strip()]
    
    if not topics:
        return jsonify({'error': 'No topics provided'})
    
    # Extract text from uploaded files
    all_content = []
    
    files = request.files.getlist('files')
    for file in files:
        if file.filename:
            text = extract_text_from_file(file)
            if text.strip():
                all_content.append(f"--- {file.filename} ---\n{text}")
    
    # Add manual content
    if manual_content.strip():
        all_content.append(f"--- Manual Notes ---\n{manual_content}")
    
    if not all_content:
        return jsonify({'error': 'No lecture content provided (upload files or paste text)'})
    
    combined_content = "\n\n".join(all_content)
    
    # Build prompt
    system_prompt, user_prompt = build_prompt(topics, combined_content)
    
    # Combine for easy copy-paste
    full_prompt = f"""{system_prompt}

---

{user_prompt}"""
    
    return jsonify({'prompt': full_prompt})


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    print("\n" + "="*50)
    print("  Cheat Sheet Generator")
    print(f"  Open: http://localhost:{port}")
    print(f"  PDF support: {'Yes' if HAS_PDF else 'No (install PyMuPDF)'}")
    print(f"  DOCX support: {'Yes' if HAS_DOCX else 'No (install python-docx)'}")
    print("="*50 + "\n")
    app.run(debug=debug, host='0.0.0.0', port=port)
