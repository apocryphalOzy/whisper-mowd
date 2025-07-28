# Whisper MOWD Simple Demo - Deployment Guide

## Overview

This is the simplified version of Whisper MOWD that:
- Uses only Python standard library + Whisper
- No complex dependencies (no FastAPI/pydantic issues)
- Runs on any Python 3.8+
- Perfect for demos and proof of concept

## Features

✅ Clean, modern UI
✅ Real-time file upload progress
✅ Audio transcription with OpenAI Whisper
✅ Copy/download results
✅ Mobile responsive
✅ Zero external dependencies

## Local Testing

### Quick Start
```bash
# From the demo folder
RUN_SIMPLE.bat
```

Or manually:
```bash
# Install Whisper
pip install openai-whisper

# Run the server
python app_simple.py

# Open browser to http://localhost:8000
```

### Test Files
Use any of these from `whisper-mowd\data\audio\`:
- `20250429_112153_saqt.mp3` (good test file)
- Any MP3 or WAV under 50MB

## VPS Deployment

### 1. Oracle Cloud Free Tier (Best Option)

```bash
# SSH to your server
ssh ubuntu@your-server-ip

# Install Python and ffmpeg
sudo apt update
sudo apt install python3-pip ffmpeg -y

# Clone your code
git clone your-repo
cd whisper-demo/demo

# Install Whisper
pip3 install openai-whisper

# Run with nohup
nohup python3 app_simple.py > app.log 2>&1 &

# Or use screen
screen -S whisper
python3 app_simple.py
# Ctrl+A, D to detach
```

### 2. Using Docker

```bash
# Build and run
docker build -f Dockerfile.simple -t whisper-demo .
docker run -d -p 8000:8000 whisper-demo
```

### 3. Using systemd (Production)

Create `/etc/systemd/system/whisper-demo.service`:
```ini
[Unit]
Description=Whisper MOWD Demo
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/whisper-demo/demo
ExecStart=/usr/bin/python3 /home/ubuntu/whisper-demo/demo/app_simple.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable whisper-demo
sudo systemctl start whisper-demo
```

## Adding HTTPS (Optional)

### With Nginx

1. Install Nginx:
```bash
sudo apt install nginx
```

2. Configure `/etc/nginx/sites-available/whisper`:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 50M;
    }
}
```

3. Enable and get SSL:
```bash
sudo ln -s /etc/nginx/sites-available/whisper /etc/nginx/sites-enabled/
sudo certbot --nginx -d your-domain.com
```

## Performance Tips

1. **Model Size**: Stick with "tiny" for demos (39MB, fast)
2. **File Cleanup**: Results are saved in `results.json`, clear periodically
3. **Memory**: Needs ~2GB RAM for tiny model
4. **CPU**: 2+ cores recommended

## Monitoring

Check logs:
```bash
# If using nohup
tail -f app.log

# If using systemd
sudo journalctl -u whisper-demo -f

# Check resource usage
htop
```

## Demo Script

1. **Open the demo**: "This is our audio transcription service"
2. **Show constraints**: "Perfect for educational content"
3. **Upload sample**: Use a clear 1-2 minute audio
4. **Show progress**: "Real-time processing feedback"
5. **Display results**: "Accurate transcription in seconds"
6. **Copy/Download**: "Easy to use results"
7. **Value prop**: "Imagine this for all your lectures!"

## Troubleshooting

### "No module named whisper"
```bash
pip3 install --upgrade openai-whisper
```

### "Address already in use"
```bash
# Find and kill the process
lsof -i :8000
kill -9 [PID]
```

### Out of memory
- Use tiny model only
- Restart the service
- Upgrade VPS if needed

### Slow processing
- Normal: ~30 seconds per minute of audio
- Check CPU usage with `top`
- Ensure using tiny model

## Next Steps

When you get interest:
1. Add user authentication
2. Implement file storage (S3)
3. Add batch processing
4. Create API endpoints
5. Deploy full version

---

**Remember**: This is a DEMO. Keep it simple, show value quickly, collect feedback!