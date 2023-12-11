from database import db, Usuario

# Em validacoesLogin.py

def verificar_credenciais(email, senha):
    print(f'Tentando autenticar com Email: {email}, Senha: {senha}')  # Debugging
    usuario = Usuario.query.filter_by(email=email, senha=senha).first()
    print(f'Usuário encontrado: {usuario}')  # Debugging
    return usuario
