# 🕹️ Projeto-Loja-digital-de-jogos

## Integrantes:
-  Paulo Andre de Oliveira Hirata RA: 22.125.072-3
-  Victor Merker Binda RA: 22.125.075-6

## Tema do projeto:
  O projeto Loja Digital de Jogos tem como objetivo simular o funcionamento de uma plataforma de venda de jogos online, permitindo o gerenciamento de catálogo de jogos, cadastro de clientes e integração de dados entre diferentes fontes.


## ⚙️ Descrição dos Serviços

### Principais recursos usados:
- python
- FastAPI
- Docker & Docker Compose
- SQL server
- MongoDB
- RedisDB

🧠 S1 – Catálogo de Jogos

O S1 representa o primeiro serviço da aplicação, responsável pelo gerenciamento dos jogos cadastrados.
Sua função central é lidar com as operações sobre os registros de jogos.
Este serviço é responsável por interagir diretamente com o banco MongoDB, onde os dados de jogos são armazenados.

🔗 S2 – Integração e Clientes

O S2 é o segundo serviço e atua como camada de integração entre os diferentes bancos de dados do sistema.
Ele é implementado em FastAPI e realiza a comunicação com:

SQL Server → Armazena dados de clientes, como nome, e-mail, CPF e endereço. Principal motivos de escolhermos ele foi a familiaridade

MongoDB → Consulta o catálogo de jogos disponível. Usamos principalmente por conta da familiaridade e sua flexíbilidade

Redis → Funciona como cache de consultas, atuando no carrinho dos clientes. O escolhemos por conta de ser ótimo com dados temporários

Dessa forma, o S2 combina informações do catálogo e do cadastro de clientes, realizando a interação entre os 3 bancos de dados.

## Como executar:

1. **Clone o repositório:**
   
   ```bash
   git clone https://github.com/poulison/Projeto-Loja-digital-de-jogos
   cd Projeto-Loja-digital-de-jogos
   
2. **Pré-requisitos**
   ```bash
   Antes de rodar o projeto,
   certifique-se de ter instalado:
    -Docker
    -VS code
   obs(Seria bom ter insatalado o mongo e o SQL server porém não é obrigatorio pois podem ser inicializados pelo terminal 

3. **Iniciar os serviços**
    ```bash  
    execute na pasta principal onde estão os codigos:
    docker compose up --build
    Isso irá:
    -Criar e inicializar os contêineres do SQL Server, MongoDB, Redis, S1 e S2.
    -Executar os scripts de inicialização dos bancos:
        -init.sql → cria a base marketdb e a tabela Clientes;
        -init.js → cria a coleção games com índices e dados iniciais.

4. **Testar a aplicação**
   ```bash
   Após o passo anterior os servidores estaram funcionando, para acessar as API's deve usar a porta do LocalHost de cada descritos na tabela abaixo:
    | Serviço     | Porta padrão | Descrição                            |
    | ----------- | ------------ | ------------------------------------ |
    | `s1`        | `8000`       | Faz a requisição de processos        |
    | `s2`        | `8001`       | API de integração                    |
    | `mongo`     | `27017`      | Banco de jogos                       |
    | `sqlserver` | `1433`       | Banco de clientes                    |
    | `redis`     | `6379`       | Cache                                |

   Exemplo:
   - http://localhost:8000/docs  → S1

   
