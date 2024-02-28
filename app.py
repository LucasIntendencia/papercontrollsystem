from dotenv import load_dotenv,dotenv_values
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user
from database import configure_database, db, Usuario, Reposicao, Reabastecimento, Ajuda
from sqlalchemy import Integer, func, text
from decimal import Decimal
from datetime import datetime, timedelta
import secrets
import logging
import pandas as pd
import smtplib
import json
from email.message import EmailMessage
from werkzeug.exceptions import BadRequestKeyError
import os
from flask_socketio import SocketIO, send
from collections import defaultdict
import os
from credencial import (
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER
)

app = Flask(__name__)


app.secret_key = secrets.token_hex(32)
database_uri = os.getenv('SQLALCHEMY_DATABASE_URI')
configure_database(app)

login_manager = LoginManager(app)
login_manager.login_view = 'fazer_login'

logging.basicConfig(filename='erro.log', level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)

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
    try:
        if current_user.tipo_user == 'repositor':
            return redirect(url_for('loginrec'))
        elif current_user.tipo_user == 'administrador':
            return redirect(url_for('loginadm'))
        else:
            return render_template('login.html')
    except Exception as e:
        logging.error(f"Erro ao acessar a página inicial: {str(e)}")
        flash('Erro ao acessar a página inicial.', 'error')
        return redirect(url_for('fazer_login'))


@app.route('/LoginPaper', methods=['GET', 'POST'])
def fazer_login():
    mensagem_erro = None

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        if not email or not senha:
            mensagem_erro = "Por favor, preencha todos os campos."
        else:
            # Consulta o banco de dados para encontrar o usuário com as credenciais fornecidas
            usuario = Usuario.query.filter_by(email=email, senha=senha).first()

            if usuario:
                user = User(usuario.id_user, usuario.tipo_user)
                login_user(user)

                if usuario.tipo_user == 'repositor':
                    return redirect(url_for('loginrec', exibirPopup='true'))
                elif usuario.tipo_user == 'administrador':
                    return redirect(url_for('loginadm'))
            else:
                mensagem_erro = "Credenciais inválidas. Tente novamente."

    return render_template('login.html', mensagem_erro=mensagem_erro)


@app.route('/RepositorHome', methods=['GET', 'POST'])
@login_required
def loginrec():
    print("Rota RepositorHome acionada.")
    usuario = Usuario.query.filter_by(
        id_user=current_user.id, tipo_user="repositor").first()
    return render_template('loginrec.html')
   

@app.route('/AdmHome', methods=['GET', 'POST'])
@login_required
def loginadm():
    print("Rota Adm's acionada.")
    usuario = Usuario.query.filter_by(
        id_user=current_user.id, tipo_user="administrador").first()
    return render_template('loginadm.html')


@app.route('/Abastecimento', methods=['GET', 'POST'])
@login_required
def abastecimento():
    print(f"Rota Abastecimento acionada.")
    estoque = None
    mensagem = None

    if request.method == 'POST':
        print(f"Formulário enviado!")

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

                    numero_ilhas_reabastecidas = db.session.query(
                        func.count(Reposicao.ilha.distinct())
                    ).filter_by(id_user=current_user.id).scalar()

                    # Definir o limite desejado
                    limite_ilhas_reabastecidas = 128

                    if numero_ilhas_reabastecidas >= limite_ilhas_reabastecidas:
                        enviar_email_ilhas_reabastecidas(
                            numero_ilhas_reabastecidas)

                else:
                    mensagem = "Erro ao obter o repositório associado ao usuário."

        except Exception as e:
            db.session.rollback()
            mensagem = f"Erro ao registrar reabastecimento no banco de dados: {str(e)}"
            print(mensagem)

    return render_template('abastecimento.html', quantidade_estoque=estoque, mensagem_erro=None, mensagem=mensagem)

def enviar_email_ilhas_reabastecidas(numero_ilhas):
    try:
        # Configuração do e-mail
        msg = EmailMessage()
        msg['From'] = 'papercontrol@planejamento.mg.gov.br'
        msg['To'] = 'espaco@planejamento.mg.gov.br'
        msg['Subject'] = 'Limite de Ilhas Reabastecidas Atingido'
        content = f"""
        Olá,
        Você atingiu o limite de {numero_ilhas} ilhas reabastecidas.
        Todas as ilhas estao devidamente abastecidas!
        Atenciosamente,
        Equipe Paper Control
        """
        msg.set_content(content)

        smtp_server = os.getenv('MAIL_SERVER')
        smtp_port = os.getenv('MAIL_PORT')
        smtp_user = os.getenv('MAIL_USERNAME')
        smtp_password = os.getenv('MAIL_PASSWORD')

        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)

        logging.info(f'E-mail para {msg["To"]} enviado com sucesso!')
        return 'E-mail enviado com sucesso!'
    except Exception as e:
        logging.error(f'Erro ao enviar e-mail: {str(e)}', exc_info=True)
        return f'Erro ao enviar e-mail: {str(e)}'


