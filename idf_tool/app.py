import os
import sys
import logging
import re
import webbrowser

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, redirect, flash, session, send_file, url_for, jsonify, send_from_directory
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
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # 15MB max file size
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
    cell_types = {'M10': [182.0, 182.0, 10, 13.1], 'M10 HC': [182.0, 91.0, 10, 13.1], 'G1': [158.75, 158.75, 5, 16.625]}

    logging.info("Route: /submit - IDF file parsed")

    # Data processing
    corrected_component_outlines = component_outlines.copy()
    corrected_component_placements = component_placements.copy()

    fig = idf.draw_board(board_outline, component_outlines, component_placements)
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    w_sbar = {}
    for sbar in sbars:
        id = [id for id, placement in corrected_component_placements.items() if placement["name"] == sbar][0]
        w_sbar[sbar] = corrected_component_placements[id]['placement'][3]
    z_sbar = {sbar: False for sbar in sbars}
    new_string_names = session.get('new_string_names', None)

    w_string = {}
    for id, placement in corrected_component_placements.items():
        if placement["component_type"] == "string":
            w_string[id] = corrected_component_placements[id]['placement'][3]

    w_sbar_prev = {}
    for sbar, value in w_sbar.items():
        if sbar not in w_sbar_prev:
            w_sbar_prev[sbar] = []
        w_sbar_prev[sbar].append(value)

    w_string_prev = {}
    for id, value in w_string.items():
        if id not in w_string_prev:
            w_string_prev[id] = []
        w_string_prev[id].append(value)

    widthheight_prev = {}
    for name, outline in corrected_component_outlines.items():
        if outline['component_type'] == 'string':
            widthheight_prev[name] = outline['widthheight']

    if new_string_names is None:
        new_string_names = {string: '' for string in strings}

    file.seek(0)
    file_content = file.read().decode('utf-8')
    logging.info("Route: /submit - Data processed")

    string_metadata = {}
    for string in strings:
        outline = corrected_component_outlines[string]
        dist, cell_type, nr_cells, plus, minus = idf.reverse_engineer_string_outline(outline['coordinates'], cell_types)
        print(f"String: {string}, dist: {dist}, cell_type: {cell_type}, nr_cells: {nr_cells}, plus: {plus}, minus: {minus}")
        string_metadata[string] = {'dist': dist, 'cell_type': cell_type, 'nr_cells': nr_cells, 'plus': plus, 'minus': minus}

    # Store session data
    session['string_metadata'] = string_metadata
    session['cell_types'] = cell_types
    session['file_content'] = file_content
    session['widthheight_prev'] = widthheight_prev
    session['graph_json'] = graph_json
    session['board_outline'] = board_outline
    session['component_outlines'] = component_outlines
    session['component_placements'] = component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    session['corrected_component_placements'] = corrected_component_placements
    session['w_sbar'] = w_sbar
    session['w_string'] = w_string
    session['z_sbar'] = z_sbar
    session['sbars'] = sbars
    session['strings'] = strings
    session['w_sbar_prev'] = w_sbar_prev
    session['w_string_prev'] = w_string_prev
    logging.info("Route: /submit - Session data stored")

    return render_template('home.html', strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, w_sbar=w_sbar, w_string=w_string, new_string_names=new_string_names, z_sbar=z_sbar, fig_dir=fig_dir)

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
    w_sbar_prev = session.get('w_sbar_prev', {})
    w_string_prev = session.get('w_string_prev', {})
    w_string = session.get('w_string', {})
    z_sbar = session.get('z_sbar', {sbar: False for sbar in sbars})
    w_sbar = session.get('w_sbar', {sbar: 0.0 for sbar in sbars})
    widthheight_prev = session.get('widthheight_prev', {string: [0, 0] for string in strings})
    cell_types = session.get('cell_types', {})
    logging.info("Route: /submit_parameters - Session data retrieved")

    # HTML Parsing
    new_string_names = {key[7:]: request.form[key] for key in request.form if key.startswith('string_')}

    for id, placement in corrected_component_placements.items():
        if placement["component_type"] == "string":
            w_string[id] = float(request.form.get(f'string180deg_{id}', 0.0))
    
    for sbar in sbars:
        w_sbar[sbar] = float(request.form.get(f'sbar180deg_{sbar}', 0.0))
        z_sbar[sbar] = bool(request.form.get(f'sbarheight_{sbar}', False))
    logging.info("Route: /submit_parameters - HTML parsed")

    # Data processing
    if request.form.get('new_sbar_name_dyn', None) is not None or request.form.get('new_string_name_dyn', None) is not None:
        idf.add_components(request.form, corrected_component_outlines, corrected_component_placements, w_sbar, z_sbar, w_string, sbars, strings)
    
    if request.form.get('cell_type', None) is not None:
        cell_name = request.form.get('new_string_name', "String M10 HC 5 Cells 2mm +10mm -10mm")
        cell_type = request.form.get('cell_type', "M10 HC")
        nr_cells = int(request.form.get('nr_cells', 5))
        dist = float(request.form.get('dist', 2.0))
        plus = float(request.form.get('plus', 10.0))
        minus = float(request.form.get('minus', 10.0))
        idf.generate_string_outline(cell_type, nr_cells, dist, plus, minus, corrected_component_outlines, cell_name, cell_types)

    for sbar, value in w_sbar.items():
        if sbar not in w_sbar_prev:
            w_sbar_prev[sbar] = []
            w_sbar_prev[sbar].append(value)
        w_sbar_prev[sbar].append(value)
        if len(w_sbar_prev[sbar]) > 2:
            w_sbar_prev[sbar].pop(0)
    for string, value in w_string.items():
        if string not in w_string_prev:
            w_string_prev[string] = []
            w_string_prev[string].append(value)
        w_string_prev[string].append(value)
        if len(w_string_prev[string]) > 2:
            w_string_prev[string].pop(0)

    for name, component in corrected_component_outlines.items():
        if component['component_type'] == 'string':
            if request.form.get(f'outline_{name}_0', None) is None or request.form.get(f'outline_{name}_1', None) is None:
                widthheight = [1000.00, 182.00]
            else:
                widthheight = [float(request.form.get(f'outline_{name}_0', None)), float(request.form.get(f'outline_{name}_1', None))]
            if name not in widthheight_prev:
                widthheight_prev[name] = []
                widthheight_prev[name].append(widthheight)
            else:
                widthheight_prev[name].append(widthheight)
            if len(widthheight_prev[name]) > 2:
                widthheight_prev[name].pop(0)

    
    for id, placement in corrected_component_placements.items():
        placement['name'] == request.form.get(f'name_{id}', placement['name'])

    idf.translate(corrected_component_placements, corrected_component_outlines, w_sbar_prev, w_string_prev, request.form, widthheight_prev=widthheight_prev)
    idf.rotate(corrected_component_placements, corrected_component_outlines, w_sbar_prev, w_sbar, w_string_prev, w_string)

    idf.change_string_names(corrected_component_placements, corrected_component_outlines, new_string_names, strings)
    idf.change_sbar_height(corrected_component_outlines, z_sbar)

    
    for string in strings:
        print(string)
        if request.form.get(f'nr_of_cells_{string}') != "" and request.form.get(f'dist_{string}') != "" and request.form.get(f'plus_{string}') != "" and request.form.get(f'minus_{string}') != "":
            cell_type = request.form.get(f'cell_type_{string}', "M10 HC")
            nr_cells = int(float(request.form.get(f'nr_of_cells_{string}', 5)))
            dist = float(request.form.get(f'dist_{string}', 2.0))
            plus = float(request.form.get(f'plus_{string}', 10.0))
            minus = float(request.form.get(f'minus_{string}', 10.0))
            if request.form.get(f'string_{string}', None) is None or request.form.get(f'string_{string}', None) == "":
                cell_name = f"String {cell_type} {nr_cells} Cells {int(dist)}mm +{int(plus)}mm -{int(minus)}mm"
            else:
                cell_name = request.form.get(f'string_{string}')
            idf.generate_string_outline(cell_type, nr_cells, dist, plus, minus, corrected_component_outlines, cell_name, cell_types)
            for id, placement in corrected_component_placements.items():
                if placement["name"] == string:
                    placement['name'] = cell_name
                    break
            corrected_component_outlines[cell_name] = corrected_component_outlines.pop(string)
            strings = [name for name, _ in corrected_component_outlines.items() if name.startswith('String')]

    
    for sbar in sbars:
        id = [id for id, placement in corrected_component_placements.items() if placement["name"] == sbar][0]
        w_sbar[sbar] = corrected_component_placements[id]['placement'][3]
    
    for id, placement in corrected_component_placements.items():
        if placement["component_type"] == "string":
            w_string[id] = corrected_component_placements[id]['placement'][3]

    for name, component in corrected_component_outlines.items():
        if component['component_type'] == 'string':
            widthheight_prev[name] = component['widthheight']
            if len(widthheight_prev[name]) > 2:
                widthheight_prev[name].pop(0)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    new_file_content = idf.regenerate_idf_file_content(file_path, corrected_component_outlines, corrected_component_placements)
    logging.info("Route: /submit_parameters - Data processed")

    string_metadata = {}
    for string in strings:
        outline = corrected_component_outlines[string]
        dist, cell_type, nr_cells, plus, minus = idf.reverse_engineer_string_outline(outline['coordinates'], cell_types)
        string_metadata[string] = {'dist': dist, 'cell_type': cell_type, 'nr_cells': nr_cells, 'plus': plus, 'minus': minus}

    # Store session data
    session['string_metadata'] = string_metadata
    session['new_file_content'] = new_file_content
    session['new_string_names'] = new_string_names
    session['corrected_component_placements'] = corrected_component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    session['w_sbar'] = w_sbar
    session['widthheight_prev'] = widthheight_prev
    session['w_string'] = w_string
    session['z_sbar'] = z_sbar
    session['w_sbar_prev'] = w_sbar_prev
    session['w_string_prev'] = w_string_prev
    session['strings'] = strings
    logging.info("Route: /submit_parameters - Session data stored")

    # Clear input fields
    for key in new_string_names.keys():
        new_string_names[key] = ""

    return render_template('manipulate.html', string_metadata=string_metadata , manipulate_after_submit_parameters = True, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, w_sbar=w_sbar, w_string=w_string, z_sbar=z_sbar, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements, corrected_component_outlines=corrected_component_outlines)


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
    # fig = idf.draw_board(board_outline, component_outlines, component_placements)
    # graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    fig2 = idf.draw_board(board_outline, corrected_component_outlines, corrected_component_placements)
    graph_json2 = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
    logging.info("Route: /observe_src - Data processed")

    # Store session data
    session['graph_json2'] = graph_json2
    logging.info("Route: /observe_src - Session data stored")
    
    return render_template('observe.html', section='visualize', file_content=file_content, graph_json=graph_json, graph_json2=graph_json2, new_file_content=new_file_content, fig_dir=fig_dir)

