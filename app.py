from flask import Flask, render_template, request, jsonify, redirect, url_for
from validation.validacoesLogin import verificar_credenciais
from flask_sqlalchemy import SQLAlchemy
from database import configure_database, db, Usuario, Repositor

app = Flask(__name__)

# Configure o banco de dados
database_uri = 'mysql+mysqlconnector://root:Celeste123@localhost/papercontrolsystem'
configure_database(app, database_uri)
db.init_app(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def fazer_login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(email=email, senha=senha).first()

        if usuario:
            if usuario.tipo_user == "administrador":
                return redirect(url_for('pagina_administrador'))
            elif usuario.tipo_user == "repositor":
                return redirect(url_for('loginrec', email=email))  # Passe o email como parâmetro para a rota
            else:
                return render_template('login.html', mensagem_falha=True)

    return render_template('login.html')


@app.route('/loginrec', methods=['GET', 'POST'])
def loginrec():
    email_exemplo = request.args.get('email')  # Obtenha o email da query string
    usuario = Usuario.query.filter_by(email=email_exemplo, tipo_user="repositor").first()

    if usuario and usuario.repositor:
        repositor = usuario.repositor
        estoque_repositor = repositor.estoque
        return render_template('loginrec.html', quantidade_estoque=estoque_repositor, mensagem_erro=None)
    else:
        print("Acesso não autorizado.")
        return redirect(url_for('fazer_login'))



@app.route('/verificar_conexao')
def verificar_conexao():
    try:
        users = Usuario.query.all()

        users_data = [{
            'id_user': user.id_user,
            'email': user.email,
            'senha': user.senha,
            'tipo_user': user.tipo_user
        }for user in users] 
        # Retorna os dados como JSON
        return jsonify(users_data)

    except Exception as e:
        return f'Erro ao verificar a conexão: {str(e)}'


if __name__ == '__main__':
    app.run(debug=True)
