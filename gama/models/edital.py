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