@app.route('/Reabastecimento', methods=['GET', 'POST'])
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

                if nova_reposicao.id is not None:  # Verifica se a adição ao banco de dados foi bem-sucedida
                    enviar_email_ilhas_solicitante(andar, predio)
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

def enviar_email_ilhas_solicitante(andar, predio):
    try:
        # Configuração do e-mail
        msg = EmailMessage()
        msg['From'] = 'papercontrol@planejamento.mg.gov.br'
        msg['To'] = 'espaco@planejamento.mg.gov.br'
        msg['Subject'] = 'Limite de Ilhas Reabastecidas Atingido'
        content = f"""
        Olá,
        Solicito reabastecimento no seguinte local:
        {andar} e {predio}
        Atenciosamente,
        Equipe Paper Control
        """
        msg.set_content(content)
        smtp_server = os.getenv('MAIL_SERVER')
        smtp_port = os.getenv('MAIL_PORT')
        smtp_user = os.getenv('MAIL_USERNAME')
        smtp_password = os.getenv('MAIL_PASSWORD')

        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)

        logging.info(f'E-mail para {msg["To"]} enviado com sucesso!')
        return 'E-mail enviado com sucesso!'
    except Exception as e:
        logging.error(f'Erro ao enviar e-mail: {str(e)}', exc_info=True)
        return f'Erro ao enviar e-mail: {str(e)}'


@app.route('/RelatoriosAdm', methods=['GET', 'POST'])
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

        elif relatorio_type == 'Reposições':
            tipo_reposicoes = request.form.get('tipoReposicoes')
            if tipo_reposicoes == 'Completo':
                data = db.session.query(Reposicao, Usuario)
                df = pd.DataFrame([{'ID da reposição': repo.id_reposicao, 'ID do usuário': user.id_user, 'Data da reposição': repo.data_reposicao,
                            'Tipo de reposição': repo.tipo_reposicao, 'Quantidade de reposição': repo.quantidade_reposicao,
                            'Andar': repo.andar, 'Ilha': repo.ilha, 'Prédio': repo.predio} for repo, user in data])
                filename = 'relatorio_reposicoes_completo.xlsx'
                df.to_excel(filename, index=False)
                return send_file(filename, as_attachment=True)

            elif tipo_reposicoes == 'Por Prédio':
                predio = request.form.get('selectPredio')
                reposicoes_data = db.session.query(Reposicao, Usuario).join(
                    Usuario).filter(Reposicao.predio == predio).all()
                df = pd.DataFrame([{'ID da reposição': repo.id_reposicao, 'ID do usuário': user.id_user, 'Data da reposição': repo.data_reposicao,
                            'Tipo de reposição': repo.tipo_reposicao, 'Quantidade de reposição': repo.quantidade_reposicao,
                            'Andar': repo.andar, 'Ilha': repo.ilha, 'Prédio': repo.predio} for repo, user in reposicoes_data])
                filename = f'relatorio_por_predio_{predio.lower()}.xlsx'
                df.to_excel(filename, index=False)
                return send_file(filename, as_attachment=True)

            elif tipo_reposicoes == 'Por Data':
                data_param = request.form.get('data_reposicao')
                if ' to ' in data_param:
                    data_inicio, data_fim = data_param.split(' to ')
                    
                    # Verificação de datas futuras
                    if datetime.strptime(data_inicio, '%Y-%m-%d') > datetime.now() or datetime.strptime(data_fim, '%Y-%m-%d') > datetime.now():
                        flash('Você não pode selecionar uma data futura para o relatório.')
                        return redirect(url_for('relatoriosadm'))
                    
                    data = db.session.query(Reposicao, Usuario).join(Usuario).filter(
                        Reposicao.data_reposicao.between(data_inicio, data_fim)).all()
                    df = pd.DataFrame([{'ID da reposição': repo.Reposicao.id_reposicao, 'ID do usuário': user.Usuario.id_user, 'Data da reposição': repo.Reposicao.data_reposicao,
                            'Tipo de reposição': repo.Reposicao.tipo_reposicao, 'Quantidade de reposição': repo.Reposicao.quantidade_reposicao,
                            'Andar': repo.Reposicao.andar, 'Ilha': repo.Reposicao.ilha, 'Prédio': repo.Reposicao.predio} for repo, user in data])
                    filename = f'relatorio_reposicoes_por_data_{data_inicio}_{data_fim}.xlsx'
                else:
                    data = db.session.query(Reposicao, Usuario).join(Usuario).filter(
                        Reposicao.data_reposicao == data_param).all()
                    df = pd.DataFrame([{'ID da reposição': repo.Reposicao.id_reposicao, 'ID do usuário': user.Usuario.id_user, 'Data da reposição': repo.Reposicao.data_reposicao,
                            'Tipo de reposição': repo.Reposicao.tipo_reposicao, 'Quantidade de reposição': repo.Reposicao.quantidade_reposicao,
                            'Andar': repo.Reposicao.andar, 'Ilha': repo.Reposicao.ilha, 'Prédio': repo.Reposicao.predio} for repo, user in data])
                    filename = f'relatorio_reposicoes_por_data_{data_param}.xlsx'
                df.to_excel(filename, index=False)
                return send_file(filename, as_attachment=True)
            
            elif tipo_reposicoes == 'Por Tipo':
                tipo = request.form.get('selectTipo')
                reposicoes_data = db.session.query(Reposicao, Usuario).join(
                    Usuario).filter(Reposicao.tipo_reposicao == tipo).all()
                df = pd.DataFrame([{'ID da reposição': repo.Reposicao.id_reposicao, 'ID do usuário': user.Usuario.id_user, 'Data da reposição': repo.Reposicao.data_reposicao,
                        'Tipo de reposição': repo.Reposicao.tipo_reposicao, 'Quantidade de reposição': repo.Reposicao.quantidade_reposicao,
                        'Andar': repo.Reposicao.andar, 'Ilha': repo.Reposicao.ilha, 'Prédio': repo.Reposicao.predio} for repo, user in reposicoes_data])
                filename = f'relatorio_reposicoes_por_tipo_{tipo.lower()}.xlsx'
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