@app.route('/manipulate_src')
def manipulate():
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    string_metadata = session.get('string_metadata', {})
    strings = session.get('strings', [])
    sbars = session.get('sbars', [])
    filename = session.get('filename', None)
    w_sbar = session.get('w_sbar', {})
    w_string = session.get('w_string', {})
    z_sbar = session.get('z_sbar', {})
    new_string_names = session.get('new_string_names', {})
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    logging.info("Route: /manipulate_src - Session data retrieved")

    return render_template('manipulate.html', string_metadata=string_metadata, manipulate_after_submit_parameters = True, strings=strings, sbars=sbars, filename=filename, w_sbar=w_sbar, w_string=w_string, new_string_names=new_string_names, z_sbar=z_sbar, corrected_component_placements= corrected_component_placements, fig_dir=fig_dir, corrected_component_outlines=corrected_component_outlines)

@app.route('/remove_busbar', methods=['POST'])
def remove_busbar():
    print("remove_busbar")
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    cell_types = session.get('cell_types', {})
    new_string_names = session.get('new_string_names', {})
    sbars = session.get('sbars', [])
    strings = session.get('strings', [])
    graph_json = session.get('graph_json', None)
    w_sbar = session.get('w_sbar', {})
    w_string = session.get('w_string', {})
    z_sbar = session.get('z_sbar', {})
    filename = session.get('filename', None)
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    string_metadata = session.get('string_metadata', {})
    logging.info("Route: /remove_busbar - Session data retrieved")

    # HTML Parsing
    sbar_to_delete = request.form['sbar']
    logging.info(f"Route: /remove_busbar - {sbar_to_delete} to be deleted")

    # Data processing
    del corrected_component_outlines[sbar_to_delete]
    keys_to_delete = [id for id, placement in corrected_component_placements.items() if placement["name"] == sbar_to_delete]
    for key in keys_to_delete:
        del corrected_component_placements[key]
    del z_sbar[sbar_to_delete]
    del w_sbar[sbar_to_delete]
    sbars = [sbar for sbar in sbars if sbar != sbar_to_delete]
    logging.info("Route: /remove_busbar - Data processed")

    string_metadata = {}
    for string in strings:
        outline = corrected_component_outlines[string]
        dist, cell_type, nr_cells, plus, minus = idf.reverse_engineer_string_outline(outline['coordinates'], cell_types)
        string_metadata[string] = {'dist': dist, 'cell_type': cell_type, 'nr_cells': nr_cells, 'plus': plus, 'minus': minus}

    # Store session data
    session['corrected_component_placements'] = corrected_component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    session['sbars'] = sbars
    session['z_sbar'] = z_sbar
    session['w_sbar'] = w_sbar
    session['strings'] = strings
    session['w_string'] = w_string
    session['string_metadata'] = string_metadata
    logging.info("Route: /remove_busbar - Session data stored")

    return render_template('manipulate.html', string_metadata=string_metadata, manipulate_after_submit_parameters = True, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, w_sbar=w_sbar, w_string=w_string, z_sbar=z_sbar, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements, corrected_component_outlines=corrected_component_outlines)

