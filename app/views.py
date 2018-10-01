from flask import Blueprint, render_template, current_app, request, abort, jsonify
from .models import db, User, Game, Move
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from datetime import datetime

login_manager = LoginManager()
root = Blueprint('root', __name__)

@login_manager.user_loader
def load_user(name):
    return User.query.get(name)

@root.route('/', methods=['GET'])
def index():
    env = current_app.config['ENV']
    if env == 'production': env += '.min'
    return render_template('index.html', env=env)

@root.route('/login', methods=['POST'])
def login():
    user = User.query.get(request.json['name'])
    if user is None or user.password != request.json['password']: abort(401)
    login_user(user)
    return ('', 204)

@root.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return ('', 204)

@root.route('/whoami', methods=['GET'])
def whoami():
    ans = {}
    if current_user.is_authenticated: ans['name'] = current_user.name
    return jsonify(ans)

@root.route('/games', methods=['POST'])
@login_required
def games():
    game = Game(user1_name=current_user.name, user1_move_first=request.json['move_first'])
    db.session.add(game)
    db.session.commit()
    return jsonify({'game_id': game.id})

@root.route('/games/<int:game_id>', methods=['GET'])
def game(game_id):
    game = Game.query.get(game_id)
    if game is None: abort(404)
    ans = {'user1_name': game.user1_name, 'user1_move_first': game.user1_move_first}
    if game.user2_name: ans['user2_name'] = game.user2_name
    ans['moves'] = [(move.row, move.column) for move in game.moves]
    return jsonify(ans)

@root.route('/games/<int:game_id>/moves', methods=['POST'])
@login_required
def game_moves(game_id):
    game = Game.query.get(game_id)
    if game is None: abort(404)
    if (len(game.moves) % 2 == 0) == game.user1_move_first:
        if game.user1.name != current_user.name: abort(403)
    else:
        if game.user2.name != current_user.name: abort(403)
    move = Move(game_id=game_id, row=request.json['row'], column=request.json['column'],
                time=datetime.utcnow())
    db.session.add(move)
    db.session.commit()
    return ('', 204)
