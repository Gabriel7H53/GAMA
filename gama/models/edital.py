# gama/models/edital.py
import sqlite3
from gama.database.database import conectar
from datetime import datetime

class Edital:
    # ... O código da classe Edital permanece o mesmo ...
    @staticmethod
    def create(numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Edital (numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status))
            conn.commit()
            return True, "Edital criado com sucesso."
        except sqlite3.IntegrityError:
            return False, f"O edital com número '{numero_edital}' já existe."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao criar edital: {e}"
        finally:
            conn.close()

    @staticmethod
    def get_all():
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Edital ORDER BY data_publicacao DESC")
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erro ao buscar editais: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def update(id_edital, numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE Edital 
                SET numero_edital = ?, data_edital = ?, data_publicacao = ?, vencimento_edital = ?, prazo_prorrogacao = ?, status = ?
                WHERE id_edital = ?
            """, (numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status, id_edital))
            conn.commit()
            return True, "Edital atualizado com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao atualizar edital: {e}"
        finally:
            conn.close()

    @staticmethod
    def delete(id_edital):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Candidato WHERE id_edital = ?", (id_edital,))
            cursor.execute("DELETE FROM Cargo WHERE id_edital = ?", (id_edital,))
            cursor.execute("DELETE FROM Edital WHERE id_edital = ?", (id_edital,))
            conn.commit()
            return True, "Edital e todos os seus dados foram removidos."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao remover edital: {e}"
        finally:
            conn.close()


class Cargo:
    # ... O código da classe Cargo permanece o mesmo ...
    @staticmethod
    def get_or_create(id_edital, nome_cargo):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id_cargo FROM Cargo WHERE nome_cargo = ? AND id_edital = ?", (nome_cargo, id_edital))
            cargo = cursor.fetchone()
            if cargo:
                return cargo[0]
            
            cursor.execute("INSERT INTO Cargo (nome_cargo, id_edital) VALUES (?, ?)", (nome_cargo, id_edital))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def get_by_edital(id_edital):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Cargo WHERE id_edital = ?", (id_edital,))
            return cursor.fetchall()
        finally:
            conn.close()


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
    def get_max_classificacao(id_edital):
        """Busca o maior número de classificação para um determinado edital."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT MAX(classificacao) FROM Candidato WHERE id_edital = ?", (id_edital,))
            resultado = cursor.fetchone()
            # Retorna o máximo encontrado, ou 0 se não houver nenhum candidato.
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