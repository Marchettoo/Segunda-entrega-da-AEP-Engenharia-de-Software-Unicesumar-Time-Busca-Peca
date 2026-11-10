# ADR 0001 - Arquitetura em camadas
Status: Aceito
Contexto: o marketplace precisa isolar regras de negócio da persistência.
Decisão: camadas controllers -> services -> repositories, com segurança isolada em security/.
Alternativas rejeitadas: Active Record (acopla domínio ao banco).
