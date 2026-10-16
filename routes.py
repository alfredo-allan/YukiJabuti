import hmac
import time
from datetime import date
from functools import wraps

from flask import Blueprint, abort, current_app, jsonify, request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash
from models import Ajuste, Jabuti, Registro, db

api = Blueprint("api", __name__, url_prefix="/api")

SEXOS = ("macho", "femea", "nao-sei")
HUMORES = ("feliz", "calmo", "sonolento", "estranho")


# ---------- login da tutora ----------
_tentativas = {}  # ip -> [horários das senhas erradas]
MAX_TENTATIVAS, JANELA_S = 5, 15 * 60


def _assinador():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="editora")


def _ip():
    return (request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For", "").split(",")[0]
            or request.remote_addr or "?").strip()


def _hash_senha():
    a = db.session.get(Ajuste, "senha_hash")
    return a.valor if a else None


def _versao():
    # Muda quando a senha muda: trocar a senha desloga os outros aparelhos
    h = _hash_senha()
    return h[-12:] if h else "resgate"


def _novo_token():
    return _assinador().dumps(_versao())


def _validar_senha_nova(d):
    senha = str(d.get("senha", ""))
    if len(senha) < 4:
        abort(400, "A senha precisa ter pelo menos 4 letras ou números.")
    if len(senha) > 100:
        abort(400, "Essa senha é comprida demais.")
    return senha


def _token_valido():
    cab = request.headers.get("Authorization", "")
    if not cab.startswith("Bearer "):
        return False
    try:
        versao = _assinador().loads(cab[7:], max_age=current_app.config["TOKEN_VALIDADE_S"])
    except BadSignature:
        return False
    return hmac.compare_digest(str(versao), _versao())


def editora(f):
    """Rotas que alteram dados: só com o token da tutora."""
    @wraps(f)
    def interna(*a, **kw):
        if not _token_valido():
            abort(401, "Só a tutora pode alterar o diário. Entre com a senha.")
        return f(*a, **kw)
    return interna


# ---------- validação ----------
def _num(v):
    if v in (None, ""):
        return None
    try:
        n = float(str(v).replace(",", "."))
    except ValueError:
        abort(400, "Peso e tamanho precisam ser números.")
    if n < 0 or n > 100000:
        abort(400, "Esse número não parece certo. Confira o peso ou o tamanho.")
    return n


def _data(v, campo="Data"):
    if not v:
        return None
    try:
        d = date.fromisoformat(v)
    except ValueError:
        abort(400, f"{campo} precisa estar no formato AAAA-MM-DD.")
    if d > date.today():
        abort(400, f"{campo} não pode ser no futuro.")
    return d


def _texto(v, limite):
    return (v or "").strip()[:limite]


def _foto(v):
    if v in (None, ""):
        return None
    if not isinstance(v, str) or not v.startswith("data:image/"):
        abort(400, "A foto precisa ser uma imagem.")
    if len(v) > current_app.config["MAX_FOTO_BYTES"]:
        abort(400, "A foto é grande demais. Tente outra.")
    return v


def _aplicar(j, dados, novo=False):
    """Aplica os campos enviados no jabuti (só os que vieram)."""
    if novo or "nome" in dados:
        nome = _texto(dados.get("nome"), 60)
        if not nome:
            abort(400, "Dê um nome para o seu jabuti.")
        j.nome = nome
    if "especie" in dados or novo:
        esp = dados.get("especie") or current_app.config["ESPECIE_PADRAO"]
        if esp not in current_app.config["ESPECIES"]:
            abort(400, "Espécie desconhecida.")
        j.especie = esp
    if "sexo" in dados:
        if dados["sexo"] not in SEXOS:
            abort(400, "Sexo inválido.")
        j.sexo = dados["sexo"]
    if "nascimento" in dados:
        j.nascimento = _data(dados["nascimento"], "Nascimento")
    if "chegada" in dados:
        j.chegada = _data(dados["chegada"], "Chegada") or date.today()
    if "tutor" in dados:
        j.tutor = _texto(dados["tutor"], 60)
    if "microchip" in dados:
        j.microchip = _texto(dados["microchip"], 40)
    if "foto" in dados:
        j.foto = _foto(dados["foto"])


# ---------- rotas ----------
@api.get("/saude")
def saude():
    return jsonify({"ok": True})


