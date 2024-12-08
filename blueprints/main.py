# blueprints/main.py

"""
Main Blueprint.

This module handles the main routes for the application, including
the index page, creating stories, selecting stories, adding and editing units, etc.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, send_file
from flask_login import login_required, current_user
from werkzeug.datastructures import MultiDict

# Import service functions from the story_creator package
from story_creator.services import (
    get_stories_by_user_email,
    create_story,
    get_story_by_id,
    add_unit_to_story,
    get_unit_by_name,
    update_unit,
    get_units_by_story_id,
    update_references_with_new_unit,
)

# Import necessary unit subclasses
from story_creator.new_models import Unit

main_bp = Blueprint('main', __name__)

def unit_classes_dict_helper():
    """Helper function to get a dictionary of Unit subclasses."""
    return {cls.__name__: cls for cls in Unit.__subclasses__()}

@main_bp.route('/')
def index():
    """Index route: Display user's stories and allow selection."""
    if current_user.is_authenticated:
        # Get user stories using the service layer
        user_stories = get_stories_by_user_email(current_user.email)
        selected_story_id = session.get('current_story_id')
        selected_story = None
        if selected_story_id:
            selected_story = get_story_by_id(selected_story_id)
        return render_template(
            'index.html',
            stories=user_stories,
            selected_story=selected_story,
            unit_classes_dict=unit_classes_dict_helper()
        )
    else:
        return redirect(url_for('auth.login'))

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
            # Handle the OpenAI API call (if applicable)
            pass  # Add the logic for calling OpenAI API if needed
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
                unit = unit_class(unit_type=unit_type, features=features, story_id=story.id)
                add_unit_to_story(story_id, unit)
                # After adding the unit, update references if needed
                update_references_with_new_unit(unit, story)
                flash(f"{unit_type} '{name}' has been added.")
                return redirect(url_for('main.index'))

    else:
        # GET request, render form
        fields = prepare_fields(feature_schema, story)
        return render_template(
            'add_unit.html',
            unit_type=unit_type,
            fields=fields,
            errors=[],
            form_data=MultiDict(),
            story=story,
            edit_mode=False
        )

@main_bp.route('/story/<int:story_id>/edit_unit/<unit_name>', methods=['GET', 'POST'])
@login_required
def edit_unit(story_id, unit_name):
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
            # Handle the OpenAI API call (if applicable)
            errors = ["OpenAI API functionality is not implemented in this version."]
            return render_template(
                'add_unit.html',
                unit_type=unit_type,
                fields=prepare_fields(feature_schema, story),
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
        return render_template(
            'add_unit.html',
            unit_type=unit_type,
            fields=fields,
            errors=[],
            form_data=form_data,
            story=story,
            edit_mode=True
        )


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

def prepare_fields(feature_schema, story):
    """Prepare fields for the unit form based on the feature schema."""
    fields = []
    for feature_name, expected_type in feature_schema.items():
        if feature_name == 'name':
            field = {'name': feature_name, 'type': 'str', 'required': True}
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
            selected_values = form_data.getlist(feature_name)
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
    return features, errors

