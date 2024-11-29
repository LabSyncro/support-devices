import requests
import json

def fetch_device_list():
    """Fetch the list of devices from the API."""
    url = "http://localhost:5000/api/get_device_list"  # URL of the Flask API
    try:
        # Send GET request to fetch the JSON data
        response = requests.get(url)
        if response.status_code == 200:
            device_list = response.json()  # Parse the JSON response
            print("Raw JSON Response:", device_list)

            # Handle cases where the response is wrapped in a dictionary
            if isinstance(device_list, dict) and "devices" in device_list:
                device_list = device_list["devices"]
                print("Extracted devices:", device_list)

            # Validate the format of the JSON response
            if isinstance(device_list, list) and all("url" in device for device in device_list):
                return device_list
            else:
                print("Invalid JSON format received.")
                return []
        else:
            print(f"Failed to fetch device list: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []
    
def forward_device_data_to_printer(device_list):
    """Forward the device data to the printer as a raw JSON file."""
    printer_url = "https://dc03-171-252-153-91.ngrok-free.app/print_labels"  # Printer API endpoint

    # Wrap the device list in a JSON object with the 'devices' key
    payload = {"devices": device_list}

    try:
        # Send the payload (the raw JSON data) directly to the printer API
        response = requests.post(printer_url, json=payload)  # Sends the JSON payload directly
        if response.status_code == 200:
            print("Device data forwarded successfully to the printer.")
        else:
            print(f"Failed to forward data to printer: {response.status_code}")
            print(response.text)  # Print the error message from the printer API
    except requests.exceptions.RequestException as e:
        print(f"Error forwarding data: {e}")

# Example usage
device_list = fetch_device_list()
if device_list:
    print("Fetched device list:")
    for device in device_list:
        print(device)
    forward_device_data_to_printer(device_list)
