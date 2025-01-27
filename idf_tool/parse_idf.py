import numpy as np
import os
import plotly.graph_objects as go
from collections import Counter
import re

def most_common_value(lst):
    if not lst:
        return None  # Handle empty list case
    
    # Filter out 0 values
    filtered_lst = [value for value in lst if value != 0]
    
    if not filtered_lst:
        return None  # Handle case where all values were 0
    
    counter = Counter(filtered_lst)
    most_common = counter.most_common(1)[0][0]  # Get the most common value
    return most_common

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
                current_component = {name: {'component_type': component_type, 'height': height, 'coordinates': [], "widthheight": []}}
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
    for name, outline in component_outlines.items():
        outline['widthheight'].append([outline['coordinates'][0][0], most_common_value([coordinate[1] for coordinate in outline['coordinates']])])
        print(name, outline['widthheight'])
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
        fig.add_trace(go.Scatter(x=x_corr, y=y_corr, mode='lines', name=f"{component_id} {component_placement['name']}"))

    # Add component placements as scatter points
    for component_id, component_placement in component_placements.items():
        fig.add_trace(go.Scatter(
            x=[component_placement['placement'][0]],
            y=[component_placement['placement'][1]],
            mode='markers',
            marker=dict(color='red', size=4),
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

def translate(corrected_component_placements, corrected_component_outlines, w_sbar_prev, w_string_prev, form_data, widthheight_prev):
    for id, placement in corrected_component_placements.items():
        if placement['component_type'] == 'busbar':
            if w_sbar_prev[placement["name"]][-1] == w_sbar_prev[placement["name"]][-2]:
                placement['placement'][0] = float(form_data.get(f'placement_{id}_0', placement['placement'][0]))
                placement['placement'][1] = float(form_data.get(f'placement_{id}_1', placement['placement'][1]))
                placement['placement'][2] = float(form_data.get(f'placement_{id}_2', placement['placement'][2]))
        elif placement['component_type'] == 'string':
            if w_string_prev[id][-1] == w_string_prev[id][-2] or len(w_string_prev[id]) == 1:
                placement['placement'][0] = float(form_data.get(f'placement_{id}_0', placement['placement'][0]))
                placement['placement'][1] = float(form_data.get(f'placement_{id}_1', placement['placement'][1]))
                placement['placement'][2] = float(form_data.get(f'placement_{id}_2', placement['placement'][2]))

    for name, outline in corrected_component_outlines.items():
        if outline['component_type'] == 'busbar':
            if w_sbar_prev[name][-1] == w_sbar_prev[name][-2]:
                outline['coordinates'][2][0] = float(form_data.get(f'outline_{name}_0', outline['coordinates'][2][0]))
                outline['coordinates'][1][0] = float(form_data.get(f'outline_{name}_0', outline['coordinates'][2][0]))
                outline['coordinates'][2][1] = float(form_data.get(f'outline_{name}_1', outline['coordinates'][2][1]))
                outline['coordinates'][3][1] = float(form_data.get(f'outline_{name}_1', outline['coordinates'][2][1]))
        elif outline['component_type'] == 'string':
            for id, _ in w_string_prev.items():
                if corrected_component_placements[id]['name'] == name:
                    if w_string_prev[id][-1] == w_string_prev[id][-2] or len(w_string_prev[id]) == 1:
                        if len(widthheight_prev[name]) == 1:
                            break
                        if widthheight_prev[name][-1] != widthheight_prev[name][-2]:
                            print("Widthheight changed")
                            print(widthheight_prev[name][-1], widthheight_prev[name][-2])
                            outline['coordinates'] = [[0.0, 0.0, 0.0],
                                                    [float(form_data.get(f'outline_{name}_0', outline['coordinates'][1][0])), 0.0, 0.0],
                                                    [float(form_data.get(f'outline_{name}_0', outline['coordinates'][1][0])), float(form_data.get(f'outline_{name}_1', outline['coordinates'][2][1])), 0.0],
                                                    [0.0, float(form_data.get(f'outline_{name}_1', outline['coordinates'][2][1])), 0.0],
                                                    [0.0, 0.0, 0.0]]
                            outline['widthheight'] = [[float(form_data.get(f'outline_{name}_0', outline['coordinates'][1][0])), float(form_data.get(f'outline_{name}_1', outline['coordinates'][2][1]))]]
    return

def rotate0to180(id, corrected_component_placements, corrected_component_outlines):
    outline = corrected_component_outlines[corrected_component_placements[id]['name']]['coordinates']
    if corrected_component_placements[id]['component_type'] == "string":
        component_long_side = corrected_component_outlines[corrected_component_placements[id]['name']]['widthheight'][0][0]
        component_short_side = corrected_component_outlines[corrected_component_placements[id]['name']]['widthheight'][0][1]
    else:
        component_long_side = np.max(outline)
        component_short_side = 5
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
    return

def rotate180to0(id, corrected_component_placements, corrected_component_outlines):
    outline = corrected_component_outlines[corrected_component_placements[id]['name']]['coordinates']
    if corrected_component_placements[id]['component_type'] == "string":
        component_long_side = corrected_component_outlines[corrected_component_placements[id]['name']]['widthheight'][0][0]
        component_short_side = corrected_component_outlines[corrected_component_placements[id]['name']]['widthheight'][0][1]
    else:
        component_long_side = np.max(outline)
        component_short_side = 5
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

def rotate_to_zero(corrected_component_placements, corrected_component_outlines, id, prev_angle):
    if prev_angle == 90:
        corrected_component_placements[id]['placement'][3] -= 90
    elif prev_angle == 180:
        rotate180to0(id, corrected_component_placements, corrected_component_outlines)
    elif prev_angle == 270:
        rotate180to0(id, corrected_component_placements, corrected_component_outlines)
        corrected_component_placements[id]['placement'][3] -= 90

def rotate(corrected_component_placements, corrected_component_outlines, w_sbar_prev, w_sbar, w_string_prev, w_string):
    for id, component_placement in corrected_component_placements.items():
        for sbar, _ in w_sbar.items():
            if sbar == component_placement['name']:
                prev_angle = w_sbar_prev[sbar][0]
                current_angle = w_sbar[sbar]
                if prev_angle != current_angle:
                    # Rotate back to 0
                    rotate_to_zero(corrected_component_placements, corrected_component_outlines, id, prev_angle)
                    
                    # Rotate to the current angle
                    if current_angle == 90:
                        corrected_component_placements[id]['placement'][3] += 90
                    elif current_angle == 180:
                        rotate0to180(id, corrected_component_placements, corrected_component_outlines)
                    elif current_angle == 270:
                        corrected_component_placements[id]['placement'][3] += 90
                        rotate0to180(id, corrected_component_placements, corrected_component_outlines)
    for id, _ in w_string.items():
        prev_angle = w_string_prev[id][0]
        current_angle = w_string[id]
        if prev_angle != current_angle:
            # Rotate back to 0
            rotate_to_zero(corrected_component_placements, corrected_component_outlines, id, prev_angle)
            
            # Rotate to the current angle
            if current_angle == 90:
                corrected_component_placements[id]['placement'][3] += 90
            elif current_angle == 180:
                rotate0to180(id, corrected_component_placements, corrected_component_outlines)
            elif current_angle == 270:
                corrected_component_placements[id]['placement'][3] += 90
                rotate0to180(id, corrected_component_placements, corrected_component_outlines)
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
        if component_placement['component_type'] == 'string':
            new_lines += f'"{component_placement["name"]}" "{component_placement["component_type"]}" {component_id}\n'
            new_lines += f'{component_placement["placement"][0]} {component_placement["placement"][1]} {component_placement["placement"][2]} {component_placement["placement"][3]} TOP PLACED\n'
    for component_id, component_placement in corrected_component_placements.items():
        if component_placement['component_type'] == 'busbar':
            new_lines += f'"{component_placement["name"]}" "{component_placement["component_type"]}" {component_id}\n'
            new_lines += f'{component_placement["placement"][0]} {component_placement["placement"][1]} {component_placement["placement"][2]} {component_placement["placement"][3]} TOP PLACED\n'
    new_lines += '.END_PLACEMENT' + '\n'
    
    for component_id, corrected_component_outline in corrected_component_outlines.items():
        if corrected_component_outline['component_type'] == 'busbar':
            new_lines += '.MECHANICAL' + '\n'
            new_lines += f'"{component_id}" "{corrected_component_outline["component_type"]}" MM {corrected_component_outline["height"]}\n'
            for coordinate in corrected_component_outline['coordinates']:
                new_lines += f'0 {coordinate[0]} {coordinate[1]} {coordinate[2]}\n'
            new_lines += '.END_MECHANICAL' + '\n'
    for component_id, corrected_component_outline in corrected_component_outlines.items():
        if corrected_component_outline["component_type"] == "string":
            new_lines += '.MECHANICAL' + '\n'
            new_lines += f'"{component_id}" "{corrected_component_outline["component_type"]}" MM {corrected_component_outline["height"]}\n'
            for coordinate in corrected_component_outline['coordinates']:
                new_lines += f'0 {coordinate[0]} {coordinate[1]} {coordinate[2]}\n'
            new_lines += '.END_MECHANICAL' + '\n'
    return new_lines


import numpy as np

def add_components(form_data, corrected_component_outlines, corrected_component_placements, w_sbar, z_sbar, w_string, sbars, strings):
    # Initialize sbar_checkboxes
    if form_data.get('new_sbar_name_dyn') is not None:
        for sbar in form_data.getlist('sbars'):
            w_sbar[sbar] = float(form_data.get(f'sbar180deg_{sbar}'))
            z_sbar[sbar] = bool(form_data.get(f'sbarheight_{sbar}'))

        # Data processing
        new_sbar_data = ()
        new_sbar_name = form_data.get('new_sbar_name_dyn')
        new_placement_x = form_data.get('new_placement_x_dyn')
        new_placement_y = form_data.get('new_placement_y_dyn')
        new_placement_z = form_data.get('new_placement_z_dyn')
        new_outline_height = form_data.get('new_outline_length_dyn')
        new_outline_width = form_data.get('new_outline_width_dyn')
        new_sbar_data = (new_sbar_name, 0.0, False, float(new_placement_x), float(new_placement_y), float(new_placement_z), float(new_outline_height), float(new_outline_width))
        sbars.append(new_sbar_name)
        add_busbar(corrected_component_outlines, corrected_component_placements, w_sbar, z_sbar, new_sbar_data)

    if form_data.get('new_string_name_dyn') is not None:
        new_string_name = form_data.get('new_string_name_dyn')
        new_placement_x = form_data.get('new_placement_x_dyn')
        new_placement_y = form_data.get('new_placement_y_dyn')
        new_placement_z = form_data.get('new_placement_z_dyn')
        strings.append(new_string_name)
        new_string_data = (0.0, float(new_placement_x), float(new_placement_y), float(new_placement_z), 182.00, 1000.00)
        add_string(corrected_component_outlines, corrected_component_placements, w_string, new_string_data)
    return

def add_busbar(corrected_component_outlines, corrected_component_placements, w_sbar, z_sbar, new_sbar_data):
    new_sbar_name, new_sbar180deg, new_sbarheight, new_placement_x, new_placement_y, new_placement_z, new_outline_height, new_outline_width = new_sbar_data
    outline = [[0.0, 0.0, 0.0], [float(new_outline_height), 0.0, 0.0], [float(new_outline_height), float(new_outline_width), 0.0], [0.0, float(new_outline_width), 0.0], [0.0, 0.0, 0.0]]
    placement = [float(new_placement_x), float(new_placement_y), float(new_placement_z), 0.0]

    bb_keys = [key for key in corrected_component_placements.keys() if key.startswith('BB')]

    if bb_keys:
        max_index = max(int(key[2:]) for key in bb_keys)
    else:
        max_index = 0
    
    new_index = max_index + 1
    new_id = f'BB{new_index:03}'

    corrected_component_outlines[new_sbar_name] = {'component_type': 'busbar', 'height': new_sbarheight, 'coordinates': outline}
    corrected_component_placements[new_id] = {'name': new_sbar_name, 'component_type': 'busbar', 'placement': placement}
    w_sbar[new_sbar_name] = new_sbar180deg
    z_sbar[new_sbar_name] = new_sbarheight

def add_string(corrected_component_outlines, corrected_component_placements, w_string, new_string_data):
    print("Adding string")
    new_string180deg, new_placement_x, new_placement_y, new_placement_z, new_outline_height, new_outline_width = new_string_data
    outline = [[0.0, 0.0, 0.0], [float(new_outline_height), 0.0, 0.0], [float(new_outline_height), float(new_outline_width), 0.0], [0.0, float(new_outline_width), 0.0], [0.0, 0.0, 0.0]]
    placement = [float(new_placement_x), float(new_placement_y), float(new_placement_z), 0.0]

    str_keys = [key for key in corrected_component_placements.keys() if re.match(r'STR\d{3}', key)]
    
    if not str_keys:
        next_str_key = 'STR000'
    else:
        max_num = max(int(key[3:]) for key in str_keys)
        next_num = max_num + 1
        next_str_key = f'STR{next_num:03}'

    corrected_component_outlines["temp"] = {'component_type': 'string', 'height': 1.0, 'coordinates': outline, 'widthheight': [[float(new_outline_height), float(new_outline_width)]]}
    corrected_component_placements[next_str_key] = {'name': "temp", 'component_type': 'string', 'placement': placement}
    w_string[next_str_key] = new_string180deg

def change_string_names(corrected_component_placements, corrected_component_outlines, new_string_names, strings):
    for string_name, new_string_name in new_string_names.items():
        ids = []
        if new_string_name != '':
            for id, placement in corrected_component_placements.items():
                if placement['name'] == string_name:
                    ids.append(id)
            print(ids)
            for id in ids:
                corrected_component_placements[id]['name'] = new_string_name
            if string_name in corrected_component_outlines:
                corrected_component_outlines[new_string_name] = corrected_component_outlines.pop(string_name)
            if string_name in strings:
                strings[strings.index(string_name)] = new_string_name
    return

def change_sbar_height(corrected_component_outlines, z_sbar):
    for sbar, height in z_sbar.items():
        if height:
            corrected_component_outlines[sbar]['height'] = "2.3"
        else:
            corrected_component_outlines[sbar]['height'] = "0.3"
    return

def export(filename, output_file_path, new_lines):
    with open(output_file_path, 'w') as outfile:
            outfile.write(new_lines)