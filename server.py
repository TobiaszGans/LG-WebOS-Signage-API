#!/usr/bin/env python3
"""
Simple LG WebOS Signage Control Server
One endpoint - you handle the logic

Installation:
    pip install fastapi uvicorn

Usage:
    python lg_simple_server.py
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from lg_webos_unified_client import LGWebOSClient

app = FastAPI()


class PlayRequest(BaseModel):
    host: str
    password: str
    playlist: str
    port: Optional[int] = None
    max_attempts: Optional[int] = 5


@app.post("/play")
async def play_playlist(request: PlayRequest):
    """
    Login to display and play a playlist
    
    Example:
        POST /play
        {
            "host": "10.0.30.1",
            "password": "password!",
            "playlist": "Niedziela.pls",
            "max_attempts": 5
        }
    """
    try:
        # Create client
        client = LGWebOSClient(
            host=request.host,
            password=request.password,
            port=request.port
        )
        
        playlist = request.playlist

        # Login
        if not client.login(verbose=True, max_retry_attempts=request.max_attempts):
            raise HTTPException(status_code=401, detail="Login failed")
        print(f"\n✓ Connected to {client.display_type} display\n")
        
        # Play playlist
        if not client.play_playlist(playlist, verbose=True):
            raise HTTPException(status_code=500, detail="Failed to play playlist")
        
        print(f"✓ {playlist} Playlist started!")
        
        return {
            "success": True,
            "host": request.host,
            "playlist": request.playlist,
            "display_type": client.display_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("Starting server on http://localhost:8000")
    print("POST to http://localhost:8000/play")
    uvicorn.run(app, host="0.0.0.0", port=8000)