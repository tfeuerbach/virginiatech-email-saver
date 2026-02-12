from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Alias for test compatibility
db_session = db.session
