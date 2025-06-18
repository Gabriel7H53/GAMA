
from functools import wraps

# Dicionário de permissões para cada tipo de usuário
PERMISSOES = {
    "administrador": ["excluir_usuario", "gerenciarTarifas"],
    "usuario": ["registrar_entrada"]
}

def verificar_permissao(func):
    """Decorador para verificar se o usuário tem permissão para executar a função"""
    @wraps(func)
    def wrapper(self, id_usuario, *args, **kwargs):
        tipo_usuario = self.usuario_model.buscar_tipo_usuario(id_usuario)

        # Obtém o nome da função e verifica se está na lista de permissões do usuário
        if func.__name__ in PERMISSOES.get(tipo_usuario, []):
            return func(self, id_usuario, *args, **kwargs)
        else:
            print(f"❌ Permissão negada! O usuário '{tipo_usuario}' não pode acessar '{func.__name__}'.")
            return None  # Ou lançar uma exceção, se preferir
    return wrapper