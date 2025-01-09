# new_models.py

"""
Model Classes for the Story Creator.

This module defines the classes for the Story Creator application,
including 'User', 'Story', 'Unit', and various subclasses of 'Unit' representing different
entities like 'Character', 'EventOrScene', 'Item', etc.
"""

from fpdf import FPDF
from flask_login import UserMixin
import os
from .openai_api_call import call_openai

class User(UserMixin):
    """User class for authentication."""
    def __init__(self, email, username):
        self.email = email
        self.username = username
        self.stories = []  # List of Story objects

    def get_id(self):
        """Returns a unique identifier for the user."""
        return self.email


class Story:
    """Class representing a Story.

    Attributes:
        id (int): Unique identifier for the story.
        name (str): Name of the story.
        user_email (str): Email of the user who owns the story.
        undefined_names (list): List of undefined names used in the story.
        setting_and_style (str): Description of the story's setting and style.
        main_challenge (str): Description of the main challenge in the story.
        units (list): List of units associated with the story.
    """

    def __init__(self, id, name, user_email, setting_and_style, main_challenge):
        """Initialize a new Story instance.

        Args:
            id (int): Unique identifier for the story.
            name (str): Name of the story.
            user_email (str): Email of the user who owns the story.
            setting_and_style (str): Description of the setting and style.
            main_challenge (str): Description of the main challenge.
        """
        self.id = id
        self.name = name
        self.user_email = user_email
        self.setting_and_style = setting_and_style
        self.main_challenge = main_challenge
        self.undefined_names = []
        self.units = []  # List of Unit objects

    def _generate_prompt(self):
        """Generate a prompt for the OpenAI API based on the story content."""
        prompt = f"Write a full story based on the following details:\n\n"
        prompt += f"Setting and Style:\n{self.setting_and_style}\n\n"
        prompt += f"Main Challenge:\n{self.main_challenge}\n\n"
        prompt += "Units:\n"
        for unit in self.units:
            prompt += f"{unit.unit_type}: {unit.name}\n"
            for key, value in unit.features.items():
                prompt += f"  {key}: {value}\n"
            prompt += "\n"
        return prompt

    def to_text(self, filename='story.txt'):
        """Generate the story as a text file using OpenAI API."""

        try:
            # Prepare the prompt
            messages = [{
                "role": "user",
                "content": self._generate_prompt()
            }]

            story_text = call_openai(messages=messages, model="o1-mini") # , model="gpt-4o-mini"

            # Write the story to the text file
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(story_text)

        except Exception as e:
            print(f"Error generating story text: {e}")
            raise

    # --- Serialization Methods ---
    def to_text_list(self):
        """Return a textual list of units in the story."""
        text = ""
        for unit in self.units:
            text += f"{unit.unit_type}: {unit.name}\n"
            for key, value in unit.features.items():
                text += f"  {key}: {value}\n"
            text += "\n"
        return text

    def to_json(self):
        """Serialize the story to a JSON-friendly dictionary.

        Returns:
            dict: Dictionary representation of the story.
        """
        return {
            'name': self.name,
            'setting_and_style': self.setting_and_style,
            'main_challenge': self.main_challenge,
            'units': [unit.to_json() for unit in self.units],
        }

    def to_html(self):
        """Convert the story to an HTML representation.

        Returns:
            str: HTML content representing the story.
        """
        html_content = f"<h1>{self.name}</h1>"
        html_content += f"<h2>Setting and Style</h2><p>{self.setting_and_style}</p>"
        html_content += f"<h2>Main Challenge</h2><p>{self.main_challenge}</p>"
        for unit in self.units:
            html_content += unit.to_html()
        return html_content

    def to_pdf(self, filename='story.pdf'):
        """Export the story to a PDF file.

        Args:
            filename (str, optional): Filename for the PDF. Defaults to 'story.pdf'.
        """

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, self.name, ln=True, align='C')
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, f"Setting and Style: {self.setting_and_style}\n")
        pdf.multi_cell(0, 10, f"Main Challenge: {self.main_challenge}\n")
        for unit in self.units:
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, f"{unit.unit_type}: {unit.name}", ln=True)
            pdf.set_font('Arial', '', 12)
            for key, value in unit.features.items():
                pdf.multi_cell(0, 10, f"{key}: {value}")
                pdf.ln(1)
            pdf.ln(5)
        pdf.output(filename)

    # --- Magic Methods ---

    def __getitem__(self, unit_name):
        """Get a unit by name using indexing syntax.

        Args:
            unit_name (str): Name of the unit.

        Returns:
            Unit: The unit matching the given name.

        Raises:
            KeyError: If no unit with the given name is found.
        """
        for unit in self.units:
            if unit.name == unit_name:
                return unit
        raise KeyError(f"No unit named '{unit_name}' found.")

    def __len__(self):
        """Get the number of units in the story.

        Returns:
            int: Number of units.
        """
        return len(self.units)

    def __iter__(self):
        """Iterate over the units in the story.

        Returns:
            iterator: Iterator over units.
        """
        return iter(self.units)


