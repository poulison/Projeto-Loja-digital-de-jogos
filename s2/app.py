from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os, pymongo, redis, pymssql

# ---------- Config ----------
MSSQL_HOST = os.getenv("MSSQL_HOST", "sqlserver")
MSSQL_USER = os.getenv("MSSQL_USER", "sa")
MSSQL_PASS = os.getenv("MSSQL_PASSWORD", "Aa123456!")
MSSQL_DB   = os.getenv("MSSQL_DB", "marketdb")

MONGO_URL  = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB   = os.getenv("MONGO_DB", "marketdb")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# ---------- Conexões ----------
def mssql_conn():
    return pymssql.connect(server=MSSQL_HOST, user=MSSQL_USER, password=MSSQL_PASS,
                           database=MSSQL_DB, as_dict=True)

mongo = pymongo.MongoClient(MONGO_URL)
mdb = mongo[MONGO_DB]
games = mdb["games"]

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ---------- FastAPI ----------
app = FastAPI(title="S2 - Loja de Jogos (SQL + Mongo + Redis)")

@app.get("/health")
def health():
    try:
        with mssql_conn() as c: pass
        mongo.admin.command("ping")
        r.ping()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"health error: {e}")

# ---------- Models ----------
class ClienteIn(BaseModel):
    Nome: str
    Email: str
    Telefone: str | None = None
    CPF: str | None = None
    DataNascimento: str | None = None  # YYYY-MM-DD
    Rua: str | None = None
    Cidade: str | None = None
    Estado: str | None = None
    CEP: str | None = None
    PlataformaFavorita: str | None = None

class JogoIn(BaseModel):
    sku: str
    titulo: str | None = None
    plataforma: str | None = None
    genero: str | None = None
    preco: float | None = None
    estoque: int | None = None
    classificacao_indicativa: int | None = Field(default=None, ge=0)

class CartItem(BaseModel):
    sku: str
    qty: int = Field(..., ge=1)

# ---------- Clientes (SQL Server) ----------
@app.get("/clientes")
def listar_clientes():
    with mssql_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM dbo.Clientes ORDER BY IdCliente")
            return list(cur.fetchall())

@app.post("/clientes")
def criar_cliente(c: ClienteIn):
    with mssql_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO dbo.Clientes
                (Nome, Email, Telefone, CPF, DataNascimento, Rua, Cidade, Estado, CEP, PlataformaFavorita)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (c.Nome, c.Email, c.Telefone, c.CPF, c.DataNascimento,
                  c.Rua, c.Cidade, c.Estado, c.CEP, c.PlataformaFavorita))
            conn.commit()
            cur.execute("SELECT TOP 1 * FROM dbo.Clientes WHERE Email=%s", (c.Email,))
            return cur.fetchone()

# ---------- Jogos (Mongo) ----------
def _normalize_game(doc: dict) -> dict:
    # aceita tanto campos pt (titulo, plataforma...) quanto en (title, platform...)
    if "title" in doc and "titulo" not in doc:
        doc["titulo"] = doc.pop("title")
    if "platform" in doc and "plataforma" not in doc:
        doc["plataforma"] = doc.pop("platform")
    if "genre" in doc and "genero" not in doc:
        doc["genero"] = doc.pop("genre")
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

@app.get("/jogos")
def listar_jogos():
    return [_normalize_game(x) for x in games.find({}).sort("sku")]

@app.post("/jogos")
def criar_jogo(j: JogoIn):
    # cria índices na primeira vez (idempotente)
    games.create_index([("sku", 1)], unique=True)
    games.create_index([("plataforma", 1), ("genero", 1)])
    games.create_index([("titulo", "text")])
    try:
        res = games.insert_one({k: v for k, v in j.dict().items() if v is not None})
        return {"inserted_id": str(res.inserted_id)}
    except pymongo.errors.DuplicateKeyError:
        raise HTTPException(409, "SKU já existente")

@app.get("/jogos/busca")
def buscar_jogos(q: str | None = None, plataforma: str | None = None, genero: str | None = None):
    filtro = {}
    if q: filtro["$text"] = {"$search": q}
    if plataforma: filtro["plataforma"] = plataforma
    if genero: filtro["genero"] = genero
    return [_normalize_game(x) for x in games.find(filtro).limit(50)]

# ---------- Carrinho (Redis) ----------
def _cart_key(cid: int) -> str:
    return f"cart:{cid}"

@app.post("/carrinho/{id_cliente}/itens")
def adicionar_item(id_cliente: int, item: CartItem):
    # incrementa quantidade do sku no hash
    r.hincrby(_cart_key(id_cliente), item.sku, item.qty)
    return {"ok": True, "items": r.hgetall(_cart_key(id_cliente))}

@app.get("/carrinho/{id_cliente}")
def listar_carrinho(id_cliente: int):
    raw = r.hgetall(_cart_key(id_cliente))  # {sku: qty}
    # enriquece com dados do Mongo
    items = []
    for sku, qty in raw.items():
        prod = games.find_one({"sku": sku}) or {}
        prod = _normalize_game(prod)
        items.append({"sku": sku, "qty": int(qty), "jogo": prod})
    return {"cliente": id_cliente, "itens": items}

@app.delete("/carrinho/{id_cliente}/itens/{sku}")
def remover_item(id_cliente: int, sku: str):
    r.hdel(_cart_key(id_cliente), sku)
    return {"ok": True, "items": r.hgetall(_cart_key(id_cliente))}

@app.delete("/carrinho/{id_cliente}")
def esvaziar_carrinho(id_cliente: int):
    r.delete(_cart_key(id_cliente))
    return {"ok": True}
