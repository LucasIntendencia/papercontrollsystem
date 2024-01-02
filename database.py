from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
 
db = SQLAlchemy()
migrate = Migrate()
 
 
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
 
    def __init__(self, user_id, tipo_user=None, nome=None):
        self.id = user_id
        self.tipo_user = tipo_user
        self.nome = nome
 
    id_user = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    cpf = db.Column(db.String(11), nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    tipo_user = db.Column(db.String(50), nullable=False)
    estoque = db.Column(db.Integer, nullable=False, default=0)
 
    def __repr__(self):
        return f"<User {self.id}: {self.nome} ({self.tipo_user})>"
 
    def get_id(self):
        return str(self.id_user)
 
    def is_active(self):
        return True
 
    def is_authenticated(self):
        return True if self else False
 
    def is_anonymous(self):
        return False
 
 
class Reposicao(db.Model):
    __tablename__ = 'reposicao'
    id_reposicao = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_user = db.Column(db.Integer, db.ForeignKey(
        'usuarios.id_user'), nullable=False)
    data_reposicao = db.Column(db.Date, nullable=False)
    tipo_reposicao = db.Column(db.String(50), nullable=False)
    quantidade_reposicao = db.Column(db.Integer, nullable=False)
    andar = db.Column(db.String(50), nullable=False)
    ilha = db.Column(db.String(50), nullable=False)
    predio = db.Column(db.String(50), nullable=False)
    status_reposicao = db.Column(
        db.String(20), nullable=False, default='pendente')
 
 
class Reabastecimento(db.Model):
    __tablename__ = 'reabastecimento'

    id_reabastecimento = db.Column(db.Integer, primary_key=True)
    quantidade_reabastecimento = db.Column(db.Integer, nullable=False)
    id_user = db.Column(db.Integer, db.ForeignKey('usuarios.id_user'), nullable=False)
    usuario = relationship("Usuario", backref="reabastecimentos")
    andar = db.Column(db.String(50), nullable=False)
    predio = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"<Reabastecimento {self.id_reabastecimento}>"
    
class Ajuda(db.Model):
    __tablename__ = 'ajuda'
    
    id_ajuda =  db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(25), nullable=False)
    descricao = db.Column(db.String(950), nullable=False)
    id_user = db.Column(db.Integer, db.ForeignKey('usuarios.id_user'), nullable=False)
    email = db.Column(db.String(255), db.ForeignKey('usuarios.email'), nullable=False)
 
 
def configure_database(app, database_uri):
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    migrate.init_app(app, db)
 
    def __init__(self, usuario, quantidade_reabastecimento):
        self.usuario = usuario
        self.quantidade_reabastecimento = quantidade_reabastecimento
 