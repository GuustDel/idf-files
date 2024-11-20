import os
import sys
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, redirect, flash, session, send_file, url_for, jsonify
from flask_session import Session
import idf_tool.parse_idf as idf
import json
import plotly
from werkzeug.utils import secure_filename
import numpy as np

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
    )
app.secret_key = 'supersecretkey'

app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True
)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads")
app.config['EXPORT_FOLDER'] = os.path.join(os.getcwd(), "submits")
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024  # 15kB max file size
app.config['ALLOWED_EXTENSIONS'] = {'idf'}

Session(app)

logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

def allowed_file(filename):

    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def base():
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    return render_template('home.html', fig_dir=fig_dir, enable_drop=True)

@app.route('/home_src')
def home():
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    graph_json = session.get('graph_json', None)

    return render_template('home.html', graph_json=graph_json, fig_dir=fig_dir, enable_drop=True)

@app.route('/submit', methods=['POST'])
def submit_file():
    print("submit_file")
    session.clear()
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # File management
    file = request.files.get('file')
    if not file or file.filename == '' or not allowed_file(file.filename):
        print("File not found")
        return redirect(request.url)

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    session['filename'] = filename
    logging.info(f'Route: /submit - File {filename} uploaded')

    # IDF parsing
    board_outline = idf.board_outline(file_path)
    component_outlines = idf.component_outlines(file_path)
    component_placements = idf.component_placements(file_path)
    sbars, strings = idf.get_component_names_by_type(component_outlines)
    logging.info("Route: /submit - IDF file parsed")

    # Data processing
    corrected_component_outlines = component_outlines.copy()
    corrected_component_placements = component_placements.copy()

    fig = idf.draw_board(board_outline, component_outlines, component_placements)
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    sbar_checkboxes_180deg = session.get('sbar_checkboxes_180deg', {sbar: False for sbar in sbars})
    sbar_checkboxes_height = session.get('sbar_checkboxes_height', {sbar: False for sbar in sbars})
    new_string_names = session.get('new_string_names', None)

    if new_string_names is None:
        new_string_names = {string: '' for string in strings}

    file.seek(0)
    file_content = file.read().decode('utf-8')
    logging.info("Route: /submit - Data processed")

    # Store session data
    session['file_content'] = file_content
    session['graph_json'] = graph_json
    session['board_outline'] = board_outline
    session['component_outlines'] = component_outlines
    session['component_placements'] = component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    session['corrected_component_placements'] = corrected_component_placements
    session['sbars'] = sbars
    session['strings'] = strings
    logging.info("Route: /submit - Session data stored")

    return render_template('home.html', strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, sbar_checkboxes_180deg=sbar_checkboxes_180deg, new_string_names=new_string_names, sbar_checkboxes_height=sbar_checkboxes_height, fig_dir=fig_dir)

