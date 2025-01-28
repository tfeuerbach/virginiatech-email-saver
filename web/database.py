from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Alias db.session as db_session for compatibility with tests
db_session = db.session