class Unit:
    """Base Class representing a Unit in the Story.

    Attributes:
        id (int): Unique identifier for the unit.
        unit_type (str): Type of the unit (e.g., 'Character', 'EventOrScene').
        name (str): Name of the unit.
        story_id (int): ID of the associated story.
        features (dict): Dictionary of unit's features.
    """

    base_feature_schema = {'name': str}

    def __init__(self, unit_type, name, story_id, features, id=None):
        """Initialize a new Unit instance.

        Args:
            id (int): Unique identifier for the unit.
            unit_type (str): Type of the unit.
            name (str): Name of the unit.
            story_id (int): ID of the associated story.
            features (dict): Dictionary of the unit's features.
        """
        self.id = id
        self.unit_type = unit_type
        self.name = name
        self.story_id = story_id
        self.features = features

    # --- Serialization Methods ---

    def to_json(self):
        """Serialize the unit to a JSON-friendly dictionary.

        Returns:
            dict: Dictionary representation of the unit.
        """
        return {
            'unit_type': self.unit_type,
            'name': self.name,
            'features': self.features,
        }

    def to_html(self):
        """Convert the unit to an HTML representation.

        Returns:
            str: HTML content representing the unit.
        """
        html_content = f"<h3>{self.unit_type}: {self.name}</h3>"
        html_content += "<ul>"
        for key, value in self.features.items():
            html_content += f"<li><strong>{key}:</strong> {value}</li>"
        html_content += "</ul>"
        return html_content


# Subclasses of Unit

class EventOrScene(Unit):
    """Class representing an Event or Scene in the Story.

    Attributes:
        feature_schema (dict): Schema defining the features and their data types.
    """
    # Extend the base feature schema with specific fields
    feature_schema = {**Unit.base_feature_schema, **{
        'Which people are involved?': list,
        'Which groups are involved?': list,
        'Which beasts are involved?': list,
        'Which items are involved?': list,
        'Which secrets are involved?': list,
        'What motivations are involved?': list,
        'Where might this happen?': list,
        'Is this an investigation scene?': bool,
        'Is this a social interaction?': bool,
        'Is this a fight scene?': bool,
        'What happens?': str,
        'How do relationships change?': str,
        'What triggers this scene to happen?': str,
        'Is this scene a start scene?': bool,
        "If this scene is a start scene, who's start scene is it?": list,
        'How likely will this scene occur?': float,
    }}


class Secret(Unit):
    """Class representing a Secret in the Story."""
    feature_schema = {**Unit.base_feature_schema, **{
        'What is the secret?': str,
        'Who knows of it?': list,
        'Which people are involved?': list,
        'Which groups are involved?': list,
        'Which items are involved?': list,
        'Excitement level': float,
    }}


class Item(Unit):
    """Class representing an Item in the Story."""
    feature_schema = {**Unit.base_feature_schema, **{
        'Who owns this?': list,
        'Worth': float,
        'What is it?': str,
        'Where is it?': list,
    }}


class Beast(Unit):
    """Class representing a Beast in the Story."""
    feature_schema = {**Unit.base_feature_schema, **{
        'Which race is this beast?': str,
        'Where could it be?': list,
        'What does it look like?': str,
        'Aggressiveness': float,
    }}


class Grouping(Unit):
    """Class representing a Group in the Story."""
    feature_schema = {**Unit.base_feature_schema, **{
        'Who is part of the group?': list,
        'Reason for solidarity': str,
        'Where did the group first meet?': list,
    }}


class Motivation(Unit):
    """Class representing a Motivation in the Story."""
    feature_schema = {**Unit.base_feature_schema, **{
        'Who is motivated?': list,
        'What is the motivation for?': str,
        'By whom is the motivation?': list,
        # Boolean fields representing different sources of motivation.
        'Is ambition the source of motivation?': bool,
        'Is determination the source of motivation?': bool,
        # ... Additional motivation sources ...
        'Is reflection the source of motivation?': bool,
    }}


class Place(Unit):
    """Class representing a Place in the Story."""
    feature_schema = {**Unit.base_feature_schema, **{
        'Where is it?': str,
        'Environmental conditions': str,
        'Associated places': list,
        'People present': list,
        'Groups present': list,
        'Beasts present': list,
        'Items present': list,
        'Secrets can be found here': list,
        'Size (0.0 to 1.0)': float,
        'What does it look like?': str,
        'Special history': list,
        'Upcoming events at this place': str,
        # Boolean fields representing place types.
        'Is it a space in nature?': bool,
        'Is it an urban space?': bool,
        # ... Additional place types ...
        'Is it a cave?': bool,
    }}


class TransportationInfrastructure(Unit):
    """Class representing Transportation Infrastructure in the Story."""
    feature_schema = {**Unit.base_feature_schema, **{
        'Connecting places': list,
        'Usage frequency': float,
        # Boolean fields representing allowed transportation types.
        'For motor vehicles?': bool,
        'For non-motor vehicles?': bool,
        'For pedestrians?': bool,
        # Boolean fields representing infrastructure types.
        'Is it a street?': bool,
        'Is it a railway?': bool,
        # ... Additional infrastructure types ...
        'Is it a bridge?': bool,
    }}


class Character(Unit):
    """Class representing a Character in the Story."""
    feature_schema = {**Unit.base_feature_schema, **{
        'Is this a player character?': bool,
        'Skills or talents': str,
        'Involved events or scenes': list,
        'Groups part of': list,
        'Plans involving this character': list,
        "Character's backstory": str,
        'Important people for this character': list,
        'Important items for this character': list,
    }}


# Mapping of unit_type to class
UNIT_TYPE_TO_CLASS = {
    'EventOrScene': EventOrScene,
    'Secret': Secret,
    'Item': Item,
    'Beast': Beast,
    'Grouping': Grouping,
    'Motivation': Motivation,
    'Place': Place,
    'TransportationInfrastructure': TransportationInfrastructure,
    'Character': Character,
}

def get_unit_class(unit_type):
    return UNIT_TYPE_TO_CLASS.get(unit_type, Unit)