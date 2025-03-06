# blueprints/main.py

"""
Main Blueprint.

This module handles the main routes for the application, including
the index page, creating stories, selecting stories, adding and editing units, etc.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, send_file, make_response
from flask_login import login_required, current_user
from werkzeug.datastructures import MultiDict
import json
import os
import tempfile
import warnings

from story_creator.openai_api_call import call_openai


# Import service functions from the story_creator package
from story_creator.database_handler import (
    get_stories_by_user_email,
    create_story,
    get_story_by_id,
    add_unit_to_story,
    get_unit_by_name,
    update_unit,
    get_units_by_story_id,
    update_references_with_new_unit,
    update_story,
    create_label,
    assign_labels_to_units,
    get_labels_by_user,
    get_units_by_labels,
    get_all_units_with_labels,
    get_unit_by_id,
    get_all_labels,
    get_units_by_label_filters,
    delete_unit_from_story
)

# Import necessary unit subclasses
from story_creator.new_models import Unit

main_bp = Blueprint('main', __name__)

def unit_classes_dict_helper():
    """Helper function to get a dictionary of Unit subclasses."""
    return {cls.__name__: cls for cls in Unit.__subclasses__()}


@main_bp.route('/')
def index():
    """Index route: Display user's stories, units, and handle unit labels."""
    if current_user.is_authenticated:
        # Get user stories using the service layer
        user_stories = get_stories_by_user_email(current_user.email)
        selected_story_id = session.get('current_story_id')
        selected_story = None
        if selected_story_id is not None:
            selected_story = get_story_by_id(selected_story_id)
        unit_classes_dict = unit_classes_dict_helper()

        # Get all units with labels
        all_units = get_all_units_with_labels()

        # Get user's labels
        all_labels = get_all_labels()

        # Get selected filter labels from request.args
        selected_label_ids = request.args.getlist('label_ids', type=int)
        exclude_label_ids = request.args.getlist('exclude_label_ids', type=int)
        search_query = request.args.get('search_query', '').strip()

        if selected_label_ids or exclude_label_ids or search_query:
            # Filter units based on selected labels and search query
            filtered_units = get_units_by_label_filters(selected_label_ids, exclude_label_ids, search_query)
        else:
            filtered_units = all_units

        return render_template(
            'index.html',
            stories=user_stories,
            selected_story=selected_story,
            unit_classes_dict=unit_classes_dict,
            units=filtered_units,
            labels=all_labels,
            selected_label_ids=selected_label_ids,
            exclude_label_ids=exclude_label_ids,  # Ensure you pass this to retain the selected excludes
            search_query=search_query
        )
    else:
        return redirect(url_for('auth.login'))

@main_bp.route('/add_existing_unit/<int:unit_id>', methods=['POST'])
@login_required
def add_existing_unit(unit_id):
    """Add an existing unit to the selected story or use it as a template."""
    action = request.form.get('action')
    story_id = session.get('current_story_id')
    if not story_id:
        flash("Please select a story first.")
        return redirect(url_for('main.index'))

    story = get_story_by_id(story_id)
    if story is None or story.user_email != current_user.email:
        abort(403)

    unit = get_unit_by_id(unit_id)
    if unit is None:
        abort(404, description="Unit not found.")

    if action == 'add':
        # Check for duplicate names in the same story
        name = unit.name.strip()
        existing_unit = get_unit_by_name(story_id, name)
        if existing_unit:
            flash(f"ERROR: A unit with the name '{name}' already exists in this story.")
            # errors.append(f"A unit with the name '{name}' already exists in this story.")
            return redirect(url_for('main.index'))

        # Create a new unit with the same features
        new_unit = type(unit)(
            unit_type=unit.unit_type,
            name=unit.name,
            story_id=story_id,
            features=unit.features.copy()
        )
        # Add the new unit to the story with is_copy=True and user_email
        add_unit_to_story(story_id, new_unit, user_email=current_user.email, is_copy=True)
        flash(f"Unit '{unit.name}' has been added to your story.")
        return redirect(url_for('main.index'))
    elif action == 'use_as_template':
        # Store template data in session
        session['template_unit'] = {
            'unit_type': unit.unit_type,
            'features': unit.features
        }
        return redirect(url_for('main.add_unit', story_id=story_id, unit_type=unit.unit_type))
    else:
        flash("Invalid action.")
        return redirect(url_for('main.index'))

