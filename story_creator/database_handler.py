# database_handler.py

"""
Database Handler Module.

This module provides functions to interact with the database using plain SQL, without ORM.
It replaces the previous 'services.py' and 'database.py' modules.

All classes (User, Story, Unit, and subclasses) are independent from any database logic.
"""

import sqlite3
import json
from .new_models import (
    User, Story, Unit, get_unit_class,
    EventOrScene, Secret, Item, Beast,
    Grouping, Motivation, Place, TransportationInfrastructure, Character
)
import re
import random
import string


DATABASE_PATH = 'story_creator.db'

NAY_NAY_CHARACTERS = r"[ ?'\[\],.]()"


def init_db():
    """Initialize the database by creating the necessary tables."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()

        '''
        # Check if 'username' column exists; if not, alter the table to add it
        cursor.execute("PRAGMA table_info(user)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'username' not in columns:
            cursor.execute('ALTER TABLE user ADD COLUMN username TEXT UNIQUE NOT NULL')
        '''

        # Create User table (with username column)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user (
                email TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL
            )
        ''')

        # Create Story table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS story (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                user_email TEXT NOT NULL,
                undefined_names TEXT,
                setting_and_style TEXT NOT NULL,
                main_challenge TEXT NOT NULL,
                FOREIGN KEY (user_email) REFERENCES user(email)
            )
        ''')

        # Create Unit table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_type TEXT NOT NULL,
                name TEXT NOT NULL,
                story_id INTEGER NOT NULL,
                features TEXT,
                FOREIGN KEY (story_id) REFERENCES story(id)
            )
        ''')

        # Create tables for each Unit subclass
        unit_subclasses = {
            'EventOrScene': EventOrScene.feature_schema,
            'Secret': Secret.feature_schema,
            'Item': Item.feature_schema,
            'Beast': Beast.feature_schema,
            'Grouping': Grouping.feature_schema,
            'Motivation': Motivation.feature_schema,
            'Place': Place.feature_schema,
            'TransportationInfrastructure': TransportationInfrastructure.feature_schema,
            'Character': Character.feature_schema,
        }



        for subclass_name, feature_schema in unit_subclasses.items():
            # Start with the unit_id column
            table_columns = ['unit_id INTEGER']
            for feature_name, feature_type in feature_schema.items():
                column_name = re.sub(r'\W', '', feature_name.replace(' ', '_'))

                # Determine column type
                if feature_type == bool:
                    column_type = 'INTEGER'  # 0 or 1
                elif feature_type == int:
                    column_type = 'INTEGER'
                elif feature_type == float:
                    column_type = 'REAL'
                elif feature_type == str:
                    column_type = 'TEXT'
                elif feature_type == list:
                    column_type = 'TEXT'  # Store as JSON string
                else:
                    column_type = 'TEXT'

                # maybe include cleanup here, but shouldn't really be necessary

                table_columns.append(f"{column_name} {column_type}")

            # Add PRIMARY KEY and FOREIGN KEY constraints
            table_constraints = [
                'PRIMARY KEY (unit_id)',
                'FOREIGN KEY (unit_id) REFERENCES unit(id)'
            ]

            # Combine columns and constraints
            all_table_elements = table_columns + table_constraints

            # Join all elements with commas
            columns_definition = ',\n    '.join(all_table_elements)

            sql_command = f'''
                CREATE TABLE IF NOT EXISTS {subclass_name} (
                    {columns_definition}
                )
            '''

            # Create table for the subclass
            cursor.execute(sql_command)

        # Create Label table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS label (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                user_email TEXT,
                FOREIGN KEY (user_email) REFERENCES user(email)
            )
        ''')

        # Create Unit_Label table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unit_label (
                unit_id INTEGER NOT NULL,
                label_id INTEGER NOT NULL,
                FOREIGN KEY (unit_id) REFERENCES unit(id),
                FOREIGN KEY (label_id) REFERENCES label(id),
                PRIMARY KEY (unit_id, label_id)
            )
        ''')

        conn.commit()

def generate_random_username(length=8):
    """Generate a unique random username."""
    while True:
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        if not get_user_by_username(username):
            return username

def get_user_by_username(username):
    """Check if a username already exists."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT email, username FROM user WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            return User(email=row[0], username=row[1])
        else:
            return None

