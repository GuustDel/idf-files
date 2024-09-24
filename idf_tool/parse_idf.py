import numpy as np
import os
import plotly.graph_objects as go

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
        component_placements = []
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
                    current_component = {'name': name, 'placement': []}
                    component_placements.append(current_component)
                else:
                    parts = line.split()
                    if len(parts) == 6:
                        x, y, z, rotation = map(float, parts[:4])
                        current_component['placement'] = np.array([x, y, z, rotation])

        return component_placements

def component_outlines(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
        component_outlines = []
        current_component = None
        in_mechanical_section = False

        for line in lines:
            if '.MECHANICAL' in line:
                in_mechanical_section = True
                continue
            if in_mechanical_section:
                parts = line.split('"')
                name = parts[1].strip()
                current_component = {'name': name, 'coordinates': []}
                in_mechanical_section = False
                continue
            if '.END_MECHANICAL' in line:
                if current_component:
                    component_outlines.append(current_component)
                current_component = None
                continue
            if current_component:
                parts = line.split()
                if len(parts) == 4:
                    current_component['coordinates'].append((float(parts[1]), float(parts[2]), float(parts[3])))

        for component_outline in component_outlines:
            component_outline['coordinates'] = np.array(component_outline['coordinates'])

        return component_outlines
    
def draw_board(board_outline, component_outlines, component_placements):
    fig = go.Figure()

    # Add board outline
    x, y, z = board_outline.T
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name='Board Outline'))

    # Add component outlines and placements
    for component_outline in component_outlines:
        for component_placement in component_placements:
            if component_outline['name'] == component_placement['name']:
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
                if 'sbar' in component_outline['name']:
                    x_corr = x_outline + x_offset - component_outline['coordinates'][0, 0]
                    y_corr = y_outline + y_offset - component_outline['coordinates'][0, 1]
                    z_corr = z_outline + z_offset - component_outline['coordinates'][0, 2]
                else:
                    x_corr = x_outline + x_offset
                    y_corr = y_outline + y_offset
                    z_corr = z_outline + z_offset
                fig.add_trace(go.Scatter(x=x_corr, y=y_corr, mode='lines', name=component_outline['name']))

    # Add component placements as scatter points
    for component_placement in component_placements:
        fig.add_trace(go.Scatter(
            x=[component_placement['placement'][0]],
            y=[component_placement['placement'][1]],
            mode='markers',
            marker=dict(color='red', size=5),
            name=component_placement['name'],
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

def corrected_component_outlines(component_outlines, String_names, new_string_names):
    corrected_component_outlines_lib = []
    for component_outline in component_outlines:
        if component_outline['name'] not in String_names:
            name = component_outline['name']
            component_type = 'busbar'
            corrected_component_outline = np.array([component_outline['coordinates'][3, :], 
                                                    component_outline['coordinates'][2, :], 
                                                    component_outline['coordinates'][1, :], 
                                                    component_outline['coordinates'][0, :],
                                                    component_outline['coordinates'][3, :]])
            corrected_component_outline[:, [0,1]] = corrected_component_outline[:, [1,0]]
        else:
            if new_string_names[component_outline['name']] == '': 
                name = component_outline['name']
            else:
                name = new_string_names[component_outline['name']]
            component_type = 'string'
            corrected_component_outline = component_outline['coordinates']
        
    
        corrected_component_outline_lib = {'name': name, 'component_type': component_type, 'coordinates': corrected_component_outline}
        corrected_component_outlines_lib.append(corrected_component_outline_lib)
    return corrected_component_outlines_lib

def corrected_component_placements(component_placements, String_names, new_string_names, sbar_checkboxes_180deg, corrected_component_outlines):
    corrected_component_placements_lib = []
    counter = 0
    for component_placement in component_placements:
        if component_placement['name'] not in String_names:
            name = component_placement['name']
            component_type = 'busbar'
        else:
            if new_string_names[component_placement['name']] == '':
                name = component_placement['name']
            else:
                name = new_string_names[component_placement['name']]
            component_type = 'string'
        if 'sbar' in component_placement['name']:
            for sbar, checked in sbar_checkboxes_180deg.items():
                if sbar == component_placement['name']:
                    if checked:
                        for component in corrected_component_outlines:
                            if component['name'] == component_placement['name']:
                                component_long_side = component['coordinates'][2,0]
                                component_short_side = component['coordinates'][2,1]
                        if component_placement['placement'][3] == 0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] - component_short_side), 
                                round(component_placement['placement'][1] + component_long_side), 
                                component_placement['placement'][2], 
                                -90.0
                            ])
                        elif component_placement['placement'][3] == 90.0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] - component_short_side - component_long_side), 
                                round(component_placement['placement'][1]), 
                                component_placement['placement'][2], 
                                0.0
                            ])
                        elif component_placement['placement'][3] == 180.0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] - component_short_side), 
                                round(component_placement['placement'][1] - component_long_side), 
                                component_placement['placement'][2], 
                                90.0
                            ])
                        elif component_placement['placement'][3] == 270.0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] - component_short_side + component_long_side), 
                                round(component_placement['placement'][1]), 
                                component_placement['placement'][2], 
                                180.0
                            ])
                    else:
                        for component in corrected_component_outlines:
                            if component['name'] == component_placement['name']:
                                component_long_side = component['coordinates'][2,0]
                                component_short_side = component['coordinates'][2,1]
                        if component_placement['placement'][3] == 0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0]), 
                                round(component_placement['placement'][1]), 
                                component_placement['placement'][2], 
                                90.0
                            ])
                        elif component_placement['placement'][3] == 90.0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] - component_short_side), 
                                round(component_placement['placement'][1] + component_short_side), 
                                component_placement['placement'][2], 
                                180.0
                            ])
                        elif component_placement['placement'][3] == 180.0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] - 2*component_short_side), 
                                round(component_placement['placement'][1]), 
                                component_placement['placement'][2], 
                                -90.0
                            ])
                        elif component_placement['placement'][3] == 270.0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] - component_short_side), 
                                round(component_placement['placement'][1] - component_short_side), 
                                component_placement['placement'][2], 
                                0.0
                            ])
        else:
            corrected_placement = component_placement['placement']

        corrected_placement_lib = {'name': name, 'component_type': component_type,'placement': corrected_placement}
        corrected_component_placements_lib.append(corrected_placement_lib)
        counter += 1
    return corrected_component_placements_lib

