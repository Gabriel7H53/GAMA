import sqlite3
from gama.database.database import conectar

class Opcao:
    @staticmethod
    def get_por_tipo(tipo_opcao):
        """Busca todas as opções de um determinado tipo (ex: 'reitor' ou 'local')."""
        conn = conectar()
        conn.row_factory = sqlite3.Row # Retorna como dicionário
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Opcao WHERE tipo_opcao = ? ORDER BY valor_opcao", (tipo_opcao,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Erro ao buscar opções: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def create(tipo_opcao, valor_opcao):
        """Adiciona uma nova opção."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Opcao (tipo_opcao, valor_opcao) VALUES (?, ?)", (tipo_opcao, valor_opcao))
            conn.commit()
            return True, "Opção adicionada com sucesso."
        except sqlite3.IntegrityError:
            conn.rollback()
            return False, "Esta opção já existe."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao adicionar opção: {e}"
        finally:
            conn.close()

    @staticmethod
    def delete(id_opcao):
        """Remove uma opção pelo seu ID."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Opcao WHERE id_opcao = ?", (id_opcao,))
            conn.commit()
            return True, "Opção removida com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao remover opção: {e}"
        finally:
            conn.close()