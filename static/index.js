'use strict';

const {createElement} = React;
const {
  Button,
  Card,
  CardActions,
  CardContent,
  Checkbox,
  FormControlLabel,
  Grid,
  TextField,
  Typography,
} = window['material-ui'];

class UserLogin extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      name: '',
      password: '',
    };
    this.login = this.login.bind(this);
  }

  render() {
    return createElement(
      'form', null,
      createElement(TextField, {
        label: "Name", autoComplete: 'username', value: this.state.name,
        onChange: e => this.setState({name: e.target.value}),
      }),
      createElement(TextField, {
        label: "Password", type: 'password', autoComplete: "current-password",
        value: this.state.password, onChange: e => this.setState({password: e.target.value}),
      }),
      createElement(Button, {onClick: this.login}, "Login"),
    );
  }

  login() {
    axios.post('/login', {name: this.state.name, password: this.state.password}).then(() => {
      this.props.onLoginSuccess(this.state.name);
    });
  }
}

class NewGame extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      move_first: true,
    };
  }

  render() {
    const create = () => {
      axios.post('/games', {move_first: this.state.move_first}).then(res => {
        this.props.onCreate(res.data.game_id);
      });
    };
    return createElement(
      Card, {},
      createElement(
        CardContent, null,
        createElement(Typography, {variant: 'headline'}, "Create New Game"),
      ),
      createElement(
        CardActions, null,
        createElement(FormControlLabel, {
          control: createElement(Checkbox, {
            checked: this.state.move_first,
            onChange: e => this.setState({move_first: e.target.checked}),
          }),
          label: "Move First",
        }),
        createElement(Button, {onClick: create}, "Create"),
      ),
    );
  }
}

class JoinGame extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      game_id: '',
    };
  }

  render() {
    return createElement(
      Card, null,
      createElement(
        CardContent, null,
        createElement(Typography, {variant: 'headline'}, "Join Existing Game"),
      ),
      createElement(
        CardActions, null,
        createElement(TextField, {
          label: "Game ID", value: this.state.game_id,
          onChange: e => this.setState({game_id: e.target.value}),
        }),
        createElement(Button, {onClick: () => this.props.onJoin(this.state.game_id)}, "Join"),
      ),
    );
  }
}

class Game extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      userX: null,
      userO: null,
      board: [[null, null, null], [null, null, null], [null, null, null]],
      x_is_next: true,
      winner: null,
    };
  }

  myTurn() {
    return (this.props.user == this.state.userX) == this.state.x_is_next;
  }

  makeMove(i, j) {
    this.state.board[i][j] = this.state.x_is_next ? 'X' : 'O';
    this.setState({board: this.state.board, x_is_next: !this.state.x_is_next});
  }

  waitOpponent() {
    axios.post(`/games/${this.props.game_id}/wait`).then(res => {
      const [i, j] = res.data.move;
      this.makeMove(i, j);
      this.setState({winner: res.data.winner});
    });
  }

  componentDidMount() {
    axios.get(`/games/${this.props.game_id}`).then(res => {
      this.setState({
        userX: (res.data.user1_move_first ? res.data.user1 : res.data.user2),
        userO: (res.data.user1_move_first ? res.data.user2 : res.data.user1),
        winner: res.data.winner,
      });
      for (let ij of res.data.moves) {
        const [i, j] = ij;
        this.makeMove(i, j);
      }
      if (!this.state.winner && !this.myTurn()) this.waitOpponent();
    });
  }

  renderSquare(i, j) {
    const onClick = () => {
      if (!this.state.board[i][j] && !this.state.winner && this.myTurn()) axios.post(
        `/games/${this.props.game_id}/moves`, [i, j],
      ).then(res => {
        this.makeMove(i, j);
        this.setState({winner: res.data.winner});
        if (!res.data.winner) this.waitOpponent();
      });
    };
    return createElement('button', {className: 'square', onClick}, this.state.board[i][j]);
  }

  render() {
    return createElement(
      Card, null,
      createElement(
        CardContent, null,
        createElement(Typography, {variant: 'headline'}, `Game ${this.props.game_id}`),
        createElement(Typography, {component: 'p'}, `X: ${this.state.userX}`),
        createElement(Typography, {component: 'p'}, `O: ${this.state.userO}`),
        createElement(Typography, {component: 'p'}, `Next Player: ${this.state.x_is_next ? 'X' : 'O'}`),
        createElement(Typography, {component: 'p'}, `Winner: ${this.state.winner}`),
        createElement(
          'div', null,
          createElement(
            'div', {className: 'board-row'},
            this.renderSquare(0, 0),
            this.renderSquare(0, 1),
            this.renderSquare(0, 2),
          ),
          createElement(
            'div', {className: 'board-row'},
            this.renderSquare(1, 0),
            this.renderSquare(1, 1),
            this.renderSquare(1, 2),
          ),
          createElement(
            'div', {className: 'board-row'},
            this.renderSquare(2, 0),
            this.renderSquare(2, 1),
            this.renderSquare(2, 2),
          ),
        ),
      ),
    );
  }
}

class App extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      user: null,
      game_id: null,
    };
  }

  componentDidMount() {
    axios.get('/whoami').then(res => {
      const {name} = res.data;
      if (name) this.setState({user: name});
    });
  }

  render() {
    if (!this.state.user) {
      return createElement(UserLogin, {onLoginSuccess: user => this.setState({user: user})});
    }
    if (!this.state.game_id) {
      return createElement(
        Grid, {container: true, spacing: 24},
        createElement(
          Grid, {item: true, xs: 3},
          createElement(NewGame, {onCreate: game_id => this.setState({game_id: game_id})}),
        ),
        createElement(
          Grid, {item: true, xs: 3},
          createElement(JoinGame, {
            onJoin: game_id => {
              axios.post(`/games/${game_id}`).then(() => this.setState({game_id: game_id}));
            },
          }),
        ),
      );
    }
    return createElement(Game, {game_id: this.state.game_id, user: this.state.user});
  }
}

const root = document.querySelector('#root');
ReactDOM.render(createElement(App), root);
