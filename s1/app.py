from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
import sqlite3
from datetime import datetime
import random

app = FastAPI(title="S1 - Orquestrador / Cliente de teste", version="1.0.0")

# =========================================================
# CONFIG
# =========================================================
# dentro do docker compose o nome do serviço do S2 é "s2"
S2_BASE_URL = os.getenv("S2_BASE_URL", "http://s2:8000")

DB_PATH = os.getenv("LOG_DB_PATH", "s1_logs.db")

# =========================================================
# DB (SQLite) - para guardar tudo que o S1 fez
# =========================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            acao TEXT NOT NULL,
            endpoint_s2 TEXT NOT NULL,
            request_json TEXT,
            response_status INTEGER,
            response_json TEXT
        );
        """
    )
    conn.commit()
    conn.close()

init_db()

def save_log(acao: str, endpoint_s2: str, request_json: str, response_status: int, response_json: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO logs (timestamp, acao, endpoint_s2, request_json, response_status, response_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(),
            acao,
            endpoint_s2,
            request_json,
            response_status,
            response_json,
        ),
    )
    conn.commit()
    conn.close()

# =========================================================
# MODELOS (só pra tipar os endpoints do S1, não do S2)
# =========================================================

class ForcarCliente(BaseModel):
    nome: str | None = None
    email: str | None = None
    cpf: str | None = None

class ForcarJogo(BaseModel):
    sku: str | None = None
    titulo: str | None = None


# =========================================================
# FUNÇÕES GERADORAS DE DADOS
# =========================================================

def gerar_cliente_fake():
    # coisas simples só pro demo
    nomes = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe"]
    cidades = ["São Paulo", "Rio", "BH", "Campinas", "Curitiba"]
    estados = ["SP", "RJ", "MG", "PR"]

    nome = random.choice(nomes)
    cpf = f"{random.randint(10000000000, 99999999999)}"
    email = f"{nome.lower()}@teste.com"

    return {
        "Nome": nome,
        "Email": email,
        "Telefone": None,
        "CPF": cpf,
        "DataNascimento": "2000-01-01",
        "Rua": "Rua de Teste",
        "Cidade": random.choice(cidades),
        "Estado": random.choice(estados),
        "CEP": "00000-000",
        "PlataformaFavorita": random.choice(["PS5", "Xbox", "PC", "Switch"]),
    }


def gerar_jogo_fake():
    titulos = ["GTA V", "The Witcher 3", "FIFA 25", "Minecraft", "Elden Ring"]
    plataformas = ["PS5", "PS4", "Xbox", "PC", "Switch"]
    generos = ["Ação", "RPG", "Esporte", "Aventura"]

    titulo = random.choice(titulos)
    plataforma = random.choice(plataformas)

    return {
        "sku": f"{titulo[:3].upper()}-{random.randint(1000,9999)}",
        "titulo": titulo,
        "plataforma": plataforma,
        "genero": random.choice(generos),
        "preco": round(random.uniform(50, 300), 2),
        "estoque": random.randint(0, 50),
        "classificacao_indicativa": random.choice([0, 10, 12, 14, 16, 18]),
    }


def gerar_item_carrinho_fake():
    # aqui o S1 vai supor que o cliente 1 está adicionando algo
    # e que já existe um jogo com esse sku — mas vamos deixar ele escolher
    return {
        "id_cliente": 1,
        "sku": "TESTE-SKU",   # o S2 vai validar; você pode sobrescrever
        "qty": 1
    }

# =========================================================
# ENDPOINTS DO S1
# =========================================================

@app.get("/")
def root():
    return {
        "message": "S1 rodando. Use /clientes/teste, /jogos/teste ou /carrinho/teste",
        "s2_base_url": S2_BASE_URL
    }

# ----------- CLIENTES -> SQL --------------
@app.post("/clientes/teste")
def criar_cliente_teste(body: ForcarCliente | None = None):
    payload = gerar_cliente_fake()

    # se o usuário quiser forçar nome/email/cpf, sobrescreve
    if body:
        if body.nome:
            payload["Nome"] = body.nome
        if body.email:
            payload["Email"] = body.email
        if body.cpf:
            payload["CPF"] = body.cpf

    url = f"{S2_BASE_URL}/clientes"
    resp = requests.post(url, json=payload)

    # salva log
    save_log(
        acao="criar_cliente",
        endpoint_s2=url,
        request_json=str(payload),
        response_status=resp.status_code,
        response_json=resp.text,
    )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {
        "enviado_para": url,
        "payload": payload,
        "resposta_s2": resp.json(),
    }

# ----------- JOGOS -> MONGO --------------
@app.post("/jogos/teste")
def criar_jogo_teste(body: ForcarJogo | None = None):
    payload = gerar_jogo_fake()
    if body:
        if body.sku:
            payload["sku"] = body.sku
        if body.titulo:
            payload["titulo"] = body.titulo

    url = f"{S2_BASE_URL}/jogos"
    resp = requests.post(url, json=payload)

    save_log(
        acao="criar_jogo",
        endpoint_s2=url,
        request_json=str(payload),
        response_status=resp.status_code,
        response_json=resp.text,
    )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {
        "enviado_para": url,
        "payload": payload,
        "resposta_s2": resp.json(),
    }

# ----------- CARRINHO -> REDIS --------------
@app.post("/carrinho/teste")
def adicionar_carrinho_teste():
    """
    Aqui o S1 vai tentar pegar um jogo qualquer do S2 primeiro.
    Se não tiver jogo nenhum, ele avisa.
    """
    # 1) pega lista de jogos do S2
    url_listar = f"{S2_BASE_URL}/jogos"
    resp_listar = requests.get(url_listar)

    if resp_listar.status_code != 200:
        save_log(
            acao="carrinho_falhou_listar_jogos",
            endpoint_s2=url_listar,
            request_json="{}",
            response_status=resp_listar.status_code,
            response_json=resp_listar.text,
        )
        raise HTTPException(status_code=500, detail="Não consegui listar jogos no S2")

    jogos = resp_listar.json()
    if not jogos:
        # loga e avisa
        save_log(
            acao="carrinho_sem_jogos",
            endpoint_s2=url_listar,
            request_json="{}",
            response_status=200,
            response_json="[]",
        )
        raise HTTPException(status_code=400, detail="Não há jogos no S2 para colocar no carrinho")

    # pega um jogo aleatório
    jogo = random.choice(jogos)
    sku = jogo["sku"]

    # 2) adiciona no carrinho do cliente 1
    url_carrinho = f"{S2_BASE_URL}/carrinho/1/itens"
    payload = {
        "sku": sku,
        "qty": 1
    }
    resp = requests.post(url_carrinho, json=payload)

    save_log(
        acao="carrinho_adicionar",
        endpoint_s2=url_carrinho,
        request_json=str(payload),
        response_status=resp.status_code,
        response_json=resp.text,
    )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {
        "enviado_para": url_carrinho,
        "payload": payload,
        "resposta_s2": resp.json(),
    }

# ----------- LOGS --------------
@app.get("/logs")
def listar_logs():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, timestamp, acao, endpoint_s2, request_json, response_status, response_json FROM logs ORDER BY id DESC LIMIT 200")
    rows = cur.fetchall()
    conn.close()

    logs = []
    for r in rows:
        logs.append({
            "id": r[0],
            "timestamp": r[1],
            "acao": r[2],
            "endpoint_s2": r[3],
            "request_json": r[4],
            "response_status": r[5],
            "response_json": r[6],
        })

    return logs
