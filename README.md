# IDF Tool

This repository contains a web application built with Flask that allows users to upload, view, and modify IDF (Intermediate Data Format) files. The application provides a user-friendly interface for managing IDF files, including features for uploading, processing, and visualizing data.

## Features

### Current Features
- **Upload IDF Files**: Users can upload IDF files to the server.
- **File Validation**: Ensures that only valid IDF files are uploaded.
- **Correct IDF Files**: Automatically correct IDF files from the SunEwat tool to ensure compatibility with the SolTech Bussing machine.
- **Modify IDF File Content**: Modify IDF files by rotating busbars 180 degrees or adding soldering pads under busbars (providing a z offset of 2mm).
- **Add/Remove Busbar Components**: Add new busbar components to the IDF files or remove existing ones.
- **Rename Strings**: Change the names of strings to make them recognizable by the production team.
- **Data Visualization**: Visualize data from IDF files using Plotly.
- **Export Processed Files**: Save processed files to the server and provide users with a download link to download the IDF files to their local machine.
- **Session Management**: Uses Flask-Session to manage user sessions.
- **File Security**: Securely handles file uploads using Werkzeug.

### Beta Features
- **Change Location/Dimensions of Busbars**: Modify the location and dimensions of existing busbars.

### Future Features
- **Upload Pre-Processed IDF Files**: Allow users to upload IDF files that have already been processed and exported by this tool. These files will not undergo additional processing to ensure they remain compatible with the Bussing machine.

## Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/GuustDel/idf-tool.git
    cd idf-tool
    ```

2. **Create a virtual environment**:
    ```bash
    python -m venv venv
    ```

3. **Activate the virtual environment**:
    - On Windows:
        ```bash
        venv\Scripts\activate
        ```
    - On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

4. **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5. **Run the application**:
    - On Windows:
        ```bash
        run_app.bat
        ```
    - On macOS/Linux:
        ```bash
        chmod +x run_app.sh
        ```
        ```bash
        ./run_app.sh
        ```
    Your default web browser will open and navigate to `http://127.0.0.1:5000`.

## Configuration

- **UPLOAD_FOLDER**: Directory where uploaded files are stored.
- **EXPORT_FOLDER**: Directory where processed files are saved.
- **MAX_CONTENT_LENGTH**: Maximum allowed size for uploaded files (15kB).
- **ALLOWED_EXTENSIONS**: Set of allowed file extensions for uploads (`{'idf'}`).

To change these settings, open the `app.py` file and modify the corresponding variables. 

**Note: It is not advised to change these variables unless you are sure of the implications.**

## Usage

1. **Upload an IDF file**: Go to the home page and upload an IDF file.
2. **Modify the file**: Use the tools on the manipulate page to make changes to the IDF file.
3. **Verify the changes**: Check the modifications on the observe page, both in the raw IDF file and the visual representation.
4. **Repeat as needed**: Continue modifying and verifying the file until you are satisfied with the changes.
5. **Export the file**: Download the final version of the IDF file to your local machine.

## Dependencies

- Flask
- Flask-Session
- Plotly
- Werkzeug
- NumPy

## Python Version

This project requires Python 3.10 or higher.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contact

For any questions or suggestions, please open an issue or contact the repository owner.