def corrected_component_placements_new(corrected_component_placements, sbar_checkboxes_180deg, corrected_component_outlines):
    corrected_component_placements_lib = []
    for component_placement in corrected_component_placements:
        if 'sbar' in component_placement['name']:
            for sbar, checked in sbar_checkboxes_180deg.items():
                if sbar == component_placement['name']:
                    if checked:
                        for component in corrected_component_outlines:
                            if component['name'] == component_placement['name']:
                                component_long_side = component['coordinates'][2,0]
                                component_short_side = component['coordinates'][2,1]
                        if component_placement['placement'][3] == 0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] + component_long_side), 
                                round(component_placement['placement'][1] + component_short_side), 
                                component_placement['placement'][2], 
                                180.0
                            ])
                        elif component_placement['placement'][3] == 90.0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] - component_short_side), 
                                round(component_placement['placement'][1] + component_long_side), 
                                component_placement['placement'][2], 
                                -90.0
                            ])
                        elif component_placement['placement'][3] == 180.0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] - component_long_side), 
                                round(component_placement['placement'][1] - component_short_side), 
                                component_placement['placement'][2], 
                                0.0
                            ])
                        elif component_placement['placement'][3] == 270.0:
                            corrected_placement = np.array([
                                round(component_placement['placement'][0] + component_short_side), 
                                round(component_placement['placement'][1] - component_long_side), 
                                component_placement['placement'][2], 
                                90.0
                            ])
                    else:
                        corrected_placement = component_placement['placement']
        else:
            corrected_placement = component_placement['placement']

        corrected_placement_lib = {'name': component_placement['name'], 'component_type': component_placement['component_type'],'placement': corrected_placement}
        corrected_component_placements_lib.append(corrected_placement_lib)
    return corrected_component_placements_lib

