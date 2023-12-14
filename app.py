from flask import Flask, render_template, request, jsonify, redirect, url_for
from validation.validacoesLogin import verificar_credenciais
from database import configure_database, db, Usuario, Repositor, Reposicao
from sqlalchemy import func
import json
from decimal import Decimal
from datetime import date 

app = Flask(__name__)

database_uri = 'mysql+mysqlconnector://root:Celeste123@localhost/papercontrolsystem'
configure_database(app, database_uri)
db.init_app(app)


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/loginadm', methods=['GET', 'POST'])
def loginadm():
    dados_predios = db.session.query(
        Reposicao.predio,
        func.sum(Reposicao.quantidade_reposicao).label('total_reposicao')
    ).group_by(Reposicao.predio).all()

    dados_formulario = db.session.query(
        Reposicao.predio,
        func.count(Reposicao.id_reposicao).label('reposicoes_pendentes')
    ).filter(Reposicao.status_reposicao == 'pendente').group_by(Reposicao.predio).all()

    dados_predios_json = json.dumps(
        [{'predio': item.predio, 'total_reposicao': item.total_reposicao} for item in dados_predios], default=decimal_default)

    return render_template('loginadm.html', dados_predios=dados_predios_json, dados_formulario=dados_formulario)


@app.route('/login', methods=['GET', 'POST'])
def fazer_login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(email=email, senha=senha).first()

        # Debugging - imprima informações relevantes
        print("Usuário (login):", usuario)

        if usuario:
            if usuario.tipo_user == "administrador":
                print("Redirecionando para /loginadm")
                return redirect(url_for('loginadm', email=email))
            elif usuario.tipo_user == "repositor":
                return redirect(url_for('loginrec', email=email))
            else:
                return render_template('login.html', mensagem_falha=True)

    return render_template('login.html')

@app.route('/loginrec', methods=['GET', 'POST'])
def loginrec():
    # Obtenha o email da query string
    email_exemplo = request.args.get('email')
    usuario = Usuario.query.filter_by(
        email=email_exemplo, tipo_user="repositor").first()

    if usuario and usuario.repositor:
        # Acesse o objeto Repositor diretamente
        repositorio = usuario.repositor
        estoque_repositor = repositorio.estoque
        return render_template('loginrec.html', quantidade_estoque=estoque_repositor, mensagem_erro=None)
    else:
        print("Acesso não autorizado.")
        return redirect(url_for('fazer_login'))
    

@app.route('/abastecimento', methods=['GET', 'POST'])
def abastecimento():
    estoque_repositor = None
    mensagem = None

    if request.method == 'POST':
        print("Formulário enviado!")

        predio = request.form['predio']
        andar = request.form['andar']
        ilha = request.form['ilha']
        quantidade_reposicao = int(request.form['quantidade_reposicao'])

        print(f"Dados do formulário: Predio={predio}, Andar={andar}, Ilha={ilha}, Quantidade={quantidade_reposicao}")

        try:
            repositorio = Repositor.query.get(1)
            if repositorio:
                estoque_repositor = repositorio.estoque
                print(f"Estoque do Repositório: {estoque_repositor}")

            nova_reposicao = Reposicao(
                id_repositor=1,
                data_reposicao=date.today(),
                tipo_reposicao='Reabastecimento',
                quantidade_reposicao=quantidade_reposicao,
                andar=andar,
                ilha=ilha,
                estoque_restante=0,
                predio=predio,
                status_reposicao='pendente'
            )

            db.session.add(nova_reposicao)
            db.session.commit()

            mensagem = "Reabastecimento registrado no banco de dados!"
            print(mensagem)

        except Exception as e:
            mensagem = f"Erro ao registrar reabastecimento no banco de dados: {str(e)}"
            print(mensagem)

        # Redirecionamento para evitar reenvio do formulário ao atualizar a página
        return redirect(url_for('index', mensagem=mensagem))

    return render_template('abastecimento.html', quantidade_estoque=estoque_repositor, mensagem_erro=None, mensagem=mensagem)


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

        repositors = Repositor.query.all()

        repositors_data = [{
            'id_repositor': repositor.id_repositor,
            'usuario_id': repositor.usuario_id,
            'estoque:': repositor.estoque
        }for repositor in repositors]
        return jsonify(users_data, repositors_data)
    except Exception as e:
        return f'Erro ao verificar a conexão: {str(e)}'


if __name__ == '__main__':
    app.run(debug=True)
