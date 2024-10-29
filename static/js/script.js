function removeBusbar(busbarId, IdNr, sbar) {
    console.log('Removing busbar:', sbar);

    // Create a form data object
    const form = document.querySelector('form');
    const formData = new FormData(form);
    formData.append('busbar_id', busbarId);
    formData.append('IdNr', IdNr);
    

    // Function to handle the removal of the busbar
    function executeRemoveBusbar(updatedIdNr) {
        console.log('Executing remove busbar with updated IdNr:', updatedIdNr);
        formData.set('IdNr', updatedIdNr); // Update IdNr in formData
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

    // First fetch /submit_parameters
    fetch('/submit_parameters', {
        method: 'POST',
        body: formData
    }).then(response => {
        if (response.ok) {
            console.log('Parameters submitted successfully');
            // If IdNr is 3, change it to 2 before removing the busbar
            const updatedIdNr = IdNr;
            executeRemoveBusbar(updatedIdNr);
        } else {
            console.error('Failed to submit parameters');
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
            input.value = parseFloat(input.value).toFixed(1);
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


    // Add event listener to dynamically added rows
    document.getElementById('add-row-btn').addEventListener('click', function() {
        const existingRows = document.getElementById('existing-rows').children.length;
        console.log(existingRows);

        const newRow = document.createElement('div');
        newRow.className = 'row mb-2';
        newRow.innerHTML = `
            <div class="col">
                <button type="button" class="btn btn-danger" onclick="removeBusbar(${existingRows}, 3)">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash3" viewBox="0 0 16 16">
                        <path d="M6.5 1h3a.5.5 0 0 1 .5.5v1H6v-1a.5.5 0 0 1 .5-.5M11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3A1.5 1.5 0 0 0 5 1.5v1H1.5a.5.5 0 0 0 0 1h.538l.853 10.66A2 2 0 0 0 4.885 16h6.23a2 2 0 0 0 1.994-1.84l.853-10.66h.538a.5.5 0 0 0 0-1zm1.958 1-.846 10.58a1 1 0 0 1-.997.92h-6.23a1 1 0 0 1-.997-.92L3.042 3.5zm-7.487 1a.5.5 0 0 1 .528.47l.5 8.5a.5.5 0 0 1-.998.06L5 5.03a.5.5 0 0 1 .47-.53Zm5.058 0a.5.5 0 0 1 .47.53l-.5 8.5a.5.5 0 1 1-.998-.06l.5-8.5a.5.5 0 0 1 .528-.47M8 4.5a.5.5 0 0 1 .5.5v8.5a.5.5 0 0 1-1 0V5a.5.5 0 0 1 .5-.5"/>
                    </svg>
                </button>
            </div>
            <div class="col">
                <input type="text" style="width: 200px;" class="form-control" name="new_sbar_name_dyn" placeholder="Enter name">
            </div>
            <div class="col">
                <input type="checkbox" name="new_sbar180deg_dyn_${existingRows}">
            </div>
            <div class="col">
                <input type="checkbox" name="new_sbarheight_dyn_${existingRows}">
            </div>
            <div class="col">
                <input type="number" class="form-control" name="new_placement_x_dyn" placeholder="Enter x" step="any">
            </div>
            <div class="col">
                <input type="number" class="form-control" name="new_placement_y_dyn" placeholder="Enter y" step="any">
            </div>
            <div class="col">
                <input type="number" class="form-control" name="new_placement_z_dyn" placeholder="Enter z" step="any">
            </div>
            <div class="col">
                <input type="number" class="form-control" name="new_outline_length_dyn" placeholder="Enter width" step="any">
            </div>
            <div class="col">
                <input type="number" class="form-control" name="new_outline_width_dyn" placeholder="Enter height" step="any">
            </div>
        `;
        document.getElementById('existing-rows').appendChild(newRow);

        // Add event listener to the new input fields
        addEnterKeyPrevention();
        addFloatConversion();
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