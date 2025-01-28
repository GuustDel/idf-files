function removeBusbar(sbar) {
    console.log('Removing busbar:', sbar);
    
    // Create a form data object
    const form = document.querySelector('form');
    const formData = new FormData(form);
    formData.append('sbar', sbar);

    // Function to handle the removal of the busbar
    fetch('/remove_busbar', {
        method: 'POST',
        body: formData
    }).then(response => {
        if (response.ok) {
            // Handle successful removal, e.g., reload the page or update the UI
            location.reload();
        } else {
            // Handle errors
            console.error('Failed to remove busbar');
        }
    }).catch(error => {
        console.error('Error:', error);
    });
}

function removeString(id) {
    console.log('Removing string:', id);
    
    // Create a form data object
    const form = document.querySelector('form');
    const formData = new FormData(form);
    formData.append('string', id);

    // Function to handle the removal of the busbar
    fetch('/remove_string', {
        method: 'POST',
        body: formData
    }).then(response => {
        if (response.ok) {
            // Handle successful removal, e.g., reload the page or update the UI
            location.reload();
        } else {
            // Handle errors
            console.error('Failed to remove string');
        }
    }).catch(error => {
        console.error('Error:', error);
    });
}

document.addEventListener('DOMContentLoaded', function() {            
    // Function to prevent form submission on Enter key press in input fields
    function preventEnterKeySubmission(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
        }
    }
    
    function convertToFloat(input) {
        if (!isNaN(parseFloat(input.value))) {
            input.value = parseFloat(input.value).toFixed(2);
        }
    }

    // Function to add event listener to all relevant input fields
    function addEnterKeyPrevention() {
        document.querySelectorAll('input[type="text"], input[type="checkbox"], input[type="number"]').forEach(input => {
            input.removeEventListener('keydown', preventEnterKeySubmission); // Remove existing listener to avoid duplicates
            input.addEventListener('keydown', preventEnterKeySubmission);
        });
    }

    function addFloatConversion() {
        document.querySelectorAll('input[type="number"]').forEach(input => {
            input.addEventListener('blur', function() {
                convertToFloat(input);
            });
        });
    }

    // Initial call to add event listener to all existing input fields
    addEnterKeyPrevention();
    addFloatConversion();

    function addNewRow2(busbarName, id) {
        console.log("adding busbar", busbarName);
        const newRow = document.createElement('div');
        newRow.className = 'row mb-2';
        newRow.innerHTML = `
            <div class="col">
                <button type="button" class="btn btn-danger" onclick="removeBusbar('${busbarName}')">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash3" viewBox="0 0 16 16">
                        <path d="M6.5 1h3a.5.5 0 0 1 .5.5v1H6v-1a.5.5 0 0 1 .5-.5M11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3A1.5 1.5 0 0 0 5 1.5v1H1.5a.5.5 0 0 0 0 1h.538l.853 10.66A2 2 0 0 0 4.885 16h6.23a2 2 0 0 0 1.994-1.84l.853-10.66h.538a.5.5 0 0 0 0-1zm1.958 1-.846 10.58a1 1 0 0 1-.997.92h-6.23a1 1 0 0 1-.997-.92L3.042 3.5zm-7.487 1a.5.5 0 0 1 .528.47l.5 8.5a.5.5 0 0 1-.998.06L5 5.03a.5.5 0 0 1 .47-.53Zm5.058 0a.5.5 0 0 1 .47.53l-.5 8.5a.5.5 0 1 1-.998-.06l.5-8.5a.5.5 0 0 1 .528-.47M8 4.5a.5.5 0 0 1 .5.5v8.5a.5.5 0 0 1-1 0V5a.5.5 0 0 1 .5-.5"/>
                    </svg>
                </button>
            </div>
            <div class="col">
                <label name="new_sbar_name_dyn" value="${id}">${id}:</label>
            </div>
            <div class="col">
                <select id="new_sbar180deg_${busbarName}" name="sbar180deg_${busbarName}">
                    <option value="0" {% if w_sbar[${busbarName}] == 0 %}selected{% endif %}>0</option>
                    <option value="90" {% if w_sbar[${busbarName}] == 90 %}selected{% endif %}>90</option>
                    <option value="180" {% if w_sbar[${busbarName}] == 180 %}selected{% endif %}>180</option>
                    <option value="270" {% if w_sbar[${busbarName}] == 270 %}selected{% endif %}>270</option>
                </select>
            </div>
            <div class="col">
                <input type="checkbox" name="new_sbarheight_dyn" value="false">
            </div>
            <div class="col">
                <input type="number" class="form-control" name="new_placement_x_dyn" placeholder="Enter x" value="0.0" step="any">
            </div>
            <div class="col">
                <input type="number" class="form-control" name="new_placement_y_dyn" placeholder="Enter y" value="0.0" step="any">
            </div>
            <div class="col">
                <input type="number" class="form-control" name="new_placement_z_dyn" placeholder="Enter z" value="0.92" step="any">
            </div>
            <div class="col">
                <input type="number" class="form-control" name="new_outline_length_dyn" placeholder="Enter width" value="100.0" step="any">
            </div>
            <div class="col">
                <input type="number" class="form-control" name="new_outline_width_dyn" placeholder="Enter height" value="5.0" step="any">
            </div>
        `;
        document.getElementById('existing-rows2').appendChild(newRow);
    
        // Add event listener to the new input fields
        addEnterKeyPrevention();
        addFloatConversion();
    }

    function addNewRow(id) {
        console.log("adding string", id);
        const newRow = document.createElement('div');
        newRow.className = 'row mb-2';
        newRow.innerHTML = `
            <div class="col">
                <button type="button" class="btn btn-danger" onclick="removeString('${id}')">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash3" viewBox="0 0 16 16">
                        <path d="M6.5 1h3a.5.5 0 0 1 .5.5v1H6v-1a.5.5 0 0 1 .5-.5M11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3A1.5 1.5 0 0 0 5 1.5v1H1.5a.5.5 0 0 0 0 1h.538l.853 10.66A2 2 0 0 0 4.885 16h6.23a2 2 0 0 0 1.994-1.84l.853-10.66h.538a.5.5 0 0 0 0-1zm1.958 1-.846 10.58a1 1 0 0 1-.997.92h-6.23a1 1 0 0 1-.997-.92L3.042 3.5zm-7.487 1a.5.5 0 0 1 .528.47l.5 8.5a.5.5 0 0 1-.998.06L5 5.03a.5.5 0 0 1 .47-.53Zm5.058 0a.5.5 0 0 1 .47.53l-.5 8.5a.5.5 0 1 1-.998-.06l.5-8.5a.5.5 0 0 1 .528-.47M8 4.5a.5.5 0 0 1 .5.5v8.5a.5.5 0 0 1-1 0V5a.5.5 0 0 1 .5-.5"/>
                    </svg>
                </button>
            </div>
                <div class="col">
                    <label name="new_string_name_dyn" style="width: 220px;" value="${id}">${id}:</label>
                </div>
            <div class="col">
                <select class="form-control" style="width: 100px;" id="name_{{ id }}" name="string_${id}">
                    {% for name, outline in corrected_component_outlines.items() %} 
                    {% if outline.component_type == "string" %}
                    <option value="{{ name }}" {% if name == placement.name %}selected{% endif %}></option>
                    {% endif %}
                    {% endfor %}
                </select>
            </div>
            <div class="col">
                <select id="new_string180deg_${id}" name="new_string180deg_${id}">
                    <option value="0" {% if w_string[${id}] == 0 %}selected{% endif %}>0</option>
                    <option value="90" {% if w_string[${id}] == 90 %}selected{% endif %}>90</option>
                    <option value="180" {% if w_string[${id}] == 180 %}selected{% endif %}>180</option>
                    <option value="270" {% if w_string[${id}] == 270 %}selected{% endif %}>270</option>
                </select>
            </div>
            <div class="col">
                <input type="number" class="form-control" style="width: 150px;" name="new_placement_x_dyn" placeholder="Enter x" value="0.0" step="any">
            </div>
            <div class="col">
                <input type="number" class="form-control" style="width: 150px;" name="new_placement_y_dyn" placeholder="Enter y" value="0.0" step="any">
            </div>
            <div class="col">
                <input type="number" class="form-control" style="width: 150px;" name="new_placement_z_dyn" placeholder="Enter z" value="0.92" step="any">
            </div>
        `;
        document.getElementById('existing-rows').appendChild(newRow);
    
        // Add event listener to the new input fields
        addEnterKeyPrevention();
        addFloatConversion();
    }

    function addNewRow3(name) {
        console.log("adding string", name);
        const newRow = document.createElement('div');
        newRow.className = 'row mb-2';
        newRow.innerHTML = `
            <div class="col">
                        <label for="string_${name} style="width: 200px;">${name}:</label>
                    </div>
                    <div class="col">
                        <input type="text" class="form-control" style="width: 150px;" id="string_${name}" name="string_${name}" value="">
                    </div>
                    <div class="col">
                        <select class="form-control" style="width: 150px;"id="cell_type_${name}" name="cell_type_{{ name }}">
                            <option value="M10">M10</option>
                            <option value="M10 HC">M10 HC</option>
                            <option value="G1">G1</option>
                        </select>
                    </div>
                    <div class="col">
                        <input type="number" class="form-control" style="width: 150px;" id="nr_cells_${name}" name="nr_of_cells_${name}" value="">
                    </div>
                    <div class="col">
                        <input type="number" class="form-control" style="width: 150px;" id="dist_${name}" name="dist_${name}" value="">
                    </div>
                    <div class="col">
                        <input type="number" class="form-control" style="width: 150px;" id="plus_${name}" name="plus_${name}" value="">
                    </div>
                    <div class="col">
                        <input type="number" class="form-control" style="width: 150px;" id="minus_${name}" name="minus_${name}" value="">
                    </div>
        `;
        document.getElementById('existing-rows3').appendChild(newRow);
    
        // Add event listener to the new input fields
        addEnterKeyPrevention();
        addFloatConversion();
    }

    function executeSubmitParameters3(name) {
        console.log('Submitting parameters');

        const form = document.querySelector('form');
        const formData = new FormData(form);
        formData.append('new_string_name', name)
        formData.append('cell_type', "M10 HC")
        formData.append('dist', 2);
        formData.append('nr_cells', 5);
        formData.append('plus', 10);
        formData.append('minus', 10);
        console.log(formData);
        fetch('/submit_parameters', {
            method: 'POST',
            body: formData
        }).then(response => {
            if (response.ok) {
                console.log('Parameters submitted successfully');
                location.reload();
            } else {
                // Handle errors
                console.error('Failed to submit parameters');
            }
        }).catch(error => {
            console.error('Error:', error);
        });
    }

    function executeSubmitParameters2(busbarName, id) {
        console.log('Submitting parameters');

        const form = document.querySelector('form');
        const formData = new FormData(form);
        formData.append('new_sbar_name_dyn', busbarName)
        formData.append('new_sbar180deg_dyn', '0');
        formData.append('new_sbarheight_dyn', 'False');
        formData.append('new_id', id);
        console.log(formData);
        fetch('/submit_parameters', {
            method: 'POST',
            body: formData
        }).then(response => {
            if (response.ok) {
                console.log('Parameters submitted successfully');
                location.reload();
            } else {
                // Handle errors
                console.error('Failed to submit parameters');
            }
        }).catch(error => {
            console.error('Error:', error);
        });
    }

    function executeSubmitParameters(id) {
        console.log('Submitting parameters');

        const form = document.querySelector('form');
        const formData = new FormData(form);
        formData.append('new_string_name_dyn', id)
        formData.append('new_string180deg_dyn', '0');

        fetch('/submit_parameters', {
            method: 'POST',
            body: formData
        }).then(response => {
            if (response.ok) {
                console.log('Parameters submitted successfully');
                location.reload();
            } else {
                // Handle errors
                console.error('Failed to submit parameters');
            }
        }).catch(error => {
            console.error('Error:', error);
        });
    }

    // Add event listener to dynamically added rows
    document.getElementById('add-row-btn2').addEventListener('click', function() {
        console.log('Adding new busbar');
        fetch('/generate_busbar_name')
            .then(response => response.json())
            .then(data => {
                const busbarName = data.busbar_name;
                const id = data.id;
                console.log('Generating busbar name:', busbarName);
                console.log('Adding new row');
                addNewRow2(busbarName, id);
                console.log('Executing submit parameters');
                executeSubmitParameters2(busbarName, id);
            })
            .catch(error => console.error('Error:', error));
    });

    document.getElementById('add-row-btn').addEventListener('click', function() {
        console.log('Adding new string');
        fetch('/generate_string_id')
            .then(response => response.json())
            .then(data => {
                const id = data.string_id;
                console.log('Generating string name:', id);
                console.log('Adding new row');
                addNewRow(id);
                console.log('Executing submit parameters');
                executeSubmitParameters(id);
            })
            .catch(error => console.error('Error:', error));
    });

    document.getElementById('add-row-btn3').addEventListener('click', function() {
        console.log('Adding new string');
        fetch('/generate_string_name')
            .then(response => response.json())
            .then(data => {
                const name = data.string_name;
                console.log('Generating string name:', name);
                console.log('Adding new row');
                addNewRow3(name);
                executeSubmitParameters3(name);
            })
            .catch(error => console.error('Error:', error));
    });

    function removeRow(index) {
        const existingRows = document.getElementById('existing-rows');
        if (index >= 0 && index < existingRows.children.length) {
            existingRows.removeChild(existingRows.children[index]);
        }
    }

    document.getElementById('submit-btn').addEventListener('click', function(event) {
        // Create a form data object
        const form = document.querySelector('form');
        const formData = new FormData(form);
        const newRow = document.querySelector('#existing-rows .row:last-child');
        let allValid = true;
        const warningMessage = document.getElementById('warning-message');
        
        if (!newRow) {
            console.log('All fields are valid');
            warningMessage.style.display = 'none';
            fetch('/submit_parameters', {
                method: 'POST',
                body: formData
            }).then(response => {
                if (response.ok) {
                    // Handle successful submission, e.g., redirect to another page or update the UI
                    console.log('Form submitted successfully');
                    // Optionally, you can redirect to another page
                    location.reload();
                } else {
                    // Handle errors
                    console.error('Failed to submit form');
                }
            }).catch(error => {
                console.error('Error:', error);
            });
            event.preventDefault();
        } else {
            const numberInputs = newRow.querySelectorAll('input[type="number"]');
            const textInput = newRow.querySelector('input[type="text"]');
            numberInputs.forEach(input => {
                if (input.value === '' || isNaN(input.value)) {
                    input.style.borderColor = 'red';
                    allValid = false;
                } else {
                    input.style.borderColor = '';
                }
            });
        
            // Check text input
            if (!textInput.value.startsWith('sbar')) {
                textInput.style.borderColor = 'red';
                allValid = false;
            } else {
                textInput.style.borderColor = '';
            }
        
            // Display warning message
            
            if (!allValid) {
                console.log('Please fill in all fields correctly');
                warningMessage.textContent = 'Please fill in all fields correctly. Text input must start with "sbar".';
                warningMessage.style.display = 'block';
            } else {
                console.log('All fields are valid');
                warningMessage.style.display = 'none';
                fetch('/submit_parameters', {
                    method: 'POST',
                    body: formData
                }).then(response => {
                    if (response.ok) {
                        // Handle successful submission, e.g., redirect to another page or update the UI
                        console.log('Form submitted successfully');
                        // Optionally, you can redirect to another page
                        location.reload();
                    } else {
                        // Handle errors
                        console.error('Failed to submit form');
                    }
                }).catch(error => {
                    console.error('Error:', error);
                });
                event.preventDefault();
            }
        }
    });

    // Add event listener to the form submission
    document.querySelector('form').addEventListener('submit', function(event) {
        // Convert numeric input values to floats
        document.querySelectorAll('input[type="number"]').forEach(input => {
            input.value = parseFloat(input.value);
        });
    });
    
    
});