from flask import Flask, jsonify, render_template
from database import configure_database, Usuario

app = Flask(__name__)

# Configure o banco de dados
configure_database(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/verificar_conexao')
def verificar_conexao():
    try:
        user = Usuario.query.first()

        # Retorna os dados como JSON
        return jsonify({
            'id_user': user.id_user,
            'nome': user.Nome,
            'email': user.Email,
            'cpf': user.CPF,
            'senha': user.Senha
        })

    except Exception as e:
        return f'Erro ao verificar a conexão: {str(e)}'


if __name__ == '__main__':
    app.run(debug=True)
