# Grupo_284_desafio_4
Desafio 4 - 21/08
LançAI - Automatização Contábil-Fiscal com Inteligência Artificial

# Contexto geral

Este repositório contém o código-fonte da solução "LançAI", desenvolvida como parte do desafio 4.
O objetivo é construir um agente inteligente que automatize a leitura de XMLs fiscais (NF-e e CT-e), gere lançamentos contábeis automatizados, e possibilite futuras interações com modelos de linguagem como o Gemini para análises avançadas.

O sistema utiliza uma interface amigável em Streamlit, que permite ao usuário fazer upload de um arquivo ZIP com XMLs, processar automaticamente os dados e exportar os lançamentos contábeis em CSV.

# Estrutura da solução

# 1. Interface do Usuário (Streamlit)

- Upload de um arquivo ZIP contendo diversos XMLs fiscais
- Botão para enviar o ZIP para o agente
- Exibição dos dados processados

Geração de lançamentos contábeis com base em regras simples (ex: CFOPs iniciando com "1" ou "5")

Exporta os lançamentos em CSV para download

# 2. Processamento dos XMLs

O arquivo ZIP é descompactado automaticamente
Cada XML é lido com ElementTree e transformado em pandas.DataFrame
Os dados consolidados são utilizados para gerar lançamentos
As regras são aplicadas com base no CFOP dos produtos

# 3. Integração com LLM (LangChain + Google Gemini)

O modelo gemini-1.5-pro-latest é inicializado usando a biblioteca langchain_google_genai
Está pronto para ser utilizado para análises dos lançamentos ou diagnóstico de inconsistências (em fase experimental)

Tecnologias e Bibliotecas Utilizadas

- Streamlit — Interface Web interativa
- Python-dotenv — Leitura segura da Google API Key
- LangChain + langchain-google-genai — Framework para agentes com LLM
- Langchain-Experimental — create_pandas_dataframe_agent
- Pandas — Manipulação de dados estruturados
- xml.etree.ElementTree — Leitura dos XMLs
- zipfile — Descompacta arquivos ZIP

Regras de Lógica Contábil Implementadas (MVP)

- CFOP iniciando com "5": Considerado lançamento de venda
     - Débito: 1.1.04.0001 - Clientes
     - Crédito: 3.1.01.0001 - Receita de Vendas

- CFOP iniciando com "1": Considerado lançamento de compra
     - Débito: 1.1.06.0001 - Estoque de Mercadorias
     - Crédito: 2.1.01.0001 - Fornecedores

# Como rodar localmente

# 1. Clonar o repositório

```bash
git clone https://github.com/Ehllonna/Grupo_284_desafio_4/agentecsv.git
cd agentecsv
```

# 2. Instalar as Dependências

```bash
pip install -r requirements.txt
```

# 3. Criar o Arquivo .env

Crie um arquivo .env na raiz do projeto:

```bash
GOOGLE_API_KEY="SUA_CHAVE_AQUI"
```
# 4. Alterar o nome do arquivo de aplicativo.py por app.py

# 5. Rodar o projeto com Streamlit

```bash
streamlit run app.py
```

# Exemplos de uso

- Upload de um ZIP contendo XMLs de NF-e/CT-e
- Processamento automático dos dados dos produtos, fornecedores, CFOP, CST, etc.
- Geração de lançamentos contábeis automáticos
- Exportação dos lançamentos em CSV
- Recursos Futuros (Roadmap)
- Interface para editar regras CFOP/NCM/CST
- Exportação para ERPs
- Auditoria com LLM (LangChain)
- Classificação de inconsistências tributárias
- Integração com banco de dados contábil

# Possíveis problemas

- GOOGLE_API_KEY não encontrada: Verifique seu .env
- Erros de parsing XML: Alguns arquivos podem estar malformados
- Erros de import: Verifique se todas as dependências foram instaladas corretamente

# Licença

Projeto desenvolvido para fins educacionais e de demonstração. Consulte o autor para uso comercial.

