# No topo de gama/models/candidato.py
import sqlite3
from gama.database.database import conectar
from datetime import datetime

class Candidato:
    # ... (métodos create, get_by_edital e delete permanecem os mesmos) ...
    @staticmethod
    def create(id_edital, id_cargo, nome, inscricao, nota, classificacao, pcd, cotista, situacao, data_posse):
        conn = conectar()
        cursor = conn.cursor()
        try:
            data_posse = datetime.strptime(data_posse, '%Y-%m-%d').date() if data_posse else None
            pcd_bool = 1 if pcd else 0
            cotista_bool = 1 if cotista else 0
            
            cursor.execute("""
                INSERT INTO Candidato (id_edital, id_cargo, nome, numero_inscricao, nota, classificacao, pcd, cotista, situacao, data_posse)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (id_edital, id_cargo, nome, inscricao, nota, classificacao, pcd_bool, cotista_bool, situacao, data_posse))
            conn.commit()
            return True, "Candidato adicionado com sucesso."
        except sqlite3.IntegrityError:
            return False, f"O candidato com número de inscrição '{inscricao}' já existe."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao adicionar candidato: {e}"
        finally:
            conn.close()

    @staticmethod
    def get_by_edital(id_edital):
        conn = conectar()
        cursor = conn.cursor()
        try:
            query = """
                SELECT cand.*, carg.nome_cargo 
                FROM Candidato cand
                JOIN Cargo carg ON cand.id_cargo = carg.id_cargo
                WHERE cand.id_edital = ? 
                ORDER BY cand.classificacao ASC
            """
            cursor.execute(query, (id_edital,))
            return cursor.fetchall()
        finally:
            conn.close()
    
    # MÉTODO ATUALIZADO
    @staticmethod
    def update(id_candidato, id_cargo, nome, inscricao, nota, classificacao, pcd, cotista, situacao, data_posse):
        conn = conectar()
        cursor = conn.cursor()
        try:
            data_posse = datetime.strptime(data_posse, '%Y-%m-%d').date() if data_posse else None
            pcd_bool = 1 if pcd else 0
            cotista_bool = 1 if cotista else 0
            
            cursor.execute("""
                UPDATE Candidato 
                SET id_cargo = ?, nome = ?, numero_inscricao = ?, nota = ?, classificacao = ?, pcd = ?, cotista = ?, situacao = ?, data_posse = ?
                WHERE id_candidato = ?
            """, (id_cargo, nome, inscricao, nota, classificacao, pcd_bool, cotista_bool, situacao, data_posse, id_candidato))
            conn.commit()
            return True, "Candidato atualizado com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao atualizar candidato: {e}"
        finally:
            conn.close()

    @staticmethod
    def delete(id_candidato):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Candidato WHERE id_candidato = ?", (id_candidato,))
            conn.commit()
            return True, "Candidato removido com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao remover candidato: {e}"
        finally:
            conn.close()

    @staticmethod
    def get_max_classificacao(id_edital, id_cargo=None):
        """
        Busca o maior número de classificação para um edital.
        Se id_cargo for fornecido, a busca é filtrada por esse cargo.
        """
        conn = conectar()
        cursor = conn.cursor()
        try:
            query = "SELECT MAX(classificacao) FROM Candidato WHERE id_edital = ?"
            params = (id_edital,)
            
            if id_cargo:
                query += " AND id_cargo = ?"
                params = (id_edital, id_cargo)

            cursor.execute(query, params)
            resultado = cursor.fetchone()
            return resultado[0] if resultado and resultado[0] is not None else 0
        except sqlite3.Error as e:
            print(f"Erro ao buscar classificação máxima: {e}")
            return 0
        finally:
            conn.close()
            
    @staticmethod
    def nomear(id_candidato, data_posse):
        """Atualiza a situação de um candidato para 'nomeado' e define a data de posse."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE Candidato
                SET situacao = 'nomeado', data_posse = ?
                WHERE id_candidato = ?
            """, (data_posse, id_candidato))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao nomear candidato {id_candidato}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def search_by_name(query):
        """Busca nomes de candidatos para autocompletar, retornando nomes únicos."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            # O 'LIKE ?' com '%' busca nomes que começam com o texto digitado
            # O 'DISTINCT' garante que não haverá nomes repetidos na sugestão
            cursor.execute("SELECT DISTINCT nome FROM Candidato WHERE nome LIKE ? LIMIT 10", (query + '%',))
            # Retornamos uma lista simples de nomes
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Erro ao buscar nomes de candidatos: {e}")
            return []
        finally:
            conn.close()
