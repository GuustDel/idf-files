import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, redirect, flash, session, send_file, url_for, jsonify
from flask_session import Session
import idf_tool.parse_idf as parse_idf
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

# Global variables
file_path = None
board_outline = None
component_outlines = None
component_placements = None
strings = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/home_src')
def home():
    strings = session.get('strings', [])
    graph_json = session.get('graph_json', None)
    sbars = session.get('sbars', [])
    filename = session.get('filename', None)
    sbar_checkboxes_180deg = session.get('sbar_checkboxes_180deg', {})
    sbar_checkboxes_height = session.get('sbar_checkboxes_height', {})
    new_string_names = session.get('new_string_names', None)
    if new_string_names is None:
        new_string_names = {string: '' for string in strings}

    fig_dir = url_for('static', filename='img/Soltech_logo.png')
    return render_template('home.html', strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, sbar_checkboxes_180deg=sbar_checkboxes_180deg, new_string_names=new_string_names, sbar_checkboxes_height=sbar_checkboxes_height, fig_dir=fig_dir, enable_drop=True)

@app.route('/')
def base():
    fig_dir = url_for('static', filename='img/Soltech_logo.png')
    return render_template('home.html', fig_dir=fig_dir, enable_drop=True)

@app.route('/submit', methods=['POST'])
def submit_file():
    session.clear()

    global file_path, board_outline, component_outlines, component_placements, strings
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        session['filename'] = filename

        board_outline, component_outlines, component_placements, strings, sbars = parse_idf.get_coordinates(file_path)
        session['sbars'] = sbars

        fig = parse_idf.draw_board(board_outline, component_outlines, component_placements)

        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        board_outline_list = [board.tolist() for board in board_outline]
        for component in component_outlines:
            component['coordinates'] = component['coordinates'].tolist()
        for component in component_placements:
            component['placement'] = component['placement'].tolist()

        session['strings'] = strings
        session['graph_json'] = graph_json
        session['board_outline'] = board_outline_list
        session['component_outlines'] = component_outlines
        session['component_placements'] = component_placements

        sbar_checkboxes_180deg_False = {}
        sbar_checkboxes_height_False = {}
        for sbar in sbars:
            sbar_checkboxes_180deg_False[sbar] = False
            sbar_checkboxes_height_False[sbar] = False


        sbar_checkboxes_180deg = session.get('sbar_checkboxes_180deg', sbar_checkboxes_180deg_False)
        sbar_checkboxes_height = session.get('sbar_checkboxes_height', sbar_checkboxes_height_False)
        new_string_names = session.get('new_string_names', None)

        if new_string_names is None:
            new_string_names = {string: '' for string in strings}

        if component_outlines is not None:
            for component in component_outlines:
                component['coordinates'] = np.array(component['coordinates'])
        if component_placements is not None:
            for component in component_placements:
                component['placement'] = np.array(component['placement'])

        corrected_component_outlines = parse_idf.corrected_component_outlines(component_outlines = component_outlines, String_names = strings, new_string_names = new_string_names)
        session['corrected_component_outlines'] = corrected_component_outlines
        corrected_component_placements = parse_idf.corrected_component_placements(component_placements = component_placements, String_names = strings, new_string_names = new_string_names, sbar_checkboxes_180deg = sbar_checkboxes_180deg, corrected_component_outlines = corrected_component_outlines)
        session['corrected_component_placements'] = corrected_component_placements

        # Read file content and store it in the session
        file.seek(0)
        file_content = file.read().decode('utf-8')
        session['file_content'] = file_content
        fig_dir = url_for('static', filename='img/Soltech_logo.png')
        return render_template('home.html', strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, sbar_checkboxes_180deg=sbar_checkboxes_180deg, new_string_names=new_string_names, sbar_checkboxes_height=sbar_checkboxes_height, fig_dir=fig_dir)
    else:
        flash('Invalid file type')
        return redirect(request.url)

