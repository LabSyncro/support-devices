from flask import Flask, jsonify, send_file
import os

app = Flask(__name__)

# Path to the JSON file
JSON_FILE_PATH = 'sampleURLs.json'

@app.route('/api/get_device_list', methods=['GET'])
def get_device_list():
    """API endpoint to serve the device list as JSON."""
    if not os.path.exists(JSON_FILE_PATH):
        return jsonify({"error": "JSON file not found."}), 404

    try:
        # Send the JSON file to the client
        return send_file(JSON_FILE_PATH, mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # Make it accessible to others
