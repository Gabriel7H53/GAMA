from gama.database.database import conectar
import sqlite3

class Candidato:
    def __init__(self, nome, numero_inscricao, nota, id_cargo, ordem_nomeacao, pcd, cotista, situacao="a_nomear", data_posse=None, id_edital=None, id_candidato=None):
        self.id_candidato = id_candidato
        self.nome = nome
        self.numero_inscricao = numero_inscricao
        self.id_cargo = id_cargo
        self.ordem_nomeacao = ordem_nomeacao
        self.pcd = pcd
        self.cotista = cotista
        self.situacao = situacao
        self.data_posse = data_posse
        self.id_edital = id_edital
        self.nota = nota

    def salvar(self):
        """Insere um novo candidato no banco de dados."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO Candidato (nome, numero_inscricao, id_cargo, ordem_nomeacao, pcd, cotista, situacao, data_posse, id_edital, nota)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.nome, self.numero_inscricao, self.nota, self.id_cargo, self.ordem_nomeacao, self.pcd, self.cotista, self.situacao, self.data_posse, self.id_edital))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao inserir candidato: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def buscar_por_numero_inscricao(numero_inscricao):
        """Busca um candidato pelo número de inscrição."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            SELECT c.*, ca.nome_cargo
            FROM Candidato c
            JOIN Cargo ca ON c.id_cargo = ca.id_cargo
            WHERE c.numero_inscricao = ?
            ''', (numero_inscricao,))
            candidato = cursor.fetchone()
            return candidato
        except sqlite3.Error as e:
            print(f"Erro ao buscar candidato: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def listar_todos():
        """Lista todos os candidatos cadastrados."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            SELECT c.*, ca.nome_cargo, e.numero_edital
            FROM Candidato c
            JOIN Cargo ca ON c.id_cargo = ca.id_cargo
            LEFT JOIN Edital e ON c.id_edital = e.id_edital
            ORDER BY c.ordem_nomeacao
            ''')
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erro ao listar candidatos: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def listar_por_edital(id_edital):
        """Lista todos os candidatos de um edital específico, agrupados por cargo."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id_cargo, nome_cargo FROM Cargo WHERE id_edital = ?", (id_edital,))
            cargos = cursor.fetchall()
            
            candidatos_por_cargo = {}
            for cargo in cargos:
                cursor.execute('''
                SELECT c.*, ca.nome_cargo
                FROM Candidato c
                JOIN Cargo ca ON c.id_cargo = ca.id_cargo
                WHERE c.id_edital = ? AND c.id_cargo = ?
                ORDER BY c.ordem_nomeacao
                ''', (id_edital, cargo[0]))
                candidatos_por_cargo[cargo[1]] = cursor.fetchall()
            
            return candidatos_por_cargo
        except sqlite3.Error as e:
            print(f"Erro ao listar candidatos do edital: {e}")
            return {}
        finally:
            conn.close()

    @staticmethod
    def atualizar(id_candidato, nome=None, numero_inscricao=None, nota=None, id_cargo=None, ordem_nomeacao=None, pcd=None, cotista=None, situacao=None, data_posse=None, id_edital=None):
        """Atualiza os dados de um candidato."""
        conn = conectar()
        cursor = conn.cursor()
        updates = []
        values = []

        if nome:
            updates.append("nome = ?")
            values.append(nome)
        if numero_inscricao:
            updates.append("numero_inscricao = ?")
            values.append(numero_inscricao)
        if nota:
            updates.append("nota = ?")
            values.append(nota)
        if id_cargo:
            updates.append("id_cargo = ?")
            values.append(id_cargo)
        if ordem_nomeacao is not None:
            updates.append("ordem_nomeacao = ?")
            values.append(ordem_nomeacao)
        if pcd is not None:
            updates.append("pcd = ?")
            values.append(pcd)
        if cotista is not None:
            updates.append("cotista = ?")
            values.append(cotista)
        if situacao:
            updates.append("situacao = ?")
            values.append(situacao)
        if data_posse is not None:
            updates.append("data_posse = ?")
            values.append(data_posse)
        if id_edital:
            updates.append("id_edital = ?")
            values.append(id_edital)

        if not updates:
            return False

        values.append(id_candidato)

        try:
            query = f"UPDATE Candidato SET {', '.join(updates)} WHERE id_candidato = ?"
            cursor.execute(query, values)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao atualizar candidato: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def deletar(id_candidato):
        """Remove um candidato pelo ID."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Candidato WHERE id_candidato = ?", (id_candidato,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao remover candidato: {e}")
            return False
        finally:
            conn.close()