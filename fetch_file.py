import requests

def send_labels_to_printer(zip_file_path):
    url = "http://192.168.1.4:5000/print_labels"  # Change this to the IP of Computer B
    with open(zip_file_path, 'rb') as f:
        files = {'zip_file': f}
        response = requests.post(url, files=files)
        return response.json()

# Example usage:
response = send_labels_to_printer('labels.zip')  # Path to the zip file containing 20 PNG images
print(response)
