from flask import Flask, render_template, request, redirect, url_for, jsonify, current_app
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user
from database import configure_database, db, Usuario, Reposicao, InfoAndar, Reabastecimento
from sqlalchemy import func
import json
from decimal import Decimal
from datetime import datetime, date
import secrets
import logging
 
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
print(app.secret_key)
database_uri = 'mysql+mysqlconnector://root:Celeste123@localhost/papercontrol'
configure_database(
    app, 'mysql+mysqlconnector://root:Celeste123@localhost/papercontrol')
login_manager = LoginManager(app)
login_manager.login_view = 'fazer_login'
logging.basicConfig(filename='erro.log', level=logging.INFO)
 
 
class User(UserMixin):
    def __init__(self, user_id, tipo_user=None):
        self.id = user_id
        self.tipo_user = tipo_user
 
    @staticmethod
    def load_user(user_id):
        return Usuario.query.get(int(user_id))
 
 
@login_manager.user_loader
def load_user(user_id):
    usuario = Usuario.query.get(int(user_id))
    if usuario:
        return User(usuario.id_user, usuario.tipo_user)
    return None
 
 
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
 
 
@app.route('/')
@login_required
def index():
    if current_user.tipo_user == 'repositor':
        return redirect(url_for('loginrec'))
    elif current_user.tipo_user == 'administrador':
        return redirect(url_for('loginadm'))
    else:
        return render_template('login.html')
 
 
@app.route('/login', methods=['GET', 'POST'])
def fazer_login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
 
        usuario = Usuario.query.filter_by(email=email, senha=senha).first()
 
        if usuario:
            user = User(usuario.id_user, usuario.tipo_user)
            login_user(user)
 
            if usuario.tipo_user == 'repositor':
                print(f"usuario logado: {user}")
                return redirect(url_for('loginrec'))
            elif usuario.tipo_user == 'administrador':
                print(f"usuario logado: {user}")
                return redirect(url_for('loginadm'))
 
        else:
            # Se as credenciais do usuário não forem válidas, você pode retornar uma mensagem de erro.
            return render_template('login.html', mensagem_erro="Credenciais inválidas. Tente novamente.")
 
    # Se o método não for POST, apenas renderize o template de login.
    return render_template('login.html')
 
 
@app.route('/loginrec', methods=['GET', 'POST'])
@login_required
def loginrec():
    print("Rota loginrec acionada.")
    usuario = Usuario.query.filter_by(
        id_user=current_user.id, tipo_user="repositor").first()
 
    if usuario:
        # Acesse o estoque diretamente da tabela de usuários
        estoque = usuario.estoque
        return render_template('loginrec.html', quantidade_estoque=estoque, mensagem_erro=None)
    else:
        print("Acesso não autorizado.")
        return redirect(url_for('fazer_login'))
 
 
@app.route('/loginadm', methods=['GET', 'POST'])
@login_required
def loginadm():
    dados_predios = db.session.query(
        Reposicao.predio,
        func.sum(Reposicao.quantidade_reposicao).label('total_reposicao')
    ).group_by(Reposicao.predio).all()
 
    dados_formulario = db.session.query(
        Reposicao.predio,
        func.count(Reposicao.id_user).label('reposicoes_pendentes')
    ).filter(Reposicao.status_reposicao == 'pendente').group_by(Reposicao.predio).all()
 
    dados_predios_json = json.dumps(
        [{'predio': item.predio, 'total_reposicao': item.total_reposicao} for item in dados_predios], default=decimal_default)
 
    return render_template('loginadm.html', dados_predios=dados_predios_json, dados_formulario=dados_formulario)
 
 
@app.route('/abastecimento', methods=['GET', 'POST'])
@login_required
def abastecimento():
    estoque = None
    mensagem = None
 
    if request.method == 'POST':
        print("Formulário enviado!")
 
        predio = request.form['predio']
        andar = request.form['andar']
        ilha = request.form['ilha']
        quantidade_reposicao = int(request.form['quantidade_reposicao'])
 
        print(
            f"Dados do formulário: Predio={predio}, Andar={andar}, Ilha={ilha}, Quantidade={quantidade_reposicao}")
 
        try:
            # Verifica se o usuário está autenticado
            if current_user.is_authenticated:
                repositorio = Usuario.query.filter_by(
                    id_user=current_user.id).first()
 
                if isinstance(repositorio, Usuario):
                    estoque = repositorio.estoque
                    print(f"Estoque do Repositório: {estoque}")
 
                    # Determina o tipo de reposição com base no botão clicado
                    tipo_reposicao = request.form['tipo_reposicao']
 
                    # Cria uma data de reposição usando a data atual
                    data_reposicao = datetime.now().date()
 
                    nova_reposicao = Reposicao(
                        id_user=current_user.id,
                        data_reposicao=data_reposicao,
                        tipo_reposicao=tipo_reposicao,
                        quantidade_reposicao=quantidade_reposicao,
                        andar=andar,
                        ilha=ilha,
                        predio=predio,
                        status_reposicao='OK'  # Muda o status para "OK"
                    )
 
                    repositorio.estoque -= quantidade_reposicao
 
                    db.session.add(nova_reposicao)
                    db.session.commit()
 
                    mensagem = "Reabastecimento registrado no banco de dados!"
                    print(mensagem)
 
                else:
                    mensagem = "Erro ao obter o repositório associado ao usuário."
 
        except Exception as e:
            db.session.rollback()
            mensagem = f"Erro ao registrar reabastecimento no banco de dados: {str(e)}"
            print(mensagem)
 
    return render_template('abastecimento.html', quantidade_estoque=estoque, mensagem_erro=None, mensagem=mensagem)

