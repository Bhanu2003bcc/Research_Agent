# Deployment Guide: Multi-Agent Research System

This guide outlines how to deploy the Multi-Agent Research System to a free-tier service.

## Recommended Option: Hugging Face Spaces (FREE)

Hugging Face Spaces is the recommended option because its free tier provides **16GB of RAM**, which is essential for loading the AI models and FAISS index used in this project.

### Step-by-Step Instructions

1.  **Create a Hugging Face Account**: If you don't have one, sign up at [huggingface.co](https://huggingface.co/join).
2.  **Create a New Space**:
    *   Click on **"New Space"** in the top right.
    *   Give it a name (e.g., `multi-agent-research`).
    *   Select **"Docker"** as the SDK.
    *   Choose the **"Blank"** template.
    *   Ensure **"Public"** is selected (or Private if you have a PRO account).
    *   Select the **"CPU basic • 2 vCPU • 16 GB • Free"** tier.
3.  **Upload the Code**:
    *   The easiest way is to use Git:
        ```bash
        git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
        git add .
        git commit -m "Deployment commit"
        git push hf main
        ```
    *   Alternatively, you can upload the files directly via the Hugging Face Web UI.
4.  **Configure Environment Variables**:
    *   Go to the **"Settings"** tab of your Space.
    *   Under **"Variables and secrets"**, add the following Secrets:
        *   `OPENAI_API_KEY`: Your OpenAI API key.
        *   `EXA_API_KEY`: Your Exa API key.
        *   `GROQ_API_KEY`: (Optional) Your Groq API key.
5.  **Wait for Build**: Hugging Face will automatically build the Docker image using the provided `Dockerfile` and start the service.

## Alternative Option: Render.com (NOT RECOMMENDED)

While a `render.yaml` is provided, Render's free tier only offers **512MB RAM**. 
> [!WARNING]
> Testing shows this project uses ~850MB RAM when idle. Render Free is highly likely to crash with an **Out of Memory (OOM)** error. 

If you must use Render, you may need to upgrade to a "Starter" plan ($7/month) to get enough RAM.

---

## Technical Details

- **Python Version**: 3.13-slim
- **Port**: 8000 (standard for this project)
- **Base Image**: optimized for CPU-only Torch (`torch==2.11.0+cpu`) to keep the startup memory footprint as low as possible.
