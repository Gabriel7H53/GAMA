# gama/models/vaga.py
import sqlite3
from gama.database.database import conectar
import pandas as pd

class CargoGestao:
    @staticmethod
    def create(cod_cargo, nome_cargo, situacao, nivel):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO CargoGestao (cod_cargo, nome_cargo, situacao, nivel)
                VALUES (?, ?, ?, ?)
            """, (cod_cargo, nome_cargo, situacao, nivel))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            conn.rollback()
            return None # Falha (código duplicado)
        finally:
            conn.close()

    @staticmethod
    def get_by_cod_cargo(cod_cargo):
        conn = conectar()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CargoGestao WHERE cod_cargo = ?", (cod_cargo,))
        return cursor.fetchone()

    @staticmethod
    def get_all_with_counts():
        """
        Busca todos os cargos e calcula dinamicamente a contagem de vagas
        livres e ocupadas usando SQL.
        """
        conn = conectar()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            query = """
                SELECT
                    cg.id, cg.cod_cargo, cg.nome_cargo, cg.situacao, cg.nivel,
                    COUNT(v.id) AS total_vagas,
                    SUM(CASE WHEN v.situacao = 'Ocupada' THEN 1 ELSE 0 END) AS ocupadas,
                    SUM(CASE WHEN v.situacao = 'Livre' THEN 1 ELSE 0 END) AS livres
                FROM
                    CargoGestao cg
                LEFT JOIN
                    Vaga v ON cg.id = v.cargo_gestao_id
                GROUP BY
                    cg.id
                ORDER BY
                    cg.nome_cargo
            """
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def update(id_cargo, cod_cargo, nome_cargo, situacao, nivel):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE CargoGestao
                SET cod_cargo = ?, nome_cargo = ?, situacao = ?, nivel = ?
                WHERE id = ?
            """, (cod_cargo, nome_cargo, situacao, nivel, id_cargo))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            conn.rollback()
            return False # Código duplicado
        finally:
            conn.close()

    @staticmethod
    def delete(id_cargo):
        """Deleta um cargo e todas as suas vagas associadas (ON DELETE CASCADE)"""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM CargoGestao WHERE id = ?", (id_cargo,))
            conn.commit()
            return True
        finally:
            conn.close()


