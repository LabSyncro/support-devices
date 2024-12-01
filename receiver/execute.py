import os
import subprocess
import qrcode
import math
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
# Set the temporary directory for saving images
TEMP_DIR = "/tmp"

# Printer name
PRINTER_NAME = "XP-365B"  # Change this to your printer's name
DPI = 203
VERTICAL_GAP = int(0.37 * DPI)
HORIZONTAL_GAP = int(0.2 * DPI)
LEFT_MARGIN = int(0 * DPI)
RIGHT_MARGIN = int(0 * DPI)
TOP_MARGIN = 0
BOTTOM_MARGIN = 0

INDIVIDUAL_LABEL_WIDTH = int(3.5 * DPI)                             # 3.5cm per label width
INDIVIDUAL_LABEL_HEIGHT = int(2.2 * DPI)                            # 2.2cm per label height
QRCODE_SIZE = int((INDIVIDUAL_LABEL_WIDTH // 2) * 0.8)              # QR Code size: Half of label width, vertically centered
BORDER_GAP = int(0.2 * DPI)                                         # Gap between border & content, between QRcode & text
QR_TEXT_GAP = int(0.1 * DPI)
MAX_TEXT_WIDTH = int(INDIVIDUAL_LABEL_WIDTH - QRCODE_SIZE - (BORDER_GAP * 2) - QR_TEXT_GAP)
MAX_TEXT_HEIGHT = int(INDIVIDUAL_LABEL_HEIGHT - (BORDER_GAP * 2))
FONT_SIZE = int(INDIVIDUAL_LABEL_HEIGHT * 0.08)                     # Text size: 8% label height
LABEL_PER_ROW = 2
def save_image(image, path):
    """Save the resized image to the specified path."""
    image.save(path)

def generateQR(url, size):
    """Generate a scalable QR code."""
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr_image = qr.make_image(fill='black', back_color='white')
    qr_image = qr_image.resize((size, size), Image.LANCZOS)
    return qr_image

def get_font_for_text(font_size, font_path=None): # Check the size
    """Get font based on fixed size and check if it fits the provided space."""
    # Default font path for portability
    default_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path or default_font, font_size)
    return font
def print_image(image_path, num_rows):
    """Send the print job to the printer using the lp command."""
    try:
        format = subprocess.run(
            ["lpoptions", "-p", PRINTER_NAME, 
             "-o", f"PageSize=Custom.{200}x{150 * num_rows}", 
             "-o", "portrait=true",
             "-o" "landscape=false"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    except subprocess.CalledProcessError as e:
        print(f"Error formating {image_path}: {e.stderr.decode()}")
        return False
    try:
        result = subprocess.run(
            ["lpr", "-P", PRINTER_NAME, image_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"Printed {image_path} successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error printing {image_path}: {e.stderr.decode()}")
        return False
    

def wrap_text(text, max_text_width, max_text_height, font, draw):
    """Wrap text to fit within a given width."""
    lines = []
    words = text.split()
    current_line = []

    for word in words:
        current_line.append(word)
        # Use textbbox instead of textsize
        bbox = draw.textbbox((0, 0), ' '.join(current_line), font=font)
        line_width = bbox[2] - bbox[0]  # Get width from bounding box
        if line_width >= max_text_width:
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    # Add ellipsis if the text exceeds the height
    max_lines = max_text_height // font.size
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + ['...']

    return '\n'.join(lines)

@app.route('/print_labels', methods=['POST'])
def print_labels():
    """Handle POST request to print labels with QR codes."""
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data or 'devices' not in data:
            return jsonify({"error": "Invalid JSON payload or missing 'devices' key"}), 400

        device_list = data['devices']
        if not isinstance(device_list, list) or not all('url' in item and 'name' in item and 'id' in item for item in device_list):
            return jsonify({"error": "Invalid device list format"}), 400

        # Calculate sheet height dynamically
        num_cols = LABEL_PER_ROW
        num_rows = math.ceil(len(device_list) / LABEL_PER_ROW)  # Total rows based on number of devices
        sheet_height = (num_rows * INDIVIDUAL_LABEL_HEIGHT) + (num_rows * VERTICAL_GAP) + TOP_MARGIN + BOTTOM_MARGIN
        sheet_width = int((num_cols * INDIVIDUAL_LABEL_WIDTH) + ((num_cols - 1) * HORIZONTAL_GAP) + LEFT_MARGIN + RIGHT_MARGIN)
        sheet_image = Image.new('RGB', (sheet_width, sheet_height), (255, 255, 255))  # White background

        # Initialize offsets
        x_offset = LEFT_MARGIN
        y_offset = TOP_MARGIN

        for index, device in enumerate(device_list):
            # Create label image
            label_image = Image.new('RGB', (INDIVIDUAL_LABEL_WIDTH, INDIVIDUAL_LABEL_HEIGHT), (255, 255, 255))
            draw = ImageDraw.Draw(label_image)

            # Generate & Add QR Code
            qr_image = generateQR(device['url'], QRCODE_SIZE)
            label_image.paste(qr_image, (10, 30))

            # Add text
            font = get_font_for_text(FONT_SIZE)
            wrapped_text = wrap_text(f"{device['id']}:\n{device['name']}", MAX_TEXT_WIDTH, MAX_TEXT_HEIGHT, font, draw)
            text_x_offset = QRCODE_SIZE + QR_TEXT_GAP
            draw.multiline_text((text_x_offset, BORDER_GAP), wrapped_text, fill='black', font=font, align="left")

            # Paste label on the sheet
            sheet_image.paste(label_image, (x_offset, y_offset))

            # Update offsets
            if (index + 1) % LABEL_PER_ROW == 0:  # End of row
                x_offset = LEFT_MARGIN
                y_offset += INDIVIDUAL_LABEL_HEIGHT + VERTICAL_GAP
            else:
                x_offset += INDIVIDUAL_LABEL_WIDTH + HORIZONTAL_GAP

        # Save and print the label sheet after the loop completes
        final_image_path = os.path.join(TEMP_DIR, "label_sheet.png")
        save_image(sheet_image, final_image_path)
        if not print_image(final_image_path, num_rows):
            return jsonify({"error": "Failed to print the label sheet."}), 500

        # os.remove(final_image_path)  # Cleanup
        return jsonify({"message": "Labels printed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)