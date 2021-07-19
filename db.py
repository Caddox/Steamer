import sqlite3
from flask import g

def get_db():
    '''
    Function used by Flask to acquire the sqlite database
    '''
    if 'db' not in g:
        g.db = sqlite3.connect(
            "steamer.db",
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    '''
    Funciton used by Flask to remove the database context.
    '''
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_app(app):
    '''
    Function used by Flask to setup the database teardown
    '''
    app.teardown_appcontext(close_db)