@app.route('/submit_parameters', methods=['POST'])
def submit_parameters():
    print("submit_parameters")
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    sbars = session.get('sbars', [])
    strings = session.get('strings', [])
    graph_json = session.get('graph_json', None)
    filename = session.get('filename', None)
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    sbar_checkboxes_180deg_history = session.get('sbar_checkboxes_180deg_history', {})
    logging.info("Route: /submit_parameters - Session data retrieved")
    
    # HTML Parsing
    new_string_names = {key[7:]: request.form[key] for key in request.form if key.startswith('string_')}
    sbar_checkboxes_180deg = {}
    sbar_checkboxes_height = {}
    for sbar in sbars:
        sbar_checkboxes_180deg[sbar] = bool(request.form.get(f'sbar180deg_{sbar}'))
        sbar_checkboxes_height[sbar] = bool(request.form.get(f'sbarheight_{sbar}'))
    logging.info("Route: /submit_parameters - HTML parsed")

    # Data processing
    if request.form.get('new_sbar_name_dyn', None) is not None:
        idf.add_busbars(request.form, corrected_component_outlines, corrected_component_placements, sbar_checkboxes_180deg, sbar_checkboxes_height, sbars)

    for sbar, value in sbar_checkboxes_180deg.items():
        if sbar not in sbar_checkboxes_180deg_history:
            sbar_checkboxes_180deg_history[sbar] = []
        sbar_checkboxes_180deg_history[sbar].append(value)

    idf.translate(corrected_component_placements, corrected_component_outlines, sbar_checkboxes_180deg_history, request.form)
    idf.rotate(corrected_component_placements, corrected_component_outlines, sbar_checkboxes_180deg_history, sbar_checkboxes_180deg)

    idf.change_string_names(corrected_component_placements, corrected_component_outlines, new_string_names, strings)
    idf.change_sbar_height(corrected_component_outlines, sbar_checkboxes_height)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    new_file_content = idf.regenerate_idf_file_content(file_path, corrected_component_outlines, corrected_component_placements)
    logging.info("Route: /submit_parameters - Data processed")

    # Store session data
    session['new_file_content'] = new_file_content
    session['new_string_names'] = new_string_names
    session['corrected_component_placements'] = corrected_component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    session['sbar_checkboxes_180deg'] = sbar_checkboxes_180deg
    session['sbar_checkboxes_height'] = sbar_checkboxes_height
    session['sbar_checkboxes_180deg_history'] = sbar_checkboxes_180deg_history
    logging.info("Route: /submit_parameters - Session data stored")

    return render_template('manipulate.html', manipulate_after_submit_parameters = True, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, sbar_checkboxes_180deg=sbar_checkboxes_180deg, sbar_checkboxes_height=sbar_checkboxes_height, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements, corrected_component_outlines=corrected_component_outlines)


@app.route('/observe_src')
def preview(): 
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval 
    file_content = session.get('file_content', 'No file content found')
    graph_json = session.get('graph_json', None)
    board_outline = session.get('board_outline', None)
    component_outlines = session.get('component_outlines', None)
    component_placements = session.get('component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', {})
    corrected_component_placements = session.get('corrected_component_placements', {})
    new_file_content = session.get('new_file_content', 'No new file content found')
    logging.info("Route: /observe_src - Session data retrieved")

    # Data processing
    if board_outline is None or component_outlines is None or component_placements is None:
        return redirect('/')
    
    fig = idf.draw_board(board_outline, component_outlines, component_placements)
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    fig2 = idf.draw_board(board_outline, corrected_component_outlines, corrected_component_placements)
    graph_json2 = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
    logging.info("Route: /observe_src - Data processed")

    # Store session data
    session['graph_json2'] = graph_json2
    logging.info("Route: /observe_src - Session data stored")
    
    return render_template('observe.html', section='preview', file_content=file_content, graph_json=graph_json, graph_json2=graph_json2, new_file_content=new_file_content, fig_dir=fig_dir)

@app.route('/manipulate_src')
def manipulate():
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    strings = session.get('strings', [])
    sbars = session.get('sbars', [])
    filename = session.get('filename', None)
    sbar_checkboxes_180deg = session.get('sbar_checkboxes_180deg', {})
    sbar_checkboxes_height = session.get('sbar_checkboxes_height', {})
    new_string_names = session.get('new_string_names', {})
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    logging.info("Route: /manipulate_src - Session data retrieved")

    return render_template('manipulate.html', manipulate_after_submit_parameters = True, strings=strings, sbars=sbars, filename=filename, sbar_checkboxes_180deg=sbar_checkboxes_180deg, new_string_names=new_string_names, sbar_checkboxes_height=sbar_checkboxes_height, corrected_component_placements= corrected_component_placements, fig_dir=fig_dir, corrected_component_outlines=corrected_component_outlines)

