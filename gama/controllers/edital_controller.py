from gama.models.edital import Edital, Cargo

class EditalController:
    @staticmethod
    def criar_edital(numero_edital, data_edital, data_publicacao, vencimento_edital, cargos):
        """Cria um novo edital com status 'ativo' e adiciona os cargos."""
        edital = Edital(numero_edital, data_edital, data_publicacao, vencimento_edital, status="ativo")
        if not edital.salvar():
            return False
        
        # Adicionar cargos
        for cargo_nome in cargos:
            if cargo_nome.strip():
                cargo = Cargo(cargo_nome.strip(), edital.id_edital)
                if not cargo.salvar():
                    return False
        
        return True

    @staticmethod
    def buscar_por_numero(numero_edital):
        """Busca um edital pelo número."""
        return Edital.buscar_por_numero(numero_edital)

    @staticmethod
    def buscar_por_id(id_edital):
        """Busca um edital pelo ID."""
        return Edital.buscar_por_id(id_edital)

    @staticmethod
    def editar_edital(id_edital, numero_edital=None, data_edital=None, data_publicacao=None, vencimento_edital=None, status=None):
        """Atualiza os dados de um edital."""
        return Edital.atualizar(id_edital, numero_edital, data_edital, data_publicacao, vencimento_edital, status)

    @staticmethod
    def prorrogar_edital(id_edital, dias_prorrogacao):
        """Prorroga o vencimento do edital."""
        return Edital.prorrogar(id_edital, dias_prorrogacao)

    @staticmethod
    def excluir_edital(id_edital):
        """Remove um edital pelo ID."""
        return Edital.deletar(id_edital)

    @staticmethod
    def listar_editais():
        """Lista todos os editais cadastrados."""
        return Edital.listar_todos()

    @staticmethod
    def listar_cargos(id_edital):
        """Lista todos os cargos de um edital."""
        return Cargo.listar_por_edital(id_edital)