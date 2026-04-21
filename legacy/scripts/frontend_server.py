"""
<<<<<<< HEAD
KAVACH-AI Frontend Server
=======
Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques Frontend Server
>>>>>>> 7df14d1 (UI enhanced)
Serves the built React frontend
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import os

# Get the project root
PROJECT_ROOT = Path(__file__).parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

# Create FastAPI app for static serving
<<<<<<< HEAD
app = FastAPI(title="KAVACH-AI Frontend")
=======
app = FastAPI(title="Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques Frontend")
>>>>>>> 7df14d1 (UI enhanced)

# Mount static files
if FRONTEND_DIST.exists():
    app.mount(
        "/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets"
    )

    @app.get("/")
    async def serve_frontend():
        """Serve the frontend index.html"""
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)

    @app.get("/favicon.svg")
    async def serve_favicon():
        """Serve favicon"""
        favicon_path = FRONTEND_DIST / "vite.svg"
        if favicon_path.exists():
            return FileResponse(str(favicon_path))
        return HTMLResponse(content="", status_code=404)

    print(f"Frontend mounted at: {FRONTEND_DIST}")
    print(f"Access frontend at: http://localhost:3000")
else:

    @app.get("/")
    async def frontend_not_found():
        return HTMLResponse(
            content="""
<<<<<<< HEAD
            <h1>KAVACH-AI Backend Running</h1>
=======
            <h1>Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques Backend Running</h1>
>>>>>>> 7df14d1 (UI enhanced)
            <p>Backend API: <a href="http://localhost:8000">http://localhost:8000</a></p>
            <p>API Documentation: <a href="http://localhost:8000/docs">http://localhost:8000/docs</a></p>
            <p><em>Frontend not built. Navigate to frontend directory and run: npm run build</em></p>
        """,
            status_code=200,
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3000)
