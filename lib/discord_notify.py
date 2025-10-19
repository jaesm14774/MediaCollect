import requests
import json

def notify(webhook_url, msg, file_path=None):
    if file_path:
        with open(file_path, 'rb') as file:
            files = {
                'payload_json': (None, json.dumps({"content": msg})),
                'image.png': file
            }
            response = requests.post(webhook_url, files=files)
    else:
        data = {"content": msg}
        response = requests.post(webhook_url, data=data)
    
    if response.status_code in [200, 201, 202, 203, 204]:
        print(f"{'File' if file_path else 'Message'} sent successfully.")
    else:
        print(f"Failed to send the {'file' if file_path else 'message'}.")
        print(response.text)