def update_username(email, new_username):
    """Update the username and associated labels when a user changes their username."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        # Get the old username
        cursor.execute('SELECT username FROM user WHERE email = ?', (email,))
        row = cursor.fetchone()
        if not row:
            return  # User does not exist
        old_username = row[0]

        # Update the username in the user table
        cursor.execute('''
            UPDATE user
            SET username = ?
            WHERE email = ?
        ''', (new_username, email))

        # Get the old label id
        cursor.execute('''
            SELECT id FROM label WHERE name = ? AND user_email IS NULL
        ''', (old_username,))
        old_label_row = cursor.fetchone()
        if old_label_row:
            old_label_id = old_label_row[0]
            # Check if a label with new_username already exists
            cursor.execute('''
                SELECT id FROM label WHERE name = ? AND user_email IS NULL
            ''', (new_username,))
            new_label_row = cursor.fetchone()
            if new_label_row:
                # Label with new_username exists
                new_label_id = new_label_row[0]
                # Update unit_label table to point to new_label_id
                cursor.execute('''
                    UPDATE unit_label
                    SET label_id = ?
                    WHERE label_id = ?
                ''', (new_label_id, old_label_id))
                # Delete the old label
                cursor.execute('''
                    DELETE FROM label WHERE id = ?
                ''', (old_label_id,))
            else:
                # Update the label's name to new_username
                cursor.execute('''
                    UPDATE label
                    SET name = ?
                    WHERE id = ?
                ''', (new_username, old_label_id))
        conn.commit()




def get_user_by_email(email):
    """Retrieve a user by email.

    Args:
        email (str): The user's email.

    Returns:
        User or None: The User object if found, else None.
    """
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT email, username FROM user WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row:
            return User(email=row[0], username=row[1])
        else:
            return None


def create_user(email):
    """Create a new user with the given email.

    Args:
        email (str): The user's email.

    Returns:
        User: The newly created User object.
    """
    username = generate_random_username()
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO user (email, username) VALUES (?, ?)', (email, username))
        conn.commit()
        return User(email=email, username=username)


def get_stories_by_user_email(user_email):
    """Retrieve all stories associated with a user.

    Args:
        user_email (str): The user's email.

    Returns:
        list of Story: A list of Story objects.
    """
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, undefined_names, setting_and_style, main_challenge
            FROM story WHERE user_email = ?
        ''', (user_email,))
        stories = []
        rows = cursor.fetchall()
        for row in rows:
            story_id = row[0]
            story = Story(
                id=story_id,
                name=row[1],
                user_email=user_email,
                setting_and_style=row[3],
                main_challenge=row[4]
            )
            undefined_names_json = row[2]
            if undefined_names_json:
                story.undefined_names = json.loads(undefined_names_json)
            else:
                story.undefined_names = []

            # Load units associated with the story
            story.units = get_units_by_story_id(story_id)
            stories.append(story)
        return stories


def create_story(name, user_email, setting_and_style, main_challenge):
    """Create a new story.

    Args:
        name (str): Name of the story.
        user_email (str): The user's email.
        setting_and_style (str): The story's setting and style.
        main_challenge (str): The main challenge of the story.

    Returns:
        Story: The newly created Story object.
    """
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO story (name, user_email, undefined_names, setting_and_style, main_challenge)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, user_email, json.dumps([]), setting_and_style, main_challenge))
        conn.commit()
        story_id = cursor.lastrowid
        return Story(
            id=story_id,
            name=name,
            user_email=user_email,
            setting_and_style=setting_and_style,
            main_challenge=main_challenge
        )


def get_story_by_id(story_id):
    """Retrieve a story by its ID.

    Args:
        story_id (int): The story's ID.

    Returns:
        Story or None: The Story object if found, else None.
    """
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, user_email, undefined_names, setting_and_style, main_challenge
            FROM story WHERE id = ?
        ''', (story_id,))
        row = cursor.fetchone()
        if row:
            story = Story(
                id=row[0],
                name=row[1],
                user_email=row[2],
                setting_and_style=row[4],
                main_challenge=row[5]
            )
            undefined_names_json = row[3]
            if undefined_names_json:
                story.undefined_names = json.loads(undefined_names_json)
            else:
                story.undefined_names = []

            # Load units associated with the story
            story.units = get_units_by_story_id(story_id)
            return story
        else:
            return None


def add_unit_to_story(story_id, unit, user_email=None, is_copy=False):
    """Add a unit to a story and assign automatic labels."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()

        # Insert into unit table
        cursor.execute('''
            INSERT INTO unit (unit_type, name, story_id, features)
            VALUES (?, ?, ?, ?)
        ''', (unit.unit_type, unit.name, story_id, json.dumps(unit.features)))
        conn.commit()
        unit_id = cursor.lastrowid
        unit.id = unit_id
        unit.story_id = story_id

        # Insert into subclass table
        subclass_name = unit.unit_type
        if subclass_name:

            # Prepare columns and values based on feature_schema
            feature_schema = type(unit).feature_schema
            columns = []
            values = []
            for feature_name, feature_type in feature_schema.items():
                column_name = re.sub(r'\W', '', feature_name.replace(' ', '_'))
                value = unit.features.get(feature_name)

                if feature_type == list:
                    value = json.dumps(value) if value is not None else json.dumps([])
                elif feature_type == bool:
                    value = 1 if value else 0
                columns.append(column_name)
                values.append(value)

            columns_sql = ', '.join(['unit_id'] + columns)
            placeholders = ', '.join(['?'] * (len(values) + 1))
            values = [unit_id] + values

            sql_command = f'''
                INSERT INTO {subclass_name} ({columns_sql})
                VALUES ({placeholders})
            '''

            cursor.execute(sql_command, values)
            conn.commit()
    # Assign automatic labels
    story = get_story_by_id(story_id)
    username = None
    if user_email:
        user = get_user_by_email(user_email)
        username = user.username

    labels_to_assign = []

    # Label for story name
    story_label_id = get_or_create_label(story.name)
    labels_to_assign.append(story_label_id)

    # Label for unit_type
    unit_type_label_id = get_or_create_label(unit.unit_type)
    labels_to_assign.append(unit_type_label_id)

    # Label for creator username
    if username:
        username_label_id = get_or_create_label(username)
        labels_to_assign.append(username_label_id)

    # Label for "copy" if applicable
    if is_copy:
        copy_label_id = get_or_create_label('copy')
        labels_to_assign.append(copy_label_id)

    # Assign labels to unit
    assign_labels_to_units(labels_to_assign, [unit_id])

    return unit