@app.route('/abastecimentoP', methods=['GET', 'POST'])
@login_required
def abastecimentoP():
    estoque = None
    mensagem = None
 
    if request.method == 'POST':
        print("Formulário enviado!")
 
        predio = request.form['predio']
        andar = request.form['andar']
        ilha = request.form['ilha']
        quantidade_reposicao = int(request.form['quantidade_reposicao'])
 
        print(
            f"Dados do formulário: Predio={predio}, Andar={andar}, Ilha={ilha}, Quantidade={quantidade_reposicao}")
 
        try:
            # Verifica se o usuário está autenticado
            if current_user.is_authenticated:
                repositorio = Usuario.query.filter_by(
                    id_user=current_user.id).first()
 
                if isinstance(repositorio, Usuario):
                    estoque = repositorio.estoque
                    print(f"Estoque do Repositório: {estoque}")
 
                    # Determina o tipo de reposição com base no botão clicado
                    tipo_reposicao = request.form['tipo_reposicao']
 
                    # Cria uma data de reposição usando a data atual
                    data_reposicao = datetime.now().date()
 
                    nova_reposicao = Reposicao(
                        id_user=current_user.id,
                        data_reposicao=data_reposicao,
                        tipo_reposicao=tipo_reposicao,
                        quantidade_reposicao=quantidade_reposicao,
                        andar=andar,
                        ilha=ilha,
                        predio=predio,
                        status_reposicao='OK'  # Muda o status para "OK"
                    )
 
                    repositorio.estoque -= quantidade_reposicao
 
                    db.session.add(nova_reposicao)
                    db.session.commit()
 
                    mensagem = "Reabastecimento registrado no banco de dados!"
                    print(mensagem)
 
                else:
                    mensagem = "Erro ao obter o repositório associado ao usuário."
 
        except Exception as e:
            db.session.rollback()
            mensagem = f"Erro ao registrar reabastecimento no banco de dados: {str(e)}"
            print(mensagem)
 
    return render_template('abastecimento.html', quantidade_estoque=estoque, mensagem_erro=None, mensagem=mensagem)
  
 
@app.route('/reabastecimento', methods=['GET', 'POST'])
@login_required
def reabastecimento():
    try:
        if request.method == 'POST':
            # Capturar os dados do formulário
            andar = request.form.get('andar')
            predio = request.form.get('predio')
            quantidade_reabastecimento = request.form.get('quantidade_reposicao')

            # Obter o usuário logado usando a variável current_user do Flask-Login
            usuario = Usuario.query.filter_by(id_user=current_user.id).first()

            nova_reposicao = Reabastecimento(
                id_user=usuario.id_user,
                quantidade_reabastecimento=quantidade_reabastecimento,
                andar=andar,
                predio=predio
            )

            db.session.add(nova_reposicao)
            db.session.commit()

            logging.info('Reabastecimento solicitado com sucesso.')

            return redirect(url_for('reabastecimento'))

        # Se o método for GET, continua com o restante da função
        if current_user.is_authenticated:
            usuario = Usuario.query.filter_by(id_user=current_user.id).first()
            quantidade_estoque = usuario.estoque if usuario else 0

            # Buscar todos os registros de reabastecimento
            dados_reabastecimento = Reabastecimento.query.all()

            logging.info('Página de reabastecimento carregada com sucesso.')

            return render_template('reabastecimento.html', dados_reabastecimento=dados_reabastecimento, quantidade_estoque=quantidade_estoque)

    except Exception as e:
        logging.error(f"Erro ao processar requisição: {str(e)}")

    return render_template('reabastecimento.html', dados_reabastecimento=[], quantidade_estoque=0, error_message="Erro ao buscar dados de reabastecimento")


@app.route('/adminfo')
@login_required
def adminfo():
    try:
        lista_predios = db.session.query(InfoAndar.predio).distinct().all()
        predio_selecionado = request.args.get('predio')
 
        dados_andares = None
        if predio_selecionado:
            dados_andares = db.session.query(
                InfoAndar.andar,
                InfoAndar.num_ilhas
            ).filter_by(predio=predio_selecionado).all()
 
        dados_template = {
            'lista_predios': [predio[0] for predio in lista_predios],
            'dados_andares': dados_andares
        }
 
        return render_template('adminfo.html', **dados_template)
 
    except Exception as e:
        print(f'Erro: {str(e)}')
        return render_template('adminfo.html', lista_predios=[], dados_andares=None)
 
 
@app.route('/obter-status-andares', methods=['GET'])
@login_required
def obter_status_andares():
    try:
        predio_selecionado = request.args.get('predio')
        andares_info = db.session.query(
            InfoAndar.andar,
            func.coalesce(Reposicao.status_reposicao,
                          'OK').label('status_reposicao')
        ).outerjoin(
            Reposicao,
            (InfoAndar.andar == Reposicao.andar) & (
                InfoAndar.predio == Reposicao.predio)
        ).filter(InfoAndar.predio == predio_selecionado).all()
 
        # Remover duplicatas de andares
        andares_unicos = set()
        andares_filtrados = []
        for andar, status in andares_info:
            if andar not in andares_unicos:
                andares_filtrados.append({'andar': andar, 'status': status})
                andares_unicos.add(andar)
 
        return jsonify(andares_filtrados)
 
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter dados dos andares: {str(e)}'}), 500
 
 
@app.route('/verificar_conexao')
def verificar_conexao():
    try:
        users = Usuario.query.all()
 
        users_data = [{
            'id_user': user.id_user,
            'email': user.email,
            'senha': user.senha,
            'tipo_user': user.tipo_user,
            'estoque': user.estoque
        }for user in users]
 
        return jsonify(users_data)
    except Exception as e:
        return f'Erro ao verificar a conexão: {str(e)}'
 
 
if __name__ == '__main__':
    app.run(debug=True)
 