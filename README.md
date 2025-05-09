# Servidor MCP para o GLPI

Aplicação do Model Context Protocol para entregar a modelos de LLM a capacidade de interagir com a API do GLPI.

## Tools

### criar_chamado_glpi()

Abre um novo chamado com o título e descrição fornecidos na chamada da função.

### identificar_usuario_por_telefone()

Como se trata de um mcp destinado a conversação no whatsapp, faz sentido que os usuários sejam identificados pelo número de telefone. Com base no número de telefone, a ferramenta busca o id do usuário de telefone correspondente.

### associar_usuario_ao_chamado_glpi()

Após a abertura do chamado e identificação do usuário, associa ambos.


