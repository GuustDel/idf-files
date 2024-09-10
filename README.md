IDF Tool
This repository contains a web application built with Flask that allows users to upload, view, and modify IDF (Intermediate Data Format) files. The application provides a user-friendly interface for managing IDF files, including features for uploading, processing, and visualizing data.

Features
Upload IDF Files: Users can upload IDF files to the server.
File Validation: Ensures that only valid IDF files are uploaded.
Data Visualization: Visualize data from IDF files using Plotly.
Session Management: Uses Flask-Session to manage user sessions.
File Security: Securely handles file uploads using Werkzeug.
Installation
Clone the repository:

Create a virtual environment:

Activate the virtual environment:

On Windows:
On macOS/Linux:
Install the dependencies:

Run the application:

Open your browser and navigate to:

Configuration
UPLOAD_FOLDER: Directory where uploaded files are stored.
EXPORT_FOLDER: Directory where processed files are saved.
MAX_CONTENT_LENGTH: Maximum allowed size for uploaded files (15kB).
ALLOWED_EXTENSIONS: Set of allowed file extensions for uploads ({'idf'}).
Usage
Upload an IDF file: Navigate to the upload page and select an IDF file to upload.
Modify the file: Use the provided tools to modify the IDF file as needed.
Save changes: Save the modified file to the server.
Dependencies
Flask
Flask-Session
Plotly
Werkzeug
NumPy
Contributing
Contributions are welcome! Please fork the repository and submit a pull request with your changes.

License
This project is licensed under the MIT License. See the LICENSE file for details.

Contact
For any questions or suggestions, please open an issue or contact the repository owner.
