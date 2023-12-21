from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id_user = db.Column(db.Integer, primary_key=True)
    id_repositor = db.Column(db.Integer, db.ForeignKey('repositor.id_repositor'), unique=True, nullable=True)
    repositor = db.relationship('Repositor', back_populates='usuario', uselist=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    senha = db.Column(db.String(255), nullable=False)
    tipo_user = db.Column(db.String(50), nullable=False)

    def get_id(self):
        return str(self.id_user)

    def is_active(self):
        return True

    def is_authenticated(self):
        return True if self else False

    def is_anonymous(self):
        return False

class Repositor(db.Model):
    __tablename__ = 'repositor'

    id_repositor = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id_user'))
    usuario = db.relationship('Usuario', back_populates='repositor')
    estoque = db.Column(db.Integer, nullable=False)

class Reposicao(db.Model):
    __tablename__ = 'reposicao'
    id_reposicao = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_repositor = db.Column(db.Integer, db.ForeignKey('repositor.id_repositor'), nullable=False)
    data_reposicao = db.Column(db.Date, nullable=False)
    tipo_reposicao = db.Column(db.String(50), nullable=False)
    quantidade_reposicao = db.Column(db.Integer, nullable=False)
    andar = db.Column(db.String(50), nullable=False) 
    ilha = db.Column(db.String(50), nullable=False)
    predio = db.Column(db.String(50), nullable=False)
    status_reposicao = db.Column(db.String(20), nullable=False, default='pendente')
    
class InfoAndar(db.Model):
    __tablename__ = 'info_andar'

    id_info_andar = db.Column(db.Integer, primary_key=True)
    andar = db.Column(db.String(50), nullable=False)
    num_ilhas = db.Column(db.Integer, nullable=False)
    predio = db.Column(db.String(50), db.ForeignKey('reposicao.predio'), nullable=False)

    # Relacionamento com a tabela Reposicao
    reposicoes = db.relationship('Reposicao', backref='info_andar')

class Reabastecimento(db.Model):
    __tablename__ = 'reabastecimento'
 
    id_reabastecimento = db.Column(db.Integer, primary_key=True)
    quantidade_reabastecimento = db.Column(db.Integer)
    id_repositor = db.Column(
        db.Integer, db.ForeignKey('repositor.id_repositor'))
    estoque_atualizado = db.Column(db.Integer)
 
    def __repr__(self):
        return f"<Reabastecimento {self.id_reabastecimento}>"

def configure_database(app, database_uri):
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    migrate.init_app(app, db)