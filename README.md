# 🐢 Yuki Jabuti — API (back-end)

API em **Flask + SQLite** do diário da Yuki. Hospedagem: **PythonAnywhere**.
O front-end fica em outro repositório (`yukijabuti-frontend`, na Vercel).

## Estrutura

```
app.py                  cria a aplicação, CORS e tratamento de erros
config.py               configurações (banco, CORS, espécie padrão)
models.py               tabelas Jabuti e Registro
routes.py               rotas /api/...
wsgi_pythonanywhere.py  modelo do arquivo WSGI
```

## Rodar no computador

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
SECRET_KEY=dev python app.py   # http://localhost:5000/api/saude
```

## Login da tutora

Ler é público (quem recebe o link vê o diário). Criar, alterar e apagar exigem um token
no cabeçalho `Authorization: Bearer ...`.

- No primeiro acesso a tutora cria a senha (`POST /api/senha`); ela fica com hash no banco.
  Depois disso essa rota fica bloqueada — crie a senha logo depois do deploy.
- `POST /api/login` devolve o token. Depois de 5 senhas erradas, aquele IP espera 15 minutos.
- `PUT /api/senha` troca a senha e desloga os outros aparelhos.
- Esqueceu? Defina `EDITOR_SENHA` (senha de resgate) no WSGI, entre com ela e troque a senha em Ajustes.
- Trocar `SECRET_KEY` desloga todos os aparelhos.

## Rotas

| Método | Rota | O que faz |
|---|---|---|
| GET | /api/saude | teste rápido |
| POST | /api/senha | primeiro acesso: cria a senha (`senha`) → `token` |
| PUT | /api/senha | troca a senha (pede token) → `token` novo |
| POST | /api/login | `senha` → `token` da tutora |
| GET | /api/sessao | `editora` (token válido?) e `senha_criada` |
| GET | /api/config | espécies aceitas e espécie padrão |
| GET | /api/jabutis | lista os jabutis |
| POST | /api/jabutis | cria (`nome`, `especie`, `sexo`, `nascimento`, `chegada`, `tutor`, `microchip`, `foto`) |
| GET | /api/jabutis/:id | jabuti com todos os registros |
| PATCH | /api/jabutis/:id | altera só os campos enviados (ex.: nova foto) |
| DELETE | /api/jabutis/:id | apaga jabuti e registros |
| POST | /api/jabutis/:id/registros | dia/medida: `data, peso_g, comprimento_cm, comeu, banho, sol, humor, observacao, foto` |
| GET | /api/jabutis/:id/fotos | galeria pública do jabuti |
| POST | /api/jabutis/:id/fotos | adiciona mídia à galeria (`foto`/`imagem`, `legenda`, `data`) |
| PATCH | /api/fotos/:id | altera somente a descrição (`legenda` ou `caption`) |
| DELETE | /api/registros/:id | apaga um registro |
| DELETE | /api/fotos/:id | apaga uma mídia da galeria |

POST, PATCH e DELETE pedem o token da tutora (sem ele: 401).

`especie`: `piranga` (padrão), `tinga` ou `outra`. Os campos `foto` aceitam data URLs
JPEG, PNG, GIF e WebP de até **20 MB decodificados**. A galeria e `Registro.foto`
também aceitam vídeos MP4, WebM e MOV (`video/quicktime`) de até **100 MB decodificados**.
O MIME declarado precisa corresponder à assinatura do arquivo; base64 inválido e conteúdo
malformado são rejeitados. As respostas mantêm `foto` e acrescentam `foto_tipo`; itens
da galeria usam `tipo` (também exposto como `media_type`).

## Deploy no PythonAnywhere

1. Console **Bash**: `git clone <seu-repo> yukijabuti-backend`
2. `mkvirtualenv yuki --python=python3.10` e `pip install -r yukijabuti-backend/requirements.txt`
3. Aba **Web** → *Add a new web app* → *Manual configuration* → Python 3.10
4. **Virtualenv**: `/home/SEUUSUARIO/.virtualenvs/yuki`
5. Cole o conteúdo de `wsgi_pythonanywhere.py` no arquivo WSGI, ajustando usuário e domínio da Vercel
6. **Reload** e teste `https://SEUUSUARIO.pythonanywhere.com/api/saude`

O startup chama `create_all()` e aplica apenas `ALTER TABLE` para colunas novas (`foto_tipo`
e os campos de mídia de `Registro`); não apaga nem recria o banco existente. A tabela de
galeria é criada automaticamente. O limite HTTP é 140 MiB para acomodar a expansão base64
de um vídeo de 100 MB e o JSON. Em PythonAnywhere, confirme também que o proxy/web app
aceita esse request; o Flask responderá HTTP 413 quando o limite for excedido.
