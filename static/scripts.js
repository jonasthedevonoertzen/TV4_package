// JavaScript to collect selected unit IDs for label assignment
document.addEventListener('DOMContentLoaded', function() {
    var labelForm = document.getElementById('label-form');
    if (labelForm) {
        labelForm.addEventListener('submit', function(event) {
            var selectedUnitIds = [];
            var checkboxes = document.querySelectorAll('input[name="unit_checkbox"]:checked');
            checkboxes.forEach(function(checkbox) {
                selectedUnitIds.push(checkbox.value);
            });
            document.getElementById('selected-unit-ids').value = selectedUnitIds.join(',');
        });
    }
});

function addUnit(button) {
    var actionUrl = button.getAttribute('data-add-url');
    var form = document.createElement('form');
    form.method = 'post';
    form.action = actionUrl;
    var actionInput = document.createElement('input');
    actionInput.type = 'hidden';
    actionInput.name = 'action';
    actionInput.value = 'add';
    form.appendChild(actionInput);
    document.body.appendChild(form);
    form.submit();
}

function useAsTemplate(button) {
    var actionUrl = button.getAttribute('data-template-url');
    var form = document.createElement('form');
    form.method = 'post';
    form.action = actionUrl;
    var actionInput = document.createElement('input');
    actionInput.type = 'hidden';
    actionInput.name = 'action';
    actionInput.value = 'use_as_template';
    form.appendChild(actionInput);
    document.body.appendChild(form);
    form.submit();
}

