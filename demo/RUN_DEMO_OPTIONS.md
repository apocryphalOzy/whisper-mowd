# Demo Run Options

## For Interview Demo (Recommended)
```bash
# Simple run without reload
python app_demo.py
```

## For Development (with auto-reload)
```bash
# If you need auto-reload during development
uvicorn app_demo:app --host 0.0.0.0 --port 8000 --reload
```

## Alternative Ports
```bash
# If port 8000 is busy
uvicorn app_demo:app --host 0.0.0.0 --port 8080
```

## Access the Demo
- Local: http://localhost:8000
- Network: http://[your-ip]:8000
- Password: whisper2025

## Note
The warning about reload was fixed by removing the reload parameter from the direct uvicorn.run() call. The app will now start cleanly without warnings.