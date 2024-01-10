from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file,flash
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user
from database import configure_database, db, Usuario, Reposicao, Reabastecimento, Ajuda
from sqlalchemy import func
from decimal import Decimal
from datetime import datetime
import secrets
import logging
import pandas as pd
import smtplib
import json
from email.message import EmailMessage
from werkzeug.exceptions import BadRequestKeyError



app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
database_uri = 'mysql+mysqlconnector://root:Celeste123@localhost/papercontrol'
configure_database(app, database_uri)
login_manager = LoginManager(app)
login_manager.login_view = 'fazer_login'
logging.basicConfig(filename='erro.log', level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'lucas.nascimento@planejamento.mg.gov.br'
app.config['MAIL_PASSWORD'] = 'Celeste123'
app.config['MAIL_DEFAULT_SENDER'] = 'lucas.nascimento@planejamento.mg.gov.br'


class User(UserMixin):
    def __init__(self, user_id, tipo_user=None, nome=None, email=None):
        self.id = user_id
        self.tipo_user = tipo_user
        self.nome = nome
        self.email = email 
    @staticmethod
    def load_user(user_id):
        return Usuario.query.get(int(user_id))
    
@login_manager.user_loader
def load_user(user_id):
    usuario = Usuario.query.get(int(user_id))
    if usuario:
        return User(usuario.id_user, usuario.tipo_user, usuario.nome, usuario.email)
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
    ).group_by(Reposicao.predio).all()
 
    dados_predios_json = json.dumps(
        [{'predio': item.predio, 'total_reposicao': item.total_reposicao} for item in dados_predios], default=decimal_default)
 
    return render_template('loginadm.html', dados_predios=dados_predios_json, dados_formulario=dados_formulario)
 
 
@app.route('/abastecimento', methods=['GET', 'POST'])
@login_required
def abastecimento():
    print("Rota abs acionada.")
    estoque = None
    mensagem = None
 
    if request.method == 'POST':
        print("Formulário enviado!")
 
        predio = request.form['predio']
        andar = request.form['andar']
        ilha = request.form['ilha']
        quantidade_reposicao = int(request.form['quantidade_reposicao'])
        tipo_reposicao = request.form['tipo_reposicao']
 
        print(
            f"Dados do formulário: Predio={predio}, Andar={andar}, Ilha={ilha}, Quantidade={quantidade_reposicao}")
 
        try:
            if current_user.is_authenticated:
                repositorio = Usuario.query.filter_by(
                    id_user=current_user.id).first()
 
                if isinstance(repositorio, Usuario):
                    estoque = repositorio.estoque
                    print(f"Estoque do Repositório: {estoque}")
 
                    data_reposicao = datetime.now().date()
 
                    nova_reposicao = Reposicao(
                        id_user=current_user.id,
                        data_reposicao=data_reposicao,
                        tipo_reposicao=tipo_reposicao,
                        quantidade_reposicao=quantidade_reposicao,
                        andar=andar,
                        ilha=ilha,
                        predio=predio,
                    )
 
                    # Reduz o estoque apenas se a reposição for pendente
                    novo_estoque = estoque - quantidade_reposicao
                    if novo_estoque >= 0:  # Verifica se o estoque não ficará negativo
                        repositorio.estoque = novo_estoque
                    else:
                        mensagem = "Erro: Não é possível realizar a reposição, estoque insuficiente."
                        print(mensagem)
                        return render_template('abastecimento.html', quantidade_estoque=estoque, mensagem_erro=mensagem, mensagem=None)
 
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
            quantidade_reabastecimento = int(request.form.get(
                'quantidade_reposicao', 0))  # Converte para inteiro
 
            # Obter o usuário logado usando a variável current_user do Flask-Login
            usuario = Usuario.query.filter_by(id_user=current_user.id).first()
 
            # Incrementar o estoque do usuário com base na quantidade fornecida
            if usuario and quantidade_reabastecimento > 0:
                # Aumenta o estoque com a quantidade fornecida
                usuario.estoque += quantidade_reabastecimento
                db.session.commit()  # Salva a atualização do estoque
 
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
 
        # Restante da função (GET request)
        if current_user.is_authenticated:
            usuario = Usuario.query.filter_by(id_user=current_user.id).first()
            quantidade_estoque = usuario.estoque if usuario else 0
 
            dados_reabastecimento = Reabastecimento.query.all()
 
            logging.info('Página de reabastecimento carregada com sucesso.')
 
            return render_template('reabastecimento.html', dados_reabastecimento=dados_reabastecimento, quantidade_estoque=quantidade_estoque)
 
    except Exception as e:
        logging.error(f"Erro ao processar requisição: {str(e)}")
 
    return render_template('reabastecimento.html', dados_reabastecimento=[], quantidade_estoque=0, error_message="Erro ao buscar dados de reabastecimento")

