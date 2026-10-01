import os
import subprocess
from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Squeeze Web UI")

# Basic HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Squeeze</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; background: #f9fafb; color: #111827; }
        h1 { color: #2563eb; }
        textarea { width: 100%; height: 120px; padding: 0.75rem; margin-bottom: 1rem; border: 1px solid #d1d5db; border-radius: 0.375rem; font-family: inherit; font-size: 1rem; box-sizing: border-box; }
        button { background: #2563eb; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 0.375rem; cursor: pointer; font-size: 1rem; font-weight: bold; }
        button:hover { background: #1d4ed8; }
        .result { margin-top: 2rem; background: white; padding: 1.5rem; border-radius: 0.5rem; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); white-space: pre-wrap; font-family: monospace; }
        .logs { margin-top: 1rem; background: #1e293b; color: #e2e8f0; padding: 1rem; border-radius: 0.5rem; white-space: pre-wrap; font-family: monospace; font-size: 0.875rem; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>Squeeze Dashboard</h1>
    <p>Run the best open-weight models your hardware can handle—fully offline, fully private.</p>
    
    <form method="post" action="/run">
        <textarea name="prompt" placeholder="Enter your task here... (e.g. Write a Python function to validate an email)" required></textarea>
        <br>
        <button type="submit">Run Task</button>
    </form>

    {% if result %}
    <div class="result">
        <h2>Result</h2>
        {{ result }}
    </div>
    {% endif %}

    {% if logs %}
    <div class="logs">
        <h3>Terminal Logs</h3>
        {{ logs }}
    </div>
    {% endif %}
</body>
</html>
"""

os.makedirs("templates", exist_ok=True)
with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(HTML_TEMPLATE)

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/run", response_class=HTMLResponse)
async def run_task(request: Request, prompt: str = Form(...)):
    # Run Squeeze via subprocess
    cmd = [".venv/Scripts/python", "-m", "squeeze", "run", prompt]
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        logs = process.stdout + "\n" + process.stderr
    except Exception as e:
        logs = str(e)
    
    # Find the latest result.md
    out_dir = Path("out")
    result_text = "No result generated."
    if out_dir.exists():
        subdirs = sorted([d for d in out_dir.iterdir() if d.is_dir()], key=os.path.getmtime, reverse=True)
        if subdirs:
            latest = subdirs[0]
            res_file = latest / "result.md"
            if res_file.exists():
                with open(res_file, "r", encoding="utf-8") as f:
                    result_text = f.read()

    return templates.TemplateResponse(
        request=request,
        name="index.html", 
        context={"result": result_text, "logs": logs}
    )

if __name__ == "__main__":
    import uvicorn
    print("Starting Squeeze Web UI on http://localhost:8000")
    uvicorn.run("web:app", host="127.0.0.1", port=8000, reload=True)