@app.route('/AjudaSugestao', methods=['GET', 'POST'])
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
            nova_ajuda = Ajuda(tipo=tipo, descricao=descricao,
                               id_user=id_user, email=current_user.email)
            db.session.add(nova_ajuda)
            db.session.commit()
            print('preparando para envio do email')
            # Envia e-mail
            enviar_email(tipo, descricao)
            flash('Sua ajuda foi enviada com sucesso!', 'success')
        except BadRequestKeyError as e:
            flash('Erro na solicitação: {}'.format(str(e)), 'error')

    return render_template('ajudaOZe.html')

def enviar_email(tipo, descricao):
    try:
        # Obter a última ajuda inserida no banco de dados
        ajuda = Ajuda.query.order_by(Ajuda.id_ajuda.desc()).first()

        # Configuração do log
        logger = logging.getLogger(__name__)

        # Verificar se existe uma ajuda
        if ajuda:
            # Configuração do e-mail
            msg = EmailMessage()
            msg['From'] = MAIL_DEFAULT_SENDER
            msg['To'] = 'lucas.nascimento@planejamento.mg.gov.br'
            msg['Subject'] = f'{tipo.capitalize()} - ID da Solicitação: {ajuda.id_ajuda}'
            content = f"""
            Olá, sou o {Usuario.nome}
            Aqui estão algumas informações da Ajuda:
            - ID da Ajuda: {ajuda.id_ajuda}
            - ID do Usuário: {Usuario.id_user}
            - Descrição: {ajuda.descricao}
            - E-mail do Usuário: {Usuario.email}
            Atenciosamente,
            Equipe Paper Control
            """
            msg.set_content(content)

            # Configuração do servidor SMTP
            smtp_server = MAIL_SERVER
            smtp_port = MAIL_PORT
            smtp_user = MAIL_USERNAME
            smtp_password = MAIL_PASSWORD

            with smtplib.SMTP(smtp_server, smtp_port) as smtp:
                smtp.starttls()
                smtp.login(smtp_user, smtp_password)

                # Log antes de enviar o e-mail
                logger.info(
                    f'Enviando e-mail para {msg["To"]} sobre a Ajuda de ID {ajuda.id_ajuda}')

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