@main_bp.route('/assign_labels', methods=['POST'])
@login_required
def assign_labels():
    """Assign labels to selected units."""
    unit_ids_str = request.form.get('unit_ids', '')
    unit_ids = [int(uid) for uid in unit_ids_str.split(',') if uid.isdigit()]
    label_name = request.form.get('label_name', '').strip()

    if not unit_ids:
        flash("No units selected.")
        return redirect(url_for('main.index'))

    if not label_name:
        flash("Please enter a label name.")
        return redirect(url_for('main.index'))

    # Create the label
    label_id = create_label(label_name, current_user.email)

    # Assign the labels to units
    assign_labels_to_units([label_id], unit_ids)

    flash(f"Label '{label_name}' has been assigned to selected units.")
    return redirect(url_for('main.index'))


@main_bp.route('/create_story', methods=['GET', 'POST'])
@login_required
def create_story_route():
    """Route to create a new story."""
    if request.method == 'POST':
        story_name = request.form.get('story_name', '').strip()
        setting_and_style = request.form.get('setting_and_style', '').strip()
        main_challenge = request.form.get('main_challenge', '').strip()

        errors = []

        if not story_name:
            errors.append("Please enter a story name.")
        if not setting_and_style:
            errors.append("Please provide the setting and style of your story.")
        if not main_challenge:
            errors.append("Please describe the main challenge, task, or goal.")

        if errors:
            for error in errors:
                flash(error)
            return render_template('create_story.html')

        # Check for duplicate story name for the user
        user_stories = get_stories_by_user_email(current_user.email)
        if any(s.name == story_name for s in user_stories):
            flash(f"A story with the name '{story_name}' already exists.")
            return render_template('create_story.html')

        # Create the Story using the service layer
        story = create_story(
            name=story_name,
            user_email=current_user.email,
            setting_and_style=setting_and_style,
            main_challenge=main_challenge
        )
        session['current_story_id'] = story.id
        flash(f"Story '{story_name}' has been created.")
        return redirect(url_for('main.index'))

    return render_template('create_story.html')

@main_bp.route('/select_story/<int:story_id>')
@login_required
def select_story(story_id):
    """Route to select a story."""
    story = get_story_by_id(story_id)
    if story is None:
        abort(404, description="Story not found.")
    if story.user_email != current_user.email:
        abort(403)
    session['current_story_id'] = story.id
    flash(f"Story '{story.name}' has been selected.")
    return redirect(url_for('main.index'))


def clean_form_data(form_data, fields):
    for field in fields:
        for name in [field.get('name'), f"{field.get('name')}_new"]:
            if form_data.get(name) not in [None, [], '', ['']]:
                if isinstance(form_data.get(name), list):
                    form_data[name] = form_data.get(name)[0]
                else:
                    form_data[name] = form_data.get(name)
                    warnings.warn(f"Value in form_data not of type list: {name} : {form_data.get(name)}")
            else:
                warnings.warn("When you see this, something is wrong")
                if name.endswith('_new'):
                    form_data[name] = ''
                elif field.get('type') == 'list':
                    form_data[name] = []
                elif field.get('type') == 'str':
                    form_data[name] = ''
                elif field.get('type') == 'bool':
                    form_data[name] = False
                elif field.get('type') == 'float':
                    form_data[name] = 0.
                elif field.get('type') == 'int':
                    form_data[name] = 0
                else:
                    warnings.warn("When you see this, something is double wrong")
    return form_data


