from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import pymssql
import pymongo
import redis
from datetime import datetime
import json

app = FastAPI(title="S2 - Loja de Jogos", version="1.0.0")

# =========================================================
# CONFIGURAÇÕES / VARIÁVEIS DE AMBIENTE
# =========================================================
SQL_HOST = os.getenv("SQL_HOST", "sqlserver")
SQL_USER = os.getenv("SQL_USER", "sa")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "Your_strong_password123!")
SQL_DB = os.getenv("SQL_DB", "marketdb")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "marketdb")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


# =========================================================
# FUNÇÕES DE CONEXÃO
# =========================================================
def get_sql_conn():
    try:
        return pymssql.connect(
            server=SQL_HOST,
            user=SQL_USER,
            password=SQL_PASSWORD,
            database=SQL_DB,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao conectar no SQL Server: {e}")


def get_mongo_collection():
    try:
        client = pymongo.MongoClient(MONGO_URL)
        db = client[MONGO_DB]
        col = db["games"]
        # garante índice de SKU
        existing = col.index_information()
        if "sku_1" not in existing:
            col.create_index([("sku", 1)], unique=True)
        return col
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao conectar no MongoDB: {e}")


def get_redis():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()  # teste rápido de conexão
        return r
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao conectar no Redis: {e}")


# =========================================================
# MODELOS
# =========================================================
class ClienteIn(BaseModel):
    Nome: str
    Email: str
    Telefone: str | None = None
    CPF: str
    DataNascimento: str | None = None  # yyyy-mm-dd
    Rua: str | None = None
    Cidade: str | None = None
    Estado: str | None = None
    CEP: str | None = None
    PlataformaFavorita: str | None = None


class JogoIn(BaseModel):
    sku: str
    titulo: str
    plataforma: str
    genero: str
    preco: float
    estoque: int = 0
    classificacao_indicativa: int | None = Field(default=None, ge=0)


class ItemCarrinhoIn(BaseModel):
    sku: str
    qty: int = Field(gt=0)


# =========================================================
# HEALTHCHECK
# =========================================================
@app.get("/health")
def health():
    """
    Verifica se todos os bancos estão acessíveis.
    """
    try:
        conn = get_sql_conn()
        conn.close()
    except Exception as e:
        return {"status": "degraded", "sql": str(e)}

    try:
        col = get_mongo_collection()
        col.estimated_document_count()
    except Exception as e:
        return {"status": "degraded", "mongo": str(e)}

    try:
        r = get_redis()
        r.ping()
    except Exception as e:
        return {"status": "degraded", "redis": str(e)}

    return {"status": "ok"}


# =========================================================
# ENDPOINTS - CLIENTES (SQL)
# =========================================================
@app.post("/clientes")
def criar_cliente(cliente: ClienteIn):
    conn = get_sql_conn()
    cur = conn.cursor(as_dict=True)

    try:
        cur.execute("""
            INSERT INTO Clientes
                (Nome, Email, Telefone, CPF, DataNascimento,
                 Rua, Cidade, Estado, CEP, PlataformaFavorita)
            VALUES
                (%s, %s, %s, %s, %s,
                 %s, %s, %s, %s, %s)
        """, (
            cliente.Nome,
            cliente.Email,
            cliente.Telefone,
            cliente.CPF,
            cliente.DataNascimento,
            cliente.Rua,
            cliente.Cidade,
            cliente.Estado,
            cliente.CEP,
            cliente.PlataformaFavorita,
        ))
        conn.commit()
    except pymssql.IntegrityError:
        raise HTTPException(status_code=409, detail="Já existe cliente com esse CPF")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar cliente: {e}")
    finally:
        conn.close()

    return {"message": "cliente criado com sucesso"}


@app.get("/clientes")
def listar_clientes():
    conn = get_sql_conn()
    cur = conn.cursor(as_dict=True)
    cur.execute("SELECT TOP 100 * FROM Clientes ORDER BY IdCliente DESC;")
    rows = cur.fetchall()
    conn.close()
    return rows


# =========================================================
# ENDPOINTS - JOGOS (MONGO)
# =========================================================
@app.post("/jogos")
def criar_jogo(jogo: JogoIn):
    col = get_mongo_collection()
    doc = jogo.model_dump()

    try:
        result = col.insert_one(doc)
    except pymongo.errors.DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Já existe jogo com esse SKU")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar jogo: {e}")

    # remove _id antes de retornar
    doc.pop("_id", None)

    return {
        "message": "jogo criado com sucesso",
        "jogo": doc,
        "id_mongo": str(result.inserted_id),
    }


@app.get("/jogos")
def listar_jogos():
    col = get_mongo_collection()
    jogos = list(col.find({}, {"_id": 0}))
    return jogos


# =========================================================
# ENDPOINTS - CARRINHO (REDIS)
# =========================================================
@app.post("/carrinho/{id_cliente}/itens")
def adicionar_item_carrinho(id_cliente: int, item: ItemCarrinhoIn):
    col = get_mongo_collection()
    jogo = col.find_one({"sku": item.sku}, {"_id": 0})

    if not jogo:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    r = get_redis()
    key = f"carrinho:{id_cliente}"

    item_data = {
        "sku": item.sku,
        "titulo": jogo.get("titulo"),
        "preco": jogo.get("preco"),
        "quantidade": item.qty,
        "adicionado_em": datetime.utcnow().isoformat()
    }

    # salva no Redis
    r.hset(key, item.sku, json.dumps(item_data))

    raw = r.hgetall(key)
    carrinho = {sku: json.loads(v) for sku, v in raw.items()}

    return {"id_cliente": id_cliente, "carrinho": carrinho}


@app.get("/carrinho/{id_cliente}")
def obter_carrinho(id_cliente: int):
    r = get_redis()
    key = f"carrinho:{id_cliente}"
    raw = r.hgetall(key)
    carrinho = {sku: json.loads(v) for sku, v in raw.items()}
    return {"id_cliente": id_cliente, "carrinho": carrinho}
