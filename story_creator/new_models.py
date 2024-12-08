# story_creator/new_models.py

"""
Database Models and ORM Classes for the Story Creator.

This module defines the SQLAlchemy ORM models for the Story Creator application,
including the 'User', 'Story', 'Unit', and various subclasses of 'Unit' representing different
entities like 'Character', 'EventOrScene', 'Item', etc.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    ForeignKey,
    PickleType,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.ext.declarative import declarative_base

from flask_login import UserMixin

# Base class for declarative class definitions.
Base = declarative_base()

class User(Base, UserMixin):
    """User model for authentication."""
    __tablename__ = 'user'

    email = Column(String(150), primary_key=True)

    # Define relationship to Story model
    stories = relationship('Story', back_populates='user')

    def get_id(self):
        return self.email

class Story(Base):
    """ORM Model representing a Story.

    Attributes:
        id (int): Primary key.
        name (str): Name of the story.
        user_email (str): Email of the user who owns the story.
        undefined_names (list): List of undefined names used in the story.
        setting_and_style (str): Description of the story's setting and style.
        main_challenge (str): Description of the main challenge in the story.
        units (list): List of units associated with the story.
    """

    __tablename__ = 'story'

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    user_email = Column(String(150), ForeignKey('user.email'), nullable=False)
    undefined_names = Column(MutableList.as_mutable(PickleType), default=[])
    setting_and_style = Column(Text, nullable=False)
    main_challenge = Column(Text, nullable=False)

    # Relationship to 'Unit' models.
    units = relationship('Unit', cascade='all, delete-orphan', back_populates='story')
    # Relationship to 'User' model
    user = relationship('User', back_populates='stories')

    def __init__(self, name, user_email, setting_and_style, main_challenge):
        """Initialize a new Story instance.

        Args:
            name (str): Name of the story.
            user_email (str): Email of the user who owns the story.
            setting_and_style (str): Description of the setting and style.
            main_challenge (str): Description of the main challenge.
        """
        self.name = name
        self.user_email = user_email
        self.setting_and_style = setting_and_style
        self.main_challenge = main_challenge
        self.undefined_names = []
        # The Story instance will be saved to the database via the service layer.

    # --- Serialization Methods ---

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
        from fpdf import FPDF
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

class Unit(Base):
    """Base ORM Model representing a Unit in the Story.

    Attributes:
        id (int): Primary key.
        unit_type (str): Type of the unit (e.g., 'Character', 'EventOrScene').
        name (str): Name of the unit.
        story_id (int): Foreign key to the associated story.
        features (dict): Dictionary of unit's features.
        story (Story): Relationship to the associated story.
    """

    __tablename__ = 'unit'
    id = Column(Integer, primary_key=True)
    unit_type = Column(String(50))
    name = Column(String(150), nullable=False)
    story_id = Column(Integer, ForeignKey('story.id'), nullable=False)
    features = Column(MutableDict.as_mutable(PickleType), default={})

    # Relationship to the 'Story' model.
    story = relationship('Story', back_populates='units')

    __mapper_args__ = {
        'polymorphic_identity': 'unit',
        'polymorphic_on': unit_type
    }

    # Base feature schema that can be extended by subclasses.
    base_feature_schema = {'name': str}

    def __init__(self, unit_type, features, story_id=None):
        """Initialize a new Unit instance.

        Args:
            unit_type (str): Type of the unit.
            features (dict): Dictionary of the unit's features.
            story_id (int, optional): ID of the associated story.
        """
        self.unit_type = unit_type
        self.features = features
        self.name = self.features.get('name', '').strip()
        if story_id:
            self.story_id = story_id
        # The Unit instance will be saved to the database via the service layer.

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
    """ORM Model representing an Event or Scene in the Story.

    Attributes:
        feature_schema (dict): Schema defining the features and their data types.
    """
    # Extend the base feature schema with specific fields for EventOrScene.
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

    __mapper_args__ = {
        'polymorphic_identity': 'EventOrScene',
    }

class Secret(Unit):
    """ORM Model representing a Secret in the Story.

    Attributes:
        feature_schema (dict): Schema defining the features and their data types.
    """
    # Extend the base feature schema with specific fields for Secret.
    feature_schema = {**Unit.base_feature_schema, **{
        'What is the secret?': str,
        'Who knows of it?': list,
        'Which people are involved?': list,
        'Which groups are involved?': list,
        'Which items are involved?': list,
        'Excitement level (0.0 to 1.0)': float,
    }}
    __mapper_args__ = {
        'polymorphic_identity': 'Secret',
    }

class Item(Unit):
    """ORM Model representing an Item in the Story.

    Attributes:
        feature_schema (dict): Schema defining the features and their data types.
    """
    # Extend the base feature schema with specific fields for Item.
    feature_schema = {**Unit.base_feature_schema, **{
        'Who owns this?': list,
        'Worth (0.0 to 1.0)': float,
        'What is it?': str,
        'Where is it?': list,
    }}
    __mapper_args__ = {
        'polymorphic_identity': 'Item',
    }

class Beast(Unit):
    """ORM Model representing a Beast in the Story.

    Attributes:
        feature_schema (dict): Schema defining the features and their data types.
    """
    # Extend the base feature schema with specific fields for Beast.
    feature_schema = {**Unit.base_feature_schema, **{
        'Which race is this beast?': str,
        'Where could it be?': list,
        'What does it look like?': str,
        'Aggressiveness (0.0 to 1.0)': float,
    }}
    __mapper_args__ = {
        'polymorphic_identity': 'Beast',
    }

class Group(Unit):
    """ORM Model representing a Group in the Story.

    Attributes:
        feature_schema (dict): Schema defining the features and their data types.
    """
    # Extend the base feature schema with specific fields for Group.
    feature_schema = {**Unit.base_feature_schema, **{
        'Who is part of the group?': list,
        'Reason for solidarity': str,
        'Where did the group first meet?': list,
    }}
    __mapper_args__ = {
        'polymorphic_identity': 'Group',
    }

class Motivation(Unit):
    """ORM Model representing a Motivation in the Story.

    Attributes:
        feature_schema (dict): Schema defining the features and their data types.
    """
    # Extend the base feature schema with specific fields for Motivation.
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
    __mapper_args__ = {
        'polymorphic_identity': 'Motivation',
    }

class Place(Unit):
    """ORM Model representing a Place in the Story.

    Attributes:
        feature_schema (dict): Schema defining the features and their data types.
    """
    # Extend the base feature schema with specific fields for Place.
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
    __mapper_args__ = {
        'polymorphic_identity': 'Place',
    }

class TransportationInfrastructure(Unit):
    """ORM Model representing Transportation Infrastructure in the Story.

    Attributes:
        feature_schema (dict): Schema defining the features and their data types.
    """
    # Extend the base feature schema with specific fields for TransportationInfrastructure.
    feature_schema = {**Unit.base_feature_schema, **{
        'Connecting places': list,
        'Usage frequency (0.0 to 1.0)': float,
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
    __mapper_args__ = {
        'polymorphic_identity': 'TransportationInfrastructure',
    }

class Character(Unit):
    """ORM Model representing a Character in the Story.

    Attributes:
        feature_schema (dict): Schema defining the features and their data types.
    """
    # Extend the base feature_schema with specific fields for Character.
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
    __mapper_args__ = {
        'polymorphic_identity': 'Character',
    }
