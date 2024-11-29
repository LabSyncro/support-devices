import os
import subprocess
import qrcode
import math
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# Set the temporary directory for saving images
TEMP_DIR = "/tmp"

# Printer name
PRINTER_NAME = "XP-365B"  # Change this to your printer's name

DPI = 203
INDIVIDUAL_LABEL_WIDTH = int(3.7 * DPI)  # cm per label width
INDIVIDUAL_LABEL_HEIGHT = int(2.5 * DPI)  # 3cm per label height
HORIZONTAL_GAP = int(0.2 * DPI)  # 0.2cm gap between labels
VERIZONTAL_GAP = int(0.2 * DPI)
TOTAL_LABEL_WIDTH = (2 * INDIVIDUAL_LABEL_WIDTH) + HORIZONTAL_GAP
TOTAL_LABEL_HEIGHT = INDIVIDUAL_LABEL_HEIGHT + VERIZONTAL_GAP

def save_image(image, path):
    """Save the resized image to the specified path."""
    image.save(path)

def generateQR(url, size):
    """Generate a scalable QR code."""
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr_image = qr.make_image(fill='black', back_color='white')
    qr_image = qr_image.resize((size, size), Image.LANCZOS)
    return qr_image

def get_font_for_text(font_size, text, max_width, max_height, font_path=None):
    """Get font based on fixed size and check if it fits the provided space."""
    font = ImageFont.truetype(font_path or "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    # text_width, text_height = font.getsize_multiline(text)

    # Ensure text does not exceed the max width and height
    return font

def print_image(image_path):
    """Send the print job to the printer using the lp command."""
    try:
        result = subprocess.run(
            ["lp", "-d", PRINTER_NAME, "-o", f"media={int(TOTAL_LABEL_WIDTH)}x{int(TOTAL_LABEL_HEIGHT)}", image_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"Printed {image_path} successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error printing {image_path}: {e.stderr.decode()}")
        return False

@app.route('/print_labels', methods=['POST'])
def print_labels():
    """Handle POST request to print labels with QR codes."""
    try:
        # Get the JSON data from the request
        data = request.get_json()
        if not data or 'devices' not in data:
            return jsonify({"error": "Invalid JSON payload or missing 'devices' key"}), 400

        device_list = data['devices']
        if not isinstance(device_list, list) or not all('url' in item and 'name' in item and 'id' in item for item in device_list):
            return jsonify({"error": "Invalid device list format"}), 400

        # Create a blank sheet image to hold all labels
        num_rows = math.ceil(len(device_list) / 2)  # Two labels per row
        sheet_height = (num_rows * TOTAL_LABEL_HEIGHT)
        sheet_image = Image.new('RGB', (TOTAL_LABEL_WIDTH, sheet_height), (255, 255, 255))  # White background

        # Draw each label
        x_offset = 0
        y_offset = 0
        # Modified portion inside the loop to ensure correct positioning of each label
        for index, device in enumerate(device_list):
            # Create a label image
            label_image = Image.new('RGB', (INDIVIDUAL_LABEL_WIDTH, INDIVIDUAL_LABEL_HEIGHT), (255, 255, 255))
            draw = ImageDraw.Draw(label_image)

            # Generate QR code for the left half of the label
            qr_size = INDIVIDUAL_LABEL_WIDTH // 2
            qr_image = generateQR(device['url'], qr_size)
            label_image.paste(qr_image, (5, 5))

            # Add the text to the label with appropriate scaling
            max_text_width = INDIVIDUAL_LABEL_WIDTH // 2  # Half the label width
            max_text_height = INDIVIDUAL_LABEL_HEIGHT  # Full label height
            device_name = f"{device['id']}:\n{str(device['name'])}"  # Ensure device name is a string

            # Set font size to 5% of QR code size
            font_size = int(qr_size * 0.1)
            font = get_font_for_text(font_size, device_name, max_text_width, max_text_height)
            wrapped_text = wrap_text(device_name, max_text_width, font, draw)

            text_x_offset = INDIVIDUAL_LABEL_WIDTH // 2 + 5  # Offset to the right side of the label
            text_y_offset = 5  # Add some padding from the top
            draw.multiline_text((text_x_offset, text_y_offset), wrapped_text, fill='black', font=font, align="left")

            # Paste the label on the sheet
            sheet_image.paste(label_image, (x_offset, y_offset))

            # Move to the next position
            if index % 2 == 0:  # First label in the row
                x_offset = INDIVIDUAL_LABEL_WIDTH + HORIZONTAL_GAP  # Move to second column
            else:  # Second label in the row
                x_offset = 0  # Reset to the first column
                y_offset += TOTAL_LABEL_HEIGHT  # Move to the next row

        # Save and print the label sheet
        final_image_path = os.path.join(TEMP_DIR, "label_sheet.png")
        save_image(sheet_image, final_image_path)

        if not print_image(final_image_path):
            return jsonify({"error": "Failed to print the label sheet."}), 500

        os.remove(final_image_path)  # Cleanup
        return jsonify({"message": "Labels printed successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def wrap_text(text, max_width, font, draw):
    """Wrap text to fit within a given width."""
    lines = []
    words = text.split()
    current_line = []

    for word in words:
        current_line.append(word)
        # Use textbbox instead of textsize
        bbox = draw.textbbox((0, 0), ' '.join(current_line), font=font)
        line_width = bbox[2] - bbox[0]  # Get width from bounding box
        if line_width > max_width:
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]


    if current_line:
        lines.append(' '.join(current_line))

    # Add ellipsis if the text exceeds the height
    max_lines = INDIVIDUAL_LABEL_HEIGHT // 15  # Rough estimate based on font size
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + ['...']

    return '\n'.join(lines)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)