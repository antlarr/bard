from bard.musicdatabase import MusicDatabase
import bard.config as config
from bcrypt import hashpw, gensalt
import getpass


class User:
    def __init__(self, username=''):
        """Create a User object that can be used with Flask-Login."""
        self.username = username
        self.userID = MusicDatabase.getUserID(username)
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
        self.is_admin = False

    def get_id(self):
        return self.username

    def validate(self, possible_password):
        self.is_authenticated = False
        hashed = MusicDatabase.userPassword(self.username)
        if not hashed:
            return

        possible_password = possible_password.encode('utf-8')
        if hashpw(possible_password, hashed) == hashed:
            self.is_authenticated = True


def requestNewPassword(username):
    if not username:
        username = config.config['username']
    userID = MusicDatabase.getUserID(username)

    prompt = f'Enter the new password for user \'{username}\': '
    password = getpass.getpass(prompt)

    hashed = hashpw(password.encode('utf-8'), gensalt())
    if MusicDatabase.setUserPassword(userID, hashed):
        print('password changed successfully')
    else:
        print('Error changing password')
