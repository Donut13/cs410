from asyncio import CancelledError
from datetime import datetime
from models import users, metadata, games, moves
from sqlalchemy.sql import select
from tornado import gen
from tornado.concurrent import Future
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from tornado.options import define, options, parse_command_line
from tornado.web import Application, RequestHandler, HTTPError
import os.path
import sqlalchemy

define("port", default=5000, type=int)
define("debug", default=True)
define("db_url", default='sqlite:///./development.db')
define('init_db', default=False)

engine = None
opponent_move = {}

def winner(game):
    board = [[None] * 3 for _ in range(3)]
    users = (game['user1'], game['user2'])
    k = 0 if game['user1_move_first'] else 1
    for i, j in game['moves']:
        board[i][j] = k % 2
        k += 1
    for i in range(3):
        if board[i][0] is not None and board[i][0] == board[i][1] and board[i][0] == board[i][2]:
            return users[board[i][0]]
    for j in range(3):
        if board[0][j] is not None and board[0][j] == board[1][j] and board[0][j] == board[2][j]:
            return users[board[0][j]]
    if board[0][0] is not None and board[0][0] == board[1][1] and board[0][0] == board[2][2]:
        return users[board[0][0]]
    if board[0][2] is not None and board[0][2] == board[1][1] and board[0][2] == board[2][0]:
        return users[board[0][2]]
    return None

def game_details(game_id):
    with engine.connect() as conn:
        sel = select([
            games.c.user1, games.c.user2, games.c.user1_move_first
        ]).where(games.c.id == game_id)
        user1, user2, user1_move_first = conn.execute(sel).fetchone()
        ans = {'user1': user1, 'user1_move_first': user1_move_first}
        if user2 is not None: ans['user2'] = user2
        sel = select([
            moves.c.row, moves.c.column,
        ]).where(moves.c.game == game_id).order_by(moves.c.time)
        ans['moves'] = [(move['row'], move['column'])
                        for move in conn.execute(sel).fetchall()]
    w = winner(ans)
    if w is not None: ans['winner'] = w
    return ans

def whose_turn(game):
    n = len(game['moves'])
    return game['user1'] if (n % 2 == 0) == game['user1_move_first'] else game.get('user2')

class BaseHandler(RequestHandler):

    def get_current_user(self):
        ans = self.get_secure_cookie('user')
        if ans is None: return None
        return ans.decode()

    def ensure_authenticated(self):
        if self.current_user is None: raise HTTPError(401)

class RootHandler(BaseHandler):

    def get(self):
        self.render('index.html', env=('development' if options.debug else 'production.min'))

class WhoAmIHandler(BaseHandler):

    def get(self):
        ans = {}
        if self.current_user is not None: ans['name'] = self.current_user
        self.write(ans)

class LoginHandler(BaseHandler):

    def post(self):
        user = json_decode(self.request.body)
        sel = select([users.c.password]).where(users.c.name == user['name'])
        with engine.connect() as conn:
            user2 = conn.execute(sel).fetchone()
        if user2 is None or user2['password'] != user['password']: raise HTTPError(401)
        self.set_secure_cookie('user', user['name'])
        self.set_status(204)
        self.finish()

class Games(BaseHandler):

    def post(self):
        self.ensure_authenticated()
        game = json_decode(self.request.body)
        ins = games.insert().values(user1=self.current_user, user1_move_first=game['move_first'])
        with engine.connect() as conn:
            game_id, = conn.execute(ins).inserted_primary_key
        self.write({'game_id': game_id})

class Game(BaseHandler):

    def get(self, game_id):
        self.write(game_details(int(game_id)))

    def post(self, game_id):
        self.ensure_authenticated()
        game_id = int(game_id)
        sel = select([games.c.user1, games.c.user2]).where(games.c.id == game_id)
        with engine.connect() as conn:
            user1, user2 = conn.execute(sel).fetchone()
            if user1 != self.current_user:
                if user2 is None:
                    upd = games.update().where(games.c.id == game_id).values(user2=self.current_user)
                    conn.execute(upd)
                elif user2 != self.current_user:
                    raise HTTPError(403)
        self.set_status(204)
        self.finish()

class Moves(BaseHandler):

    def post(self, game_id):
        self.ensure_authenticated()
        game = game_details(int(game_id))
        if 'winner' in game: raise HTTPError(400)
        if whose_turn(game) != self.current_user: raise HTTPError(403)
        move = json_decode(self.request.body)
        with engine.connect() as conn:
            ins = moves.insert().values(game=game_id, row=move['row'], column=move['column'],
                                        time=datetime.utcnow())
            conn.execute(ins)
        game['moves'].append((move['row'], move['column']))
        event = {'move': game['moves'][-1]}
        w = winner(game)
        if w is not None: event['winner'] = w
        if game_id in opponent_move:
            for fut in opponent_move[game_id]: fut.set_result(event)
            del opponent_move[game_id]
        self.write(event)

class Wait(BaseHandler):

    @gen.coroutine
    def post(self, game_id):
        self.ensure_authenticated()
        game_id = int(game_id)
        game = game_details(game_id)
        if self.current_user not in (game['user1'], game.get('user2')): raise HTTPError(403)
        event = {}
        if whose_turn(game) == self.current_user:
            if game['moves']: event['move'] = game['moves'][-1]
            if 'winner' in game: event['winner'] = game['winner']
        else:
            if game_id not in opponent_move: opponent_move[game_id] = []
            self.wait_future = Future()
            opponent_move[game_id].append(self.wait_future)
            try:
                event = yield self.wait_future
            except CancelledError:
                pass
        if not self.request.connection.stream.closed():
            self.write(event)

    def on_connection_close(self):
        if self.wait_future:
            self.wait_future.cancel()

def main():
    parse_command_line()
    global engine
    engine = sqlalchemy.create_engine(options.db_url, echo=options.debug, convert_unicode=True)
    if options.init_db:
        metadata.create_all(engine)
        with engine.connect() as conn:
            conn.execute(users.insert(), [
                {'name': 'tester1', 'password': '111111'},
                {'name': 'tester2', 'password': '222222'},
            ])
        return
    app = Application(
        (('/', RootHandler),
         ('/whoami', WhoAmIHandler),
         ('/login', LoginHandler),
         ('/games', Games),
         (r'/games/(\d+)', Game),
         (r'/games/(\d+)/moves', Moves),
         (r'/games/(\d+)/wait', Wait)),
        static_path=os.path.join(os.path.dirname(__file__), 'static'),
        debug=options.debug,
        cookie_secret='42',
    )
    app.listen(options.port)
    IOLoop.current().start()

if __name__ == '__main__' and '__file__' in globals():
    main()
