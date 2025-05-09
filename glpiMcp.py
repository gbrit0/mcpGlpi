from mcp.server.fastmcp import FastMCP, Context
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import os
import requests
import json
from dataclasses import dataclass
import sys
import mysql.connector

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "app_errors.log")

logging.basicConfig(
   level=logging.INFO, 
   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
   # handlers=[
   #    RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3),
   #    logging.StreamHandler()
   # ]
)
logger = logging.getLogger(__name__)

logger.info("Carregando variáveis de ambiente do erquivo .env...")

load_dotenv(override=True)

GLPI_API_URL = os.getenv("GLPI_API_URL")
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN")
GLPI_USER_TOKEN = os.getenv("GLPI_USER_TOKEN")

if not GLPI_API_URL or not GLPI_APP_TOKEN or not GLPI_USER_TOKEN:
   logger.error("As variáveis de ambiente GLPI_API_URL, GLPI_API_TOKEN e GLPI_USER_TOKEN não estão definidas.")
   raise EnvironmentError("As variáveis de ambiente GLPI_API_URL, GLPI_API_TOKEN e GLPI_USER_TOKEN devem ser definidas.")

logger.info("Variáveis de ambiente carregadas com sucesso.")

logger.info("Inicializando o servidor MCP Glpi...")
mcp = FastMCP("GLPIMCPServer")

def initSession():
   """Inicializa uma sessão na API REST do GLPI."""
   headers = {
        "Authorization": f"{GLPI_USER_TOKEN}",
        "App-Token": f"{GLPI_APP_TOKEN}",
        "Content-Type": "application/json"
    }

   url = f"{GLPI_API_URL}/initSession/"

   response = requests.request("GET", url, headers=headers)
   
   # Debug the response
   logger.info(f"Response status code: {response.status_code}")
   logger.info(f"Response content: {response.text}")
   
   # Safely try to get the token
   response_data = response.json()
   if isinstance(response_data, dict) and 'session_token' in response_data:
      return response_data['session_token']
   else:
      logger.error(f"Unexpected response format: {response_data}")
      return None

def killSession(session_token):
   """Finaliza uma sessão na API REST do GLPI."""
   headers = {
      "Session-Token": f"{session_token}",
      "App-Token": f"{GLPI_APP_TOKEN}",
      "Content-Type": "application/json"
   }

   url = f"{GLPI_API_URL}/killSession"

   response = requests.request("GET", url, headers=headers)
   return response.json()


@dataclass
class Ticket:
   name: str
   description: str
   itilcategories_id: int
   users_id: int

@dataclass
class TicketUser:
   tickets_id: int
   users_id: int
   type: int # 1=solicitante, 2=técnico, 3=observador

def add_glpi_item(itemtype, input_data):
   """
   Adiciona um ou mais itens ao GLPI via API REST.
   
   Args:
      itemtype (str): Tipo do item (ex: 'Computer', 'Monitor', etc.)
      input_data (dict or list): Dados do item ou lista de itens a serem adicionados
   
   Returns:
      dict: Resposta da API com status e IDs dos itens adicionados, ou erro
   """
   session_token = initSession()
   # Configura os cabeçalhos
   headers = {
      'Content-Type': 'application/json',
      'Session-Token': session_token,
      'App-Token': f"{GLPI_APP_TOKEN}"
   }
      
   # Prepara o payload
   payload = {
      'input': input_data
   }
   
   # Monta a URL completa
   endpoint = f"{GLPI_API_URL}/{itemtype}/"
   
   try:
      # Faz a requisição POST
      response = requests.post(
         endpoint,
         headers=headers,
         json=payload
      )
      
      # Processa a resposta
      response_data = {
         'status_code': response.status_code,
         'headers': dict(response.headers)
      }
      
      # Tenta parsear o corpo da resposta como JSON
      try:
         response_data['body'] = response.json()
      except json.JSONDecodeError:
         response_data['body'] = response.text
         
      return response_data
      
   except requests.RequestException as e:
      logger.error(f"Erro ao fazer a requisição: {e}")
      return {
         'status_code': None,
         'error': str(e)
      }
   finally:
      killSession(session_token)

