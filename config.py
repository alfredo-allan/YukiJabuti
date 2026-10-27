import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "yuki.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Domínios do front-end liberados no CORS (separe vários por vírgula)
    FRONTEND_ORIGIN = os.environ.get(
        "FRONTEND_ORIGIN", "http://localhost:3000,https://yuki-jabuti-web-site.vercel.app"
    )
    # Login da tutora: só quem sabe a senha altera; o resto do mundo só visualiza.
    # A tutora cria a senha no primeiro acesso (fica salva com hash no banco).
    SECRET_KEY = os.environ.get("SECRET_KEY")
    # Opcional: senha de resgate do adulto, se ela esquecer a dela
    EDITOR_SENHA = os.environ.get("EDITOR_SENHA")
    TOKEN_VALIDADE_S = 180 * 24 * 3600  # 6 meses logada no aparelho
    MAX_FOTO_BYTES = 20 * 1024 * 1024
    MAX_VIDEO_BYTES = 100 * 1024 * 1024
    # Base64 expands the media by about one third; leave room for JSON metadata.
    MAX_CONTENT_LENGTH = 140 * 1024 * 1024

    ESPECIES = ("piranga", "tinga", "outra")
    ESPECIE_PADRAO = "piranga"
