import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# Função para conectar ao banco de dados
def conectar():
    diretorio_db = "gama/database"
    if not os.path.exists(diretorio_db):
        os.makedirs(diretorio_db)
    
    return sqlite3.connect(f"{diretorio_db}/editais.db")

# Função para verificar o login
def verificar_login(email, senha):
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM Usuario WHERE email = ?", (email,))
    usuario = cursor.fetchone()
    conn.close()
    
    if usuario and check_password_hash(usuario[4], senha):
        return usuario
    return None

# Função para criar as tabelas e dados iniciais no banco
def criar_tabelas():
    conexao = conectar()
    cursor = conexao.cursor()
    
    # Criação das tabelas principais
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS Edital (
        id_edital INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_edital TEXT NOT NULL UNIQUE,
        data_edital DATE NOT NULL,
        data_publicacao DATE NOT NULL,
        vencimento_edital DATE NOT NULL,
        prazo_prorrogacao INTEGER,
        status TEXT NOT NULL CHECK (status IN ('ativo', 'inativo', 'prorrogado'))
    );
    
    CREATE TABLE IF NOT EXISTS Cargo (
        id_cargo INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_cargo TEXT NOT NULL,
        id_edital INTEGER NOT NULL,
        FOREIGN KEY (id_edital) REFERENCES Edital(id_edital),
        UNIQUE (nome_cargo, id_edital)
    );
    
    CREATE TABLE IF NOT EXISTS Candidato (
        id_candidato INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        numero_inscricao TEXT NOT NULL UNIQUE,
        nota FLOAT NOT NULL,
        id_cargo INTEGER NOT NULL,
        ordem_nomeacao INTEGER NOT NULL,
        pcd BOOLEAN NOT NULL,
        cotista BOOLEAN NOT NULL,
        situacao TEXT NOT NULL CHECK (situacao IN ('nomeado', 'a_nomear')),
        data_posse DATE,
        id_edital INTEGER NOT NULL,
        FOREIGN KEY (id_cargo) REFERENCES Cargo(id_cargo),
        FOREIGN KEY (id_edital) REFERENCES Edital(id_edital)
    );
    
    CREATE TABLE IF NOT EXISTS Usuario (
        id_usuario TEXT PRIMARY KEY,
        cpf_usuario TEXT NOT NULL,
        nome TEXT NOT NULL,
        email TEXT NOT NULL,
        senha TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK (tipo IN ('administrador', 'usuario')),
        data_ingresso DATETIME NOT NULL,
        data_saida DATETIME
    );
    """)
    
    # Verifica se o usuário master já existe pelo id_usuario
    cursor.execute("SELECT * FROM Usuario WHERE id_usuario = ?", ('master_001',))
    if not cursor.fetchone():
        hashed_password = generate_password_hash('admin123')
        cursor.execute("""
        INSERT INTO Usuario (id_usuario, cpf_usuario, nome, email, senha, tipo, data_ingresso)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            'master_001',
            '00000000000',
            'Administrador Master',
            'master@admin.com',
            hashed_password,
            'administrador',
            datetime.datetime.now()
        ))
    
    conexao.commit()
    conexao.close()

# Executa a criação das tabelas e dados iniciais
criar_tabelas()

# Função para adicionar um usuário ao banco
def adicionar_usuario(nome, email, senha, tipo):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO Usuario (nome, email, senha, tipo)
    VALUES (?, ?, ?, ?)
    """, (nome, email, senha, tipo))
    conn.commit()
    conn.close()