@app.route('/export', methods=['POST'])
def export():
    global file_path

    if file_path:
        filename, _ = os.path.splitext(session.get('filename', None))
        new_file_content = session.get('new_file_content', 'No new file content found')
        output_file_path = os.path.join(app.config['EXPORT_FOLDER'], filename)
        with open(output_file_path, 'w') as outfile:
            outfile.write(new_file_content)
        return send_file(output_file_path, as_attachment=True, download_name=f'{filename}_output.idf')

    fig_dir = url_for('static', filename='img/Soltech_logo.png')
    return render_template('home.html', fig_dir=fig_dir)

@app.route('/submit_parameters', methods=['POST'])
def submit_parameters():
    new_string_names = {key[7:]: request.form[key] for key in request.form if key.startswith('string_')}
    sbars = session.get('sbars', [])
    strings = session.get('strings', [])
    graph_json = session.get('graph_json', None)
    sbar_checkboxes_180deg = {}
    sbar_checkboxes_height = {}
    for sbar in sbars:
        sbar_checkboxes_180deg[sbar] = bool(request.form.get(f'sbar180deg_{sbar}'))
        sbar_checkboxes_height[sbar] = bool(request.form.get(f'sbarheight_{sbar}'))

    filename = session.get('filename', None)

    session['sbar_checkboxes_180deg'] = sbar_checkboxes_180deg
    session['sbar_checkboxes_height'] = sbar_checkboxes_height
    session['new_string_names'] = new_string_names
    fig_dir = url_for('static', filename='img/Soltech_logo.png')
    
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    
    new_sbar_data = []
    front_end_sbar_data = session.get('front_end_sbar_data', [])
    Index_dyn_busbar = len(front_end_sbar_data)
    session['Index_dyn_busbar'] = Index_dyn_busbar
    for i in range(len(request.form.getlist('new_sbar_name_dyn'))):
        new_sbar_name = request.form.getlist('new_sbar_name_dyn')[i]
        new_sbar180deg = bool(request.form.get(f'new_sbar180deg_dyn_{i}', False))
        new_sbarheight = bool(request.form.get(f'new_sbarheight_dyn_{i}', False))
        new_placement_x = request.form.getlist('new_placement_x_dyn')[i]
        new_placement_y = request.form.getlist('new_placement_y_dyn')[i]
        new_placement_z = request.form.getlist('new_placement_z_dyn')[i]
        new_outline_height = request.form.getlist('new_outline_length_dyn')[i]
        new_outline_width = request.form.getlist('new_outline_width_dyn')[i]
        new_sbar_data.append([new_sbar_name, new_sbar180deg, new_sbarheight, float(new_placement_x), float(new_placement_y), float(new_placement_z), float(new_outline_height), float(new_outline_width)])
        front_end_sbar_data.append([new_sbar_name, new_sbar180deg, new_sbarheight, float(new_placement_x), float(new_placement_y), float(new_placement_z), float(new_outline_height), float(new_outline_width)])

    for i in range(len(request.form.getlist('new_sbar_name'))):
        front_end_sbar_data[i][0] = request.form.getlist('new_sbar_name')[i]
        front_end_sbar_data[i][1] = bool(request.form.get(f'new_sbar180deg_{i}', False))
        front_end_sbar_data[i][2] = bool(request.form.get(f'new_sbarheight_{i}', False))

        front_end_sbar_data[i][3] = float(request.form.get(f'placement_{front_end_sbar_data[i][0]}_0', front_end_sbar_data[i][3]))
        front_end_sbar_data[i][4] = float(request.form.get(f'placement_{front_end_sbar_data[i][0]}_1', front_end_sbar_data[i][4]))
        front_end_sbar_data[i][5] = float(request.form.get(f'placement_{front_end_sbar_data[i][0]}_2', front_end_sbar_data[i][5]))
        front_end_sbar_data[i][6] = float(request.form.get(f'outline_{front_end_sbar_data[i][0]}_0', front_end_sbar_data[i][6]))
        front_end_sbar_data[i][7] = float(request.form.get(f'outline_{front_end_sbar_data[i][0]}_1', front_end_sbar_data[i][7]))

    for i in range(len(new_sbar_data)):
        corrected_component_placements, corrected_component_outlines, sbar_checkboxes_180deg, sbar_checkboxes_height = parse_idf.add_busbar(True, corrected_component_outlines, corrected_component_placements, sbar_checkboxes_180deg, sbar_checkboxes_height, new_sbar_data[i][0], new_sbar_data[i][1], new_sbar_data[i][2], new_sbar_data[i][3], new_sbar_data[i][4], new_sbar_data[i][5], new_sbar_data[i][6], new_sbar_data[i][7])
    print("new_sbar_data", new_sbar_data)
    for i in range(len(front_end_sbar_data)):
        _, _, sbar_checkboxes_180deg, sbar_checkboxes_height = parse_idf.add_busbar(False, corrected_component_outlines, corrected_component_placements, sbar_checkboxes_180deg, sbar_checkboxes_height, front_end_sbar_data[i][0], front_end_sbar_data[i][1], front_end_sbar_data[i][2], front_end_sbar_data[i][3], front_end_sbar_data[i][4], front_end_sbar_data[i][5], front_end_sbar_data[i][6], front_end_sbar_data[i][7])

    print("front_end_sbar_data", front_end_sbar_data)
    print("sbar_checkboxes_180deg", sbar_checkboxes_180deg)
    
    if 'sbar_checkboxes_180deg_history' not in session:
        session['sbar_checkboxes_180deg_history'] = {}

    sbar_checkboxes_180deg_history = session['sbar_checkboxes_180deg_history']
    for sbar, value in sbar_checkboxes_180deg.items():
        if sbar not in sbar_checkboxes_180deg_history:
            sbar_checkboxes_180deg_history[sbar] = []
        sbar_checkboxes_180deg_history[sbar].append(value)
    session['sbar_checkboxes_180deg_history'] = sbar_checkboxes_180deg_history

    for placement in corrected_component_placements:
        name = placement['name']
        if placement['component_type'] == 'busbar':
            if (len(sbar_checkboxes_180deg_history[name]) >= 2 and sbar_checkboxes_180deg_history[name][-1] == sbar_checkboxes_180deg_history[name][-2]) or (len(sbar_checkboxes_180deg_history[name]) == 1 and sbar_checkboxes_180deg_history[name][-1] == False):
                placement['placement'][0] = float(request.form.get(f'placement_{name}_0', placement['placement'][0]))
                placement['placement'][1] = float(request.form.get(f'placement_{name}_1', placement['placement'][1]))
                placement['placement'][2] = float(request.form.get(f'placement_{name}_2', placement['placement'][2]))

    for outline in corrected_component_outlines:
        name = outline['name']
        if outline['component_type'] == 'busbar':
            if (len(sbar_checkboxes_180deg_history[name]) >= 2 and sbar_checkboxes_180deg_history[name][-1] == sbar_checkboxes_180deg_history[name][-2]) or (len(sbar_checkboxes_180deg_history[name]) == 1 and sbar_checkboxes_180deg_history[name][-1] == False):
                outline['coordinates'][2, 0] = float(request.form.get(f'outline_{name}_0', outline['coordinates'][2, 0]))
                outline['coordinates'][1, 0] = float(request.form.get(f'outline_{name}_0', outline['coordinates'][2, 0]))
                outline['coordinates'][2, 1] = float(request.form.get(f'outline_{name}_1', outline['coordinates'][2, 1]))
                outline['coordinates'][3, 1] = float(request.form.get(f'outline_{name}_1', outline['coordinates'][2, 1]))
                
    corrected_component_placements_new = parse_idf.corrected_component_placements_new(corrected_component_placements = corrected_component_placements, sbar_checkboxes_180deg = sbar_checkboxes_180deg, corrected_component_outlines = corrected_component_outlines, sbar_checkboxes_180deg_history = sbar_checkboxes_180deg_history)
    print("corrected_component_placements", corrected_component_placements_new)

    session['front_end_sbar_data'] = front_end_sbar_data
    session['corrected_component_placements'] = corrected_component_placements_new
    session['corrected_component_outlines'] = corrected_component_outlines
    session['sbar_checkboxes_180deg'] = sbar_checkboxes_180deg
    session['sbar_checkboxes_height'] = sbar_checkboxes_height

    print("submit_parameters")
    return render_template('manipulate.html', manipulate_after_submit_parameters = True, front_end_sbar_data=front_end_sbar_data, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, sbar_checkboxes_180deg=sbar_checkboxes_180deg, sbar_checkboxes_height=sbar_checkboxes_height, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements_new, corrected_component_outlines=corrected_component_outlines)


