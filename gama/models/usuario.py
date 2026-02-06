import sqlite3
from datetime import datetime
from gama.database.database import conectar


class Usuario:
    def __init__(self, id_usuario, cpf, nome, email, senha, tipo='usuario', db_path="gama.db"):
        self.id_usuario = id_usuario
        self.cpf = cpf
        self.nome = nome
        self.email = email
        self.senha = senha
        self.tipo = tipo
        self.data_ingresso = datetime.now()
        self.data_saida = None
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def inserir_usuario(self):
        try:
            self.cursor.execute("""
                INSERT INTO usuario (id_usuario, cpf_usuario, nome, email, senha, tipo, data_ingresso, data_saida)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.id_usuario, self.cpf, self.nome, self.email, self.senha, self.tipo, self.data_ingresso, self.data_saida))
            self.conn.commit()
            print(f"Usuário {self.nome}({self.tipo}) cadastrado com sucesso.")
        except sqlite3.Error as e:
            print(f"Erro ao inserir usuário: {e}")
            self.conn.rollback()

    def buscar_usuario(self, id_usuario):
        self.cursor.execute("SELECT * FROM usuario WHERE id_usuario = ?", (id_usuario,))
        return self.cursor.fetchone()

    def buscar_tipo_usuario(self, id_usuario):
        self.cursor.execute("SELECT tipo FROM usuario WHERE id_usuario = ?", (id_usuario,))
        return self.cursor.fetchone()

    def atualizar_usuario(self, id_usuario, nome=None, email=None, senha=None, tipo=None, data_saida=None):
        updates = []
        values = []

        if nome:
            updates.append("nome = ?")
            values.append(nome)
        if email:
            updates.append("email = ?")
            values.append(email)
        if senha:
            updates.append("senha = ?")
            values.append(senha)
        if tipo:
            updates.append("tipo = ?")
            values.append(tipo)
        if data_saida:
            updates.append("data_saida = ?")
            values.append(data_saida)

        values.append(id_usuario)
        query = f"UPDATE usuario SET {', '.join(updates)} WHERE id_usuario = ?"
        self.cursor.execute(query, values)
        self.conn.commit()

    def remover_usuario(self, id_usuario):
        self.cursor.execute("DELETE FROM usuario WHERE id_usuario = ?", (id_usuario,))
        self.conn.commit()
        print("Usuário removido com sucesso.")

    def listar_usuarios(self):
        self.cursor.execute("SELECT * FROM usuario")
        return self.cursor.fetchall()

    def fechar_conexao(self):
        self.conn.close()

    @staticmethod
    def create(id_usuario, cpf_usuario, nome, email, senha_hash):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Usuario WHERE id_usuario = ? OR email = ?", (id_usuario, email))
            if cursor.fetchone():
                return False, "ID de usuário ou email já cadastrado."

            cursor.execute("""
                INSERT INTO Usuario 
                (id_usuario, cpf_usuario, nome, email, senha, tipo, data_ingresso)
                VALUES (?, ?, ?, ?, ?, 'usuario', ?)
            """, (id_usuario, cpf_usuario, nome, email, senha_hash, datetime.now()))
            conn.commit()
            return True, "Usuário cadastrado com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao cadastrar usuário: {e}"
        finally:
            conn.close()

    @staticmethod
    def delete(id_usuario):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Usuario WHERE id_usuario = ? AND tipo = 'usuario'", (id_usuario,))
            if not cursor.fetchone():
                return False, "Usuário não encontrado."

            cursor.execute("DELETE FROM Usuario WHERE id_usuario = ?", (id_usuario,))
            conn.commit()
            return True, "Usuário removido com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao remover usuário: {e}"
        finally:
            conn.close()

    @staticmethod
    def update(id_usuario, nome, email, cpf_usuario, senha_hash=None):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Usuario WHERE id_usuario = ? AND tipo = 'usuario'", (id_usuario,))
            if not cursor.fetchone():
                return False, "Usuário não encontrado."

            if senha_hash:
                query = """
                    UPDATE Usuario 
                    SET nome = ?, email = ?, cpf_usuario = ?, senha = ?
                    WHERE id_usuario = ?
                """
                params = (nome, email, cpf_usuario, senha_hash, id_usuario)
            else:
                query = """
                    UPDATE Usuario 
                    SET nome = ?, email = ?, cpf_usuario = ?
                    WHERE id_usuario = ?
                """
                params = (nome, email, cpf_usuario, id_usuario)

            cursor.execute(query, params)
            conn.commit()
            return True, "Usuário atualizado com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao atualizar usuário: {e}"
        finally:
            conn.close()

    @staticmethod
    def get_all():
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Usuario WHERE tipo = 'usuario'")
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erro ao buscar usuários: {e}")
            return []
        finally:
            conn.close()


class Administrador(Usuario):
    def __init__(self, id_usuario, cpf, nome, email, senha, db_path="gama.db"):
        super().__init__(id_usuario, cpf, nome, email, senha, tipo="administrador", db_path=db_path)

    def criar_usuario(self, id_usuario, cpf, nome, email, senha):
        novo_usuario = Usuario(id_usuario, cpf, nome, email, senha, tipo="usuario", db_path=self.db_path)
        novo_usuario.inserir_usuario()