@main_bp.route('/story/<int:story_id>/add_unit/<unit_type>', methods=['GET', 'POST'])
@login_required
def add_unit(story_id, unit_type):
    """Route to add a unit to a story."""
    story = get_story_by_id(story_id)
    if story is None:
        abort(404, description="Story not found.")
    if story.user_email != current_user.email:
        abort(403)

    unit_classes = unit_classes_dict_helper()
    if unit_type not in unit_classes:
        return "Invalid unit type", 400

    unit_class = unit_classes[unit_type]
    feature_schema = unit_class.feature_schema

    fields = prepare_fields(feature_schema, story)

    if request.method == 'POST':
        action = request.form.get('action')
        form_data = request.form.to_dict(flat=False)

        if action == 'fill_features':
            # Handle the OpenAI API call
            description = form_data.get('unit_description', [''])[0].strip()
            if description == '':
                description = form_data.get('name', [''])[0].strip()
            if not description:  # this ifclause should now never be called
                warnings.warn('When you see this, something is wrong')
                errors = ["Please provide a description to fill features."]
                fields = prepare_fields(feature_schema, story)
                return render_template(
                    'add_unit.html',
                    unit_type=unit_type,
                    fields=fields,
                    errors=errors,
                    form_data=form_data,
                    story=story,
                    edit_mode=False
                )
            try:
                # Generate the prompt messages
                messages = feature_value_prefill_prompt(story, unit_type, description, feature_schema)
                # Call OpenAI API
                response_text = call_openai(messages)
                # Parse the JSON response
                feature_values = json.loads(response_text)
                # Update form_data with feature_values
                for key, value in feature_values.items():
                    # Ensure the key is one of the features
                    if key in feature_schema:
                        if isinstance(value, list):
                            form_data[key] = value
                        else:
                            form_data[key] = [str(value)]
                        form_data[key] = value
                for key, value in form_data.items():
                    if ((key in feature_schema.keys() and feature_schema[key] != list)
                        or key.endswith('_new')) and isinstance(value, list)\
                            or key == 'unit_description':
                        if len(value) > 1:
                            raise ValueError("Expected at most one item in the list.")
                        form_data[key] = value[0]
                    # elif feature_schema[key] != list: raise ValueError("Unexpected form element")
                # Re-render the form with updated form_data
                fields = prepare_fields(feature_schema, story)
                return render_template(
                    'add_unit.html',
                    unit_type=unit_type,
                    fields=fields,
                    errors=[],
                    form_data=form_data,
                    story=story,
                    edit_mode=False
                )
            except json.JSONDecodeError as e:
                errors = [f"Failed to parse AI response: {str(e)}", "AI response: " + response_text]
                fields = prepare_fields(feature_schema, story)
                return render_template(
                    'add_unit.html',
                    unit_type=unit_type,
                    fields=fields,
                    errors=errors,
                    form_data=form_data,
                    story=story,
                    edit_mode=False
                )
            except Exception as e:
                errors = [f"An error occurred while filling features: {str(e)}"]
                fields = prepare_fields(feature_schema, story)
                return render_template(
                    'add_unit.html',
                    unit_type=unit_type,
                    fields=fields,
                    errors=errors,
                    form_data=form_data,
                    story=story,
                    edit_mode=False
                )
        elif action == 'save_unit':
            # Process form submission
            features, errors = process_form_submission(form_data, feature_schema, story)

            # Validate 'name' field
            name = features.get('name', '').strip()
            if not name:
                errors.append("Name is required.")
            else:
                # Check for duplicate names in the same story
                existing_unit = get_unit_by_name(story_id, name)
                if existing_unit:
                    errors.append(f"A unit with the name '{name}' already exists in this story.")

            if errors:
                # Re-render the form with error messages
                fields = prepare_fields(feature_schema, story)
                form_data = clean_form_data(form_data, fields)

                return render_template(
                    'add_unit.html',
                    unit_type=unit_type,
                    fields=fields,
                    errors=errors,
                    form_data=form_data,
                    story=story,
                    edit_mode=False
                )
            else:
                # Create the Unit and add to the database
                features['name'] = name
                unit = unit_class(unit_type=unit_type, name=name, features=features, story_id=story.id)
                add_unit_to_story(story_id, unit, user_email=current_user.email, is_copy=False)

                # After adding the unit, update references if needed
                update_references_with_new_unit(unit, story, old_name=unit.name)
                flash(f"{unit_type} '{name}' has been added.")
                return redirect(url_for('main.index'))
        else:
            raise Exception('submitted with unknown action.')
    elif request.method == 'GET':
        # GET request, render form
        fields = prepare_fields(feature_schema, story)
        # Check for template data in session
        template_unit = session.pop('template_unit', None)
        if template_unit and template_unit.get('unit_type') == unit_type:
            form_data = MultiDict(template_unit.get('features'))
        else:
            form_data = MultiDict()
        return render_template(
            'add_unit.html',
            unit_type=unit_type,
            fields=fields,
            errors=[],
            form_data=form_data,
            story=story,
            edit_mode=False
        )

