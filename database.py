from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:Celeste123@localhost/papercontrolsystem'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id_user = db.Column(db.Integer, primary_key=True)
    id_repositor = db.Column(db.Integer, db.ForeignKey('repositor.id_repositor'), unique=True, nullable=True)
    repositor = db.relationship('Repositor', back_populates='usuario', uselist=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    senha = db.Column(db.String(255), nullable=False)
    tipo_user = db.Column(db.String(50), nullable=False)

class Repositor(db.Model):
    __tablename__ = 'repositor'

    id_repositor = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id_user'))
    usuario = db.relationship('Usuario', back_populates='repositor')
    estoque = db.Column(db.Integer, nullable=False)
    
def configure_database(app, database_uri):
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


class Reposicao(db.Model):
    __tablename__ = 'reposicao'
    id_reposicao = db.Column(db.Integer, primary_key=True)
    id_repositor = db.Column(db.Integer, db.ForeignKey(
        'repositor.id_repositor'), nullable=False)
    data_reposicao = db.Column(db.Date, nullable=False)
    tipo_reposicao = db.Column(db.String(50), nullable=False)
    quantidade_reposicao = db.Column(db.Integer, nullable=False)
    andar = db.Column(db.Integer, nullable=False)
    ilha = db.Column(db.Integer, nullable=False)
    estoque_restante = db.Column(db.Integer, nullable=False)
    predio = db.Column(db.String(50), nullable=False)
    status_reposicao = db.Column(
        db.String(20), nullable=False, default='pendente')


