from dotenv import load_dotenv
import os, json
from lg_webos_client import LGWebOSClient


def main():
    load_dotenv()
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


    storage_devices = client.get_media()
    print(json.dumps(storage_devices))


if __name__ == "__main__":
    main()