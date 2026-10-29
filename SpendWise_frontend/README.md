# SpendWise frontend

This folder contains the React client built with Vite. The development server proxies API requests to the FastAPI backend at `http://127.0.0.1:8000`.

See the [main project README](../README.md) for the full architecture and local setup instructions.

## Local commands

Run these commands from this directory:

```powershell
npm ci
npm run dev
```

The frontend requires the backend and a configured local database for API-backed screens. The package also provides `npm run lint` and `npm run build`.