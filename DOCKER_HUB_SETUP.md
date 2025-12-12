# Docker Hub Publishing Setup

This guide will help you publish the ComfyUI Manager image to Docker Hub so you can easily pull it on TrueNAS.

## Prerequisites

1. A Docker Hub account (sign up at https://hub.docker.com if you don't have one)
2. This repository pushed to GitHub

## Setup Steps

### 1. Create Docker Hub Access Token

1. Log in to Docker Hub (https://hub.docker.com)
2. Click your profile icon → Account Settings
3. Go to Security → New Access Token
4. Give it a name (e.g., "github-actions")
5. Set permissions to "Read, Write, Delete"
6. Click Generate and **copy the token** (you won't see it again!)

### 2. Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret" and add these two secrets:
   - **Name**: `DOCKERHUB_USERNAME`
     **Value**: Your Docker Hub username
   - **Name**: `DOCKERHUB_TOKEN`
     **Value**: The access token you just created

### 3. Trigger the Build

The GitHub Action will automatically build and push when you:

**Option A - Push to main branch:**
```bash
git add .
git commit -m "Setup Docker Hub publishing"
git push origin main
```

**Option B - Create a version tag:**
```bash
git tag -a v1.0.0 -m "First release"
git push origin v1.0.0
```

**Option C - Manual trigger:**
1. Go to your GitHub repository
2. Click Actions tab
3. Click "Build and Push Docker Image" workflow
4. Click "Run workflow" button

### 4. Monitor the Build

1. Go to the Actions tab in your GitHub repository
2. Watch the build progress
3. When complete, your image will be at: `<your-username>/comfyui-manager:latest`

### 5. Verify on Docker Hub

1. Go to https://hub.docker.com/r/<your-username>/comfyui-manager
2. You should see your image with the "latest" tag

## Using the Image on TrueNAS

Once published, follow the "Quick Start with Docker Hub" instructions in the README.md, replacing `<your-dockerhub-username>` with your actual Docker Hub username.

For example, if your Docker Hub username is "john", you would use:
```
john/comfyui-manager:latest
```

## Image Tags

The workflow creates these tags automatically:
- `latest` - Always points to the most recent build from main branch
- `main` - Same as latest
- `v1.0.0`, `v1.0`, etc. - When you create git tags like `v1.0.0`

## Troubleshooting

**Build fails with authentication error:**
- Check that your DOCKERHUB_USERNAME and DOCKERHUB_TOKEN secrets are set correctly
- Make sure the token has read/write permissions

**Image builds but won't run:**
- Check the GitHub Actions logs for errors
- The base image (yanwenkun/comfyui-boot:latest) must be accessible

**Can't find image on Docker Hub:**
- Make sure the build completed successfully (green checkmark in Actions)
- Check that the repository is public on Docker Hub (or your TrueNAS can access private repos)

## Alternative: Manual Build and Push (Recommended for Large Images)

Since the ComfyUI base image is very large (~10GB+), GitHub Actions free runners may run out of disk space. If you have a machine with Docker installed (and ideally a GPU to test), you can build and push manually:

```bash
# Clone your repo
git clone https://github.com/<your-username>/Docker-Comfyui-Manager.git
cd Docker-Comfyui-Manager

# Build the image (this will take some time)
docker build -f Dockerfile.managed -t <your-username>/comfyui-manager:latest .

# Log in to Docker Hub
docker login

# Push the image
docker push <your-username>/comfyui-manager:latest
```

**Note:** The build will download the large yanwenkun/comfyui-boot:latest base image (~10GB) so make sure you have enough disk space and a good internet connection.