def list_search_options(itemtype:str):
   """
   Retorna as opções de pesquisa disponíveis para um tipo de item no GLPI.
      
   Returns:
      dict: Resposta da API com as opções de pesquisa disponíveis.
   """
   session_token = initSession()
   headers = {
      'Content-Type': 'application/json',
      'Session-Token': session_token,
      'App-Token': f"{GLPI_APP_TOKEN}"
   }

   endpoint = f"{GLPI_API_URL}/listSearchOptions/{itemtype}"
   
   try:
      # Faz a requisição POST
      response = requests.post(
         endpoint,
         headers=headers,
      )
      
      # Processa a resposta
      response_data = {
         'status_code': response.status_code,
         'headers': dict(response.headers)
      }
      
      # Tenta parsear o corpo da resposta como JSON
      try:
         response_data['body'] = response.json()
      except json.JSONDecodeError:
         response_data['body'] = response.text
         
      return response_data
      
   except requests.RequestException as e:
      logger.error(f"Erro ao fazer a requisição: {e}")
      return {
         'status_code': None,
         'error': str(e)
      }
   finally:
      killSession(session_token)

def search_ticket_by_id(ticket_id: str):
   """
   Busca um chamado específico pelo ID.
   
   Args:
      ticket_id (str): ID do chamado a ser buscado
   
   Returns:
      dict: Resposta da API com os detalhes do chamado ou erro
   """
   # Obtém o token de sessão
   session_token = initSession()
     
   # Configura os cabeçalhos
   headers = {
      'Content-Type': 'application/json',
      'Session-Token': session_token,
      'App-Token': GLPI_APP_TOKEN  # Certifique-se que GLPI_APP_TOKEN está definido
   }
      
   # Monta o endpoint
   endpoint = f"{GLPI_API_URL}/Ticket/{ticket_id}"
   
   try:
      # Faz a requisição GET
      response = requests.get(
         endpoint,
         headers=headers
      )

      # Processa a resposta
      response_data = {
         'status_code': response.status_code,
         'headers': dict(response.headers)
      }
      
      # Tenta parsear o corpo da resposta como JSON
      try:
         response_data['body'] = response.json()
      except json.JSONDecodeError:
         response_data['body'] = response.text
      
      # print(response_data)
      return response_data
      
   except requests.RequestException as e:
      logger.error(f"Erro ao fazer a requisição: {e}")
      return {
         'status_code': None,
         'error': str(e)
      }
   finally:
      killSession(session_token)

def search_user_by_id(user_id: str):
   """
   Busca um usuário específico pelo ID.
   
   Args:
      user_id (str): ID do usurário a ser buscado
   
   Returns:
      dict: Resposta da API com os detalhes do usuário ou erro
   """
   # Obtém o token de sessão
   session_token = initSession()
     
   # Configura os cabeçalhos
   headers = {
      'Content-Type': 'application/json',
      'Session-Token': session_token,
      'App-Token': GLPI_APP_TOKEN  # Certifique-se que GLPI_APP_TOKEN está definido
   }
      
   # Monta o endpoint
   endpoint = f"{GLPI_API_URL}/User/{user_id}"
   
   try:
      # Faz a requisição GET
      response = requests.get(
         endpoint,
         headers=headers
      )

      # Processa a resposta
      response_data = {
         'status_code': response.status_code,
         'headers': dict(response.headers)
      }
      
      # Tenta parsear o corpo da resposta como JSON
      try:
         response_data['body'] = response.json()
      except json.JSONDecodeError:
         response_data['body'] = response.text
      
      # print(response_data)
      return response_data
      
   except requests.RequestException as e:
      logger.error(f"Erro ao fazer a requisição: {e}")
      return {
         'status_code': None,
         'error': str(e)
      }
   finally:
      killSession(session_token)