def get_units_by_story_id(story_id):
    """Retrieve all units associated with a story.

    Args:
        story_id (int): The story's ID.

    Returns:
        list of Unit: A list of Unit objects.
    """
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, unit_type, name, features
            FROM unit WHERE story_id = ?
        ''', (story_id,))
        units = []
        rows = cursor.fetchall()
        for row in rows:
            unit_id = row[0]
            unit_type = row[1]
            name = row[2]
            features_json = row[3]
            features = json.loads(features_json) if features_json else {}

            # Create unit instance
            unit_class = get_unit_class(unit_type)  # Use the function here
            unit = unit_class(
                unit_type=unit_type,
                name=name,
                story_id=story_id,
                features=features,
                id=unit_id
            )
            units.append(unit)
        return units


def get_unit_by_name(story_id, unit_name):
    """Retrieve a unit by name within a story.

    Args:
        story_id (int): The story's ID.
        unit_name (str): The unit's name.

    Returns:
        Unit or None: The Unit object if found, else None.
    """
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, unit_type, name, features
            FROM unit WHERE story_id = ? AND name = ?
        ''', (story_id, unit_name))
        row = cursor.fetchone()
        if row:
            unit_id = row[0]
            unit_type = row[1]
            name = row[2]
            features_json = row[3]
            features = json.loads(features_json) if features_json else {}

            # Create unit instance
            unit_class = get_unit_class(unit_type)  # Use the function here
            unit = unit_class(
                id=unit_id,
                unit_type=unit_type,
                name=name,
                story_id=story_id,
                features=features
            )
            return unit
        else:
            return None


