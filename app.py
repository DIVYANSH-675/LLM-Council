#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Council - Enterprise Grade Interface
Design: Clean Modern (Linear/Notion Style) - High Visibility (LIVE STREAMING)
"""

import asyncio
import gradio as gr
import sys
import markdown
import time
from pathlib import Path

# Setup local imports
sys.path.insert(0, str(Path(__file__).parent))

from src.core.council import create_council
from src.core.decision import Decision, BlockedDecision

# ==============================================================================
# 🎨 UI CONFIGURATION
# ==============================================================================
CUSTOM_CSS = '''
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

body { font-family: 'Inter', sans-serif !important; }

/* Header Styling */
.header-container {
    text-align: center;
    padding: 3rem 1rem 2rem;
    background: linear-gradient(to bottom, transparent, rgba(59, 130, 246, 0.05));
    border-bottom: 1px solid var(--border-color-primary);
}
.header-title { font-size: 2.25rem; font-weight: 700; letter-spacing: -0.025em; margin-bottom: 0.5rem; }
.header-subtitle { font-size: 1.1rem; color: var(--body-text-color-subdued); }

/* Agent Card Styling */
.agent-card {
    border: 1px solid var(--border-color-primary);
    border-radius: 12px;
    padding: 1.5rem;
    background: var(--background-fill-secondary);
    height: 100%;
    display: flex; flex-direction: column;
}
.agent-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border-color-primary); }
.agent-icon { font-size: 1.5rem; margin-right: 0.75rem; }
.agent-name { font-weight: 600; font-size: 1rem; }
.agent-meta { font-size: 0.85rem; color: var(--body-text-color-subdued); }

/* Response Text Styling */
.response-text { font-size: 0.95rem; line-height: 1.6; flex-grow: 1; overflow-y: auto; max-height: 400px; }
.response-text p { margin-bottom: 0.75rem; }
.response-text ul, .response-text ol { margin-left: 1.5rem; margin-bottom: 0.75rem; }
.response-text h1, .response-text h2, .response-text h3 { margin-top: 1rem; margin-bottom: 0.5rem; font-weight: 600; }
.response-text code { background: rgba(0,0,0,0.1); padding: 2px 4px; border-radius: 4px; font-family: monospace; }
.dark .response-text code { background: rgba(255,255,255,0.1); }

/* Risks Box */
.risk-box {
    margin-top: 1.5rem;
    padding: 1rem;
    background: #FFF5F5;
    border-radius: 8px;
    border: 1px solid #FED7D7;
}
.dark .risk-box {
    background: rgba(220, 38, 38, 0.1);
    border-color: rgba(220, 38, 38, 0.2);
}
.risk-header {
    font-weight: 600;
    color: #C53030;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    cursor: pointer;
}
.dark .risk-header { color: #FECACA; }
.risk-list {
    margin: 0;
    padding-left: 1.5rem;
    color: #9B2C2C;
    font-size: 0.9rem;
}
.dark .risk-list { color: #FCA5A5; }
    
/* Tables */
.response-text table { width: 100%; border-collapse: collapse; margin: 1em 0; font-size: 0.9em; }
.response-text th, .response-text td { padding: 0.6em; border: 1px solid var(--border-color-primary); text-align: left; }
.response-text th { background: var(--background-fill-secondary); font-weight: 600; }

/* Final Answer Box */
.final-answer-box { background: var(--background-fill-primary); border: 1px solid var(--primary-500); border-radius: 12px; padding: 2rem; margin-top: 2rem; position: relative; }
.final-label { position: absolute; top: -12px; left: 2rem; background: var(--primary-500); color: white; padding: 0.25rem 1rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }

footer { display: none !important; }

/* Scrollbars */
.response-text { scrollbar-width: none; -ms-overflow-style: none; }
.response-text::-webkit-scrollbar { display: none; }
.response-text pre {
    white-space: pre;
    overflow-x: auto;
    background: #0f172a;
    padding: 1.5rem;
    border-radius: 8px;
    margin: 1.5rem 0;
    border: 1px solid #334155;
    scrollbar-width: thin;
    line-height: 1.2;
}

/* --- CUSTOM AGENT BUTTONS --- */
/* Transparent row with explicit gap */
/* Standardize row but rely on item margins for gap to be safe */
#agent-row { 
    background: transparent !important; 
    border: none !important; 
    padding: 0 !important; 
    margin-bottom: 0 !important;
    overflow: visible !important; /* Ensure margins don't collapse/hide */
}
#agent-row > * { background: transparent !important; border: none !important; box-shadow: none !important; }

/* Remove default styles and add spacing */
#dd-analytical, #dd-creative, #dd-pragmatist { 
    background: transparent !important; 
    border: none !important; 
    box-shadow: none !important; 
    padding: 0 !important;
}

/* Add Right Margin to the first two to force separation */
#dd-analytical, #dd-creative { margin-right: 25px !important; }

/* The actual colored button part */
#dd-analytical .wrap, #dd-creative .wrap, #dd-pragmatist .wrap { 
    background: var(--button-primary-background-fill); 
    border: none !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

/* Hide input text and arrows */
#dd-analytical input, #dd-creative input, #dd-pragmatist input { color: transparent !important; }
#dd-analytical svg, #dd-creative svg, #dd-pragmatist svg { display: none !important; }

/* Centered Labels */
#dd-analytical::after { content: 'Analytical'; position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); color: white; pointer-events: none; font-weight: 600; font-size: 1rem; }
#dd-creative::after { content: 'Creative'; position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); color: white; pointer-events: none; font-weight: 600; font-size: 1rem; }
#dd-pragmatist::after { content: 'Pragmatist'; position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); color: white; pointer-events: none; font-weight: 600; font-size: 1rem; }

/* --- CONTROL ROWS (Slider & Checkboxes) --- */
/* We style both #slider-row (Left) and #checkbox-row (Right) identically for symmetry */
#slider-row, #checkbox-row { 
    display: flex !important; 
    align-items: center !important; 
    gap: 15px; 
    margin-top: 8px !important; /* Reduced vertical gap to match top elements */
    background: #1e293b !important; 
    padding: 6px 16px;
    border-radius: 8px; 
    border: 1px solid var(--border-color-primary);
    height: 48px; 
}

#words-label { 
    width: auto !important; 
    flex: 0 0 auto !important; 
    margin-bottom: 0 !important; 
    font-size: 0.9rem;
    font-weight: 600;
}

/* --- SLIDER FIX --- */
.force-inline-slider .form, 
.force-inline-slider .wrap .head, 
.force-inline-slider .wrap label,
.force-inline-slider input[type=number] { 
    display: none !important; 
    border: none !important;
}
.force-inline-slider .wrap { 
    background: transparent !important; 
    border: none !important; 
    padding: 0 !important;
    box-shadow: none !important;
}
.force-inline-slider { 
    flex-grow: 1 !important; 
    width: auto !important;
    min-width: 0 !important;
    margin-bottom: 0 !important;
    border: none !important;
    background: transparent !important;
}

#words-number { 
    width: 80px !important; 
    flex: 0 0 auto !important; 
}
#words-number input { text-align: center; font-weight: 600; padding: 2px !important; }

/* --- CHECKBOX FIX --- */
/* Clean up the right side row to match the left side slider row */
#checkbox-row label {
    margin: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    border: none !important;
    display: flex;
    align-items: center;
}
#checkbox-row span { font-weight: 600; }
'''

theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="slate",
    neutral_hue="slate",
    radius_size="lg",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
)

def format_agent_card(r, score=None, is_winner=False):
    agent_info = {
        "Analytical Agent": {"icon": "📊", "border": "#3b82f6"},
        "Creative Agent": {"icon": "🎨", "border": "#a855f7"},
        "Pragmatist Agent": {"icon": "🏗️", "border": "#f97316"}
    }
    meta = agent_info.get(r.agent_type, {"icon": "🤖", "border": "#64748b"})
    
    winner_badge = '<span style="background: #F59E0B; color: white; font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; font-weight: bold; margin-left: 8px;">🏆 SELECTED</span>' if is_winner else ""
    score_display = f'<span style="font-weight: 600; color: var(--primary-600);">{score:.1f}/10</span>' if score else ""
    style_override = f"border-color: {meta['border']}; border-width: 2px;" if is_winner else ""
    html_content = markdown.markdown(r.response_text, extensions=['tables', 'fenced_code'])
    
    return f'''
    <div class="agent-card" style="{style_override}">
        <div class="agent-header">
            <div style="display: flex; align-items: center;">
                <span class="agent-icon">{meta['icon']}</span>
                <div>
                    <div class="agent-name">{r.agent_type} {winner_badge}</div>
                    <div class="agent-meta">temp={r.temperature}</div>
                </div>
            </div>
            <div>{score_display}</div>
        </div>
        <div class="response-text">{html_content}</div>
    </div>
    '''

def format_grid(cards):
    return f'''
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
        {''.join(cards)}
    </div>
    '''

def format_final_section(text, risks=None, score=None, time_ms=None, refined=False):
    risks_html = ""
    if risks:
        unique_risks = list(dict.fromkeys(risks))
        count = len(unique_risks)
        items = "".join([f"<li style='margin-bottom: 4px;'>{r}</li>" for r in unique_risks])
        content = f'<ul class="risk-list">{items}</ul>'
        risks_html = f'''
        <div class="risk-box">
            <details {'open' if count <= 3 else ''}>
                <summary class="risk-header">
                    ⚠️ {count} Identified Risks (Click to expand)
                </summary>
                <div style="margin-top: 0.5rem;">
                    {content}
                </div>
            </details>
        </div>
        '''
        
    metrics_html = ""
    if score is not None:
        conf_badge = f'<span style="font-weight: 600; color: var(--secondary-600);">🎯 {score*100:.0f}% Confidence</span>'
        time_badge = f'<span style="font-family: monospace; color: var(--body-text-color-subdued);">⏱️ {time_ms}ms</span>' if time_ms else ""
        metrics_html = f"""
        <div style="display: flex; align-items: center; gap: 1.5rem; margin-bottom: 1.5rem;">
            {conf_badge} {time_badge}
            <span style="color: var(--body-text-color-subdued);">| Strategy: {'MoA Refinement' if refined else 'Direct Selection'}</span>
        </div>
        """

    final_text_html = markdown.markdown(text, extensions=['tables', 'fenced_code'])
    return f'''
    {metrics_html}
    <div class="final-answer-box">
        <div class="final-label">✨ FINAL CONSENSUS</div>
        <div class="response-text" style="font-size: 1.05rem;">{final_text_html}</div>
        {risks_html}
    </div>
    '''

def format_score_table(evaluations):
    if not evaluations:
        return ""
    
    data = {}
    for e in evaluations:
        aid = e.target_agent_id
        if aid not in data: data[aid] = {}
        data[aid][e.judge_type] = e.scores
    
    rows = ""
    for aid, judges in data.items():
        f_scores = judges.get("Factuality", {})
        acc = f_scores.get("accuracy", "-")
        evd = f_scores.get("evidence", "-")
        cmpl = f_scores.get("completeness", "-")
        
        s_scores = judges.get("Safety", {})
        harm = s_scores.get("harmlessness", "-")
        eth = s_scores.get("ethics", "-")
        
        total = 0.0
        count = 0
        if "Factuality" in judges: 
            total += sum(f_scores.values()) 
            count += len(f_scores)
        if "Safety" in judges: 
            total += sum(s_scores.values()) 
            count += len(s_scores)
        
        avg_val = total / count if count > 0 else 0
        avg = f"{avg_val:.1f}"
        
        name = aid.replace("agent_", "").replace("_", " ").title()
        if "Analytical" in name: name = "📊 " + name
        elif "Creative" in name: name = "🎨 " + name
        elif "Pragmatist" in name: name = "🏗️ " + name
        elif "Safety" in name: name = "🛡️ " + name
        
        rows += f'''
        <tr style="border-bottom: 1px solid var(--border-color-primary);">
            <td style="padding: 0.75rem;">{name}</td>
            <td style="color: var(--secondary-500);">{acc}</td>
            <td style="color: var(--secondary-500);">{evd}</td>
            <td style="color: var(--secondary-500);">{cmpl}</td>
            <td style="color: var(--primary-500);">{harm}</td>
            <td style="color: var(--primary-500);">{eth}</td>
            <td style="font-weight: bold;">{avg}</td>
        </tr>
        '''
        
    return f'''
    <div style="margin-top: 2rem; overflow-x: auto;">
        <details>
            <summary style="cursor: pointer; padding: 0.5rem; background: var(--background-fill-secondary); border-radius: 6px; font-weight: 600;">
                📋 Detailed Score Breakdown (Click to View)
            </summary>
            <table style="width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.9rem;">
                <thead>
                    <tr style="text-align: left; border-bottom: 2px solid var(--border-color-primary);">
                        <th style="padding: 0.5rem;">Agent</th>
                        <th style="color: var(--secondary-600);">Acc</th>
                        <th style="color: var(--secondary-600);">Evd</th>
                        <th style="color: var(--secondary-600);">Cmpl</th>
                        <th style="color: var(--primary-600);">Safe</th>
                        <th style="color: var(--primary-600);">Eth</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </details>
    '''

# Model Mapping
MODEL_MAP = {
    "Gpt 4o": "gpt-4o",
    "Claude-Haiku 4.5": "claude-haiku-4-5-20251001", 
    "gemini-2.5-flash": "gemini-2.5-flash"
}

# HTML Templates
APP_HTML_START = '''
<div style="text-align: center; padding: 4rem;">
    <h2 style="color: var(--primary-600);">Initiating Council Protocol...</h2>
    <p>Initializing Agents: Analytical, Creative, Safety</p>
</div>
'''

APP_HTML_BLOCKED = '''
 <div style="text-align: center; padding: 4rem; background: var(--background-fill-secondary); border-radius: 12px; border: 1px solid var(--border-color-primary);">
    <div style="font-size: 4rem; margin-bottom: 1rem;">&#128737;</div>
    <h2 style="color: var(--body-text-color);">Request Blocked</h2>
    <div style="display: inline-block; padding: 1rem 2rem; background: rgba(220, 38, 38, 0.1); color: #DC2626; border-radius: 8px;">{reason}</div>
</div>
'''

APP_HTML_LOADING_JUDGES = '''
<div style="text-align: center; margin: 2rem 0;">
    <h3 style="color: var(--secondary-600);">&#9878; Judges Evaluating Responses...</h3>
</div>
'''

APP_HTML_LOADING_SYNTHESIS = '''
<div style="text-align: center; margin: 2rem 0;">
    <h3 style="color: var(--primary-600);">&#10024; Synthesizing Final Answer (MoA)...</h3>
</div>
'''

APP_HTML_FINAL_WRAPPER = '''
<div>
    <h3 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem;">&#129504; Council Deliberation</h3>
    {cards}
    {table}
    {final}
</div>
'''

async def process_query(
    query: str, 
    use_mock: bool = False, 
    skip_synthesis: bool = False,
    word_limit: int = 1000,
    m_analytical_display: str = "Gpt 4o",
    m_creative_display: str = "Claude-Haiku 4.5",
    m_pragmatist_display: str = "Gpt 4o"
):
    if not query.strip():
        yield ""
        return
    
    # Map display names to actual model IDs
    model_overrides = {
        "analytical": MODEL_MAP.get(m_analytical_display, "gpt-4o"),
        "creative": MODEL_MAP.get(m_creative_display, "claude-haiku-4-5-20251001"),
        "pragmatist": MODEL_MAP.get(m_pragmatist_display, "gpt-4o")
    }
    
    council = create_council(
        use_mock=use_mock, 
        skip_synthesis=skip_synthesis,
        model_overrides=model_overrides
    )
    
    html_out = ""
    
    async for stage, data in council.decide_generator(query, word_limit=word_limit):
        if stage == "start":
            yield APP_HTML_START
        
        elif stage == "blocked":
            yield APP_HTML_BLOCKED.format(reason=data.block_reason)
            
        elif stage == "agents":
            cards = [format_agent_card(r) for r in data]
            yield f"<h3>🧠 Agents Generated Drafts</h3>{format_grid(cards)}{APP_HTML_LOADING_JUDGES}"
            
        elif stage == "judges":
            responses, evals = data
            scores = {}
            for e in evals:
                aid = e.target_agent_id
                if aid not in scores: scores[aid] = []
                scores[aid].append(e.total_score)
            avg_scores = {k: sum(v)/len(v) for k, v in scores.items()}
            
            cards = [format_agent_card(r, avg_scores.get(r.agent_id, 0)) for r in responses]
            table_html = format_score_table(evals)
            
            yield f"<h3>⚖️ Judicial Reviews Complete</h3>{format_grid(cards)}{table_html}{APP_HTML_LOADING_SYNTHESIS}"
            
        elif stage == "final":
            d = data
            scores = {}
            for e in d.judge_evaluations:
                aid = e.target_agent_id
                if aid not in scores: scores[aid] = []
                scores[aid].append(e.total_score)
            avg_scores = {k: sum(v)/len(v) for k, v in scores.items()}
            
            cards = [format_agent_card(r, avg_scores.get(r.agent_id, 0), r.agent_id == d.selected_response.agent_id) for r in d.agent_responses]
            table_html = format_score_table(d.judge_evaluations)
            
            final_section = format_final_section(
                d.get_final_response_text(), 
                d.identified_risks,
                d.confidence_score,
                d.processing_time_ms,
                d.was_refined
            )
            
            yield APP_HTML_FINAL_WRAPPER.format(
                cards=format_grid(cards),
                table=table_html,
                final=final_section
            )

# ==============================================================================
# 🚀 APP LAUNCH
# ==============================================================================
FORCE_DARK_JS = '''
function() {
    document.body.classList.add('dark');
    if (!document.getElementById('mermaid-script')) {
        const script = document.createElement('script');
        script.id = 'mermaid-script';
        script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js';
        script.onload = () => { mermaid.initialize({ startOnLoad: false, theme: 'dark' }); };
        document.head.appendChild(script);
    }
    const observer = new MutationObserver((mutations) => {
        if (!document.body.classList.contains('dark')) { document.body.classList.add('dark'); }
        if (window.mermaid) {
            const nodes = document.querySelectorAll('code.language-mermaid');
            nodes.forEach((node) => {
                const pre = node.parentElement;
                if (pre.tagName === 'PRE' && !pre.classList.contains('mermaid-processed')) {
                    pre.classList.add('mermaid-processed');
                    pre.style.display = 'none';
                    const div = document.createElement('div');
                    div.classList.add('mermaid');
                    div.textContent = node.textContent;
                    div.style.textAlign = 'center';
                    div.style.marginBottom = '1.5rem';
                    pre.parentNode.insertBefore(div, pre);
                    mermaid.run({ nodes: [div] });
                }
            });
        }
    });
    observer.observe(document.body, { attributes: true, childList: true, subtree: true });
}
'''

with gr.Blocks(theme=theme, css=CUSTOM_CSS, title="LLM Council", js=FORCE_DARK_JS) as demo:
    with gr.Column(elem_classes="main-container"):
        gr.HTML('''
        <div class="header-container">
            <h1 class="header-title">LLM Council</h1>
            <p class="header-subtitle">Advanced Multi-Agent Decision System with MoA Synthesis (Live Mode)</p>
        </div>
        ''')
        with gr.Row():
            # LEFT: Config Panel
            with gr.Column(scale=2):
                model_choices = list(MODEL_MAP.keys())
                # Agent Button Row
                with gr.Row(elem_id="agent-row"):
                    model_analytical = gr.Dropdown(choices=model_choices, value="Gpt 4o", show_label=False, elem_id="dd-analytical", min_width=80, container=False)
                    model_creative = gr.Dropdown(choices=model_choices, value="Claude-Haiku 4.5", show_label=False, elem_id="dd-creative", min_width=80, container=False)
                    model_pragmatist = gr.Dropdown(choices=model_choices, value="Gpt 4o", show_label=False, elem_id="dd-pragmatist", min_width=80, container=False)
                
                # Slider Row
                with gr.Row(elem_id="slider-row"):
                    gr.Markdown("Words", elem_id="words-label")
                    word_limit_slider = gr.Slider(minimum=100, maximum=3000, value=1000, step=100, show_label=False, container=False, elem_classes=["force-inline-slider"])
                    word_limit_number = gr.Number(value=1000, show_label=False, container=False, min_width=60, elem_id="words-number")
                
                word_limit_slider.change(lambda x: x, inputs=word_limit_slider, outputs=word_limit_number)
                word_limit_number.change(lambda x: x, inputs=word_limit_number, outputs=word_limit_slider)

            # MIDDLE: Input Box
            with gr.Column(scale=4):
                input_box = gr.Textbox(placeholder="Enter your query here...", lines=2, show_label=False, autofocus=True)

            # RIGHT: Buttons
            with gr.Column(scale=1):
                btn = gr.Button("Initialize", variant="primary", size="lg")
                # Checkbox Row (Added ID for styling match)
                with gr.Row(elem_id="checkbox-row"):
                    mock_chk = gr.Checkbox(label="Mock", value=False)
                    fast_chk = gr.Checkbox(label="Fast", value=False)
        
        output_html = gr.HTML(label="Council Decision")
        
        gr.Markdown(
            '''
            <div style="text-align: center; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border-color-primary); color: var(--body-text-color-subdued); font-size: 0.85rem;">
                <div style="font-weight: 600; margin-bottom: 0.5rem;">System Architecture</div>
                <span style="margin: 0 0.5rem;">&bull;</span> MALT Pipeline (Generator &rarr; Verifier &rarr; Corrector)
                <span style="margin: 0 0.5rem;">&bull;</span> Mixture-of-Agents (MoA) Synthesis
                <span style="margin: 0 0.5rem;">&bull;</span> Auto-Arena Verification
                <span style="margin: 0 0.5rem;">&bull;</span> DialogGuard Safety
            </div>
            '''
        )

    inputs = [
        input_box, mock_chk, fast_chk, 
        word_limit_slider, model_analytical, model_creative, model_pragmatist
    ]
    
    btn.click(fn=process_query, inputs=inputs, outputs=output_html)
    input_box.submit(fn=process_query, inputs=inputs, outputs=output_html)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)