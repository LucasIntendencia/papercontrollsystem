from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def configure_database(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'mysql+mysqlconnector://root:Celeste123@localhost/'
        'papercontrolsystem'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

# Modelo para a tabela `reposicao`


class Reposicao(db.Model):
    __tablename__ = 'reposicao'
    id_reposicao = db.Column(db.Integer, primary_key=True)
    id_repositor = db.Column(db.Integer, db.ForeignKey(
        'repositor.id_repositor'), nullable=False)
    # Adicione outras colunas conforme necessário
    data_reposicao = db.Column(db.Date, nullable=False)
    tipo_reposicao = db.Column(db.String(50), nullable=False)
    quantidade_reposicao = db.Column(db.Integer, nullable=False)
    andar = db.Column(db.Integer, nullable=False)
    ilha = db.Column(db.Integer, nullable=False)
    estoque_restante = db.Column(db.Integer, nullable=False)
    predio = db.Column(db.String(50), nullable=False)
    status_reposicao = db.Column(
        db.String(20), nullable=False, default='pendente')

# Modelo para a tabela `repositor`


class Repositor(db.Model):
    __tablename__ = 'repositor'
    id_repositor = db.Column(db.Integer, primary_key=True)
    estoque = db.Column(db.Integer, nullable=False)

# Modelo para a tabela `usuarios`


class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id_user = db.Column(db.Integer, primary_key=True)
    Nome = db.Column(db.String(255), nullable=False)
    Email = db.Column(db.String(255), nullable=False)
    CPF = db.Column(db.String(11), nullable=False)
    Senha = db.Column(db.String(255), nullable=False)
    tipo_user = db.Column(db.String(50), nullable=False)
    id_repositor = db.Column(db.Integer, db.ForeignKey(
        'repositor.id_repositor'), nullable=False)
