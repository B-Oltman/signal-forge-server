import time
import requests
from threading import Thread
from config import CPPServerConfig

def background_task():
    while True:
        try:
            response = requests.post(f'http://{CPPServerConfig.CPP_SERVER_HOST}:{CPPServerConfig.CPP_SERVER_PORT}/generate-data-blobs')
            print(f"Data blobs generated: {response.status_code} - {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"Error generating data blobs: {e}")
        time.sleep(10)

def start_background_task():
    thread = Thread(target=background_task)
    thread.daemon = True
    thread.start()