def update_unit(unit):
    """Update an existing unit.

    Args:
        unit (Unit): The unit to update.
    """
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()

        # Update unit table
        cursor.execute('''
            UPDATE unit
            SET name = ?, features = ?
            WHERE id = ?
        ''', (unit.name, json.dumps(unit.features), unit.id))
        conn.commit()

        # Update subclass table
        subclass_name = unit.unit_type
        if subclass_name:
            feature_schema = type(unit).feature_schema
            set_clauses = []
            values = []
            for feature_name, feature_type in feature_schema.items():
                column_name = re.sub(r'\W', '', feature_name.replace(' ', '_'))

                value = unit.features.get(feature_name)
                if feature_type == list:
                    value = json.dumps(value) if value is not None else json.dumps([])
                elif feature_type == bool:
                    value = 1 if value else 0
                set_clauses.append(f"{column_name} = ?")
                values.append(value)
            set_clause_sql = ', '.join(set_clauses)
            values.append(unit.id)
            cursor.execute(f'''
                UPDATE {subclass_name}
                SET {set_clause_sql}
                WHERE unit_id = ?
            ''', values)
            conn.commit()



def update_references_with_new_unit(unit, story, old_name=None):
    """Update references to a unit's old or undefined name in other units after naming or renaming.

    Args:
        unit (Unit): The unit that was updated or created.
        story (Story): The story containing the units.
        old_name (str or None): The old name of the unit before renaming, or None if it's newly defined.
    """
    # add new undefined names that this unit creates
    for feat, vals in unit.features.items():
        if isinstance(vals, list):
            for v in vals:
                related_unit = get_unit_by_name(story.id, v)
                if not related_unit and v not in story.undefined_names:
                    story.undefined_names.append(v)
    update_story(story)

    # Remove the unit name from undefined_names if present
    if unit.name in story.undefined_names:
        story.undefined_names.remove(unit.name)
        update_story(story)

    units = get_units_by_story_id(story.id)
    for other_unit in units:
        if other_unit.id == unit.id:
            continue  # Skip the updated unit itself
        updated = False
        feature_schema = type(other_unit).feature_schema
        for feature_name, expected_type in feature_schema.items():
            value = other_unit.features.get(feature_name)
            if expected_type == list and isinstance(value, list):
                if old_name and old_name in value:
                    new_value = [unit.name if v == old_name else v for v in value]
                    other_unit.features[feature_name] = new_value
                    updated = True
                elif unit.name in value and unit.name not in [u.name for u in units]:
                    # Replace undefined name with the defined unit's name
                    updated = True
            elif expected_type == str and isinstance(value, str):
                if value == old_name:
                    other_unit.features[feature_name] = unit.name
                    updated = True
                elif value == unit.name and unit.name not in [u.name for u in units]:
                    # Replace undefined name with the defined unit's name
                    other_unit.features[feature_name] = unit.name
                    updated = True
        if updated:
            update_unit(other_unit)


def update_story(story):
    """Update an existing story in the database."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE story
            SET undefined_names = ?
            WHERE id = ?
        ''', (json.dumps(story.undefined_names), story.id))
        conn.commit()


def get_or_create_label(label_name, user_email=None):
    """Retrieve label by name and user_email, or create it if not exists."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        if user_email:
            cursor.execute('''
                SELECT id FROM label WHERE name = ? AND user_email = ?
            ''', (label_name, user_email))
        else:
            cursor.execute('''
                SELECT id FROM label WHERE name = ? AND user_email IS NULL
            ''', (label_name,))
        row = cursor.fetchone()
        if row:
            return row[0]
        else:
            return create_label(label_name, user_email)

def create_label(label_name, user_email=None):
    """Create a new label."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO label (name, user_email) VALUES (?, ?)
        ''', (label_name, user_email))
        conn.commit()
        label_id = cursor.lastrowid
        return label_id

def assign_labels_to_units(label_ids, unit_ids):
    """Assign multiple labels to multiple units."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        entries = [(unit_id, label_id) for unit_id in unit_ids for label_id in label_ids]
        cursor.executemany('''
            INSERT OR IGNORE INTO unit_label (unit_id, label_id) VALUES (?, ?)
        ''', entries)
        conn.commit()