def regenerate_idf(corrected_component_outlines_lib, corrected_component_placements_lib, file_path, sbar_checkboxes_height):
    with open(file_path, 'r') as infile:
        new_lines = ''
        lines = infile.readlines()
        for i in range(len(lines)):
            if i < 12:
                new_lines += f'{lines[i]}'
            
        new_lines += '.PLACEMENT' + '\n'
        counter_bb = 0
        counter_str = 0
        for corrected_component_placement in corrected_component_placements_lib:
            if corrected_component_placement['component_type'] == 'busbar':
                new_lines += f'"{corrected_component_placement["name"]}" "{corrected_component_placement["component_type"]}" BB{counter_bb:03}\n'
                counter_bb += 1
            else:
                new_lines += f'"{corrected_component_placement["name"]}" "{corrected_component_placement["component_type"]}" STR{counter_str:03}\n'
                counter_str += 1
            new_lines += f'{corrected_component_placement["placement"][0]} {corrected_component_placement["placement"][1]} {corrected_component_placement["placement"][2]} {corrected_component_placement["placement"][3]} TOP PLACED\n'
        new_lines += '.END_PLACEMENT' + '\n'
        for corrected_component_outline in corrected_component_outlines_lib:
            new_lines += '.MECHANICAL' + '\n'
            if corrected_component_outline['component_type'] == 'busbar':
                if sbar_checkboxes_height[corrected_component_outline['name']]:
                    busbar_height = 2.3
                else:
                    busbar_height = 0.3
                new_lines += f'"{corrected_component_outline["name"]}" "{corrected_component_outline["component_type"]}" MM {busbar_height}\n'
            else:
                new_lines += f'"{corrected_component_outline["name"]}" "{corrected_component_outline["component_type"]}" MM 1.0\n'
            for coordinate in corrected_component_outline['coordinates']:
                new_lines += f'0 {coordinate[0]} {coordinate[1]} {coordinate[2]}\n'
            new_lines += '.END_MECHANICAL' + '\n'
    export_file_path = os.path.join(os.getcwd(), 'submits')
    output_file_path = os.path.join(export_file_path, os.path.basename(file_path))
    with open(output_file_path, 'w') as outfile:
        outfile.write(new_lines)
    return output_file_path

def regenerate_idf_file_content(corrected_component_outlines_lib, corrected_component_placements_lib, file_content, sbar_checkboxes_height, new_string_names):
    new_lines = ''
    lines = file_content.splitlines()
    for i in range(len(lines)):
        if i < 12:
            new_lines += f'{lines[i]}\n'
        
    new_lines += '.PLACEMENT' + '\n'
    counter_bb = 0
    counter_str = 0
    for corrected_component_placement in corrected_component_placements_lib:
        if corrected_component_placement['component_type'] == 'busbar':
            new_lines += f'"{corrected_component_placement["name"]}" "{corrected_component_placement["component_type"]}" BB{counter_bb:03}\n'
            counter_bb += 1
        else:
            if new_string_names[corrected_component_placement['name']] == '': 
                name = corrected_component_placement['name']
            else:
                name = new_string_names[corrected_component_placement['name']]
            new_lines += f'"{name}" "{corrected_component_placement["component_type"]}" STR{counter_str:03}\n'
            counter_str += 1
        new_lines += f'{corrected_component_placement["placement"][0]} {corrected_component_placement["placement"][1]} {corrected_component_placement["placement"][2]} {corrected_component_placement["placement"][3]} TOP PLACED\n'
    new_lines += '.END_PLACEMENT' + '\n'
    for corrected_component_outline in corrected_component_outlines_lib:
        if corrected_component_outline['component_type'] == 'busbar':
            if sbar_checkboxes_height[corrected_component_outline['name']]:
                busbar_height = 2.3
            else:
                busbar_height = 0.3
            new_lines += '.MECHANICAL' + '\n'
            new_lines += f'"{corrected_component_outline["name"]}" "{corrected_component_outline["component_type"]}" MM {busbar_height}\n'
            for coordinate in corrected_component_outline['coordinates']:
                new_lines += f'0 {coordinate[0]} {coordinate[1]} {coordinate[2]}\n'
            new_lines += '.END_MECHANICAL' + '\n'
    for corrected_component_outline in corrected_component_outlines_lib:
        if corrected_component_outline['component_type'] != 'busbar':
            new_lines += '.MECHANICAL' + '\n'
            if new_string_names[corrected_component_outline['name']] == '': 
                name = corrected_component_outline['name']
            else:
                name = new_string_names[corrected_component_outline['name']]
            new_lines += f'"{name}" "{corrected_component_outline["component_type"]}" MM 1.0\n'
            for coordinate in corrected_component_outline['coordinates']:
                new_lines += f'0 {coordinate[0]} {coordinate[1]} {coordinate[2]}\n'
            new_lines += '.END_MECHANICAL' + '\n'
    return new_lines