@app.route('/remove_busbar', methods=['POST'])
def remove_busbar():
    print("remove_busbar")
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    new_string_names = session.get('new_string_names', {})
    sbars = session.get('sbars', [])
    strings = session.get('strings', [])
    graph_json = session.get('graph_json', None)
    sbar_checkboxes_180deg = session.get('sbar_checkboxes_180deg', {})
    sbar_checkboxes_height = session.get('sbar_checkboxes_height', {})
    filename = session.get('filename', None)
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    logging.info("Route: /remove_busbar - Session data retrieved")

    # HTML Parsing
    sbar_to_delete = request.form['sbar']
    logging.info(f"Route: /remove_busbar - {sbar_to_delete} to be deleted")

    # Data processing
    del corrected_component_outlines[sbar_to_delete]
    keys_to_delete = [id for id, placement in corrected_component_placements.items() if placement["name"] == sbar_to_delete]
    for key in keys_to_delete:
        del corrected_component_placements[key]
    del sbar_checkboxes_height[sbar_to_delete]
    del sbar_checkboxes_180deg[sbar_to_delete]
    sbars = [sbar for sbar in sbars if sbar != sbar_to_delete]
    logging.info("Route: /remove_busbar - Data processed")

    # Store session data
    session['corrected_component_placements'] = corrected_component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    session['sbars'] = sbars
    session['sbar_checkboxes_height'] = sbar_checkboxes_height
    session['sbar_checkboxes_180deg'] = sbar_checkboxes_180deg
    logging.info("Route: /remove_busbar - Session data stored")

    return render_template('manipulate.html', manipulate_after_submit_parameters = True, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, sbar_checkboxes_180deg=sbar_checkboxes_180deg, sbar_checkboxes_height=sbar_checkboxes_height, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements, corrected_component_outlines=corrected_component_outlines)

@app.route('/preview_src')
def preview_src():
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    file_content = session.get('file_content', 'No file content found')
    new_file_content = session.get('new_file_content', 'No new file content found')
    logging.info("Route: /preview_src - Session data retrieved")

    return render_template('observe.html', section='preview', file_content=file_content, new_file_content=new_file_content, fig_dir=fig_dir)

@app.route('/visualize_src')
def visualize_src():
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    graph_json2 = session.get('graph_json2', None)
    graph_json = session.get('graph_json', None)
    logging.info("Route: /visualize_src - Session data retrieved")

    return render_template('observe.html', section='visualize', graph_json=graph_json, graph_json2=graph_json2, fig_dir=fig_dir)

@app.route('/about_src')
def about():
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    return render_template('about.html', fig_dir=fig_dir)

@app.route('/export', methods=['POST'])
def export():
    print("export")
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    filename = session.get('filename', None)
    new_lines = session.get('new_file_content', 'No new file content found')
    
    # Get the output directory from the form
    output_file_path = os.path.join(app.config['EXPORT_FOLDER'], filename)
    logging.info("Route: /export - Session data retrieved")

    # Export idf
    idf.export(filename, output_file_path, new_lines)
    send_file(output_file_path, as_attachment=True, download_name=f'{filename}_output.IDF')
    logging.info("Route: /export - File exported")
    
    return render_template('home.html', fig_dir=fig_dir)

@app.errorhandler(413)
def request_entity_too_large(error):
    flash('File is too large')
    return redirect(request.url)

@app.route('/generate_busbar_name', methods=['GET'])
def generate_busbar_name():    
    print("generate_busbar_name")
    sbars = session.get('sbars', [])
    if sbars:
        base_name = sbars[-1].split('_')[0]
    else:
        base_name = 'sbar'
    index = len(sbars)
    print(f"Base name: {base_name}")
    while True:
        new_sbar_name = f'{base_name}_{index:03}'
        print(f"New busbar name 1: {new_sbar_name}") 
        if new_sbar_name not in sbars:
            print(f"New busbar name 2: {new_sbar_name}")
            return jsonify(busbar_name=new_sbar_name)
        index += 1

if __name__ == '__main__':
    app.run(port=5000, debug=True, threaded=True)