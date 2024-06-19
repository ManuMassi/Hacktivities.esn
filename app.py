from flask import Flask, request, render_template, redirect, url_for, flash
from PIL import Image, UnidentifiedImageError
import os
import time
import threading

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flashing messages

# Define absolute paths for directories
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
STATIC_FOLDER = os.path.join(app.root_path, 'static')

# Ensure directories exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

def resize_image(input_path, output_path, target_width, target_height):
    image = Image.open(input_path)
    
    # Calculate aspect ratios
    target_aspect = target_width / target_height
    image_aspect = image.width / image.height
    
    # Determine new dimensions
    if image_aspect > target_aspect:
        # Image is wider than target
        new_width = target_width
        new_height = int(new_width / image_aspect)
    else:
        # Image is taller than target
        new_height = target_height
        new_width = int(new_height * image_aspect)
    
    # Resize image with minimal stretching
    image = image.resize((new_width, new_height), Image.LANCZOS)
    
    # Create a new image with black background
    new_image = Image.new("RGB", (target_width, target_height), (0, 0, 0))
    
    # Paste resized image onto black background
    paste_position = ((target_width - new_width) // 2, (target_height - new_height) // 2)
    new_image.paste(image, paste_position)
    
    # Save the result
    new_image.save(output_path, format="PNG")

def delete_files_after_delay(original_path, resized_path, delay=180):
    time.sleep(delay)
    try:
        os.remove(original_path)
        os.remove(resized_path)
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
        
        if file:
            try:
                # Verify if the uploaded file is an image
                image = Image.open(file)
                image.verify()
                file.seek(0)  # Reset file pointer to the beginning after verify
            except (UnidentifiedImageError, Image.DecompressionBombError, AttributeError):
                flash('Uploaded file is not a valid image')
                return redirect(request.url)
            
            size_option = request.form['size']
            if size_option == "main":
                target_width, target_height = 1920, 460
            else:
                target_width, target_height = 1200, 899

            input_path = os.path.join(UPLOAD_FOLDER, file.filename)
            output_path = os.path.join(STATIC_FOLDER, 'resized_' + file.filename)
            file.save(input_path)

            try:
                resize_image(input_path, output_path, target_width, target_height)
            except Exception as e:
                flash(f'Error processing image: {str(e)}')
                return redirect(request.url)

            image_url = url_for('static', filename='resized_' + file.filename)

            # Schedule deletion of files
            threading.Thread(target=delete_files_after_delay, args=(input_path, output_path)).start()

            return render_template('index.html', image_url=image_url)
    
    return render_template('index.html', image_url=None)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