@main_bp.route('/story/<int:story_id>/edit_unit/<unit_name>', methods=['GET', 'POST'])
@login_required
def edit_unit(story_id, unit_name):
    # TODO: There is an error when a user edits an object that falsely does not include all unit references by default.
    # Instead for each reference feature only the first unit is chosen by default.
    """Route to edit an existing unit."""
    story = get_story_by_id(story_id)
    if story is None:
        abort(404, description="Story not found.")
    if story.user_email != current_user.email:
        abort(403)

    unit = get_unit_by_name(story_id, unit_name)
    if not unit:
        abort(404, description="Unit not found.")

    unit_class = type(unit)
    unit_type = unit.unit_type
    feature_schema = unit_class.feature_schema

    if request.method == 'POST':
        action = request.form.get('action')
        form_data = request.form.to_dict(flat=False)

        if action == 'fill_features':
            # Handle the OpenAI API call
            description = form_data.get('unit_description', [''])[0].strip()
            if description == '':
                description = form_data.get('name', [''])[0].strip()
            if not description:  # this ifclause should now never be called
                warnings.warn('When you see this, something is wrong')
                errors = ["Please provide a description to fill features."]
                fields = prepare_fields(feature_schema, story)
                return render_template(
                    'add_unit.html',
                    unit_type=unit_type,
                    fields=fields,
                    errors=errors,
                    form_data=form_data,
                    story=story,
                    edit_mode=True
                )
            try:
                # Generate the prompt messages
                messages = feature_value_prefill_prompt(story, unit_type, description, feature_schema)
                # Call OpenAI API
                response_text = call_openai(messages)
                # Parse the JSON response
                feature_values = json.loads(response_text)
                # Update form_data with feature_values
                for key, value in feature_values.items():
                    # Ensure the key is one of the features
                    if key in feature_schema:
                        if isinstance(value, list):
                            form_data[key] = value
                        else:
                            form_data[key] = [str(value)]
                        form_data[key] = value
                for key, value in form_data.items():
                    if ((key in feature_schema.keys() and feature_schema[key] != list)
                        or key.endswith('_new')) and isinstance(value, list)\
                            or key == 'unit_description':
                        if len(value) > 1:
                            raise ValueError("Expected at most one item in the list.")
                        form_data[key] = value[0]
                    # elif feature_schema[key] != list: raise ValueError("Unexpected form element")
                # Re-render the form with updated form_data
                fields = prepare_fields(feature_schema, story)
                return render_template(
                    'add_unit.html',
                    unit_type=unit_type,
                    fields=fields,
                    errors=[],
                    form_data=form_data,
                    story=story,
                    edit_mode=True
                )
            except json.JSONDecodeError as e:
                errors = [f"Failed to parse AI response: {str(e)}", "AI response: " + response_text]
                fields = prepare_fields(feature_schema, story)
                return render_template(
                    'add_unit.html',
                    unit_type=unit_type,
                    fields=fields,
                    errors=errors,
                    form_data=form_data,
                    story=story,
                    edit_mode=True
                )
            except Exception as e:
                errors = [f"An error occurred while filling features: {str(e)}"]
                fields = prepare_fields(feature_schema, story)
                return render_template(
                    'add_unit.html',
                    unit_type=unit_type,
                    fields=fields,
                    errors=errors,
                    form_data=form_data,
                    story=story,
                    edit_mode=True
                )
        elif action == 'save_unit':
            # Process form submission
            features, errors = process_form_submission(form_data, feature_schema, story, unit_name=unit.name)

            # Validate 'name' field
            new_name = features.get('name', '').strip()
            if not new_name:
                errors.append("Name is required.")
            else:
                # Check for duplicate names in the same story (excluding current unit)
                existing_unit = get_unit_by_name(story_id, new_name)
                if existing_unit and existing_unit.id != unit.id:
                    errors.append(f"A unit with the name '{new_name}' already exists in this story.")

            if errors:
                # Re-render the form with error messages
                fields = prepare_fields(feature_schema, story)
                form_data = clean_form_data(form_data, fields)
                return render_template(
                    'add_unit.html',
                    unit_type=unit_type,
                    fields=fields,
                    errors=errors,
                    form_data=form_data,
                    story=story,
                    edit_mode=True
                )
            else:
                # Capture the old name before updating
                old_name = unit.name
                # Update the unit's features
                features['name'] = new_name
                unit.features = features
                unit.name = new_name
                update_unit(unit)
                # After updating the unit, update references if needed
                update_references_with_new_unit(unit, story, old_name)
                flash(f"{unit_type} '{new_name}' has been updated.")
                return redirect(url_for('main.index'))

    else:
        # GET request, render form with existing data
        fields = prepare_fields(feature_schema, story)
        form_data = MultiDict(unit.features)
        form_data = clean_form_data(form_data, fields)
        return render_template(
            'add_unit.html',
            unit_type=unit_type,
            fields=fields,
            errors=[],
            form_data=form_data,
            story=story,
            edit_mode=True
        )