def search_item(
   itemtype: str,
   criteria: list ):
   """
   Realiza uma busca no GLPI usando o endpoint /search/:itemtype/.

   Args:
      itemtype (str): Tipo do item a ser buscado (ex: User, Ticket, Ticket_User, etc).
      criteria (list, optional): Lista de dicionários com critérios de busca.

      Cada objeto de critério deve fornecer pelo menos:
      - link: (opcional para o 1º elemento) operador lógico: [AND, OR, AND NOT, AND NOT].
      - field: id da opção de pesquisa (use list_search_options(itemtype) para obter os ids das opções de pesquisa de um dado tipo de item)
      - searchtype: tipo de pesquisa em [contains¹, equals², notquals², lessthan, morethan, under, notunder].
      - value: o valor a ser pesquisado.

   Returns:
      dict: Resultado da busca.
   """
   url = f"{GLPI_API_URL}/search/{itemtype}"
   session_token = initSession()

   headers = {
      "Session-Token": session_token,
      "Content-Type": "application/json",
      "App-Token": GLPI_APP_TOKEN
   } 

   params = {}
   if criteria:
        for idx, crit in enumerate(criteria):
            for key, value in crit.items():
                if isinstance(value, list):
                    for nested_idx, nested_crit in enumerate(value):
                        for nested_key, nested_value in nested_crit.items():
                            params[f"criteria[{idx}][criteria][{nested_idx}][{nested_key}]"] = nested_value
                else:
                    params[f"criteria[{idx}][{key}]"] = value 

   logger.info(f"\nparams: {params}")

   response = requests.get(url, headers=headers, params=params)
   response.raise_for_status()

   return response.json()

def add_item(itemtype: str, input, content_type: str = 'application/json'):
   """
   Adiciona um ou mais itens ao GLPI via API REST.
   
   Args:
      itemtype (str): Tipo do item (ex: 'Ticket', 'Ticket_User', etc.)
      input (JSON Payload): Um objeto com campos do tipo item a serem inseridos. Você pode adicionar vários itens em uma única ação passando um array de objetos. Obrigatório.

      Importante: No caso do content_type 'multipart/data' (upload de arquivo), você deve inserir seus parâmetros em um parâmetro 'uploadManifest'. Esses dados serializados devem ser uma string JSON.

      Ex.:    
      upload_manifest = {
        "input": {
            "name": "meuarquivo.txt",  # nome do arquivo no GLPI
            "comment": "Enviado via API",
         }
      } 

      input = {
         'uploadManifest': (None, str(upload_manifest)),  # JSON como string
         'filename': open(file_path, 'rb')  # Arquivo em binário
      }
   
   Returns:
      dict: Resposta da API com status e IDs dos itens adicionados, ou erro
   """
   session_token = initSession()
   # Configura os cabeçalhos
   headers = {
      'Content-Type': content_type,
      'Session-Token': session_token,
      'App-Token': f"{GLPI_APP_TOKEN}"
   }
      
   # Prepara o payload
   payload = {
      'input': input
   }
   
   # Monta a URL completa
   endpoint = f"{GLPI_API_URL}/{itemtype}/"
   
   try:
      # Faz a requisição POST
      response = requests.post(
         endpoint,
         headers=headers,
         json=payload
      )
      
      # Processa a resposta
      response_data = {
         'status_code': response.status_code,
         'headers': dict(response.headers)
      }
      
      # Tenta parsear o corpo da resposta como JSON
      try:
         response_data['body'] = response.json()
      except json.JSONDecodeError:
         response_data['body'] = response.text
         
      return response_data
      
   except requests.RequestException as e:
      logger.error(f"Erro ao fazer a requisição: {e}")
      return {
         'status_code': None,
         'error': str(e)
      }
   finally:
      killSession(session_token)

@mcp.tool()
def criar_chamado_glpi(titulo: str, descricao: str, prioridade: int):
   """
   Cria um novo chamado (ticket) no GLPI com base no título e na descrição fornecidos. Esta função utiliza a API REST do GLPI para registrar um novo chamado.

   Args:
      titulo (str): Título do chamado (campo 'name' no GLPI)
      descricao (str): Texto descritivo do chamado (campo 'content' no GLPI)
      prioridade (int): Nível de prioridade do chamado 6 (Crítica), 5 (Muito Alta), 4 (Alta), 3 (Média), 2 (Baixa), 1 (Planejada)

   Returns:
      dict: Resposta padronizada com status HTTP, corpo da resposta e possíveis erros.
   """
   session_token = initSession()
      
   headers = {
      'Content-Type': 'application/json',
      'Session-Token': session_token,
      'App-Token': os.getenv("GLPI_APP_TOKEN")
   }

   endpoint = f"{os.getenv('GLPI_API_URL')}/Ticket/"
   
   # payload = {
   # 'input': input_data
   # }
   
   payload = {
      'input':{
         'name': titulo,
         'content': descricao,
         'priority': prioridade
      },
   }

   try:
      response = requests.post(endpoint, headers=headers, json=payload)
      
      response_data = {
         'status_code': response.status_code,
         'headers': dict(response.headers)
      }

      try:
         response_data['body'] = response.json()
      except json.JSONDecodeError:
         response_data['body'] = response.text

      return response_data

   except requests.RequestException as e:
      logger.error(f"Erro ao criar chamado: {e}")
      return {
         'status_code': None,
         'error': str(e)
      }

   finally:
      killSession(session_token)