@app.route('/relatoriosadm', methods=['GET', 'POST'])
@login_required
def relatoriosadm():
    if request.method == 'POST':
        relatorio_type = request.form.get('relatorio')
 
        if relatorio_type == 'Completo':
            tipo_relatorio = request.form.get('tipoRelatorio')
            if tipo_relatorio == 'Completo':
                usuarios_data = [{'ID do usuário': user.id_user, 'Nome': user.nome, 'CPF': user.cpf, 'Email': user.email,
                                  'Tipo de usuário': user.tipo_user, 'Estoque': user.estoque} for user in Usuario.query.all()]
                reposicoes_data = [{'ID da reposição': repo.id_reposicao, 'Data da reposição': repo.data_reposicao,
                                    'Tipo de reposição': repo.tipo_reposicao, 'Quantidade de reposição': repo.quantidade_reposicao,
                                    'Andar': repo.andar, 'Ilha': repo.ilha, 'Prédio': repo.predio} for repo in Reposicao.query.all()]
                usuarios_df = pd.DataFrame(usuarios_data)
                reposicoes_df = pd.DataFrame(reposicoes_data)
                filename = 'relatorio_completo.xlsx'
                with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                    usuarios_df.to_excel(
                        writer, sheet_name='Usuarios', index=False)
                    reposicoes_df.to_excel(
                        writer, sheet_name='Reposicoes', index=False)
                return send_file(filename, as_attachment=True)
 
            elif tipo_relatorio == 'Por Data':
                data_param = request.form.get('data_reposicao')
                if ' to ' in data_param:
                    data_inicio, data_fim = data_param.split(' to ')
                    reposicoes_data = Reposicao.query.filter(
                        Reposicao.data_reposicao.between(data_inicio, data_fim)).all()
                else:
                    reposicoes_data = Reposicao.query.filter_by(
                        data_reposicao=data_param).all()
 
                reposicoes_df = pd.DataFrame([{'ID da reposição': repo.id_reposicao, 'Data da reposição': repo.data_reposicao,
                                               'Tipo de reposição': repo.tipo_reposicao, 'Quantidade de reposição': repo.quantidade_reposicao,
                                               'Andar': repo.andar, 'Ilha': repo.ilha, 'Prédio': repo.predio} for repo in reposicoes_data])
                usuarios_data = Usuario.query.all()
                usuarios_df = pd.DataFrame([{'ID do usuário': user.id_user, 'Nome': user.nome, 'CPF': user.cpf, 'Email': user.email,
                                             'Tipo de usuário': user.tipo_user, 'Estoque': user.estoque} for user in usuarios_data])
                filename = f'relatorio_completo_por_data_{data_param}.xlsx'
 
                with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                    reposicoes_df.to_excel(
                        writer, sheet_name='Reposicoes', index=False)
                    usuarios_df.to_excel(
                        writer, sheet_name='Usuarios', index=False)
                return send_file(filename, as_attachment=True)
 
        elif relatorio_type == 'Reposições':
            tipo_reposicoes = request.form.get('tipoReposicoes')
            if tipo_reposicoes == 'Completo':
                data = Reposicao.query.all()
                df = pd.DataFrame([{'ID da reposição': repo.id_reposicao, 'Data da reposição': repo.data_reposicao,
                                    'Tipo de reposição': repo.tipo_reposicao, 'Quantidade de reposição': repo.quantidade_reposicao,
                                    'Andar': repo.andar, 'Ilha': repo.ilha, 'Prédio': repo.predio} for repo in data])
                filename = 'relatorio_reposicoes_completo.xlsx'
                df.to_excel(filename, index=False)
                return send_file(filename, as_attachment=True)
 
            elif tipo_reposicoes == 'Por Prédio':
                predio = request.form.get('selectPredio')
                data = Reposicao.query.filter_by(predio=predio).all()
                df = pd.DataFrame([{'ID da reposição': repo.id_reposicao, 'Data da reposição': repo.data_reposicao,
                                    'Tipo de reposição': repo.tipo_reposicao, 'Quantidade de reposição': repo.quantidade_reposicao,
                                    'Andar': repo.andar, 'Ilha': repo.ilha, 'Prédio': repo.predio} for repo in data])
                filename = f'relatorio_por_predio_{predio.lower()}.xlsx'
                df.to_excel(filename, index=False)
                return send_file(filename, as_attachment=True)
 
            elif tipo_reposicoes == 'Por Data':
                data_param = request.form.get('data_reposicao')
                if ' to ' in data_param:
                    data_inicio, data_fim = data_param.split(' to ')
                    data = Reposicao.query.filter(
                        Reposicao.data_reposicao.between(data_inicio, data_fim)).all()
                    df = pd.DataFrame([{'ID da reposição': repo.id_reposicao, 'Data da reposição': repo.data_reposicao,
                                        'Tipo de reposição': repo.tipo_reposicao, 'Quantidade de reposição': repo.quantidade_reposicao,
                                        'Andar': repo.andar, 'Ilha': repo.ilha, 'Prédio': repo.predio} for repo in data])
                    filename = f'relatorio_reposicoes_por_data_{data_inicio}_{data_fim}.xlsx'
                else:
                    data = Reposicao.query.filter_by(
                        data_reposicao=data_param).all()
                    df = pd.DataFrame([{'ID da reposição': repo.id_reposicao, 'Data da reposição': repo.data_reposicao,
                                        'Tipo de reposição': repo.tipo_reposicao, 'Quantidade de reposição': repo.quantidade_reposicao,
                                        'Andar': repo.andar, 'Ilha': repo.ilha, 'Prédio': repo.predio} for repo in data])
                    filename = f'relatorio_reposicoes_por_data_{data_param}.xlsx'
                df.to_excel(filename, index=False)
                return send_file(filename, as_attachment=True)
 
        elif relatorio_type == 'Usuários':
            data = Usuario.query.all()
            df = pd.DataFrame([{'ID do usuário': user.id_user, 'Nome': user.nome, 'Email': user.email,
                              'Tipo de usuário': user.tipo_user, 'Estoque': user.estoque} for user in data])
            filename = 'relatorio_usuarios_completo.xlsx'
            df.to_excel(filename, index=False)
            return send_file(filename, as_attachment=True)
 
    return render_template('relatoriosadm.html')


