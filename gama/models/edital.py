from gama.database.database import conectar
import sqlite3
from datetime import datetime, timedelta

class Edital:
    def __init__(self, numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao=None, status="ativo", id_edital=None):
        self.id_edital = id_edital
        self.numero_edital = numero_edital
        self.data_edital = data_edital
        self.data_publicacao = data_publicacao
        self.vencimento_edital = vencimento_edital
        self.prazo_prorrogacao = prazo_prorrogacao
        self.status = status

    def salvar(self):
        """Insere um novo edital no banco de dados."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO Edital (numero_edital, data_edital, data_publicacao, vencimento_edital, status)
            VALUES (?, ?, ?, ?, ?)
            ''', (self.numero_edital, self.data_edital, self.data_publicacao, self.vencimento_edital, self.status))
            self.id_edital = cursor.lastrowid
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao inserir edital: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def buscar_por_numero(numero_edital):
        """Busca um edital pelo número."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Edital WHERE numero_edital = ?", (numero_edital,))
            edital = cursor.fetchone()
            return edital
        except sqlite3.Error as e:
            print(f"Erro ao buscar edital: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def buscar_por_id(id_edital):
        """Busca um edital pelo ID."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Edital WHERE id_edital = ?", (id_edital,))
            edital = cursor.fetchone()
            return edital
        except sqlite3.Error as e:
            print(f"Erro ao buscar edital: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def listar_todos():
        """Lista todos os editais cadastrados com seus candidatos agrupados por cargo."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            SELECT e.*, COUNT(c.id_candidato) as qtd_candidatos
            FROM Edital e
            LEFT JOIN Candidato c ON e.id_edital = c.id_edital
            GROUP BY e.id_edital
            ORDER BY e.numero_edital
            ''')
            editais = cursor.fetchall()

            editais_com_candidatos = []
            for edital in editais:
                # Buscar cargos do edital
                cursor.execute("SELECT id_cargo, nome_cargo FROM Cargo WHERE id_edital = ?", (edital[0],))
                cargos = cursor.fetchall()
                
                # Para cada cargo, buscar candidatos
                candidatos_por_cargo = {}
                for cargo in cargos:
                    cursor.execute('''
                    SELECT c.*, ca.nome_cargo
                    FROM Candidato c
                    JOIN Cargo ca ON c.id_cargo = ca.id_cargo
                    WHERE c.id_edital = ? AND c.id_cargo = ?
                    ORDER BY c.ordem_nomeacao
                    ''', (edital[0], cargo[0]))
                    candidatos = cursor.fetchall()
                    candidatos_por_cargo[cargo[1]] = candidatos
                
                edital_dict = {
                    'id_edital': edital[0],
                    'numero_edital': edital[1],
                    'data_edital': edital[2],
                    'data_publicacao': edital[3],
                    'vencimento_edital': edital[4],
                    'prazo_prorrogacao': edital[5],
                    'status': edital[6],
                    'qtd_candidatos': edital[7],
                    'candidatos_por_cargo': candidatos_por_cargo
                }
                editais_com_candidatos.append(edital_dict)

            return editais_com_candidatos
        except sqlite3.Error as e:
            print(f"Erro ao listar editais: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def atualizar(id_edital, numero_edital=None, data_edital=None, data_publicacao=None, vencimento_edital=None, status=None):
        """Atualiza os dados de um edital."""
        conn = conectar()
        cursor = conn.cursor()
        updates = []
        values = []

        if numero_edital:
            updates.append("numero_edital = ?")
            values.append(numero_edital)
        if data_edital:
            updates.append("data_edital = ?")
            values.append(data_edital)
        if data_publicacao:
            updates.append("data_publicacao = ?")
            values.append(data_publicacao)
        if vencimento_edital:
            updates.append("vencimento_edital = ?")
            values.append(vencimento_edital)
        if status:
            updates.append("status = ?")
            values.append(status)

        if not updates:
            return False

        values.append(id_edital)

        try:
            query = f"UPDATE Edital SET {', '.join(updates)} WHERE id_edital = ?"
            cursor.execute(query, values)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao atualizar edital: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def prorrogar(id_edital, dias_prorrogacao):
        """Prorroga o vencimento do edital e atualiza o status."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT vencimento_edital FROM Edital WHERE id_edital = ?", (id_edital,))
            vencimento_atual = cursor.fetchone()
            if not vencimento_atual:
                return False
            
            vencimento_date = datetime.strptime(vencimento_atual[0], '%Y-%m-%d')
            novo_vencimento = (vencimento_date + timedelta(days=int(dias_prorrogacao))).strftime('%Y-%m-%d')
            
            cursor.execute('''
            UPDATE Edital SET vencimento_edital = ?, prazo_prorrogacao = ?, status = 'prorrogado'
            WHERE id_edital = ?
            ''', (novo_vencimento, dias_prorrogacao, id_edital))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao prorrogar edital: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def deletar(id_edital):
        """Remove um edital pelo ID."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Edital WHERE id_edital = ?", (id_edital,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao remover edital: {e}")
            return False
        finally:
            conn.close()

class Cargo:
    def __init__(self, nome_cargo, id_edital, id_cargo=None):
        self.id_cargo = id_cargo
        self.nome_cargo = nome_cargo
        self.id_edital = id_edital

    def salvar(self):
        """Insere um novo cargo no banco de dados."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO Cargo (nome_cargo, id_edital)
            VALUES (?, ?)
            ''', (self.nome_cargo, self.id_edital))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao inserir cargo: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def listar_por_edital(id_edital):
        """Lista todos os cargos de um edital."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id_cargo, nome_cargo FROM Cargo WHERE id_edital = ? ORDER BY nome_cargo", (id_edital,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erro ao listar cargos: {e}")
            return []
        finally:
            conn.close()