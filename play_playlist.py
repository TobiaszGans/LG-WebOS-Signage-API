from dotenv import load_dotenv
import os, json
from lg_webos_client import LGWebOSClient


def main():
    load_dotenv(override=True)
    IP = os.getenv("IP_ADDRESS")
    PORT = int(os.getenv("PORT"))
    PASSWORD = os.getenv("PASSWORD")

    client = LGWebOSClient(
        host=IP,
        password=PASSWORD, 
        port=PORT
    )

    if client.login():
        print("Login successful.")
    else:
        print("Login failed.")
        exit()


    media = client.get_media()
    
    sunday_playlist = next((obj for obj in media if obj['fileName'] == "Niedziela.pls"), None)
    
    play_sunday = client.play_media(type=sunday_playlist['mediaType'], src=sunday_playlist['fullPath'])
    if play_sunday:
        print("Playing Sunday playlist.")
    else:
        print("Failed to play Sunday playlist.")


if __name__ == "__main__":
    main()