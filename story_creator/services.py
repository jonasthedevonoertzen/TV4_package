# story_creator/services.py

from .database import SessionLocal
from .new_models import (
    User,
    Story,
    Unit,
    EventOrScene,
    Secret,
    Item,
    Beast,
    Group,
    Motivation,
    Place,
    TransportationInfrastructure,
    Character,
)
from sqlalchemy.orm import joinedload

# User Services

def get_user_by_email(email):
    session = SessionLocal()
    try:
        user = session.query(User).options(
            joinedload(User.stories)
            .joinedload(Story.units)
        ).filter(User.email == email).first()
        if user is None:
            return None
        return user
    finally:
        session.close()

def create_user(email):
    session = SessionLocal()
    try:
        user = User(email=email)
        session.add(user)
        session.commit()
        return user
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# Story Services

def get_stories_by_user_email(user_email):
    session = SessionLocal()
    try:
        stories = session.query(Story).options(
            joinedload(Story.units)
        ).filter(Story.user_email == user_email).all()
        return stories
    finally:
        session.close()

def create_story(name, user_email, setting_and_style, main_challenge):
    session = SessionLocal()
    try:
        story = Story(
            name=name,
            user_email=user_email,
            setting_and_style=setting_and_style,
            main_challenge=main_challenge
        )
        session.add(story)
        session.commit()
        return story
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_story_by_id(story_id):
    session = SessionLocal()
    try:
        story = session.query(Story).options(
            joinedload(Story.units)
        ).filter(Story.id == story_id).first()
        if story is None:
            return None
        return story
    finally:
        session.close()

# Unit Services

def add_unit_to_story(story_id, unit):
    session = SessionLocal()
    try:
        unit.story_id = story_id
        session.add(unit)
        session.commit()
        return unit
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_unit_by_name(story_id, unit_name):
    session = SessionLocal()
    try:
        unit = session.query(Unit).filter_by(story_id=story_id, name=unit_name).first()
        return unit
    finally:
        session.close()

def get_units_by_story_id(story_id):
    """Retrieve all units associated with a given story ID."""
    session = SessionLocal()
    try:
        units = session.query(Unit).filter_by(story_id=story_id).all()
        return units
    finally:
        session.close()

def update_unit(unit):
    """Update an existing unit in the database."""
    session = SessionLocal()
    try:
        # Merge the unit to update the existing record
        session.merge(unit)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def update_references_with_new_unit(unit, story, old_name):
    """Update references to a unit's old name in other units after renaming.

    Args:
        unit (Unit): The unit that was updated.
        story (Story): The story containing the units.
        old_name (str): The old name of the unit before renaming.
    """
    session = SessionLocal()
    try:
        # Fetch all units of the story except the updated unit
        units = session.query(Unit).filter(Unit.story_id == story.id, Unit.id != unit.id).all()
        for other_unit in units:
            updated = False
            # Get the feature schema of the other unit's class
            unit_class = type(other_unit)
            feature_schema = unit_class.feature_schema

            for feature_name, expected_type in feature_schema.items():
                if feature_name not in other_unit.features:
                    continue
                value = other_unit.features[feature_name]
                if expected_type == list and isinstance(value, list):
                    if old_name in value:
                        # Update the list to replace old_name with new unit name
                        new_value = [unit.name if v == old_name else v for v in value]
                        other_unit.features[feature_name] = new_value
                        updated = True
                elif expected_type == str and isinstance(value, str):
                    if value == old_name:
                        # Update the string value to the new unit name
                        other_unit.features[feature_name] = unit.name
                        updated = True
                # Add checks for other types if necessary

            if updated:
                session.merge(other_unit)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
