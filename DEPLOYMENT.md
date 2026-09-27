# Deployment Guide: Publishing YouTube Audio Extractor

This guide covers deployment to popular cloud hosting platforms. Because the app depends on **FFmpeg** for audio extraction and trimming, deployment options that support Docker or package managers are recommended.

---

## Prerequisites
- A GitHub repository with this codebase pushed.
- A free account on **Railway**, **Render**, or **Fly.io**.

---

## Option 1: Railway (Easiest & Fastest, Recommended)

Railway automatically detects the `Dockerfile` and provisions the container with `ffmpeg` already installed.

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Select your `YT_extractor` repository.
4. Railway will automatically pick up `Dockerfile` and start the build.
5. In **Settings** $\rightarrow$ **Networking**, click **Generate Domain** (e.g. `yt-extractor-production.up.railway.app`).
6. Your web app is live with HTTPS!

---

## Option 2: Render

Render provides free/low-cost Web Services with Docker.

1. Go to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** $\rightarrow$ **Web Service**.
3. Connect your GitHub repository.
4. Set **Runtime** to **Docker**.
5. The build and start commands will be derived automatically from the `Dockerfile`.
6. Click **Create Web Service**.

---

## Option 3: Fly.io

1. Install Fly CLI:
   ```bash
   brew install flyctl
   ```
2. Log in and launch:
   ```bash
   fly launch
   ```
   (Fly will detect the `Dockerfile` and generate a `fly.toml` automatically).
3. Deploy:
   ```bash
   fly deploy
   ```

---

## Option 4: Self-Hosted / VPS (Ubuntu/Debian DigitalOcean, Hetzner, AWS EC2)

1. Clone repo onto your server:
   ```bash
   git clone <your-repo-url> /opt/yt-extractor
   cd /opt/yt-extractor
   ```
2. Install system packages:
   ```bash
   sudo apt update && sudo apt install -y python3-pip ffmpeg
   pip3 install -r requirements.txt
   ```
3. Run with systemd or Docker:
   ```bash
   docker build -t yt-extractor .
   docker run -d -p 80:8080 --name yt-extractor --restart always yt-extractor
   ```

---

## Production Health Check

Once published, you can verify your service status at:
`https://<your-app-domain>/health`

Expected response:
```json
{
  "status": "healthy",
  "ffmpeg": true,
  "ffprobe": true
}
```
