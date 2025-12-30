#!/usr/bin/env python3
"""
LG Legacy Display - Playlist Playback Example
Complete workflow from login to playing a playlist
"""

from lg_webos_legacy_client import LGWebOSLegacyClient

def main():
    HOST = "10.0.30.1"
    PASSWORD = "LifeHouse4God!"
    
    print("="*70)
    print("LG LEGACY DISPLAY - PLAYLIST PLAYBACK")
    print("="*70)
    
    # Step 1: Login with OCR retry
    print("\n[Step 1] Logging in (will retry up to 10 times)...")
    client = LGWebOSLegacyClient(HOST, PASSWORD, use_ocr=True)
    
    if not client.login_with_retry(max_attempts=5, verbose=True):
        print("✗ Failed to login after 10 attempts")
        print("  This is very unlikely - check network/password")
        return
    
    print("✓ Logged in successfully!")
    
    # Step 2: Connect Socket.io (for API communication)
    print("\n[Step 2] Connecting Socket.io...")
    if not client.connect_socketio():
        print("✗ Socket.io connection failed")
        print("  Make sure python-socketio is installed:")
        print("  pip install python-socketio")
        return
    
    print("✓ Socket.io connected!")
    
    # Step 3: Play a playlist
    print("\n[Step 3] Playing playlist...")
    
    # You can use either:
    # - Full path: "/mnt/lg/appstore/signage/Niedziela.pls"
    # - Just filename: "Niedziela.pls" (path added automatically)
    
    playlist_name = "Niedziela.pls"
    
    if client.play_playlist(playlist_name, verbose=True):
        print("\n✓ Playlist playback command sent!")
        print("  The display should now be playing the playlist")
    else:
        print("\n✗ Failed to send playback command")
    
    print("\n" + "="*70)
    print("DONE")
    print("="*70)
    print("\nThe playlist should now be playing on the display.")
    print("The session will stay active - you can send more commands.")


def play_specific_playlist(host, password, playlist_name):
    """
    Simplified function to just play a playlist
    Perfect for Home Assistant integration
    
    Args:
        host (str): Display IP
        password (str): Display password
        playlist_name (str): Playlist filename or full path
        
    Returns:
        bool: True if successful
    """
    client = LGWebOSLegacyClient(host, password, use_ocr=True)
    
    # Login with retry
    if not client.login_with_retry(max_attempts=5):
        return False
    
    # Connect Socket.io
    if not client.connect_socketio():
        return False
    
    # Play playlist
    return client.play_playlist(playlist_name)


if __name__ == "__main__":
    # Run the full example
    main()