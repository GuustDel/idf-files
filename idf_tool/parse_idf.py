import numpy as np
import os
import plotly.graph_objects as go
from flask import send_file

def board_outline(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
        in_board_outline_section = False
        coordinates = []

        for line in lines:
            if '.BOARD_OUTLINE' in line:
                in_board_outline_section = True
                continue
            if '.END_BOARD_OUTLINE' in line:
                in_board_outline_section = False
                break
            if in_board_outline_section:
                parts = line.split()
                if len(parts) == 4:
                    coordinates.append((float(parts[1]), float(parts[2]), float(parts[3])))
        board_outline = np.array(coordinates)
        return board_outline
    
def component_placements(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
        component_placements = {}
        in_placement_section = False

        for line in lines:
            if '.PLACEMENT' in line:
                in_placement_section = True
                continue
            if '.END_PLACEMENT' in line:
                in_placement_section = False
                break
            if in_placement_section:
                if line.startswith('"'):
                    parts = line.split('"')
                    name = parts[1].strip()
                    component_type = parts[3].strip()
                    component_id = parts[-1].strip()
                    current_component = {'name': name, 'component_type': component_type, 'placement': []}
                    component_placements[component_id] = current_component
                else:
                    parts = line.split()
                    if len(parts) == 6:
                        x, y, z, rotation = map(float, parts[:4])
                        current_component['placement'] = [x, y, z, rotation]

        return component_placements

def component_outlines(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
        component_outlines = {}
        current_component = None
        in_mechanical_section = False

        for line in lines:
            if '.MECHANICAL' in line:
                in_mechanical_section = True
                continue
            if in_mechanical_section:
                parts = line.split('"')
                name = parts[1].strip()
                component_type = parts[3].strip()
                height = parts[-1].strip().split()[-1]
                current_component = {name: {'component_type': component_type, 'height': height, 'coordinates': []}}
                component_outlines.update(current_component)
                in_mechanical_section = False
                continue
            if '.END_MECHANICAL' in line:
                current_component = None
                continue
            if current_component:
                parts = line.split()
                if len(parts) == 4:
                    component_name = list(current_component.keys())[0]
                    component_outlines[component_name]['coordinates'].append([float(parts[1]), float(parts[2]), float(parts[3])])

        return component_outlines
    
def get_component_names_by_type(component_outlines):
    sbars = []
    strings = []
    
    for name, details in component_outlines.items():
        if details['component_type'] == 'busbar':
            sbars.append(name)
        elif details['component_type'] == 'string':
            strings.append(name)
    
    return sbars, strings
    
def draw_board(board_outline, component_outlines, component_placements):
    fig = go.Figure()

    # Add board outline
    x, y, z = board_outline.T
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name='Board Outline'))

    # Add component outlines and placements
    for component_id, component_placement in component_placements.items():
        component_outline = component_outlines[component_placement['name']]
        
        angle = component_placement['placement'][3]
        cos_angle = np.cos(angle * np.pi / 180)
        sin_angle = np.sin(angle * np.pi / 180)
        
        rotated_coordinates = []
        for point in component_outline['coordinates']:
            x, y, z = point
            x_rot = x * cos_angle - y * sin_angle
            y_rot = x * sin_angle + y * cos_angle
            rotated_coordinates.append([x_rot, y_rot, z])

        x_outline, y_outline, z_outline = np.array(rotated_coordinates).T
        x_offset, y_offset, z_offset = component_placement['placement'][:3]
        if component_outline['component_type'] == 'busbar':
            x_corr = x_outline + x_offset
            y_corr = y_outline + y_offset
            z_corr = z_outline + z_offset
        else:
            x_corr = x_outline + x_offset
            y_corr = y_outline + y_offset
            z_corr = z_outline + z_offset
        fig.add_trace(go.Scatter(x=x_corr, y=y_corr, mode='lines', name=component_placement['name']))

    # Add component placements as scatter points
    for component_id, component_placement in component_placements.items():
        fig.add_trace(go.Scatter(
            x=[component_placement['placement'][0]],
            y=[component_placement['placement'][1]],
            mode='markers',
            marker=dict(color='red', size=5),
            showlegend=False  
        ))

    # Update layout
    fig.update_layout(
        xaxis_title='X',
        yaxis_title='Y',
        xaxis=dict(
            side='top',
            scaleratio=1
        ),
        yaxis=dict(
            side='right',
            scaleratio=1
        ),
        legend=dict(x=1.5, y=1),
        dragmode='pan'
    )

    return fig

def translate(corrected_component_placements, corrected_component_outlines, sbar_checkboxes_180deg_history, form_data):
    for _, placement in corrected_component_placements.items():
        name = placement['name']
        if placement['component_type'] == 'busbar':
            if (len(sbar_checkboxes_180deg_history[name]) >= 2 and sbar_checkboxes_180deg_history[name][-1] == sbar_checkboxes_180deg_history[name][-2]) or (len(sbar_checkboxes_180deg_history[name]) == 1 and sbar_checkboxes_180deg_history[name][-1] == False):
                placement['placement'][0] = float(form_data.get(f'placement_{name}_0', placement['placement'][0]))
                placement['placement'][1] = float(form_data.get(f'placement_{name}_1', placement['placement'][1]))
                placement['placement'][2] = float(form_data.get(f'placement_{name}_2', placement['placement'][2]))

    for name, outline in corrected_component_outlines.items():
        if outline['component_type'] == 'busbar':
            if (len(sbar_checkboxes_180deg_history[name]) >= 2 and sbar_checkboxes_180deg_history[name][-1] == sbar_checkboxes_180deg_history[name][-2]) or (len(sbar_checkboxes_180deg_history[name]) == 1 and sbar_checkboxes_180deg_history[name][-1] == False):
                outline['coordinates'][2][0] = float(form_data.get(f'outline_{name}_0', outline['coordinates'][2][0]))
                outline['coordinates'][1][0] = float(form_data.get(f'outline_{name}_0', outline['coordinates'][2][0]))
                outline['coordinates'][2][1] = float(form_data.get(f'outline_{name}_1', outline['coordinates'][2][1]))
                outline['coordinates'][3][1] = float(form_data.get(f'outline_{name}_1', outline['coordinates'][2][1]))
    return

def rotate(corrected_component_placements, corrected_component_outlines, sbar_checkboxes_180deg_history, sbar_checkboxes_180deg):
    for id, component_placement in corrected_component_placements.items():
        if component_placement['component_type'] == 'busbar':
            for sbar, _ in sbar_checkboxes_180deg.items():
                if sbar == component_placement['name']:
                    outline = corrected_component_outlines[corrected_component_placements[id]['name']]['coordinates']
                    component_long_side = np.max(outline)
                    component_short_side = 5
                    if ((len(sbar_checkboxes_180deg_history[sbar]) >= 2) and (sbar_checkboxes_180deg_history[sbar][-2] == False) and (sbar_checkboxes_180deg_history[sbar][-1] == True)) or ((len(sbar_checkboxes_180deg_history[sbar]) == 1) and (sbar_checkboxes_180deg_history[sbar][-1] == True)):
                        if corrected_component_placements[id]['placement'][3] == 0:
                            corrected_component_placements[id]['placement'][0] += component_long_side
                            corrected_component_placements[id]['placement'][1] += component_short_side
                        elif corrected_component_placements[id]['placement'][3] == 90:
                            corrected_component_placements[id]['placement'][0] -= component_short_side
                            corrected_component_placements[id]['placement'][1] += component_long_side
                        elif corrected_component_placements[id]['placement'][3] == 180:
                            corrected_component_placements[id]['placement'][0] -= component_long_side
                            corrected_component_placements[id]['placement'][1] -= component_short_side
                        elif corrected_component_placements[id]['placement'][3] == 270 or corrected_component_placements[id]['placement'][3] == -90:
                            corrected_component_placements[id]['placement'][0] += component_short_side
                            corrected_component_placements[id]['placement'][1] -= component_long_side
                        corrected_component_placements[id]['placement'][3] = (corrected_component_placements[id]['placement'][3] + 180) % 360
                    elif (len(sbar_checkboxes_180deg_history[sbar]) >= 2) and (sbar_checkboxes_180deg_history[sbar][-2] == True) and (sbar_checkboxes_180deg_history[sbar][-1] == False):
                        if corrected_component_placements[id]['placement'][3] == 180:
                            corrected_component_placements[id]['placement'][0] -= component_long_side
                            corrected_component_placements[id]['placement'][1] -= component_short_side
                        elif corrected_component_placements[id]['placement'][3] == 270 or corrected_component_placements[id]['placement'][3] == -90:
                            corrected_component_placements[id]['placement'][0] += component_short_side
                            corrected_component_placements[id]['placement'][1] -= component_long_side
                        elif corrected_component_placements[id]['placement'][3] == 0:
                            corrected_component_placements[id]['placement'][0] += component_long_side
                            corrected_component_placements[id]['placement'][1] += component_short_side
                        elif corrected_component_placements[id]['placement'][3] == 90:
                            corrected_component_placements[id]['placement'][0] -= component_short_side
                            corrected_component_placements[id]['placement'][1] += component_long_side
                        corrected_component_placements[id]['placement'][3] = (corrected_component_placements[id]['placement'][3] - 180) % 360
    return

def regenerate_idf_file_content(file_path, corrected_component_outlines, corrected_component_placements):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    new_lines = ''
    for i in range(len(lines)):
        if i < 12:
            new_lines += f'{lines[i]}'
        
    new_lines += '.PLACEMENT' + '\n'
    for component_id, component_placement in corrected_component_placements.items():
        new_lines += f'"{component_placement["name"]}" "{component_placement["component_type"]}" {component_id}\n'
        new_lines += f'{component_placement["placement"][0]} {component_placement["placement"][1]} {component_placement["placement"][2]} {component_placement["placement"][3]} TOP PLACED\n'
    new_lines += '.END_PLACEMENT' + '\n'
    
    for component_id, corrected_component_outline in corrected_component_outlines.items():
        new_lines += '.MECHANICAL' + '\n'
        new_lines += f'"{component_id}" "{corrected_component_outline["component_type"]}" MM {corrected_component_outline["height"]}\n'
        for coordinate in corrected_component_outline['coordinates']:
            new_lines += f'0 {coordinate[0]} {coordinate[1]} {coordinate[2]}\n'
        new_lines += '.END_MECHANICAL' + '\n'
    
    return new_lines

import numpy as np

def add_busbars(form_data, corrected_component_outlines, corrected_component_placements, sbar_checkboxes_180deg, sbar_checkboxes_height, sbars):
    # Initialize sbar_checkboxes
    for sbar in form_data.getlist('sbars'):
        sbar_checkboxes_180deg[sbar] = bool(form_data.get(f'sbar180deg_{sbar}'))
        sbar_checkboxes_height[sbar] = bool(form_data.get(f'sbarheight_{sbar}'))

    # Data processing
    new_sbar_data = ()
    new_sbar_name = form_data.get('new_sbar_name_dyn')
    new_placement_x = form_data.get('new_placement_x_dyn')
    new_placement_y = form_data.get('new_placement_y_dyn')
    new_placement_z = form_data.get('new_placement_z_dyn')
    new_outline_height = form_data.get('new_outline_length_dyn')
    new_outline_width = form_data.get('new_outline_width_dyn')
    new_sbar_data = (new_sbar_name, False, False, float(new_placement_x), float(new_placement_y), float(new_placement_z), float(new_outline_height), float(new_outline_width))

    sbars.append(new_sbar_name)
    add_busbar(corrected_component_outlines, corrected_component_placements, sbar_checkboxes_180deg, sbar_checkboxes_height, new_sbar_data)

    return

def add_busbar(corrected_component_outlines, corrected_component_placements, sbar_checkboxes_180deg, sbar_checkboxes_height, new_sbar_data):
    new_sbar_name, new_sbar180deg, new_sbarheight, new_placement_x, new_placement_y, new_placement_z, new_outline_height, new_outline_width = new_sbar_data

    outline = [[0.0, 0.0, 0.0], [float(new_outline_height), 0.0, 0.0], [float(new_outline_height), float(new_outline_width), 0.0], [0.0, float(new_outline_width), 0.0], [0.0, 0.0, 0.0]]
    placement = [float(new_placement_x), float(new_placement_y), float(new_placement_z), 0.0]

    id = len([placement for placement in corrected_component_placements.values() if placement['component_type'] == 'busbar'])
    corrected_component_outlines[new_sbar_name] = {'component_type': 'busbar', 'height': new_sbarheight, 'coordinates': outline}
    corrected_component_placements[f"BB{id:03}"] = {'name': new_sbar_name, 'component_type': 'busbar', 'placement': placement}
    sbar_checkboxes_180deg[new_sbar_name] = new_sbar180deg
    sbar_checkboxes_height[new_sbar_name] = new_sbarheight

def change_string_names(corrected_component_placements, corrected_component_outlines, new_string_names, strings):
    for string_name, new_string_name in new_string_names.items():
        if new_string_name != '':
            for _, corrected_component_placement in corrected_component_placements.items():
                if corrected_component_placement['name'] == string_name:
                    corrected_component_placement['name'] = new_string_name
                    if string_name in corrected_component_outlines:
                        corrected_component_outlines[new_string_name] = corrected_component_outlines.pop(string_name)
                    if string_name in strings:
                        strings[strings.index(string_name)] = new_string_name
                    break
    return

def change_sbar_height(corrected_component_outlines, sbar_checkboxes_height):
    for sbar, height in sbar_checkboxes_height.items():
        if height:
            corrected_component_outlines[sbar]['height'] = str(float(corrected_component_outlines[sbar]['height']) + 2.0)
    return

def export(file_path, output_file_path, new_lines):
    filename = file_path.split('/')[-1].split('.')[0]
    with open(output_file_path, 'w') as outfile:
            outfile.write(new_lines)
    return send_file(output_file_path, as_attachment=True, download_name=f'{filename}_output.IDF')