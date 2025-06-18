import sqlite3

class Usuario:
    def __init__(self, db_path="gama.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.criar_tabela()

    def inserir_estacionamento(self, id_estacionamento, nome, endereco, capacidade_total, cnpj, status):
        """Insere um novo usuário no banco"""
        try:
            self.cursor.execute('''
                INSERT INTO estacionamento (id_estacionamento, nome, endereco, capacidade_total, cnpj, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (id_estacionamento, nome, endereco, capacidade_total, cnpj, status))
            self.conn.commit()
            print("Estacionamento cadastrado com sucesso.")
        except sqlite3.Error as e:
            print(f"Erro ao cadastrar estacionamento: {e}")

    def buscar_estacionamento(self, id_estacionamento):
        """Busca um estacioanmento pelo ID"""
        self.cursor.execute("SELECT * FROM estacionamento WHERE id_estacionamento = ?", (id_estacionamento,))
        return self.cursor.fetchone()

    def atualizar_estacionamento(self, id_estacionamento, nome=None, endereco=None, capacidade_total=None, cnpj=None, status=None):
        """Atualiza os dados do estacionamento"""
        updates = []
        values = []

        if nome:
            updates.append("nome = ?")
            values.append(nome)
        if endereco:
            updates.append("endereco = ?")
            values.append(endereco)
        if capacidade_total:
            updates.append("capacidade_total = ?")
            values.append(capacidade_total)
        if cnpj:
            updates.append("cnpj = ?")
            values.append(cnpj)
        if status:
            updates.append("status = ?")
            values.append(status)

        values.append(id_estacionamento)
        query = f"UPDATE estacionamento SET {', '.join(updates)} WHERE id_estacionamento = ?"
        self.cursor.execute(query, values)
        self.conn.commit()

    def remover_estacionamento(self, id_estacionamento):
        """Remove o estacionamento pelo ID"""
        self.cursor.execute("DELETE FROM estacionamento WHERE id_estacionamento = ?", (id_estacionamento,))
        self.conn.commit()
        print("Estacionamento removido com sucesso.")

    def listar_estacionamentos(self):
        """Lista todos os estacionamentos cadastrados"""
        self.cursor.execute("SELECT * FROM estacionamento")
        return self.cursor.fetchall()

    def fechar_conexao(self):
        """Fecha a conexão com o banco"""
        self.conn.close()

