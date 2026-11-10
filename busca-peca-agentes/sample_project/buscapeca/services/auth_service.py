from buscapeca.security.crypto import hash_senha, verificar_senha


class AuthService:
    def __init__(self):
        self.usuarios = {}

    def registrar(self, email: str, senha: str) -> None:
        if len(senha) < 8:
            raise ValueError("senha deve ter ao menos 8 caracteres")
        self.usuarios[email] = hash_senha(senha)

    def autenticar(self, email: str, senha: str) -> bool:
        armazenado = self.usuarios.get(email)
        return armazenado is not None and verificar_senha(senha, armazenado)
