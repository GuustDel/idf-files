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
app.config['EXPORT_FOLDER'] = os.path.join(os.getcwd(), "Costar")
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

    w_sbar = {}
    for sbar in sbars:
        id = [id for id, placement in corrected_component_placements.items() if placement["name"] == sbar][0]
        w_sbar[sbar] = corrected_component_placements[id]['placement'][3]
    z_sbar = {sbar: False for sbar in sbars}
    new_string_names = session.get('new_string_names', None)

    w_sbar_prev = {}
    for sbar, value in w_sbar.items():
        if sbar not in w_sbar_prev:
            w_sbar_prev[sbar] = []
        w_sbar_prev[sbar].append(value)
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
    session['w_sbar'] = w_sbar
    session['z_sbar'] = z_sbar
    session['sbars'] = sbars
    session['strings'] = strings
    session['w_sbar_prev'] = w_sbar_prev
    logging.info("Route: /submit - Session data stored")

    return render_template('home.html', strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, w_sbar=w_sbar, new_string_names=new_string_names, z_sbar=z_sbar, fig_dir=fig_dir)

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
    z_sbar = session.get('z_sbar', {sbar: False for sbar in sbars})
    w_sbar = session.get('w_sbar', {sbar: 0.0 for sbar in sbars})
    logging.info("Route: /submit_parameters - Session data retrieved")
    
    # HTML Parsing
    new_string_names = {key[7:]: request.form[key] for key in request.form if key.startswith('string_')}
    for sbar in sbars:
        w_sbar[sbar] = float(request.form.get(f'sbar180deg_{sbar}', 0.0))
        z_sbar[sbar] = bool(request.form.get(f'sbarheight_{sbar}', False))
    logging.info("Route: /submit_parameters - HTML parsed")

    # Data processing
    if request.form.get('new_sbar_name_dyn', None) is not None:
        idf.add_busbars(request.form, corrected_component_outlines, corrected_component_placements, w_sbar, z_sbar, sbars)

    for sbar, value in w_sbar.items():
        if sbar not in w_sbar_prev:
            w_sbar_prev[sbar] = []
        w_sbar_prev[sbar].append(value)
        if len(w_sbar_prev[sbar]) > 2:
            w_sbar_prev[sbar].pop(0)

    idf.translate(corrected_component_placements, corrected_component_outlines, w_sbar_prev, request.form)
    idf.rotate(corrected_component_placements, corrected_component_outlines, w_sbar_prev, w_sbar)

    idf.change_string_names(corrected_component_placements, corrected_component_outlines, new_string_names, strings)
    idf.change_sbar_height(corrected_component_outlines, z_sbar)
    
    for sbar in sbars:
        id = [id for id, placement in corrected_component_placements.items() if placement["name"] == sbar][0]
        w_sbar[sbar] = corrected_component_placements[id]['placement'][3]

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    new_file_content = idf.regenerate_idf_file_content(file_path, corrected_component_outlines, corrected_component_placements)
    logging.info("Route: /submit_parameters - Data processed")

    # Store session data
    session['new_file_content'] = new_file_content
    session['new_string_names'] = new_string_names
    session['corrected_component_placements'] = corrected_component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    session['w_sbar'] = w_sbar
    session['z_sbar'] = z_sbar
    session['w_sbar_prev'] = w_sbar_prev
    logging.info("Route: /submit_parameters - Session data stored")

    return render_template('manipulate.html', manipulate_after_submit_parameters = True, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, w_sbar=w_sbar, z_sbar=z_sbar, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements, corrected_component_outlines=corrected_component_outlines)


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
    w_sbar = session.get('w_sbar', {})
    z_sbar = session.get('z_sbar', {})
    new_string_names = session.get('new_string_names', {})
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    logging.info("Route: /manipulate_src - Session data retrieved")

    return render_template('manipulate.html', manipulate_after_submit_parameters = True, strings=strings, sbars=sbars, filename=filename, w_sbar=w_sbar, new_string_names=new_string_names, z_sbar=z_sbar, corrected_component_placements= corrected_component_placements, fig_dir=fig_dir, corrected_component_outlines=corrected_component_outlines)

@app.route('/remove_busbar', methods=['POST'])
def remove_busbar():
    print("remove_busbar")
    fig_dir = url_for('static', filename='img/Soltech_Logo.png')

    # Session retrieval
    new_string_names = session.get('new_string_names', {})
    sbars = session.get('sbars', [])
    strings = session.get('strings', [])
    graph_json = session.get('graph_json', None)
    w_sbar = session.get('w_sbar', {})
    z_sbar = session.get('z_sbar', {})
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
    del z_sbar[sbar_to_delete]
    del w_sbar[sbar_to_delete]
    sbars = [sbar for sbar in sbars if sbar != sbar_to_delete]
    logging.info("Route: /remove_busbar - Data processed")

    # Store session data
    session['corrected_component_placements'] = corrected_component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    session['sbars'] = sbars
    session['z_sbar'] = z_sbar
    session['w_sbar'] = w_sbar
    logging.info("Route: /remove_busbar - Session data stored")

    return render_template('manipulate.html', manipulate_after_submit_parameters = True, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, w_sbar=w_sbar, z_sbar=z_sbar, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements, corrected_component_outlines=corrected_component_outlines)

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
    sbars = session.get('sbars', [])
    if sbars:
        base_name = sbars[-1].split('_')[0]
    else:
        base_name = 'sbar'
    index = len(sbars)
    while True:
        new_sbar_name = f'{base_name}_{index:03}'
        if new_sbar_name not in sbars:
            return jsonify(busbar_name=new_sbar_name)
        index += 1

if __name__ == '__main__':
    app.run(port=5000, debug=True, threaded=True)