class Vaga:
    @staticmethod
    def get_by_cargo_id(cargo_id):
        conn = conectar()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Vaga WHERE cargo_gestao_id = ? ORDER BY cod_vaga", (cargo_id,))
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_cod_vaga(cod_vaga):
        conn = conectar()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Vaga WHERE cod_vaga = ?", (cod_vaga,))
        return cursor.fetchone()

    @staticmethod
    def create(cargo_gestao_id, cod_vaga, situacao, ocupante_atual, area, observacoes):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Vaga (cargo_gestao_id, cod_vaga, situacao, ocupante_atual, area, observacoes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cargo_gestao_id, cod_vaga, situacao, ocupante_atual, area, observacoes))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            conn.rollback()
            return None # Vaga duplicada
        finally:
            conn.close()

    @staticmethod
    def update(id_vaga, cod_vaga, situacao, ocupante_atual, area, observacoes):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE Vaga
                SET cod_vaga = ?, situacao = ?, ocupante_atual = ?, area = ?, observacoes = ?
                WHERE id = ?
            """, (cod_vaga, situacao, ocupante_atual, area, observacoes, id_vaga))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            conn.rollback()
            return False # Vaga duplicada
        finally:
            conn.close()
            
    @staticmethod
    def set_ocupante(id_vaga, nome_ocupante):
        """Define um ocupante para a vaga e muda o status para 'Ocupada'."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE Vaga
                SET ocupante_atual = ?, situacao = 'Ocupada'
                WHERE id = ?
            """, (nome_ocupante, id_vaga))
            conn.commit()
            return True
        finally:
            conn.close()
            
    @staticmethod
    def set_livre(id_vaga):
        """Libera uma vaga, removendo o ocupante e mudando o status para 'Livre'."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE Vaga
                SET ocupante_atual = NULL, situacao = 'Livre'
                WHERE id = ?
            """, (id_vaga,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def delete(id_vaga):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Vaga WHERE id = ?", (id_vaga,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def ocupar_por_codigo(cod_vaga, nome_ocupante):
        """Atualiza o status da vaga para Ocupada através do código."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE Vaga
                SET situacao = 'Ocupada', ocupante_atual = ?
                WHERE cod_vaga = ?
            """, (nome_ocupante, cod_vaga))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao ocupar vaga {cod_vaga}: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def desocupar_por_codigo(cod_vaga):
        """Libera a vaga através do código."""
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE Vaga
                SET situacao = 'Livre', ocupante_atual = NULL
                WHERE cod_vaga = ?
            """, (cod_vaga,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao desocupar vaga {cod_vaga}: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def get_all_vagas_livres():
        """Busca todas as vagas com situação 'Livre'."""
        conn = conectar()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            # Seleciona vagas E o nome do cargo ao qual pertencem
            cursor.execute("""
                SELECT v.id, v.cod_vaga, v.area, cg.nome_cargo
                FROM Vaga v
                JOIN CargoGestao cg ON v.cargo_gestao_id = cg.id
                WHERE v.situacao = 'Livre'
                ORDER BY cg.nome_cargo, v.cod_vaga
            """)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Erro ao buscar vagas livres: {e}")
            return []
        finally:
            conn.close()
            
    @staticmethod
    def processar_lote(file_path):
        """Processa um arquivo .xlsx e insere/atualiza cargos e vagas."""
        try:
            df = pd.read_excel(file_path, dtype=str)
            df.columns = df.columns.str.strip()
            df = df.where(pd.notnull(df), None)
        except Exception as e:
            return 0, 0, [f"Erro ao ler o arquivo Excel: {e}"]

        cargos_criados = 0
        vagas_criadas_atualizadas = 0
        erros = []

        colunas_esperadas = [
            "CODIGO_CARGO", "NOME_CARGO", "SITUACAO", "NIVEL", 
            "CODIGO_VAGA", "SITUACAO_VAGA"
        ]
        
        for col in colunas_esperadas:
            if col not in df.columns:
                erros.append(f"Coluna obrigatória não encontrada: {col}")
        if erros:
            return 0, 0, erros
            
        conn = conectar()
        cursor = conn.cursor()
        
        try:
            for index, row in df.iterrows():
                try:
                    # 1. Processamento e Normalização dos Dados do Cargo
                    cod_cargo = row.get("CODIGO_CARGO").strip()
                    nome_cargo = row.get("NOME_CARGO").strip()
                    # CORREÇÃO: Normaliza "ATIVO" para "Ativo"
                    situacao_cargo = row.get("SITUACAO").strip().title() 
                    nivel_cargo = row.get("NIVEL").strip().upper() # Garante D ou E
                    
                    if situacao_cargo not in ["Ativo", "Inativo"]:
                        erros.append(f"Linha {index + 2}: Situação do Cargo '{situacao_cargo}' inválida. Use 'Ativo' ou 'Inativo'.")
                        continue
                        
                    if nivel_cargo not in ["D", "E"]:
                        erros.append(f"Linha {index + 2}: Nível do Cargo '{nivel_cargo}' inválido. Use 'D' ou 'E'.")
                        continue

                    # 2. Processamento e Normalização dos Dados da Vaga
                    cod_vaga = row.get("CODIGO_VAGA").strip()
                    
                    situacao_vaga = row.get("SITUACAO_VAGA")
                    if situacao_vaga:
                        # CORREÇÃO: Normaliza "OCUPADA" para "Ocupada" e "DESOCUPADA" para "Livre"
                        situacao_vaga = situacao_vaga.strip().title()
                        if situacao_vaga == "Desocupada":
                            situacao_vaga = "Livre"
                    
                    ocupante = row.get("NOME_OCUPANTE")
                    if ocupante: ocupante = ocupante.strip()
                    
                    # Validação final da situação da vaga
                    if situacao_vaga not in ["Ocupada", "Livre"]:
                        situacao_vaga = "Livre" if not ocupante else "Ocupada"

                    observacoes = row.get("OBSERVACAO")
                    if observacoes: observacoes = observacoes.strip()
                    
                    area = row.get("AREA")
                    if area: area = area.strip()

                    # 3. Encontrar ou Criar Cargo
                    cursor.execute("SELECT id FROM CargoGestao WHERE cod_cargo = ?", (cod_cargo,))
                    cargo_row = cursor.fetchone()
                    
                    if not cargo_row:
                        cursor.execute("""
                            INSERT INTO CargoGestao (cod_cargo, nome_cargo, situacao, nivel)
                            VALUES (?, ?, ?, ?)
                        """, (cod_cargo, nome_cargo, situacao_cargo, nivel_cargo))
                        cargo_id = cursor.lastrowid
                        cargos_criados += 1
                    else:
                        cargo_id = cargo_row[0]
                        cursor.execute("""
                            UPDATE CargoGestao SET nome_cargo = ?, situacao = ?, nivel = ?
                            WHERE id = ?
                        """, (nome_cargo, situacao_cargo, nivel_cargo, cargo_id))

                    # 4. Encontrar ou Criar Vaga
                    cursor.execute("SELECT id FROM Vaga WHERE cod_vaga = ?", (cod_vaga,))
                    vaga_row = cursor.fetchone()
                    
                    if not vaga_row:
                        cursor.execute("""
                            INSERT INTO Vaga (cargo_gestao_id, cod_vaga, situacao, ocupante_atual, area, observacoes)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (cargo_id, cod_vaga, situacao_vaga, ocupante, area, observacoes))
                        vagas_criadas_atualizadas += 1
                    else:
                        vaga_id = vaga_row[0]
                        cursor.execute("""
                            UPDATE Vaga
                            SET cargo_gestao_id = ?, situacao = ?, ocupante_atual = ?, area = ?, observacoes = ?
                            WHERE id = ?
                        """, (cargo_id, situacao_vaga, ocupante, area, observacoes, vaga_id))
                        vagas_criadas_atualizadas += 1

                except AttributeError as e:
                    erros.append(f"Linha {index + 2}: Dado obrigatório faltando (ex: CODIGO_CARGO, NIVEL, etc). Erro: {e}")
                except Exception as e:
                    erros.append(f"Linha {index + 2}: Erro inesperado - {e}")
            
            # Se chegamos aqui, podemos salvar as alterações
            conn.commit()

        except Exception as e:
            conn.rollback() # Desfaz tudo se houver um erro fatal
            erros.append(f"Erro geral no processamento: {e}")
        finally:
            conn.close()
        
        return cargos_criados, vagas_criadas_atualizadas, erros
    
class HistoricoVaga:
    @staticmethod
    def create(id_vaga, usuario_responsavel, descricao):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO HistoricoVaga (id_vaga, usuario_responsavel, descricao, data_hora)
                VALUES (?, ?, ?, datetime('now', 'localtime'))
            """, (id_vaga, usuario_responsavel, descricao))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Erro ao criar histórico: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def get_by_vaga(id_vaga):
        conn = conectar()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM HistoricoVaga 
                WHERE id_vaga = ? 
                ORDER BY data_hora DESC
            """, (id_vaga,))
            # Converte para lista de dicts para facilitar o JSON
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()