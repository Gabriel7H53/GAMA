import sqlite3
from gama.database.database import conectar
from datetime import datetime

class Agendamento:

    @staticmethod
    def create(id_edital, id_usuario, data_hora_agendamento, nome_pessoa_entrega):
        """Cria um novo agendamento no banco de dados."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Agendamento (id_edital, id_usuario, data_hora_agendamento, nome_pessoa_entrega)
                VALUES (?, ?, ?, ?)
            """, (id_edital, id_usuario, data_hora_agendamento, nome_pessoa_entrega))
            conn.commit()
            return True, "Agendamento criado com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao criar agendamento: {e}"
        finally:
            conn.close()

    @staticmethod
    def get_by_edital(id_edital):
        """Busca todos os agendamentos de um edital específico, trazendo o nome do usuário."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            # Usamos um JOIN para buscar o nome do usuário que fez o agendamento
            cursor.execute("""
                SELECT a.*, u.nome 
                FROM Agendamento a
                JOIN Usuario u ON a.id_usuario = u.id_usuario
                WHERE a.id_edital = ? 
                ORDER BY a.data_hora_agendamento ASC
            """, (id_edital,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erro ao buscar agendamentos: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def get_by_id(id_agendamento):
        """Busca um único agendamento pelo seu ID."""
        conn = conectar()
        conn.row_factory = sqlite3.Row # Para retornar um dicionário
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Agendamento WHERE id_agendamento = ?", (id_agendamento,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def update(id_agendamento, data_hora_agendamento, nome_pessoa_entrega, status):
        """Atualiza os dados e o status de um agendamento existente."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE Agendamento
                SET data_hora_agendamento = ?, nome_pessoa_entrega = ?, status_agendamento = ?
                WHERE id_agendamento = ?
            """, (data_hora_agendamento, nome_pessoa_entrega, status, id_agendamento))
            conn.commit()
            return True, "Agendamento atualizado com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao atualizar agendamento: {e}"
        finally:
            conn.close()

    @staticmethod
    def delete(id_agendamento):
        """Remove um agendamento do banco de dados."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Agendamento WHERE id_agendamento = ?", (id_agendamento,))
            conn.commit()
            return True, "Agendamento removido com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao remover agendamento: {e}"
        finally:
            conn.close()