@mcp.tool()
def identificar_usuario_por_telefone(telefone: str):
   """
   Identifica um usuário ativo no GLPI com base no número de telefone informado.

   Esta função busca no banco de dados GLPI o usuário cujo telefone (campo `mobile`)
   coincide com o valor fornecido. Retorna o ID, nome e nome completo do usuário se encontrado.

   Args:
      telefone (str): Número de telefone completo (formato conforme armazenado no GLPI)

   Returns:
      dict: Resposta padronizada com status da requisição e dados do usuário, ou mensagem de erro.
   """
   pool = mysql.connector.pooling.MySQLConnectionPool(
      pool_name="mcpGLPI",
      pool_size=5,
      user=os.getenv('GLPI_USER'),
      password=os.getenv('GLPI_PWD'),
      port=os.getenv('GLPI_PORT'),
      host=os.getenv('GLPI_HOST'),
      database=os.getenv('GLPI_DATABASE'),
      collation='utf8mb4_general_ci'
   )

   try:
      sql = """
         SELECT 
               id,
               name,
               CONCAT(firstname, ' ', realname) AS full_name
         FROM
               glpi_users
         WHERE
               is_active = 1
               AND mobile LIKE %s;
      """
      with pool.get_connection() as con:
         with con.cursor() as cursor:
               cursor.execute(sql, (telefone,))
               result = cursor.fetchone()

      if result:
         return {
               'status_code': 200,
               'body': {
                  'id': result[0],
                  'name': result[1],
                  'full_name': result[2]
               }
         }
      else:
         return {
               'status_code': 404,
               'error': "Usuário não encontrado."
         }

   except Exception as e:
      logger.error(f"Erro ao buscar usuário: {e}")
      return {
         'status_code': None,
         'error': str(e)
      }
   
@mcp.tool()
def associar_usuario_ao_chamado_glpi(ticket_id: int, user_id: int, tipo_participacao: int = 1):
   """
   Associa um usuário a um chamado existente no GLPI, com um tipo de participação definido.

   Esta função utiliza a API REST do GLPI para adicionar um ou mais usuários a um chamado,
   com diferentes tipos de participação: solicitante, técnico ou observador.

   Args:
      ticket_id (int): ID do chamado existente.
      user_id (int): ID do usuário que será adicionado.
      tipo_participacao (int, opcional): Tipo de participação do usuário (1 = solicitante, 2 = técnico, 3 = observador). Padrão = 1.

   Returns:
      dict: Resposta padronizada com status HTTP, corpo da resposta e possíveis erros.
   """
   session_token = initSession()
   
   headers = {
      'Content-Type': 'application/json',
      'Session-Token': session_token,
      'App-Token': os.getenv("GLPI_APP_TOKEN")
   }

   endpoint = f"{os.getenv('GLPI_API_URL')}/Ticket_User/"
   
   payload = {  
      'input':[
         {
            "tickets_id": ticket_id,
            "users_id": user_id,
            "type": tipo_participacao
         },
         {
            "tickets_id": ticket_id,
            "users_id": 2,  #  usuário fixo como observador
            "type": 3
         }
      ]
   }

   try:
      response = requests.post(endpoint, headers=headers, json=payload)

      response_data = {
         'status_code': response.status_code,
         'headers': dict(response.headers)
      }

      try:
         response_data['body'] = response.json()
      except json.JSONDecodeError:
         response_data['body'] = response.text

      return response_data

   except requests.RequestException as e:
      logger.error(f"Erro ao associar usuário ao chamado: {e}")
      return {
         'status_code': None,
         'error': str(e)
      }

   finally:
      killSession(session_token)

if __name__ == "__main__":
   # Initialize and run the server
   mcp.run(transport='sse')
   