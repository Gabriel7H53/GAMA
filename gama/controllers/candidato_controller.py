from gama.models.candidato import Candidato

class CandidatoController:
    @staticmethod
    def criar_candidato(nome, numero_inscricao, nota, id_cargo, ordem_nomeacao, pcd, cotista, id_edital):
        """Cria um novo candidato com situação 'a_nomear'."""
        candidato = Candidato(nome, numero_inscricao, nota, id_cargo, ordem_nomeacao, pcd, cotista, situacao="a_nomear", id_edital=id_edital)
        return candidato.salvar()

    @staticmethod
    def criar_candidatos_em_lote(candidatos):
        """Cria múltiplos candidatos em lote com situação 'a_nomear'."""
        success = True
        for candidato_data in candidatos:
            candidato = Candidato(
                nome=candidato_data['nome'],
                numero_inscricao=candidato_data['numero_inscricao'],
                nota=candidato_data['nota'],
                id_cargo=candidato_data['id_cargo'],
                ordem_nomeacao=candidato_data['ordem_nomeacao'],
                pcd=candidato_data['pcd'],
                cotista=candidato_data['cotista'],
                situacao="a_nomear",
                id_edital=candidato_data['id_edital']
            )
            if not candidato.salvar():
                success = False
        return success

    @staticmethod
    def obter_candidato(numero_inscricao):
        """Busca um candidato pelo número de inscrição."""
        return Candidato.buscar_por_numero_inscricao(numero_inscricao)

    @staticmethod
    def editar_candidato(id_candidato, nome=None, numero_inscricao=None, nota=None, id_cargo=None, ordem_nomeacao=None, pcd=None, cotista=None, situacao=None, data_posse=None, id_edital=None):
        """Atualiza os dados de um candidato."""
        return Candidato.atualizar(id_candidato, nome, numero_inscricao, nota,id_cargo, ordem_nomeacao, pcd, cotista, situacao, data_posse, id_edital)

    @staticmethod
    def excluir_candidato(id_candidato):
        """Remove um candidato pelo ID."""
        return Candidato.deletar(id_candidato)

    @staticmethod
    def listar_candidatos():
        """Lista todos os candidatos cadastrados."""
        return Candidato.listar_todos()

    @staticmethod
    def listar_por_edital(id_edital):
        """Lista todos os candidatos de um edital específico, agrupados por cargo."""
        return Candidato.listar_por_edital(id_edital)