@app.route('/remove_string', methods=['POST'])
def remove_string():
    print("remove_string")
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    cell_types = session.get('cell_types', {})
    new_string_names = session.get('new_string_names', {})
    sbars = session.get('sbars', [])
    strings = session.get('strings', [])
    graph_json = session.get('graph_json', None)
    w_sbar = session.get('w_sbar', {})
    w_string = session.get('w_string', {})
    z_sbar = session.get('z_sbar', {})
    filename = session.get('filename', None)
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    w_string_prev = session.get('w_string_prev', {})
    string_metadata = session.get('string_metadata', {})
    logging.info("Route: /remove_string - Session data retrieved")

    # HTML Parsing
    string_to_delete = request.form['string']
    logging.info(f"Route: /remove_string - {string_to_delete} to be deleted")

    # Data processing
    count = 0
    for id, placement in corrected_component_placements.items():
        if placement['name'] == corrected_component_placements[string_to_delete]['name']:
            count += 1
    if count ==1:
        del corrected_component_outlines[corrected_component_placements[string_to_delete]['name']]
        strings = [string for string in strings if string != corrected_component_placements[string_to_delete]['name']]
    del corrected_component_placements[string_to_delete]
    del w_string[string_to_delete]
    del w_string_prev[string_to_delete]
    logging.info("Route: /remove_string - Data processed")

    string_metadata = {}
    for string in strings:
        outline = corrected_component_outlines[string]
        dist, cell_type, nr_cells, plus, minus = idf.reverse_engineer_string_outline(outline['coordinates'], cell_types)
        string_metadata[string] = {'dist': dist, 'cell_type': cell_type, 'nr_cells': nr_cells, 'plus': plus, 'minus': minus}

    # Store session data
    session['string_metadata'] = string_metadata
    session['corrected_component_placements'] = corrected_component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    session['strings'] = strings
    session['w_string'] = w_string
    logging.info("Route: /remove_string - Session data stored")

    return render_template('manipulate.html', string_metadata=string_metadata, manipulate_after_submit_parameters = True, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, w_sbar=w_sbar, w_string=w_string, z_sbar=z_sbar, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements, corrected_component_outlines=corrected_component_outlines)

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
    print("exported")

    logging.info("Route: /export - File exported")
    
    return render_template('home.html', fig_dir=fig_dir)

