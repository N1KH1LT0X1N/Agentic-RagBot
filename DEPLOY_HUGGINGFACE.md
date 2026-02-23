# 🚀 Deploy MediGuard AI to Hugging Face Spaces

This guide walks you through deploying MediGuard AI to Hugging Face Spaces using Docker.

## Prerequisites

1. **Hugging Face Account** — [Sign up free](https://huggingface.co/join)
2. **Git** — Installed on your machine
3. **API Key** — Either:
   - **Groq** (recommended) — [Get free key](https://console.groq.com/keys)
   - **Google Gemini** — [Get free key](https://aistudio.google.com/app/apikey)

## Step 1: Create a New Space

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Fill in:
   - **Space name**: `mediguard-ai` (or your choice)
   - **License**: MIT
   - **SDK**: Select **Docker**
   - **Hardware**: **CPU Basic** (free tier works!)
3. Click **Create Space**

## Step 2: Clone Your Space

```bash
# Clone the empty space
git clone https://huggingface.co/spaces/YOUR_USERNAME/mediguard-ai
cd mediguard-ai
```

## Step 3: Copy Project Files

Copy all files from this repository to your space folder:

```bash
# Option A: If you have the RagBot repo locally
cp -r /path/to/RagBot/* .

# Option B: Clone fresh
git clone https://github.com/yourusername/ragbot temp
cp -r temp/* .
rm -rf temp
```

## Step 4: Set Up Dockerfile for Spaces

Hugging Face Spaces expects the Dockerfile in the root. Copy the HF-optimized Dockerfile:

```bash
# Copy the HF Spaces Dockerfile to root
cp huggingface/Dockerfile ./Dockerfile
```

**Or** update your root `Dockerfile` to match the HF Spaces version.

## Step 5: Set Up README (Important!)

The README.md must have the HF Spaces metadata header. Copy the HF README:

```bash
# Backup original README
mv README.md README_original.md

# Use HF Spaces README
cp huggingface/README.md ./README.md
```

## Step 6: Add Your API Key (Secret)

1. Go to your Space: `https://huggingface.co/spaces/YOUR_USERNAME/mediguard-ai`
2. Click **Settings** tab
3. Scroll to **Repository Secrets**
4. Add a new secret:
   - **Name**: `GROQ_API_KEY` (or `GOOGLE_API_KEY`)
   - **Value**: Your API key
5. Click **Add**

## Step 7: Push to Deploy

```bash
# Add all files
git add .

# Commit
git commit -m "Deploy MediGuard AI"

# Push to Hugging Face
git push
```

## Step 8: Monitor Deployment

1. Go to your Space: `https://huggingface.co/spaces/YOUR_USERNAME/mediguard-ai`
2. Click the **Logs** tab to watch the build
3. Build takes ~5-10 minutes (first time)
4. Once "Running", your app is live! 🎉

## 🔧 Troubleshooting

### "No LLM API key configured"

- Make sure you added `GROQ_API_KEY` or `GOOGLE_API_KEY` in Space Settings → Secrets
- Secret names are case-sensitive

### Build fails with "No space disk"

- Hugging Face free tier has limited disk space
- The FAISS vector store might be too large
- Solution: Upgrade to a paid tier or reduce vector store size

### "ModuleNotFoundError"

- Check that all dependencies are in `huggingface/requirements.txt`
- The Dockerfile should install from this file

### App crashes on startup

- Check Logs for the actual error
- Common issue: Missing environment variables
- Increase Space hardware if OOM error

## 📁 File Structure for Deployment

Your Space should have this structure:

```
your-space/
├── Dockerfile              # HF Spaces Dockerfile (from huggingface/)
├── README.md               # HF Spaces README with metadata
├── huggingface/
│   ├── app.py              # Standalone Gradio app
│   ├── requirements.txt    # Minimal deps for HF
│   └── README.md           # Original HF README
├── src/                    # Core application code
│   ├── workflow.py
│   ├── state.py
│   ├── llm_config.py
│   ├── pdf_processor.py
│   ├── agents/
│   └── ...
├── data/
│   └── vector_stores/
│       ├── medical_knowledge.faiss
│       └── medical_knowledge.pkl
└── config/
    └── biomarker_references.json
```

## 🔄 Updating Your Space

To update after making changes:

```bash
git add .
git commit -m "Update: description of changes"
git push
```

Hugging Face will automatically rebuild and redeploy.

## 💰 Hardware Options

| Tier | RAM | vCPU | Cost | Best For |
|------|-----|------|------|----------|
| CPU Basic | 2GB | 2 | Free | Demo/Testing |
| CPU Upgrade | 8GB | 4 | ~$0.03/hr | Production |
| T4 Small | 16GB | 4 | ~$0.06/hr | Heavy usage |

The free tier works for demos. Upgrade if you experience timeouts.

## 🎉 Your Space is Live!

Once deployed, share your Space URL:

```
https://huggingface.co/spaces/YOUR_USERNAME/mediguard-ai
```

Anyone can now use MediGuard AI without any setup!

---

## Quick Commands Reference

```bash
# Clone your space
git clone https://huggingface.co/spaces/YOUR_USERNAME/mediguard-ai

# Set up remote (if needed)
git remote add origin https://huggingface.co/spaces/YOUR_USERNAME/mediguard-ai

# Push changes
git push origin main

# Force rebuild (if stuck)
# Go to Settings → Factory Reset
```

## Need Help?

- [Hugging Face Spaces Docs](https://huggingface.co/docs/hub/spaces)
- [Docker on Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)
- [Spaces Secrets](https://huggingface.co/docs/hub/spaces-secrets)
