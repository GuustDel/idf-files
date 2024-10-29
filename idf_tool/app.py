import os
import sys

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

app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads")
app.config['EXPORT_FOLDER'] = os.path.join(os.getcwd(), "submits")
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024  # 15kB max file size
app.config['ALLOWED_EXTENSIONS'] = {'idf'}

Session(app)

def allowed_file(filename):

    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def base():
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    return render_template('home.html', fig_dir=fig_dir, enable_drop=True)

@app.route('/home_src')
def home():
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    # Session retrieval
    graph_json = session.get('graph_json', None)

    return render_template('home.html', graph_json=graph_json, fig_dir=fig_dir, enable_drop=True)

@app.route('/submit', methods=['POST'])
def submit_file():
    print("submit_file")
    session.clear()
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    # File management
    file = request.files.get('file')
    if not file or file.filename == '' or not allowed_file(file.filename):
        print("File not found")
        return redirect(request.url)

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    session['filename'] = filename

    # IDF parsing
    board_outline = idf.board_outline(file_path)
    component_outlines = idf.component_outlines(file_path)
    component_placements = idf.component_placements(file_path)
    sbars, strings = idf.get_component_names_by_type(component_outlines)

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

    return render_template('home.html', strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, sbar_checkboxes_180deg=sbar_checkboxes_180deg, new_string_names=new_string_names, sbar_checkboxes_height=sbar_checkboxes_height, fig_dir=fig_dir)

@app.route('/submit_parameters', methods=['POST'])
def submit_parameters():
    print("submit_parameters")
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    # Session retrieval
    sbars = session.get('sbars', [])
    strings = session.get('strings', [])
    graph_json = session.get('graph_json', None)
    front_end_sbar_data = session.get('front_end_sbar_data', [])
    filename = session.get('filename', None)
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    sbar_checkboxes_180deg_history = session.get('sbar_checkboxes_180deg_history', {})
    
    # HTML Parsing
    new_string_names = {key[7:]: request.form[key] for key in request.form if key.startswith('string_')}
    sbar_checkboxes_180deg = {}
    sbar_checkboxes_height = {}
    for sbar in sbars:
        sbar_checkboxes_180deg[sbar] = bool(request.form.get(f'sbar180deg_{sbar}'))
        sbar_checkboxes_height[sbar] = bool(request.form.get(f'sbarheight_{sbar}'))

    # Data processing
    idf.add_busbars(request.form, corrected_component_outlines, corrected_component_placements, sbar_checkboxes_180deg, sbar_checkboxes_height, front_end_sbar_data)

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

    # Store session data
    session['new_file_content'] = new_file_content
    session['Index_dyn_busbar'] = len(front_end_sbar_data)
    session['new_string_names'] = new_string_names
    session['front_end_sbar_data'] = front_end_sbar_data
    session['corrected_component_placements'] = corrected_component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    session['sbar_checkboxes_180deg'] = sbar_checkboxes_180deg
    session['sbar_checkboxes_height'] = sbar_checkboxes_height
    session['sbar_checkboxes_180deg_history'] = sbar_checkboxes_180deg_history

    return render_template('manipulate.html', manipulate_after_submit_parameters = True, front_end_sbar_data=front_end_sbar_data, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, sbar_checkboxes_180deg=sbar_checkboxes_180deg, sbar_checkboxes_height=sbar_checkboxes_height, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements, corrected_component_outlines=corrected_component_outlines)


@app.route('/observe_src')
def preview(): 
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    # Session retrieval 
    file_content = session.get('file_content', 'No file content found')
    graph_json = session.get('graph_json', None)
    board_outline = session.get('board_outline', None)
    component_outlines = session.get('component_outlines', None)
    component_placements = session.get('component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', {})
    corrected_component_placements = session.get('corrected_component_placements', {})
    new_file_content = session.get('new_file_content', 'No new file content found')

    #Data processing
    fig = idf.draw_board(board_outline, component_outlines, component_placements)
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
    fig2 = idf.draw_board(board_outline, corrected_component_outlines, corrected_component_placements)
    graph_json2 = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)

    # Store session data
    session['graph_json2'] = graph_json2
    
    return render_template('observe.html', section='preview', file_content=file_content, graph_json=graph_json, graph_json2=graph_json2, new_file_content=new_file_content, fig_dir=fig_dir)

