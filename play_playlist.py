from dotenv import load_dotenv
import os, json
from lg_webos_unified_client import LGWebOSClient


def main():
    load_dotenv(override=True)
    HOST = os.getenv("HOST")
    PORT = int(os.getenv("PORT"))
    PASSWORD = os.getenv("PASSWORD")
    
    # Create unified client (auto-detects display type)
    client = LGWebOSClient(HOST, PASSWORD, port=PORT)
    
    if client.login(verbose=True):
        print(f"\n✓ Connected to {client.display_type} display\n")
        
        # Play a playlist (works on both types)
        if client.play_playlist("Niedziela.pls", verbose=True):
            print("✓ Playlist started!")
        
    else:
        print("✗ Login failed")



if __name__ == "__main__":
    main()