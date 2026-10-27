from datetime import date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _iso(d):
    return d.isoformat() if d else None


class Jabuti(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(60), nullable=False)
    especie = db.Column(db.String(20), nullable=False, default="piranga")
    sexo = db.Column(db.String(20), default="nao-sei")
    nascimento = db.Column(db.Date)
    chegada = db.Column(db.Date, default=date.today)
    tutor = db.Column(db.String(60), default="")
    microchip = db.Column(db.String(40), default="")
    foto = db.Column(db.Text)  # data URL (image/jpeg base64)
    criado_em = db.Column(db.Date, default=date.today)

    registros = db.relationship(
        "Registro", backref="jabuti", cascade="all, delete-orphan",
        order_by="(Registro.data, Registro.id)",
    )
    fotos = db.relationship(
        "PetFoto", backref="jabuti", cascade="all, delete-orphan",
        order_by="(PetFoto.data, PetFoto.id)",
    )

    @property
    def codigo(self):
        return f"JB-{self.id:04d}"

    def to_dict(self, com_registros=False):
        medidas = [r for r in self.registros if r.peso_g is not None or r.comprimento_cm is not None]
        peso = next((r.peso_g for r in reversed(self.registros) if r.peso_g is not None), None)
        tam = next((r.comprimento_cm for r in reversed(self.registros) if r.comprimento_cm is not None), None)
        d = {
            "id": self.id,
            "codigo": self.codigo,
            "nome": self.nome,
            "especie": self.especie,
            "sexo": self.sexo,
            "nascimento": _iso(self.nascimento),
            "chegada": _iso(self.chegada),
            "tutor": self.tutor,
            "microchip": self.microchip,
            "foto": self.foto,
            "criado_em": _iso(self.criado_em),
            "total_registros": len(self.registros),
            "total_medidas": len(medidas),
            "peso_atual_g": peso,
            "tamanho_atual_cm": tam,
        }
        if com_registros:
            d["registros"] = [r.to_dict() for r in self.registros]
        return d


class Ajuste(db.Model):
    """Chave/valor do servidor (ex.: hash da senha que a tutora criou)."""
    chave = db.Column(db.String(40), primary_key=True)
    valor = db.Column(db.Text, nullable=False)


class Registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jabuti_id = db.Column(db.Integer, db.ForeignKey("jabuti.id"), nullable=False)
    data = db.Column(db.Date, nullable=False, default=date.today)
    peso_g = db.Column(db.Float)
    comprimento_cm = db.Column(db.Float)
    comeu = db.Column(db.Boolean, default=False)
    banho = db.Column(db.Boolean, default=False)
    sol = db.Column(db.Boolean, default=False)
    humor = db.Column(db.String(20), default="feliz")
    observacao = db.Column(db.String(300), default="")
    foto = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "data": _iso(self.data),
            "peso_g": self.peso_g,
            "comprimento_cm": self.comprimento_cm,
            "comeu": self.comeu,
            "banho": self.banho,
            "sol": self.sol,
            "humor": self.humor,
            "observacao": self.observacao,
            "foto": self.foto,
        }


class PetFoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jabuti_id = db.Column(db.Integer, db.ForeignKey("jabuti.id"), nullable=False)
    foto = db.Column(db.Text, nullable=False)
    legenda = db.Column(db.String(200), default="")
    data = db.Column(db.Date, nullable=False, default=date.today)

    def to_dict(self):
        return {
            "id": self.id,
            "jabuti_id": self.jabuti_id,
            "foto": self.foto,
            "legenda": self.legenda,
            "data": _iso(self.data),
        }
