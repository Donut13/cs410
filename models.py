from sqlalchemy import Table, Column, String, MetaData, Integer, ForeignKey, Boolean, DateTime

metadata = MetaData()

users = Table(
    'users', metadata,
    Column('name', String(64, convert_unicode=True), primary_key=True),
    Column('password', String(64, convert_unicode=True), nullable=False),
)

games = Table(
    'games', metadata,
    Column('id', Integer, primary_key=True),
    Column('user1', String(64, convert_unicode=True), ForeignKey('users.name'), nullable=False),
    Column('user2', String(64, convert_unicode=True), ForeignKey('users.name')),
    Column('user1_move_first', Boolean, nullable=False),
)

moves = Table(
    'moves', metadata,
    Column('game', Integer, ForeignKey('games.id'), primary_key=True),
    Column('row', Integer, primary_key=True),
    Column('column', Integer, primary_key=True),
    Column('time', DateTime, nullable=False), # UTC time zone
)
