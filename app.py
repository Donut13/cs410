from models import users, metadata, games, moves
from sqlalchemy.sql import select
from tornado import gen
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from tornado.options import define, options, parse_command_line
from tornado.web import Application, RequestHandler, HTTPError
import os.path
import sqlalchemy
from datetime import datetime

define("port", default=5000, type=int)
define("debug", default=True)
define("db_url", default='sqlite:///./development.db')
define('init_db', default=False)

engine = None

def run_sql(statement, callback=None):
    def job():
        with engine.connect() as conn:
            ans = conn.execute(statement)
            if callback: ans = callback(ans)
            return ans
    return IOLoop.current().run_in_executor(None, job)

class BaseHandler(RequestHandler):

    def get_current_user(self):
        ans = self.get_secure_cookie('user')
        if ans is None: return None
        return ans.decode()

class RootHandler(BaseHandler):

    def get(self):
        self.render('index.html', env=('development' if options.debug else 'production.min'))

class WhoAmIHandler(BaseHandler):

    def get(self):
        ans = {}
        if self.current_user is not None: ans['name'] = self.current_user
        self.write(ans)

class LoginHandler(BaseHandler):

    @gen.coroutine
    def post(self):
        user = json_decode(self.request.body)
        user2 = yield run_sql(select([users.c.password]).where(users.c.name == user['name']),
                              lambda res: res.fetchone())
        if user2 is None or user2['password'] != user['password']: raise HTTPError(401)
        self.set_secure_cookie('user', user['name'])
        self.set_status(204)
        self.finish()

class Games(BaseHandler):

    @gen.coroutine
    def post(self):
        game = json_decode(self.request.body)
        ins = games.insert().values(user1=self.current_user, user1_move_first=game['move_first'])
        game_id, = yield run_sql(ins, lambda res: res.inserted_primary_key)
        self.write({'game_id': game_id})

class Game(BaseHandler):

    @gen.coroutine
    def get(self, game_id):
        game_id = int(game_id)
        sel = select([
            games.c.user1, games.c.user2, games.c.user1_move_first
        ]).where(games.c.id == game_id)
        user1, user2, user1_move_first = yield run_sql(sel, lambda r: r.fetchone())
        ans = {'user1_name': user1, 'user1_move_first': user1_move_first}
        if user2 is not None: ans['user2_name'] = user2
        sel = select([moves.c.row, moves.c.column]).where(moves.c.game == game_id)
        ans['moves'] = [(move['row'], move['column'])
                        for move in (yield run_sql(sel, lambda r: r.fetchall()))]
        self.write(ans)

    @gen.coroutine
    def post(self, game_id):
        game_id = int(game_id)
        sel = select([games.c.user1, games.c.user2]).where(games.c.id == game_id)
        user1, user2 = yield run_sql(sel, lambda r: r.fetchone())
        if user1 != self.current_user:
            if user2 is None:
                upd = games.update().where(games.c.id == game_id).values(user2=self.current_user)
                yield run_sql(upd)
            elif user2 != self.current_user:
                raise HTTPError(403)
        self.set_status(204)
        self.finish()

class Moves(BaseHandler):

    @gen.coroutine
    def post(self, game_id):
        game_id = int(game_id)
        sel = select([
            games.c.user1, games.c.user2, games.c.user1_move_first,
        ]).where(games.c.id == game_id)
        user1, user2, user1_move_first = yield run_sql(sel, lambda r: r.fetchone())
        sel = select([sqlalchemy.func.count()]).select_from(moves).where(moves.c.game == game_id)
        n, = yield run_sql(sel, lambda r: r.fetchone())
        if (n % 2 == 0) == user1_move_first:
            if user1 != self.current_user: raise HTTPError(403)
        else:
            if user2 != self.current_user: raise HTTPError(403)
        move = json_decode(self.request.body)
        ins = moves.insert().values(game=game_id, row=move['row'], column=move['column'],
                                    time=datetime.utcnow())
        yield run_sql(ins)
        self.set_status(204)
        self.finish()

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
         (r'/games/(\d+)/moves', Moves)),
        static_path=os.path.join(os.path.dirname(__file__), 'static'),
        debug=options.debug,
        cookie_secret='42',
    )
    app.listen(options.port)
    IOLoop.current().start()

if __name__ == '__main__' and '__file__' in globals():
    main()