@app.route('/ajudaOZe', methods=['GET', 'POST'])
@login_required
def ajudaOZe():
    if request.method == 'POST':
        try:
            tipo = request.form['tipo']
            descricao = request.form['problema']
            if not tipo or not descricao:
                flash('Por favor, preencha todos os campos.', 'error')
                return render_template('ajudaOZe.html')
            
            # Correção aqui: use current_user.id em vez de current_user.id_user
            id_user = current_user.id
            nova_ajuda = Ajuda(tipo=tipo, descricao=descricao, id_user=id_user, email=current_user.email)
            db.session.add(nova_ajuda)
            db.session.commit()
            
            # Envia e-mail
            enviar_email(current_user.email, tipo, descricao)
            flash('Sua ajuda foi enviada com sucesso!', 'success')
        except BadRequestKeyError as e:
            flash('Erro na solicitação: {}'.format(str(e)), 'error')
    
    return render_template('ajudaOZe.html')

def enviar_email(email, tipo, descricao):
    try:
        # Obter a última ajuda inserida no banco de dados
        ajuda = Ajuda.query.order_by(Ajuda.id_ajuda.desc()).first()
        
        # Configuração do log
        logger = logging.getLogger(__name__)
        
        # Verificar se existe uma ajuda
        if ajuda:
            # Configuração do e-mail
            msg = EmailMessage()
            msg['From'] = 'papercontrol@planejamento.mg.gov.br'
            msg['To'] = 'lucas.nascimento@planejamento.mg.gov.br'
            msg['Subject'] = f'{tipo.capitalize()} - ID da Ajuda: {ajuda.id_ajuda}'
            content = f"""
            Olá, {ajuda.id_user}
            Aqui estão algumas informações da Ajuda:
            - ID da Ajuda: {ajuda.id_ajuda}
            - ID do Usuário: {ajuda.id_user}
            - Descrição: {ajuda.descricao}
            - E-mail do Usuário: {ajuda.email}
            Atenciosamente,
            Equipe Paper Control
            """
            msg.set_content(content)
            smtp_server = 'seu_servidor_smtp'
            smtp_port = 587  # Porta do servidor SMTP
            smtp_user = 'seu_email'
            smtp_password = 'sua_senha'
            with smtplib.SMTP(smtp_server, smtp_port) as smtp:
                smtp.starttls()
                smtp.login(smtp_user, smtp_password)
                
                # Log antes de enviar o e-mail
                logger.info(f'Enviando e-mail para {msg["To"]} sobre a Ajuda de ID {ajuda.id_ajuda}')
                
                # Envia o e-mail
                smtp.send_message(msg)
                
                # Log após enviar o e-mail
                logger.info(f'E-mail para {msg["To"]} enviado com sucesso!')
            
            return 'E-mail enviado com sucesso!'
        else:
            return 'Nenhuma ajuda encontrada para enviar e-mail.'
    except Exception as e:
        # Log em caso de erro
        logger.error(f'Erro ao enviar e-mail: {str(e)}', exc_info=True)
        return f'Erro ao enviar e-mail: {str(e)}'
    

