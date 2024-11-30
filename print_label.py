import os
import zipfile
import io
import subprocess
from flask import Flask, request, jsonify
from PIL import Image


app = Flask(__name__)

# Set the temporary directory for saving images
TEMP_DIR = "/tmp"  # Use /tmp for temporary file storage

# Printer name
PRINTER_NAME = "XP-365B"  # Change this to your printer's name

# Label dimensions in pixel
LABEL_WIDTH = 800
LABEL_HEIGHT = 175
# Width of each label in the pair (2 labels per row)
INDIVIDUAL_LABEL_WIDTH = LABEL_WIDTH // 2
INDIVIDUAL_LABEL_HEIGHT = LABEL_HEIGHT

def save_image(image, path):
    """Save the resized image to the specified path."""
    image.save(path)

def resize_image(image, width, height):
    original_width, original_height = image.size
    
    # Scaling factor of the image
    scaling_factor = min(width / original_width, height / original_height)
    # new_width = int(original_width * scaling_factor)
    # new_height = int(original_height * scaling_factor)
    
    # TEST
    new_width = width
    new_height = height
    # Resize image
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)
    
    # Paste image
    final_image = Image.new("RGB", (width, height), (255, 255, 255))
    x_offset = (width - new_width) // 2  # Adjusted to use new width
    y_offset = (height - new_height) // 2  # Adjusted to use new height
    
    final_image.paste(resized_image, (x_offset, y_offset))
    return final_image
    
def print_image(image_path):
    """Send the print job to the printer using the lp command."""
    try:
        # Send the image to the printer using the lp command (CUPS)
        result = subprocess.run(
            ["lp", 
            "-d", PRINTER_NAME,
            "-o", f"media=80x30mm", 
            image_path],
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
    """Handle POST request to print labels."""
    if 'zip_file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    zip_file = request.files['zip_file']

    # Check if the file is a zip
    if not zip_file.filename.endswith('.zip'):
        return jsonify({"error": "The uploaded file is not a zip file."}), 400

    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            file_names = zip_ref.namelist()
            image_files = [file for file in file_names if file.endswith('.png')]

            if not image_files:
                return jsonify({"error": "No PNG files found in the zip."}), 400

            # Create a new blank image to place all the resized images onto
            sheet_image = Image.new('RGB', (LABEL_WIDTH, (len(image_files) // 2) * LABEL_HEIGHT), (255, 255, 255))  # White background

            # Resize and place each pair of images on the label sheet
            x_offset = 0
            y_offset = 0
            for idx in range(0, len(image_files), 2):  # Process images in pairs
                # Get the first image
                with zip_ref.open(image_files[idx]) as img_file:
                    img_data = img_file.read()
                    image1 = Image.open(io.BytesIO(img_data))

                    # Resize the image to fit the individual label width and height
                    image1 = resize_image(image1, INDIVIDUAL_LABEL_WIDTH, INDIVIDUAL_LABEL_HEIGHT)
                    # Paste the image onto the left half of the label
                    sheet_image.paste(image1, (x_offset, y_offset))

                # Get the second image if it exists
                if idx + 1 < len(image_files):
                    with zip_ref.open(image_files[idx + 1]) as img_file:
                        img_data = img_file.read()
                        image2 = Image.open(io.BytesIO(img_data))

                        # Resize the image to fit the individual label width and height
                        image2 = resize_image(image2, INDIVIDUAL_LABEL_WIDTH, INDIVIDUAL_LABEL_HEIGHT)
                        # Paste the image onto the right half of the label
                        sheet_image.paste(image2, (x_offset + INDIVIDUAL_LABEL_WIDTH, y_offset))

                # Move to the next row (y offset)
                y_offset += LABEL_HEIGHT

            # Save the final sheet as an image
            final_image_path = os.path.join(TEMP_DIR, "label_sheet.png")
            save_image(sheet_image, final_image_path)

            # Send the print job to the printer
            if not print_image(final_image_path):
                return jsonify({"error": "Failed to print the label sheet."}), 500

            # Cleanup temporary file
            os.remove(final_image_path)

            return jsonify({"message": "Labels printed successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