def export_idf(component_outlines, component_placements, String_names, filepath, new_string_names, sbar_checkboxes_180deg, sbar_checkboxes_height):
    corrected_component_outlines_lib = corrected_component_outlines(component_outlines, String_names, new_string_names)
    corrected_component_placements_lib = corrected_component_placements(component_placements, String_names, new_string_names, sbar_checkboxes_180deg, corrected_component_outlines_lib)
    output_file_path = regenerate_idf(corrected_component_outlines_lib, corrected_component_placements_lib, filepath, sbar_checkboxes_height)
    return output_file_path

def get_components_starting_with_string(component_placements, prefix="String"):
    strings = [component['name'] for component in component_placements if 'sbar' not in component['name']]
    return strings

def get_unique_strings(strings):
    unique_strings = []
    for string in strings:
        if string not in unique_strings:
            unique_strings.append(string)
    return unique_strings

def get_coordinates(file_path):
    sbars = []
    board_outline_data = board_outline(file_path)
    component_outlines_data = component_outlines(file_path)
    component_placements_data = component_placements(file_path)
    strings = get_components_starting_with_string(component_placements_data, prefix="String")
    unique_strings = get_unique_strings(strings)
    for component_outline in component_outlines_data:
        if 'sbar' in component_outline['name']:
            sbars.append(component_outline['name'])
    return board_outline_data, component_outlines_data, component_placements_data, unique_strings, sbars

def add_busbar(bool, corrected_component_outlines, corrected_component_placements, sbar_checkboxes_180deg, sbar_checkboxes_height, new_sbar_name, new_sbar180deg, new_sbarheight, new_placement_x, new_placement_y, new_placement_z, new_outline_height, new_outline_width):
    outline = np.array([[0.0, 0.0, 0.0], [float(new_outline_width), 0.0, 0.0], [float(new_outline_width), float(new_outline_height), 0.0], [0.0, float(new_outline_height), 0.0], [0.0, 0.0, 0.0]])
    if new_sbar180deg:
        placement = np.array([float(new_placement_x), float(new_placement_y), float(new_placement_z), 180.0])
    else:
        placement = np.array([float(new_placement_x), float(new_placement_y), float(new_placement_z), 0.0])
    
    insert_index = len(corrected_component_outlines)  
    for i, corrected_component_outline in enumerate(corrected_component_outlines):
        if corrected_component_outline['component_type'] == 'string':
            insert_index = i
            break

    if bool:
        corrected_component_outlines.insert(insert_index, {'name': new_sbar_name, 'component_type': 'busbar', 'coordinates': outline})
        corrected_component_placements.append({'name': new_sbar_name, 'component_type': 'busbar', 'placement': placement})
        sbar_checkboxes_180deg[new_sbar_name] = new_sbar180deg
        sbar_checkboxes_height[new_sbar_name] = new_sbarheight
    else:
        sbar_checkboxes_180deg[new_sbar_name] = new_sbar180deg
        sbar_checkboxes_height[new_sbar_name] = new_sbarheight
    return corrected_component_placements, corrected_component_outlines, sbar_checkboxes_180deg, sbar_checkboxes_height


