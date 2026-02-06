import sqlite3
from gama.database.database import conectar
import uuid
from datetime import datetime

class Certificado:
    @staticmethod
    def create(nome_template, id_candidato, id_usuario_emissor):
        """Salva um registro de um certificado emitido no banco."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            codigo = str(uuid.uuid4())
            data_emissao = datetime.now()

            cursor.execute("""
                INSERT INTO Certificado (codigo_validacao, data_emissao, nome_template, id_candidato, id_usuario_emissor)
                VALUES (?, ?, ?, ?, ?)
            """, (codigo, data_emissao, nome_template, id_candidato, id_usuario_emissor))
            conn.commit()
            return True, "Registro de certificado criado com sucesso."
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"Erro ao registrar certificado: {e}"
        finally:
            conn.close()
            
    @staticmethod
    def get_all():
        """Busca todos os certificados emitidos com detalhes do candidato."""
        conn = conectar()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT cert.*, cand.nome, ed.numero_edital
                FROM Certificado cert
                JOIN Candidato cand ON cert.id_candidato = cand.id_candidato
                JOIN Edital ed ON cand.id_edital = ed.id_edital
                ORDER BY cert.data_emissao DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Erro ao buscar certificados: {e}")
            return []
        finally:
            conn.close()