def get_all_labels():
    """Retrieve all labels."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name FROM label
        ''')
        labels = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        return labels



def get_units_by_label_filters(include_label_ids, exclude_label_ids, search_query=None):
    """Retrieve units filtered by including and excluding labels, and search query."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()

        # Base query
        query = '''
            SELECT DISTINCT u.id, u.unit_type, u.name, u.features, u.story_id,
                   GROUP_CONCAT(l.name) as labels
            FROM unit u
            LEFT JOIN unit_label ul ON u.id = ul.unit_id
            LEFT JOIN label l ON ul.label_id = l.id
        '''
        params = []

        conditions = []

        # Include labels (logical OR)
        if include_label_ids:
            include_placeholders = ','.join(['?'] * len(include_label_ids))
            query += f'''
                JOIN unit_label ul_include ON u.id = ul_include.unit_id AND ul_include.label_id IN ({include_placeholders})
            '''
            params.extend(include_label_ids)

        # Exclude labels
        if exclude_label_ids:
            exclude_placeholders = ','.join(['?'] * len(exclude_label_ids))
            conditions.append(f'''
                u.id NOT IN (
                    SELECT unit_id
                    FROM unit_label
                    WHERE label_id IN ({exclude_placeholders})
                )
            ''')
            params.extend(exclude_label_ids)

        # Search query
        if search_query:
            conditions.append('''(u.name LIKE ? OR u.unit_type LIKE ? OR u.features LIKE ?)''')
            params.extend([f'%{search_query}%'] * 3)

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' GROUP BY u.id'

        cursor.execute(query, params)
        units = []
        for row in cursor.fetchall():
            unit_id = row[0]
            unit_type = row[1]
            name = row[2]
            features_json = row[3]
            features = json.loads(features_json) if features_json else {}
            story_id = row[4]
            labels = row[5].split(',') if row[5] else []

            unit_class = get_unit_class(unit_type)
            unit = unit_class(
                id=unit_id,
                unit_type=unit_type,
                name=name,
                story_id=story_id,
                features=features
            )
            unit.labels = labels  # Attach labels to unit
            units.append(unit)
        return units


def get_labels_by_user(user_email):
    """Retrieve all labels created by the user."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name FROM label WHERE user_email = ?
        ''', (user_email,))
        labels = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        return labels

def get_units_by_labels(label_ids):
    """Retrieve units associated with the given labels."""
    if not label_ids:
        return []

    placeholders = ','.join(['?' for _ in label_ids])
    query = f'''
        SELECT DISTINCT u.id, u.unit_type, u.name, u.features, u.story_id
        FROM unit u
        JOIN unit_label ul ON u.id = ul.unit_id
        WHERE ul.label_id IN ({placeholders})
    '''
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(query, label_ids)
        units = []
        for row in cursor.fetchall():
            unit_id = row[0]
            unit_type = row[1]
            name = row[2]
            features_json = row[3]
            features = json.loads(features_json) if features_json else {}
            story_id = row[4]

            unit_class = get_unit_class(unit_type)
            unit = unit_class(
                id=unit_id,
                unit_type=unit_type,
                name=name,
                story_id=story_id,
                features=features
            )
            units.append(unit)
        return units

def get_all_units_with_labels():
    """Retrieve all units along with their labels."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.unit_type, u.name, u.features, u.story_id,
                   GROUP_CONCAT(l.name) as labels
            FROM unit u
            LEFT JOIN unit_label ul ON u.id = ul.unit_id
            LEFT JOIN label l ON ul.label_id = l.id
            GROUP BY u.id
        ''')
        units = []
        for row in cursor.fetchall():
            unit_id = row[0]
            unit_type = row[1]
            name = row[2]
            features_json = row[3]
            features = json.loads(features_json) if features_json else {}
            story_id = row[4]
            labels = row[5].split(',') if row[5] else []

            unit_class = get_unit_class(unit_type)
            unit = unit_class(
                id=unit_id,
                unit_type=unit_type,
                name=name,
                story_id=story_id,
                features=features
            )
            unit.labels = labels  # Attach labels to unit
            units.append(unit)
        return units

def get_unit_by_id(unit_id):
    """Retrieve a unit by its ID."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, unit_type, name, features, story_id
            FROM unit WHERE id = ?
        ''', (unit_id,))
        row = cursor.fetchone()
        if row:
            unit_id = row[0]
            unit_type = row[1]
            name = row[2]
            features_json = row[3]
            features = json.loads(features_json) if features_json else {}
            story_id = row[4]

            unit_class = get_unit_class(unit_type)
            unit = unit_class(
                id=unit_id,
                unit_type=unit_type,
                name=name,
                story_id=story_id,
                features=features
            )
            return unit
        else:
            return None


def delete_unit_from_story(unit):
    """Delete a unit from the database."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        # Delete the unit from the 'unit' table
        cursor.execute('''
            DELETE FROM unit WHERE id = ?
        ''', (unit.id,))
        conn.commit()