def obter_quantidade_reposicao(predio, andar, ilha):
    try:
        print(f'Buscando quantidade de reposição para: Predio={predio}, Andar={andar}, Ilha={ilha}')
        
        # Consulta todas as reposições correspondentes ao prédio, andar e ilha
        reposicoes = Reposicao.query.filter_by(predio=predio, andar=andar, ilha=ilha).all()

        quantidade_reposicao = sum(reposicao.quantidade_reposicao for reposicao in reposicoes)

        print(f'Quantidade de reposição encontrada: {quantidade_reposicao}')
        return quantidade_reposicao

    except Exception as e:
        # Adicione mensagens de log para depuração
        print(f'Erro ao obter quantidade de reposição do banco de dados: {str(e)}')
        return 0


@app.route('/RelatorioSemanal', methods=['GET', 'POST'])
@login_required
def quantidadeadm():
    try:
        if request.method == 'POST':
            file = request.files.get('excelFile')
            if file and file.filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
                df.columns = df.columns.str.upper()

                # Inicializar uma lista para armazenar os resultados
                resultado_lista = []

                # Iterar sobre cada linha do DataFrame do Excel
                for _, row in df.iterrows():
                    predio = row['PRÉDIO']
                    ilha = str(row['LOCALIZAÇÃO'])
                    reposicao_value = row['REPOSIÇÃO']
                    if reposicao_value:
                        try:
                            reposicao_necessaria = int(reposicao_value)
                        except ValueError:
                            logging.warning(
                                f"Valor inválido em 'REPOSIÇÃO': {reposicao_value}"
                            )
                            continue

                    # Verificar e converter 'andar' para numérico
                    andar_value = row['ANDAR']
                    if pd.notna(andar_value):
                        try:
                            andar_int = int(andar_value)
                        except ValueError:
                            logging.warning(
                                f"Valor inválido em 'andar': {andar_value}")
                            continue
                    else:
                        # Definir um valor padrão quando 'andar' é nulo
                        logging.warning(
                            f"Valor nulo em 'andar', definindo como 0")
                        andar_int = 0

                    # Verificar e converter 'QUANTIDADE' para numérico
                    quantidade_value = row['QUANTIDADE']
                    if pd.notna(quantidade_value) and quantidade_value != 'TOTAL':
                        try:
                            quantidade_impressa = float(quantidade_value)
                        except ValueError:
                            logging.warning(
                                f"Valor inválido em 'quantidade': {quantidade_value}")
                            continue
                    else:
                        logging.warning(
                            f"Valor nulo ou inválido em 'quantidade'")
                        continue

                    ilha_numero = int(''.join(filter(str.isdigit, ilha)))

                    # Consultar todas as reposições e somar as quantidades
                    soma_reposicoes = db.session.query(func.sum(Reposicao.quantidade_reposicao)).filter(
                        func.lower(Reposicao.predio) == func.lower(predio),
                        func.cast(Reposicao.andar, Integer) == andar_int,
                        func.cast(func.regexp_replace(Reposicao.ilha, '[^0-9]', ''), Integer) == ilha_numero,
                    ).scalar()

                    quantidade_reabastecida = Decimal(soma_reposicoes) if soma_reposicoes else Decimal(0)

                    print(f'Reposição encontrada: {quantidade_reabastecida}')

                    print(f'Quantidade encontrada: {quantidade_value}')
                    print(f'Reposição encontrada: {quantidade_reabastecida}')
                    # Calcular a quantidade restante
                    quantidade_restante = (
                        quantidade_reabastecida * Decimal(500)) - Decimal(quantidade_impressa)

                    if quantidade_restante >= Decimal(0):
                        reposicao_necessaria = 0
                    else:
                        reposicao_necessaria = abs(quantidade_restante) // Decimal(500)
                        if abs(quantidade_restante) % Decimal(500) != 0:
                            reposicao_necessaria += 1

                    # Adicionar o valor 'pontual' como vazio
                    resultado_lista.append({
                        'PRÉDIO': predio,
                        'ANDAR': andar_int,
                        'ILHA': ilha,
                        'IMPRESSA NA SEMANA': quantidade_impressa,
                        'REABASTECIMENTO': quantidade_reabastecida,
                        'RESTANTE': quantidade_restante,
                        'REPOSIÇÃO': reposicao_necessaria,
                        'PONTUAL': ''  # Adicionando a coluna 'pontual' com valor vazio
                    })

                resultado_df = pd.DataFrame(resultado_lista)
                relatorio_xlsx = f'tmp_relatorio_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx'

                # Reordenando as colunas para incluir 'pontual' como a última
                colunas = ['PRÉDIO', 'ANDAR', 'ILHA', 'IMPRESSA NA SEMANA', 'REABASTECIMENTO', 'RESTANTE', 'REPOSIÇÃO', 'PONTUAL']
                resultado_df = resultado_df[colunas]

                resultado_df.to_excel(
                    relatorio_xlsx, index=False, sheet_name='Relatorio')

                return send_file(relatorio_xlsx, download_name='RelatorioSemanalQuantitativo.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        logging.debug("Processamento concluído com sucesso.")
    except Exception as e:
        logging.error(f"Erro no servidor: {e}", exc_info=True)

    return render_template('quantidadeadm.html')

def enviar_notificacao_repositor(file, tipo_reposicao):
    try:
        # Carregar o arquivo Excel
        df = pd.read_excel(file)
        
        ilhas_e_quantidades = {}  # Dicionário para armazenar ilhas e suas quantidades necessárias

        if tipo_reposicao == "pontual":
            # Filtrar as linhas onde a coluna "PONTUAL" contém um "X"
            locais_pontuais = df[df['PONTUAL'] == 'X']
            for _, row in locais_pontuais.iterrows():
                # Enviar notificação para os repositores dos locais pontuais
                mensagem = f"Olá, repositores. Vocês precisam reabastecer:"
                mensagem += f"\nPrédio: {row['PRÉDIO']}, Andar: {row['ANDAR']}"
                mensagem += f"\nIlha: {row['ILHA']}, Quantidade: {row['REABASTECIMENTO']} resmas"
                ilhas_e_quantidades[row['ILHA']] = row['REABASTECIMENTO']  # Armazenar ilha e quantidade necessária
                # Aqui você pode implementar o envio de notificação, por exemplo, via e-mail
                print(mensagem)  # apenas para exemplo

        elif tipo_reposicao == "semanal":
            # Filtrar as linhas onde a coluna "REPOSIÇÃO" é diferente de zero
            locais_semanais = df[df['REPOSIÇÃO'] != 0]
            for _, row in locais_semanais.iterrows():
                # Enviar notificação para os repositores dos locais semanais
                mensagem = f"Olá, repositores. Vocês precisam reabastecer:"
                mensagem += f"\nPrédio: {row['PRÉDIO']}, Andar: {row['ANDAR']}"
                mensagem += f"\nIlha: {row['ILHA']}, Quantidade: {row['REABASTECIMENTO']} resmas"
                ilhas_e_quantidades[row['ILHA']] = row['REABASTECIMENTO']  # Armazenar ilha e quantidade necessária
                # Aqui você pode implementar o envio de notificação, por exemplo, via e-mail
                print(mensagem)  # apenas para exemplo

        print("Notificações enviadas com sucesso!")
        return ilhas_e_quantidades  # Retornar o dicionário com ilhas e quantidades necessárias

    except Exception as e:
        print(f'Erro ao enviar notificações para os repositores: {str(e)}')
        return None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}


