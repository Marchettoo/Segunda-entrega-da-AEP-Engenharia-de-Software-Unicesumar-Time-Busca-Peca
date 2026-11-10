# Busca Peça — Guia Didático para Novos Integrantes

## Visão geral
Em linguagem simples: Marketplace que conecta oficinas mecânicas para compra e venda de peças novas, usadas e excedentes de estoque, reduzindo desperdício (ODS 12). O código é dividido em partes com papéis bem definidos.

## Módulos
- `buscapeca/controllers/peca_controller.py`: esta parte recebe os pedidos de quem usa o sistema e devolve respostas. Componente da camada de apresentação (responsabilidade inferida pela estrutura).
- `buscapeca/controllers/pedido_controller.py`: esta parte recebe os pedidos de quem usa o sistema e devolve respostas. Componente da camada de apresentação (responsabilidade inferida pela estrutura).
- `buscapeca/models.py`: esta parte define o que é uma peça, um pedido e um item. Entidades de domínio do marketplace Busca Peça.
- `buscapeca/repositories/conexao.py`: esta parte salva e busca dados no banco. Cria a conexão SQLite e o esquema mínimo do MVP.
- `buscapeca/repositories/peca_repository.py`: esta parte salva e busca dados no banco. Persistência de peças em SQLite (consultas sempre parametrizadas).
- `buscapeca/repositories/pedido_repository.py`: esta parte salva e busca dados no banco. Persiste pedidos e atualiza seu status.
- `buscapeca/security/crypto.py`: esta parte protege senhas e acessos. Camada de segurança: derivação e verificação de senhas.
- `buscapeca/services/auth_service.py`: esta parte guarda as regras do marketplace (preço sugerido, estoque, frete). Componente da camada de negócio (responsabilidade inferida pela estrutura).
- `buscapeca/services/peca_service.py`: esta parte guarda as regras do marketplace (preço sugerido, estoque, frete). Regras de negócio de anúncio e busca de peças (economia circular).
- `buscapeca/services/pedido_service.py`: esta parte guarda as regras do marketplace (preço sugerido, estoque, frete). Componente da camada de negócio (responsabilidade inferida pela estrutura).

## Decisões de arquitetura
- ADR 0001 - Arquitetura em camadas: a equipe escolheu este caminho e descartou a alternativa Active Record (acopla domínio ao banco).
- ADR 0002 - SQLite no MVP: a equipe escolheu este caminho e descartou a alternativa PostgreSQL gerenciado (custo e consumo de recursos maiores na fase de MVP).

## Referências
- BASS, L.; CLEMENTS, P.; KAZMAN, R. Software architecture in practice. 3. ed. Boston: Addison-Wesley, 2012.
- GAMMA, E. et al. Padrões de projeto: soluções reutilizáveis de software orientado a objetos. Porto Alegre: Bookman, 2000.
