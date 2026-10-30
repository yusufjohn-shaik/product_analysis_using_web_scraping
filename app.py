"""Simple Flask backend: runs product_analysis.py when the button is clicked.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""
import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"  # CSVs and chart from the script go here
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/outputs/<path:filename>")
def output_file(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/api/run", methods=["POST"])
def run_script():
    # Clear files from the previous run
    for old in OUTPUT_DIR.iterdir():
        if old.is_file():
            old.unlink()

    # Agg = save charts without opening a window (so plt.show() won't hang)
    env = {**os.environ, "MPLBACKEND": "Agg"}

    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "product_analysis.py")],
        cwd=OUTPUT_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # any failure message shows up in the report
        text=True,
    )

    files = sorted(p.name for p in OUTPUT_DIR.iterdir() if p.is_file())
    return jsonify({"output": result.stdout, "files": files})


if __name__ == "__main__":
    app.run(debug=True)
