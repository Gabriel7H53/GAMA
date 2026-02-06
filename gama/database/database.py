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
        padrao_vencimento TEXT NOT NULL CHECK (padrao_vencimento IN ('D', 'E')),
        FOREIGN KEY (id_edital) REFERENCES Edital(id_edital),
        UNIQUE (nome_cargo, id_edital)
    );
    
    CREATE TABLE IF NOT EXISTS Candidato (
        id_candidato INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        numero_inscricao TEXT NOT NULL UNIQUE,
        nota FLOAT NOT NULL,
        id_cargo INTEGER NOT NULL,
        classificacao INTEGER NOT NULL,
        pcd BOOLEAN NOT NULL,
        cotista BOOLEAN NOT NULL,
        situacao TEXT NOT NULL CHECK (situacao IN ('nomeado', 'homologado', 'sem_efeito', 'empossado')),
        data_posse DATE,
        id_edital INTEGER NOT NULL,
        portaria TEXT,
        lotacao TEXT,
        contatado BOOLEAN NOT NULL DEFAULT 0,
        cod_vaga TEXT,
        FOREIGN KEY (id_cargo) REFERENCES Cargo(id_cargo),
        FOREIGN KEY (id_edital) REFERENCES Edital(id_edital)
    );
                         
    CREATE TABLE IF NOT EXISTS Agendamento (
        id_agendamento INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora_agendamento DATETIME NOT NULL,
        nome_pessoa_entrega TEXT NOT NULL,
        id_edital INTEGER NOT NULL,
        id_usuario TEXT NOT NULL,
        status_agendamento TEXT NOT NULL DEFAULT 'agendado' CHECK(status_agendamento IN ('agendado', 'concluido', 'confirmado')),
        tipo_agendamento TEXT NOT NULL DEFAULT 'documento' CHECK(tipo_agendamento IN ('documento', 'pericia')), 
        FOREIGN KEY (id_edital) REFERENCES Edital(id_edital),
        FOREIGN KEY (id_usuario) REFERENCES Usuario(id_usuario)
    );
                         
    CREATE TABLE IF NOT EXISTS Certificado (
        id_certificado INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_validacao TEXT NOT NULL UNIQUE,
        data_emissao DATETIME NOT NULL,
        nome_template TEXT NOT NULL,
        id_candidato INTEGER NOT NULL,
        id_usuario_emissor TEXT NOT NULL,
        FOREIGN KEY (id_candidato) REFERENCES Candidato(id_candidato),
        FOREIGN KEY (id_usuario_emissor) REFERENCES Usuario(id_usuario)
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

    CREATE TABLE IF NOT EXISTS Opcao (
        id_opcao INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_opcao TEXT NOT NULL, -- Ex: 'reitor', 'local', 'unidade'
        valor_opcao TEXT NOT NULL UNIQUE, -- Ex: 'Marcelo Matias de Almeida'
        is_default BOOLEAN NOT NULL DEFAULT 0
    );
                         
    CREATE TABLE IF NOT EXISTS CargoGestao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cod_cargo TEXT NOT NULL UNIQUE,
        nome_cargo TEXT NOT NULL,
        situacao TEXT NOT NULL CHECK (situacao IN ('Ativo', 'Inativo')),
        nivel TEXT NOT NULL CHECK (nivel IN ('D', 'E'))
    );
                         
    CREATE TABLE IF NOT EXISTS HistoricoVaga (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_vaga INTEGER NOT NULL,
        usuario_responsavel TEXT NOT NULL, -- Nome do usuário que fez a alteração
        descricao TEXT NOT NULL,           -- Ex: "Alterou ocupante de A para B"
        data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_vaga) REFERENCES Vaga(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS Vaga (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cod_vaga TEXT NOT NULL UNIQUE,
        situacao TEXT NOT NULL CHECK (situacao IN ('Ocupada', 'Livre')),
        ocupante_atual TEXT,
        area TEXT,
        observacoes TEXT,
        cargo_gestao_id INTEGER NOT NULL,
        FOREIGN KEY (cargo_gestao_id) REFERENCES CargoGestao(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS PortariaRascunho (
        id_edital INTEGER PRIMARY KEY,
        texto_portaria TEXT NOT NULL,
        data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_edital) REFERENCES Edital(id_edital) ON DELETE CASCADE
    );
    """)
    
    # Verifica se o usuário master já existe
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
    
    # Adiciona as opções padrão (se não existirem)
    opcoes_padrao = [
        ('reitor', 'Marcelo Matias de Almeida'),
        ('reitor', 'Zuleika Guimarães'),
        ('local', 'no Anfiteatro da Universidade Federal da Grande Dourados, Unidade 1'),
        ('local', 'Gabinete da Reitoria, Unidade II'),
        ('local', 'Anfiteatro da Unidade II UFGD'),
        ('unidade', 'Assessoria de Comunicação Social - ACS/UFGD'),
        ('unidade', 'Pró-reitoria de Gestão de Pessoas - PROGESP/UFGD')
    ]

    for tipo, valor in opcoes_padrao:
        cursor.execute("SELECT * FROM Opcao WHERE valor_opcao = ?", (valor,))
        if not cursor.fetchone():
            # A query INSERT não precisa mudar, pois 'is_default' tem o valor DEFAULT 0
            cursor.execute("INSERT INTO Opcao (tipo_opcao, valor_opcao) VALUES (?, ?)", (tipo, valor))

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