@app.errorhandler(413)
def request_entity_too_large(error):
    flash('File is too large')
    return redirect(request.url)

@app.route('/generate_busbar_name', methods=['GET'])
def generate_busbar_name():    
    print("generate_busbar_name")
    corrected_component_placements = session.get('corrected_component_placements', {})

    bb_keys = [key for key in corrected_component_placements.keys() if key.startswith('BB')]

    if bb_keys:
        max_index = max(int(key[2:]) for key in bb_keys)
    else:
        max_index = 0
    
    # Generate new busbar name and ID
    new_index = max_index + 1
    new_id = f'BB{new_index:03}'

    sbars = session.get('sbars', [])
    if sbars:
        base_name = sbars[-1].split('_')[0]
    else:
        base_name = 'sbar'
    index = len(sbars)
    while True:
        new_sbar_name = f'{base_name}_{index:03}'
        if new_sbar_name not in sbars:
            return jsonify(busbar_name=new_sbar_name, id=new_id)
        index += 1

@app.route('/generate_string_id', methods=['GET'])
def generate_string_id():
    print("generate_string_id")
    corrected_component_placements = session.get('corrected_component_placements', {})
    
    str_keys = [key for key in corrected_component_placements.keys() if re.match(r'STR\d{3}', key)]
    
    if not str_keys:
        return jsonify(string_id='STR000')
    
    # Extract the numeric part and find the maximum
    max_num = max(int(key[3:]) for key in str_keys)
    
    # Increment the number and format it back to STR###
    next_num = max_num + 1
    next_str_key = f'STR{next_num:03}'
    
    return jsonify(string_id=next_str_key)

@app.route('/generate_string_name', methods=['GET'])
def generate_string_name():
    print("generate_string_name")
    
    return jsonify(string_name='String M10 HC 5 Cells 2mm +10mm -10mm')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(os.getcwd(), 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(port=5000, debug=True, threaded=True)