@main_bp.route('/story/<int:story_id>/delete_unit/<unit_name>', methods=['GET'])
@login_required
def delete_unit(story_id, unit_name):
    """Route to delete a unit from a story."""
    story = get_story_by_id(story_id)
    if story is None:
        abort(404, description="Story not found.")

    if story.user_email != current_user.email:
        abort(403)

    # Get the unit by name within the story
    unit = get_unit_by_name(story_id, unit_name)
    if not unit:
        abort(404, description="Unit not found in this story.")

    # Delete the unit from the database
    delete_unit_from_story(unit)

    flash(f"Unit '{unit_name}' has been deleted from the story.")
    return redirect(url_for('main.index'))


@main_bp.route('/story/<int:story_id>/download')
@login_required
def download_story(story_id):
    """Route to download the story as a PDF."""
    story = get_story_by_id(story_id)
    if story is None:
        abort(404, description="Story not found.")
    if story.user_email != current_user.email:
        abort(403)

    # Generate the PDF file
    filename = f'pdf_files/story_{story.id}.pdf'
    story.to_pdf(filename)  # Assuming to_pdf is a method on the Story model

    # Send the file to the client
    return send_file(
        filename,
        as_attachment=True,
        mimetype='application/pdf'
    )


@main_bp.route('/story/<int:story_id>/download_json')
@login_required
def download_story_json(story_id):
    """Route to download the story as a JSON file."""
    story = get_story_by_id(story_id)
    if story is None:
        abort(404, description="Story not found.")
    if story.user_email != current_user.email:
        abort(403)

    # Generate the JSON representation
    story_json = json.dumps(story.to_json(), indent=4)

    # Create a response with the proper headers for file download
    response = make_response(story_json)
    response.headers.set('Content-Disposition', f'attachment; filename="{story.name}.json"')
    response.headers.set('Content-Type', 'application/json')
    return response


@main_bp.route('/story/<int:story_id>/view')
@login_required
def view_story(story_id):
    """Route to view the story as HTML."""
    story = get_story_by_id(story_id)
    if story is None:
        abort(404, description="Story not found.")
    if story.user_email != current_user.email:
        abort(403)

    # Generate the HTML representation
    story_html = story.to_html()

    return render_template('view_story.html', story=story, story_html=story_html)


@main_bp.route('/story/<int:story_id>/download_text')
@login_required
def download_story_text(story_id):
    """Route to download the story as a text file."""
    story = get_story_by_id(story_id)
    if story is None:
        abort(404, description="Story not found.")
    if story.user_email != current_user.email:
        abort(403)

    # Use a temporary file to store the generated story
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as tmp_file:
        tmp_filename = tmp_file.name

    try:
        # Generate the text file using the to_text method
        story.to_text(filename=tmp_filename)

        # Send the file to the client
        return send_file(
            tmp_filename,
            as_attachment=True,
            download_name=f"{story.name}.txt",
            mimetype='text/plain'
        )
    except Exception as e:
        flash(f"An error occurred while generating the story: {e}")
        return redirect(url_for('main.index'))
    finally:
        # Clean up the temporary file after the request is complete
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)

def prepare_fields(feature_schema, story):
    """Prepare fields for the unit form based on the feature schema."""
    fields = []
    for feature_name, expected_type in feature_schema.items():
        if feature_name == 'name':
            field = {'name': feature_name, 'type': 'str', 'required': True}
            if story.undefined_names:
                field['options'] = story.undefined_names
        else:
            field = {'name': feature_name}
            if expected_type == bool:
                field['type'] = 'bool'
            elif expected_type == float:
                field['type'] = 'float'
            elif expected_type == str:
                field['type'] = 'str'
            elif expected_type == int:
                field['type'] = 'int'
            elif expected_type == list:
                field['type'] = 'list'
                # Fetch all unit names from the story's units using the service layer
                units = get_units_by_story_id(story.id)
                field['options'] = [
                    (unit.name, unit.name) for unit in units
                ] + [
                    (name, f"{name} (undefined)") for name in story.undefined_names
                ]
            else:
                field['type'] = 'unknown'
        fields.append(field)
    return fields

