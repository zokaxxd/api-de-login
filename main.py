from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr, field_validator
import sqlite3
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
SECRET_KEY = "zoka_backend_2026_chave_super_secreta"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== TOKEN ====================

def criar_token(data: dict):
    dados = data.copy()
 
    # CORREÇÃO 1: estava como string "ACCESS_TOKEN_EXPiIRE_MINUTES" em vez da variável
    expiracao = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    dados.update({"exp": expiracao})
 
    token = jwt.encode(dados, SECRET_KEY, algorithm=ALGORITHM)
 
    return token

def verificar_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
 
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
 
        return {"id": user_id, "email": email}
 
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")


# ==================== HASH ====================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password[:72])

def verify_password(password: str, hashed: str):
    return pwd_context.verify(password[:72], hashed)


# ==================== MODELS ====================

class User(BaseModel):
    name: str
    idade: int
    email: EmailStr
    password: str

    @field_validator("idade")
    def validar_idade(cls, value):
        if value < 13:
            raise ValueError("Idade mínima é 13")
        return value


# ==================== DATABASE ====================

def criar_tabela():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        idade INTEGER,
        email TEXT UNIQUE,
        password TEXT
    )
    """)
    conn.commit()
    conn.close()

criar_tabela()

def get_db():
    conn = sqlite3.connect("users.db")
    return conn, conn.cursor()


# ==================== ROTAS ====================

@app.get("/")
def home():
    return {"msg": "API rodando"}


@app.get("/perfil")
def perfil(usuario: dict = Depends(verificar_token)):
    conn, cursor = get_db()
    cursor.execute("SELECT * FROM users WHERE id = ?", (usuario["id"],))
    dados = cursor.fetchone()
    conn.close()

    return {
        "seu_id": dados[0],
        "seu_nome": dados[1],
        "seu_idade": dados[2],
        "seu_email": dados[3]
    }


# CREATE
@app.post("/users")
def add_user(user: User):
    conn, cursor = get_db()

    cursor.execute("SELECT * FROM users WHERE email = ?", (user.email,))
    existe = cursor.fetchone()

    if existe:
        conn.close()
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    senha_hash = hash_password(user.password)

    cursor.execute(
        "INSERT INTO users (name, idade, email, password) VALUES (?, ?, ?, ?)",
        (user.name, user.idade, user.email, senha_hash)
    )

    conn.commit()
    conn.close()

    return {
        "msg": "usuario criado",
        "user": {
            "name": user.name,
            "idade": user.idade,
            "email": user.email
        }
    }


# READ ALL
@app.get("/users")
def get_users(name: str = None, limit: int = 10, offset: int = 0):
    conn, cursor = get_db()

    query = "SELECT * FROM users"
    params = ()

    if name:
        query += " WHERE name LIKE ?"
        params += (f"%{name}%",)

    if name:
        cursor.execute("SELECT COUNT(*) FROM users WHERE name LIKE ?", (f"%{name}%",))
    else:
        cursor.execute("SELECT COUNT(*) FROM users")

    total = cursor.fetchone()[0]

    query += " LIMIT ? OFFSET ?"
    params += (limit, offset)

    cursor.execute(query, params)
    dados = cursor.fetchall()

    conn.close()

    users = [
        {
            "id": u[0],
            "name": u[1],
            "idade": u[2],
            "email": u[3]
        }
        for u in dados
    ]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "users": users
    }


# READ ONE
@app.get("/users/{id}")
def get_user(id: int):
    conn, cursor = get_db()

    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    dados = cursor.fetchone()

    conn.close()

    if dados:
        return {
            "id": dados[0],
            "name": dados[1],
            "idade": dados[2],
            "email": dados[3]
        }

    raise HTTPException(status_code=404, detail="Usuário não encontrado")


# DELETE ONE
@app.delete("/users/{id}")
def delete_user(id: int):
    conn, cursor = get_db()

    cursor.execute("DELETE FROM users WHERE id = ?", (id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    conn.commit()
    conn.close()

    return {"msg": "usuario removido"}


# DELETE ALL
@app.delete("/users")
def delete_all():
    conn, cursor = get_db()

    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()

    return {"msg": "usuarios deletados"}


# UPDATE
@app.put("/users/{id}")
def update_user(id: int, user: User):
    conn, cursor = get_db()

    cursor.execute(
        "SELECT * FROM users WHERE email = ? AND id != ?",
        (user.email, id)
    )
    existe = cursor.fetchone()

    if existe:
        conn.close()
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    senha_hash = hash_password(user.password)

    cursor.execute(
        "UPDATE users SET name=?, idade=?, email=?, password=? WHERE id=?",
        (user.name, user.idade, user.email, senha_hash, id)
    )

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    conn.commit()
    conn.close()

    return {"msg": "usuario atualizado"}


# LOGIN
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn, cursor = get_db()

    cursor.execute("SELECT * FROM users WHERE email = ?", (form_data.username,))
    user = cursor.fetchone()

    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not verify_password(form_data.password, user[4]):
        raise HTTPException(status_code=401, detail="Senha incorreta")

    token = criar_token({"sub": str(user[0]), "email": user[3]})

    return {
        "access_token": token,
        "token_type": "bearer"
    }