"""Validação de identificadores SQL antes de interpolação em DDL/DML.

Nomes de coluna do warehouse derivam das chaves do JSON da API: `pd.DataFrame`
adota toda chave da resposta como coluna, e `rename_columns` apenas aplica
lower/strip — nada descarta uma chave inesperada. Esses nomes chegam então
interpolados em `ALTER TABLE`/`INSERT`, onde bind param não se aplica (só cobre
valor, nunca identificador). A única defesa possível é whitelist.

Um nome fora do padrão significa uma de duas coisas, e ambas devem parar a
carga em vez de virar SQL: dado hostil, ou schema drift real na origem — que
hoje merece exceção, não `logger.warning` — falhar alto em vez de degradar
em silêncio.
"""

import re

# Identificador Postgres sem necessidade de quoting: começa por letra/underscore,
# segue com letra, dígito ou underscore. Deliberadamente mais estreito que o
# permitido pelo Postgres — o warehouse não tem nome de coluna fora disso, e
# folga aqui só amplia superfície.
_SAFE_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def assert_safe_identifier(name: str, context: str = "identificador") -> str:
    """Retorna `name` se for um identificador SQL seguro; caso contrário levanta.

    Raises:
        ValueError: se `name` não casar com `_SAFE_IDENTIFIER`.
    """
    if not isinstance(name, str) or not _SAFE_IDENTIFIER.match(name):
        raise ValueError(
            f"{context} inválido para uso em SQL: {name!r}. "
            f"Esperado ^[a-z_][a-z0-9_]{{0,62}}$ — verifique se a origem "
            f"introduziu uma coluna nova ou um nome malicioso."
        )
    return name


def assert_safe_identifiers(names: list[str], context: str = "identificador") -> list[str]:
    """Valida todos os nomes, relatando de uma vez os que falharam.

    Falhar em bloco evita o diagnóstico gota a gota de uma coluna por execução
    quando a origem muda várias de uma vez.
    """
    invalid = [n for n in names if not (isinstance(n, str) and _SAFE_IDENTIFIER.match(n))]
    if invalid:
        raise ValueError(
            f"{context} — inválido(s) para uso em SQL: {invalid!r}. "
            f"Esperado ^[a-z_][a-z0-9_]{{0,62}}$ — verifique se a origem "
            f"introduziu colunas novas ou nomes maliciosos."
        )
    return names