@app.route('/enviarPopup', methods=['GET', 'POST'])
@login_required
def enviarPopup():
    if request.method == 'POST':
        # Verificar se um arquivo foi enviado
        if 'file' not in request.files:
            flash('Nenhum arquivo enviado.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        tipo_reposicao = request.form['tipoReposicao']

        if file.filename == '':
            flash('Nenhum arquivo selecionado.', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Processar o arquivo Excel e enviar notificações
            ilhas_e_quantidades = enviar_notificacao_repositor(file, tipo_reposicao)
            
            if ilhas_e_quantidades:
                # Renderizar a página com sucesso e exibir uma mensagem de confirmação
                flash('Notificações enviadas com sucesso!', 'success')
                return render_template('enviarNotificacao.html', ilhas_e_quantidades=ilhas_e_quantidades)
            else:
                # Renderizar a página com uma mensagem de erro
                flash('Erro ao enviar notificações.', 'error')
                return render_template('enviarNotificacao.html')
        
        else:
            flash('Tipo de arquivo não permitido.', 'error')
            return redirect(request.url)

    return render_template('enviarNotificacao.html')


@app.route('/verificar_conexao')
def verificar_conexao():
    try:
        users = Usuario.query.all()

        users_data = [{
            'id_user': user.id_user,
            'email': user.email,
            'nome': user.nome,
            'andar': user.andar_user,
            'predio':user.predio_user,

            'estoque': user.estoque
        }for user in users]
        
        repor = Reposicao.query.all()
        
        repor_data = [{
            'id_reposicao': repo.id_reposicao,
            'predio': repo.predio,
            'andar': repo.andar,
            'ilha': repo.ilha,
            'quantidade_reposicao': repo.quantidade_reposicao
        }for repo in repor]

        return jsonify(users_data, repor_data)
    except Exception as e:
        return f'Erro ao verificar a conexão: {str(e)}'

if __name__ == '__main__':
    app.run(debug=True)