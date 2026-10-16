# Copie este conteúdo para o arquivo WSGI do PythonAnywhere
# (aba Web → "WSGI configuration file") e troque SEUUSUARIO, o domínio e as senhas.
# Este arquivo do PythonAnywhere fica só na sua conta, então as senhas não vão para o git.
import os
import sys

sys.path.insert(0, "/home/SEUUSUARIO/yukijabuti-backend")
# Por enquanto só o front local; depois do deploy da Vercel, acrescente o domínio separado por vírgula:
# "http://localhost:3000,https://SEU-PROJETO.vercel.app"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:3000"
# Gere uma chave com: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
os.environ["SECRET_KEY"] = "COLE-A-CHAVE-GERADA-AQUI"
# Senha que a tutora digita na tela "Entrar para editar"
os.environ["EDITOR_SENHA"] = "TROQUE-ESTA-SENHA"

from app import app as application  # noqa: E402