@app.route('/observe_src')
def preview():  
    file_content = session.get('file_content', 'No file content found')

    graph_json = session.get('graph_json', None)
    board_outline_list = session.get('board_outline', None)
    component_outlines = session.get('component_outlines', None)
    component_placements = session.get('component_placements', None)
    sbar_checkboxes_height = session.get('sbar_checkboxes_height', {})
    sbar_checkboxes_180deg = session.get('sbar_checkboxes_180deg', {})

    if board_outline_list is not None:
        board_outline = np.array([np.array(board) for board in board_outline_list])
    if component_outlines is not None:
        for component in component_outlines:
            component['coordinates'] = np.array(component['coordinates'])
    if component_placements is not None:
        for component in component_placements:
            component['placement'] = np.array(component['placement'])
    
    fig = parse_idf.draw_board(board_outline, component_outlines, component_placements)

    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    new_string_names = session.get('new_string_names', {})
    if new_string_names == {}:
        new_file_content = ''
        return render_template('observe.html', file_content=file_content, graph_json=graph_json, new_file_content=new_file_content, fig_dir=fig_dir)
    else:
        corrected_component_outlines = session.get('corrected_component_outlines', {})
        corrected_component_placements = session.get('corrected_component_placements', {})
        new_file_content = parse_idf.regenerate_idf_file_content(corrected_component_outlines, corrected_component_placements, file_content, sbar_checkboxes_height = sbar_checkboxes_height, new_string_names = new_string_names)
        session['new_file_content'] = new_file_content
        
        fig2 = parse_idf.draw_board(board_outline, corrected_component_outlines, corrected_component_placements)
        graph_json2 = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
        session['graph_json2'] = graph_json2
        
        return render_template('observe.html', section='preview', file_content=file_content, graph_json=graph_json, graph_json2=graph_json2, new_file_content=new_file_content, fig_dir=fig_dir)

