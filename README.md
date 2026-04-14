# AutoResearch Diagrams - Local Ollama Setup

Self-improving diagram prompt optimization using the Karpathy autoresearch pattern with local Ollama models.

## About

This system applies the Karpathy autoresearch pattern to diagram generation prompts, optimizing them through an automated loop:
1. Generate diagrams with current prompt using Ollama
2. Evaluate each against 4 criteria via Ollama
3. Keep the prompt if it beats the best score, discard otherwise
4. Mutate the best prompt to try to improve further
5. Repeat every 2 minutes

## Requirements

### Local LLMs (Ollama)
- [Ollama](https://ollama.com/) installed and running
- Ollama models:
  - `qwen3-vl:latest` (for prompt generation, evaluation, and mutation)
  - These models will be automatically downloaded upon first use

### Python Dependencies
- Python 3.8+
- Required packages (see requirements below)

## Setup Instructions

1. **Install Ollama**
   - Download from [ollama.com](https://ollama.com/)
   - Start the Ollama service with `ollama serve`

2. **Pull Required Models**
   ```bash
   ollama pull qwen3-vl:latest
   ```

3. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Environment Variables (optional)**
   ```bash
   # Create a .env file in the project root
   echo "OLLAMA_API_KEY=your_api_key" > .env
   ```

## Running the System

### Normal Continuous Loop
```bash
python3 autoresearch.py
```

### Single Cycle Test
```bash
python3 autoresearch.py --once
```

### Run N Cycles
```bash
python3 autoresearch.py --cycles 10
```

### Start the Dashboard
```bash
python3 dashboard.py --port 8501
# Then open http://localhost:8501
```

## File Structure

```
.
├── autoresearch.py          # Main generate -> eval -> mutate loop
├── dashboard.py             # Live web dashboard
├── data/
│   ├── prompt.txt          # Current prompt being optimized
│   ├── best_prompt.txt     # Best prompt found so far
│   ├── state.json          # Loop state (run number, best score)
│   ├── results.jsonl       # Append-only experiment log
│   └── diagrams/
│       └── run_001/        # 10 diagrams per run
│       └── run_002/
│       └── ...
├── README.md                # This file
└── requirements.txt         # Python dependencies
```

## How It Works

### Cycle Process
1. **Generate**: Use Ollama with `qwen3-vl:latest` to generate 10 diagram descriptions based on the current prompt
2. **Evaluate**: Process each diagram through Ollama evaluation, scoring against 4 criteria:
   - Legible & grammatical text
   - Pastel colors only
   - Linear layout (left-to-right or top-to-bottom)
   - No numbers/ordinals
3. **Compare**: If batch score improves the best score, keep the prompt and save to `best_prompt.txt`
4. **Mutate**: Improve the prompt via Ollama to try to get better results
5. **Repeat**: Continue the loop every 2 minutes

### Evaluation Criteria (40 points total)
- 10 points per criteria: 10 diagrams total
- Legible & grammatical: All text readable and correctly spelled
- Pastel colors: Only soft pastel fills (light purple, light blue, etc.)
- Linear layout: Strictly left-to-right or top-to-bottom flow
- No numbers: Zero digits, steps, or labels

## Dashboard
Serves at `http://localhost:8501` with:
- 4 stat cards (current best, baseline, improvement %, runs/kept)
- Score-over-time chart with keep/discard dot coloring
- Per-criterion breakdown charts
- Run history table
- Current best prompt display
- Auto-refreshes every 15s

## System Requirements

- **RAM**: 8GB minimum recommended
- **Storage**: 50GB+ free space (for data directory)
- **Internet**: For initial Ollama model downloads
- **CPU**: 4+ cores recommended

## Cost Efficiency

Using `llama3.2:11b-vision` locally:
- No API costs for generation, evaluation, or mutation
- Very minimal resource usage during operation
- Only requires download of models once

## Troubleshooting

### If Ollama is not found:
```bash
# Ensure Ollama is running
ollama serve

# Check if Ollama is running
ollama list
```

### If models are missing or not downloading:
```bash
ollama pull llama3.2:11b-vision
```

### If Python dependencies missing:
```bash
pip install -r requirements.txt
```

### If you encounter connection errors with Ollama:
1. Make sure Ollama is running: `ollama serve`
2. Verify Ollama is responding: `ollama list`
3. Check the port number - the default for Ollama is 11434 (not 443)