def process_form_submission(form_data, feature_schema, story, unit_name=None):
    """Process the form submission for adding or editing a unit."""
    features = {}
    errors = []

    # Collect form data
    for feature_name, expected_type in feature_schema.items():
        if feature_name == 'name':
            name = form_data.get(feature_name, [''])[0].strip()
            features[feature_name] = name
            continue

        value = form_data.get(feature_name, [''])[0]
        new_value = form_data.get(f"{feature_name}_new", [''])[0].strip()

        if expected_type == bool:
            features[feature_name] = (value == 'on')
        elif expected_type == float:
            try:
                features[feature_name] = float(value) if value else 0.0
            except ValueError:
                errors.append(f"Invalid value for {feature_name}.")
                features[feature_name] = 0.0
        elif expected_type == str:
            features[feature_name] = value.strip() if value else ''
        elif expected_type == int:
            try:
                features[feature_name] = int(value) if value else 0
            except ValueError:
                errors.append(f"Invalid value for {feature_name}.")
                features[feature_name] = 0
        elif expected_type == list:
            # selected_values = form_data.getlist(feature_name)
            selected_values = form_data.get(feature_name)
            if selected_values is None:
                selected_values = []
            if not selected_values:
                selected_values = []
            new_values = new_value.split(', ')

            combined_values = [v.strip() for v in selected_values + new_values if v.strip()]

            # Add to undefined names if necessary
            for v in combined_values:
                related_unit = get_unit_by_name(story.id, v)
                if not related_unit and v not in story.undefined_names:
                    story.undefined_names.append(v)
            features[feature_name] = combined_values
        else:
            # Unsupported type
            errors.append(f"Unsupported type for {feature_name}.")
            features[feature_name] = value
    update_story(story)
    return features, errors

def feature_value_prefill_prompt(story, unit_type, description, feature_schema):
    """
    Generate prompt messages to send to OpenAI API for filling unit features.

    Args:
        story (Story): The current story object.
        unit_type (str): The type of unit being added or edited.
        description (str): The user's description of the unit.
        feature_schema (dict): The schema of features for the unit type.

    Returns:
        list: A list of messages structured for the OpenAI Chat API.
    """
    if not description:
        description = f"The {unit_type} should fit well within the story."
    # Build existing units text
    existing_units_text = ""
    for unit in story.units:
        existing_units_text += f"{unit.unit_type}: {unit.name}\n"
        for key, value in unit.features.items():
            existing_units_text += f"  {key}: {value}\n"
        existing_units_text += "\n"

    # Build the prompt
    prompt = f"""Based on the following story information and the description, please provide values for the features of the unit type '{unit_type}' in JSON format.
A Unit is an element of the story.

Story Setting and Style:
{story.setting_and_style}

Main Challenge:
{story.main_challenge}

All already existing units of the story:
{existing_units_text}

Description of the {unit_type} to create:
{description}

Please provide a JSON object with the following keys and appropriate values:

"""

    # List the features with their expected types
    prompt += "Features:\n"
    for feature_name, expected_type in feature_schema.items():
        typename = expected_type.__name__ if isinstance(expected_type, type) else 'list'
        prompt += f"- '{feature_name}' ({typename})\n"

    prompt += """

Example response:
{
    "name": "Name of the unit",
    "feature1": "value1",
    "feature2": true,
    "feature3": 0.5,
    "feature4": ["item1", "item2"],
    "feature5": "Some description"
}

Please ensure the response is valid JSON, starting with the first opening bracket "{" and ending with the last closing bracket "}".
Do not include any text outside of the JSON object.

You should make sure that the feature values are appropriate and consistent with the story and existing units.
If a feature expects a list of names of existing units, please select appropriate ones from the existing units.
If necessary, you may introduce new names, but prefer existing ones.

"""

    messages = [
        {"role": "system",
         "content": "You are an assistant that helps fill out feature values for units in a story based on a description."},
        {"role": "user", "content": prompt}
    ]
    return messages
