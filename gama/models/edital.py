import sqlite3
from gama.database.database import conectar
from datetime import datetime

class Edital:
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
    def update(id_edital, numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status, usuario_responsavel=None):
        """Atualiza o edital e grava o histórico de alterações na MESMA transação."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status
                FROM Edital WHERE id_edital = ?
            """, (id_edital,))
            antigo = cursor.fetchone()

            cursor.execute("""
                UPDATE Edital 
                SET numero_edital = ?, data_edital = ?, data_publicacao = ?, vencimento_edital = ?, prazo_prorrogacao = ?, status = ?
                WHERE id_edital = ?
            """, (numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status, id_edital))

            if antigo and cursor.rowcount:
                campos = [
                    ('número', antigo[0], numero_edital, 'edicao'),
                    ('data do edital', antigo[1], data_edital, 'edicao'),
                    ('data de publicação', antigo[2], data_publicacao, 'edicao'),
                    ('vencimento', antigo[3], vencimento_edital, 'prorrogacao'),
                    ('prazo de prorrogação', antigo[4], prazo_prorrogacao, 'prorrogacao'),
                    ('status', antigo[5], status, 'edicao'),
                ]
                for nome, valor_antigo, valor_novo, tipo in campos:
                    if str(valor_antigo if valor_antigo is not None else '') != str(valor_novo if valor_novo is not None else ''):
                        cursor.execute("""
                            INSERT INTO HistoricoEdital (id_edital, usuario_responsavel, tipo_alteracao, descricao, data_hora)
                            VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
                        """, (id_edital, usuario_responsavel or 'Usuário', tipo,
                              f"Alterou {nome}: '{valor_antigo}' ➝ '{valor_novo}'"))

            conn.commit()
            return True, "Edital atualizado com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao atualizar edital: {e}"
        finally:
            conn.close()

    @staticmethod
    def get_by_id(id_edital):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Edital WHERE id_edital = ?", (id_edital,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def get_by_numero(numero_edital):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Edital WHERE numero_edital = ?", (numero_edital,))
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def get_historico(id_edital=None):
        """Histórico de um edital; sem id_edital retorna o histórico geral (inclui editais removidos)."""
        conn = conectar()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            query = """
                SELECT h.*, e.numero_edital
                FROM HistoricoEdital h
                LEFT JOIN Edital e ON e.id_edital = h.id_edital
            """
            params = ()
            if id_edital is not None:
                query += " WHERE h.id_edital = ?"
                params = (id_edital,)
            query += " ORDER BY h.data_hora DESC, h.id DESC"
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def delete(id_edital):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Agendamento WHERE id_edital = ?", (id_edital,))
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


class HistoricoEdital:
    @staticmethod
    def create(id_edital, usuario_responsavel, tipo_alteracao, descricao):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO HistoricoEdital (id_edital, usuario_responsavel, tipo_alteracao, descricao, data_hora)
                VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
            """, (id_edital, usuario_responsavel or 'Usuário', tipo_alteracao, descricao))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao criar histórico do edital: {e}")
            return False
        finally:
            conn.close()


class Cargo:
    @staticmethod
    def get_or_create(id_edital, nome_cargo, padrao_vencimento):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id_cargo FROM Cargo WHERE nome_cargo = ? AND id_edital = ?", (nome_cargo, id_edital))
            cargo = cursor.fetchone()
            if cargo:
                return cargo[0]

            cursor.execute(
                "INSERT INTO Cargo (nome_cargo, id_edital, padrao_vencimento) VALUES (?, ?, ?)",
                (nome_cargo, id_edital, padrao_vencimento) 
            )
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



class PortariaRascunho:
    @staticmethod
    def save(id_edital, texto_portaria):
        conn = conectar()
        cursor = conn.cursor()
        try:
            # Upsert (Insert or Replace)
            cursor.execute("""
                INSERT OR REPLACE INTO PortariaRascunho (id_edital, texto_portaria, data_atualizacao)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (id_edital, texto_portaria))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao salvar rascunho de portaria: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def get(id_edital):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT texto_portaria FROM PortariaRascunho WHERE id_edital = ?", (id_edital,))
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    
    @staticmethod
    def get_all_dict():
        """Retorna um dicionário {id_edital: texto_portaria}"""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id_edital, texto_portaria FROM PortariaRascunho")
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            conn.close()