@app.route('/quantidadeadm', methods=['GET', 'POST'])
@login_required
def quantidadeadm():
    try:
        logging.debug("Iniciando processamento...")

        if request.method == 'POST':
            logging.debug("Recebendo requisição POST...")

            file = request.files.get('excelFile')
            logging.debug(f"Arquivo recebido: {file}")

            if file and file.filename.endswith(('.xlsx', '.xls')):
                # Ler o arquivo Excel
                df = pd.read_excel(file)
                df.columns = df.columns.str.upper()
                # Imprimir o cabeçalho real do DataFrame
                logging.debug(f"Cabeçalho real do DataFrame: {df.columns}")

                # Inicializar uma lista para armazenar os resultados
                resultado_lista = []

                # Iterar sobre cada linha do DataFrame do Excel
                for _, row in df.iterrows():
                    predio = row['PRÉDIO']
                    ilha = row['LOCALIZAÇÃO']

                    # Verificar e converter 'andar' para numérico
                    andar_value = row['ANDAR']
                    if pd.notna(andar_value):
                        try:
                            andar_int = int(andar_value)
                        except ValueError:
                            logging.warning(f"Valor inválido em 'andar': {andar_value}")
                            continue
                    else:
                        # Definir um valor padrão quando 'andar' é nulo
                        logging.warning(f"Valor nulo em 'andar', definindo como 0")
                        andar_int = 0

                    # Verificar e converter 'QUANTIDADE' para numérico
                    quantidade_value = row['QUANTIDADE']
                    if pd.notna(quantidade_value) and quantidade_value != 'TOTAL':
                        try:
                            quantidade_impressa = float(quantidade_value)
                        except ValueError:
                            logging.warning(f"Valor inválido em 'quantidade': {quantidade_value}")
                            continue
                    else:
                        logging.warning(f"Valor nulo ou inválido em 'quantidade'")
                        continue

                    # Imprimir para debug
                    print(f"Procurando reposição para: Prédio={predio}, Andar={andar_int}, Ilha={ilha}")

                    # Formatar 'andar' e 'ilha' para correspondência com o banco de dados
                    andar_ilha_concatenado = f"Andar {andar_int} Ilha {ilha}"

                    # Buscar a reposição no banco de dados com base em predio, andar e ilha
                    reposicao = Reposicao.query.filter(
                        func.lower(Reposicao.predio) == func.lower(predio),
                        func.lower(Reposicao.andar).like(f"Andar {andar_int}%"),
                        func.lower(Reposicao.ilha) == func.lower(ilha)
                    ).first()

                    # Imprimir para debug
                    print(f"Reposição encontrada: {reposicao}")

                    # Verificar se há uma reposição e obter a quantidade de reposição
                    if reposicao:
                        quantidade_reabastecida = reposicao.quantidade_reposicao
                        print(f'Reposição encontrada: {quantidade_reabastecida}')
                    else:
                        quantidade_reabastecida = 0

                    print(f'Quantidade encontrada: {quantidade_value}')
                    print(f'Reposição encontrada: {quantidade_reabastecida}')
                    # Calcular a quantidade restante
                    quantidade_restante = (quantidade_reabastecida * 500) - quantidade_impressa

                    # Adicionar os resultados à lista
                    resultado_lista.append({
                        'prédio': predio,
                        'andar': andar_int,
                        'ilha': ilha,
                        'quantidade_impressa': quantidade_impressa,
                        'quantidade_reabastecida': quantidade_reabastecida,
                        'quantidade_restante': quantidade_restante
                    })

                    # Imprimir para debug
                    print(f"Resultado parcial: {resultado_lista[-1]}")

                # Criar um DataFrame a partir da lista
                resultado_df = pd.DataFrame(resultado_lista)

                # Aqui você pode fazer o que quiser com o DataFrame resultado, por exemplo, retorná-lo como JSON
                resultado_json = resultado_df.to_json(orient='records')
                logging.debug("Processamento concluído com sucesso.")
                return jsonify(resultado_json)

        logging.debug("Processamento concluído com sucesso.")
    except Exception as e:
        # Adicione mensagens de log
        logging.error(f"Erro no servidor: {e}", exc_info=True)
        return jsonify({"error": "Erro interno no servidor"}), 500

    return render_template('quantidadeadm.html')


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