@app.route('/manipulate_src')
def manipulate():
    strings = session.get('strings', [])
    graph_json = session.get('graph_json', None)
    sbars = session.get('sbars', [])
    filename = session.get('filename', None)
    sbar_checkboxes_180deg = session.get('sbar_checkboxes_180deg', {})
    sbar_checkboxes_height = session.get('sbar_checkboxes_height', {})
    new_string_names = session.get('new_string_names', {})
    corrected_component_placements = session.get('corrected_component_placements', None)
    corrected_component_outlines = session.get('corrected_component_outlines', None)
    fig_dir = url_for('static', filename='img/Soltech_logo.png')
    front_end_sbar_data = session.get('front_end_sbar_data', [])

    return render_template('manipulate.html', manipulate_after_submit_parameters = True, new_sbar_data_length = len(front_end_sbar_data), strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, sbar_checkboxes_180deg=sbar_checkboxes_180deg, new_string_names=new_string_names, sbar_checkboxes_height=sbar_checkboxes_height, corrected_component_placements= corrected_component_placements, fig_dir=fig_dir, corrected_component_outlines=corrected_component_outlines, front_end_sbar_data=front_end_sbar_data)

@app.route('/remove_busbar', methods=['POST'])
def remove_busbar():
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
    fig_dir = url_for('static', filename='img/Soltech_logo.png')
    IdNr = request.form['IdNr']
    if IdNr == "1":
        busbarId = int(request.form['busbar_id'])
        del corrected_component_outlines[int(busbarId)]
        counter = 0
        for i, corrected_component_placement in enumerate(corrected_component_placements):
            if corrected_component_placement['component_type'] == 'busbar':
                if counter == busbarId:
                    del corrected_component_placements[i]
                    break
                counter += 1
        del sbar_checkboxes_height[sbars[int(busbarId)]]
        del sbars[int(busbarId)]
    elif IdNr == "2":
        busbarId = int(request.form['busbar_id']) + len(sbars)
        del corrected_component_outlines[int(busbarId)]
        counter = 0
        for i, corrected_component_placement in enumerate(corrected_component_placements):
            if corrected_component_placement['component_type'] == 'busbar':
                if counter == busbarId:
                    del corrected_component_placements[i]
                    break
                counter += 1
        del sbar_checkboxes_height[front_end_sbar_data[int(busbarId) - len(sbars)][0]]
        del front_end_sbar_data[int(busbarId) - len(sbars)]
    elif IdNr == "3":
        busbarId = int(request.form['busbar_id']) + len(sbars) + session.get('Index_dyn_busbar', 0)
        del corrected_component_outlines[int(busbarId)]
        counter = 0
        for i, corrected_component_placement in enumerate(corrected_component_placements):
            if corrected_component_placement['component_type'] == 'busbar':
                if counter == busbarId:
                    del corrected_component_placements[i]
                    break
                counter += 1
        del sbar_checkboxes_height[front_end_sbar_data[int(busbarId) - len(sbars)][0]]
        del front_end_sbar_data[int(busbarId) - len(sbars)]

    session['corrected_component_placements'] = corrected_component_placements
    session['corrected_component_outlines'] = corrected_component_outlines
    print('remove_busbar')
    return render_template('manipulate.html', manipulate_after_submit_parameters = True, new_sbar_data_length = len(front_end_sbar_data), front_end_sbar_data=front_end_sbar_data, strings=strings, graph_json=graph_json, sbars=sbars, filename=filename, new_string_names=new_string_names, sbar_checkboxes_180deg=sbar_checkboxes_180deg, sbar_checkboxes_height=sbar_checkboxes_height, fig_dir=fig_dir,corrected_component_placements= corrected_component_placements, corrected_component_outlines=corrected_component_outlines)

@app.route('/preview_src')
def preview_src():
    file_content = session.get('file_content', 'No file content found')
    new_file_content = session.get('new_file_content', 'No new file content found')
    fig_dir = url_for('static', filename='img/Soltech_logo.png')

    return render_template('observe.html', section='preview', file_content=file_content, new_file_content=new_file_content, fig_dir=fig_dir)

@app.route('/visualize_src')
def visualize_src():
    graph_json2 = session.get('graph_json2', None)
    graph_json = session.get('graph_json', None)
    fig_dir = url_for('static', filename='img/Soltech_logo.png')
    return render_template('observe.html', section='visualize', graph_json=graph_json, graph_json2=graph_json2, fig_dir=fig_dir)

@app.route('/about_src')
def about():
    fig_dir = url_for('static', filename='img/Soltech_logo.png')
    return render_template('about.html', fig_dir=fig_dir)


@app.errorhandler(413)
def request_entity_too_large(error):
    flash('File is too large')
    return redirect(request.url)

if __name__ == '__main__':
    app.run(port=5000, debug=True)