@app.route('/manipulate_src')
def manipulate():
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    # Session retrieval
    strings = session.get('strings', [])
    sbars = session.get('sbars', [])
    filename = session.get('filename', None)
    sbar_checkboxes_180deg = session.get('sbar_checkboxes_180deg', {})
    sbar_checkboxes_height = session.get('sbar_checkboxes_height', {})
    new_string_names = session.get('new_string_names', {})
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    front_end_sbar_data = session.get('front_end_sbar_data', [])

    return render_template('manipulate.html', manipulate_after_submit_parameters = True, new_sbar_data_length = len(front_end_sbar_data), strings=strings, sbars=sbars, filename=filename, sbar_checkboxes_180deg=sbar_checkboxes_180deg, new_string_names=new_string_names, sbar_checkboxes_height=sbar_checkboxes_height, corrected_component_placements= corrected_component_placements, fig_dir=fig_dir, corrected_component_outlines=corrected_component_outlines, front_end_sbar_data=front_end_sbar_data)

@app.route('/remove_busbar', methods=['POST'])
def remove_busbar():
    print("remove_busbar")
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    # Session retrieval
    new_string_names = session.get('new_string_names', {})
    sbars = session.get('sbars', [])
    strings = session.get('strings', [])
    graph_json = session.get('graph_json', None)
    sbar_checkboxes_180deg = session.get('sbar_checkboxes_180deg', {})
    sbar_checkboxes_height = session.get('sbar_checkboxes_height', {})
    front_end_sbar_data = session.get('front_end_sbar_data', [])
    filename = session.get('filename', None)
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)

    # HTML Parsing
    IdNr = request.form['IdNr']

    # Data processing
    if IdNr == "1":
        busbarId = int(request.form['busbar_id'])
        del corrected_component_outlines[sbars[int(busbarId)]]
        keys_to_delete = [id for id, placement in corrected_component_placements.items() if placement["name"] == sbars[int(busbarId)]]
        for key in keys_to_delete:
            del corrected_component_placements[key]
        del sbar_checkboxes_height[sbars[int(busbarId)]]
        del sbars[int(busbarId)]
    elif IdNr == "2":
        busbarId = int(request.form['busbar_id']) + len(sbars)
        del corrected_component_outlines[front_end_sbar_data[int(busbarId) - len(sbars)][0]]
        keys_to_delete = [id for id, placement in corrected_component_placements.items() if placement["name"] == front_end_sbar_data[int(busbarId) - len(sbars)][0]]
        for key in keys_to_delete:
            del corrected_component_placements[key]
        del sbar_checkboxes_height[front_end_sbar_data[int(busbarId) - len(sbars)][0]]
        del front_end_sbar_data[int(busbarId) - len(sbars)]
    elif IdNr == "3":
        busbarId = int(request.form['busbar_id']) + len(sbars) + session.get('Index_dyn_busbar', 0)
        del corrected_component_outlines[front_end_sbar_data[int(busbarId) - len(sbars)][0]]
        keys_to_delete = [id for id, placement in corrected_component_placements.items() if placement["name"] == front_end_sbar_data[int(busbarId) - len(sbars)][0]]
        for key in keys_to_delete:
            del corrected_component_placements[key]
        del sbar_checkboxes_height[front_end_sbar_data[int(busbarId) - len(sbars)][0]]
        del front_end_sbar_data[int(busbarId) - len(sbars)]

    # Store session data
    session['corrected_component_placements'] = corrected_component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    return render_template('manipulate.html', manipulate_after_submit_parameters = True, new_sbar_data_length = len(front_end_sbar_data), front_end_sbar_data=front_end_sbar_data, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, sbar_checkboxes_180deg=sbar_checkboxes_180deg, sbar_checkboxes_height=sbar_checkboxes_height, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements, corrected_component_outlines=corrected_component_outlines)

@app.route('/preview_src')
def preview_src():
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    # Session retrieval
    file_content = session.get('file_content', 'No file content found')
    new_file_content = session.get('new_file_content', 'No new file content found')

    return render_template('observe.html', section='preview', file_content=file_content, new_file_content=new_file_content, fig_dir=fig_dir)

@app.route('/visualize_src')
def visualize_src():
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    # Session retrieval
    graph_json2 = session.get('graph_json2', None)
    graph_json = session.get('graph_json', None)

    return render_template('observe.html', section='visualize', graph_json=graph_json, graph_json2=graph_json2, fig_dir=fig_dir)

@app.route('/about_src')
def about():
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    return render_template('about.html', fig_dir=fig_dir)

@app.route('/export', methods=['POST'])
def export():
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    # Session retrieval
    filename = session.get('filename', None)
    new_lines = session.get('new_file_content', 'No new file content found')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_file_path = os.path.join(app.config['EXPORT_FOLDER'], filename)

    # Export idf
    idf.export(file_path, output_file_path, new_lines)
    
    return render_template('home.html', fig_dir=fig_dir)

@app.errorhandler(413)
def request_entity_too_large(error):
    flash('File is too large')
    return redirect(request.url)

if __name__ == '__main__':
    app.run(port=5000, debug=True)