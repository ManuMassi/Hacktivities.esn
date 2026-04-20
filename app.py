from flask import Flask, request, render_template, redirect, url_for, flash
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
import os
import time
import threading

app = Flask(__name__)
app.secret_key = os.urandom(32)

# Define absolute paths for directories
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
STATIC_FOLDER = os.path.join(app.root_path, 'static')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)


def resize_image(input_path, output_path, target_width, target_height, save_format):
    image = Image.open(input_path)

    target_aspect = target_width / target_height
    image_aspect = image.width / image.height

    if image_aspect > target_aspect:
        new_width = target_width
        new_height = int(new_width / image_aspect)
    else:
        new_height = target_height
        new_width = int(new_height * image_aspect)

    image = image.resize((new_width, new_height), Image.LANCZOS)

    new_image = Image.new("RGB", (target_width, target_height), (0, 0, 0))
    paste_position = (
        (target_width - new_width) // 2,
        (target_height - new_height) // 2
    )
    new_image.paste(image, paste_position)

    new_image.save(output_path, format=save_format)


def delete_files_after_delay(original_path, resized_path, delay=180):
    time.sleep(delay)
    for path in [original_path, resized_path]:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        # Basic MIME check
        if not file.mimetype.startswith('image/'):
            flash('File is not an image')
            return redirect(request.url)

        try:
            # Validate image
            image = Image.open(file)
            image.verify()

            file.seek(0)
            image = Image.open(file).convert("RGB")  # Reopen after verify
        except (UnidentifiedImageError, Image.DecompressionBombError, AttributeError):
            flash('Uploaded file is not a valid image')
            return redirect(request.url)

        # Decide output format
        original_format = image.format
        if original_format in ["JPEG", "JPG"]:
            extension = ".jpg"
            save_format = "JPEG"
        else:
            extension = ".png"
            save_format = "PNG"

        # Secure filename
        base_filename = os.path.splitext(secure_filename(file.filename))[0]
        if not base_filename:
            base_filename = "image"

        input_filename = base_filename + extension
        output_filename = "resized_" + base_filename + extension

        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        output_path = os.path.join(STATIC_FOLDER, output_filename)

        # Save normalized input
        try:
            image.save(input_path, format=save_format)
        except Exception as e:
            flash(f'Error saving image: {str(e)}')
            return redirect(request.url)

        # Size selection
        size_option = request.form.get('size')
        if size_option == "main":
            target_width, target_height = 1920, 460
        else:
            target_width, target_height = 1200, 899

        try:
            resize_image(input_path, output_path, target_width, target_height, save_format)
        except Exception as e:
            flash(f'Error processing image: {str(e)}')
            return redirect(request.url)

        image_url = url_for('static', filename=output_filename)

        # Delete files later
        threading.Thread(
            target=delete_files_after_delay,
            args=(input_path, output_path),
            daemon=True
        ).start()

        return render_template('index.html', image_url=image_url)

    return render_template('index.html', image_url=None)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
