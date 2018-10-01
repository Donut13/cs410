from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import click

db = SQLAlchemy()

class User(db.Model, UserMixin):

    name = db.Column(db.String(64), primary_key=True)
    password = db.Column(db.String(64), nullable=False)

    def __repr__(self):
        return '<User name={!r}>'.format(self.name)

    def get_id(self):
        return self.name

class Game(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user1_name = db.Column(db.String(64), db.ForeignKey('user.name'), nullable=False)
    user1 = db.relationship('User', foreign_keys=[user1_name])
    user1_move_first = db.Column(db.Boolean, nullable=False)
    user2_name = db.Column(db.String(64), db.ForeignKey('user.name'))
    user2 = db.relationship('User', foreign_keys=[user2_name])

    def __repr__(self):
        return '<Game id={!r} user1_name={!r} user2_name={!r}>'.format(
            self.id, self.user1_name, self.user2_name,
        )

class Move(db.Model):

    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), primary_key=True)
    game = db.relationship('Game', backref=db.backref('moves', order_by='Move.time'))
    row = db.Column(db.Integer, primary_key=True)
    column = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, nullable=False) # UTC time zone

    def __repr__(self):
        return '<Move game_id={!r} row={!r} column={!r}>'.format(self.game_id, self.row, self.column)

@click.command('init-db')
@with_appcontext
def init_db():
    db.create_all()
    user = User(name='testuser1', password='111111')
    db.session.add(user)
    user = User(name='testuser2', password='222222')
    db.session.add(user)
    db.session.commit()
    click.echo('Initialized DB')