@api.post("/login")
def login():
    hash_senha, resgate = _hash_senha(), current_app.config["EDITOR_SENHA"]
    if not hash_senha and not resgate:
        abort(400, "Ainda não existe senha. Crie a sua primeiro.")
    ip, agora = _ip(), time.time()
    erros = [t for t in _tentativas.get(ip, []) if agora - t < JANELA_S]
    if len(erros) >= MAX_TENTATIVAS:
        abort(429, "Muitas tentativas. Espere 15 minutos e tente de novo.")
    senha = str((request.get_json(silent=True) or {}).get("senha", ""))
    # EDITOR_SENHA (opcional, no WSGI) é a senha de resgate do adulto, caso ela esqueça a dela
    certa = (hash_senha and check_password_hash(hash_senha, senha)) or (
        resgate and hmac.compare_digest(senha.encode(), resgate.encode()))
    if not certa:
        _tentativas[ip] = erros + [agora]
        time.sleep(1)
        abort(401, "Senha errada. Tente de novo.")
    _tentativas.pop(ip, None)
    return jsonify({"token": _novo_token()})


@api.post("/senha")
def criar_senha():
    """Primeiro acesso: a tutora cria a própria senha. Só funciona enquanto não existe nenhuma."""
    if _hash_senha():
        abort(400, "A senha já foi criada. Use a tela de entrar.")
    senha = _validar_senha_nova(request.get_json(silent=True) or {})
    db.session.add(Ajuste(chave="senha_hash", valor=generate_password_hash(senha)))
    db.session.commit()
    return jsonify({"token": _novo_token()}), 201


@api.put("/senha")
@editora
def trocar_senha():
    senha = _validar_senha_nova(request.get_json(silent=True) or {})
    a = db.session.get(Ajuste, "senha_hash") or Ajuste(chave="senha_hash")
    a.valor = generate_password_hash(senha)
    db.session.add(a)
    db.session.commit()
    return jsonify({"token": _novo_token()})


@api.get("/sessao")
def sessao():
    return jsonify({"editora": _token_valido(), "senha_criada": bool(_hash_senha())})


@api.get("/config")
def config():
    c = current_app.config
    return jsonify({"especies": list(c["ESPECIES"]), "especie_padrao": c["ESPECIE_PADRAO"]})


@api.get("/jabutis")
def listar():
    return jsonify([j.to_dict() for j in Jabuti.query.order_by(Jabuti.id).all()])


@api.post("/jabutis")
@editora
def criar():
    j = Jabuti()
    _aplicar(j, request.get_json(silent=True) or {}, novo=True)
    db.session.add(j)
    db.session.commit()
    return jsonify(j.to_dict()), 201


@api.get("/jabutis/<int:jid>")
def ver(jid):
    j = db.get_or_404(Jabuti, jid, description="Jabuti não encontrado.")
    return jsonify(j.to_dict(com_registros=True))


@api.patch("/jabutis/<int:jid>")
@editora
def editar(jid):
    j = db.get_or_404(Jabuti, jid, description="Jabuti não encontrado.")
    _aplicar(j, request.get_json(silent=True) or {})
    db.session.commit()
    return jsonify(j.to_dict(com_registros=True))


@api.delete("/jabutis/<int:jid>")
@editora
def apagar(jid):
    j = db.get_or_404(Jabuti, jid, description="Jabuti não encontrado.")
    db.session.delete(j)
    db.session.commit()
    return jsonify({"ok": True})


@api.post("/jabutis/<int:jid>/registros")
@editora
def registrar(jid):
    j = db.get_or_404(Jabuti, jid, description="Jabuti não encontrado.")
    d = request.get_json(silent=True) or {}
    humor = d.get("humor") or "feliz"
    if humor not in HUMORES:
        abort(400, "Humor inválido.")
    r = Registro(
        jabuti=j,
        data=_data(d.get("data")) or date.today(),
        peso_g=_num(d.get("peso_g")),
        comprimento_cm=_num(d.get("comprimento_cm")),
        comeu=bool(d.get("comeu")),
        banho=bool(d.get("banho")),
        sol=bool(d.get("sol")),
        humor=humor,
        observacao=_texto(d.get("observacao"), 300),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict()), 201


@api.delete("/registros/<int:rid>")
@editora
def apagar_registro(rid):
    r = db.get_or_404(Registro, rid, description="Registro não encontrado.")
    db.session.delete(r)
    db.session.commit()
    return jsonify({"ok": True})
