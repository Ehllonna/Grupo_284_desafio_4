import os
import pandas as pd
import zipfile
import streamlit as st
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

# Certifique-se que esta linha esteja aqui e não comentada!
from langchain_google_genai import ChatGoogleGenerativeAI
# A linha abaixo também precisa estar, se você for usar o create_pandas_dataframe_agent
from langchain_experimental.agents import create_pandas_dataframe_agent


# --- Configuração Inicial ---
# Define o caminho para a pasta 'data' que armazenará os arquivos
DATA_FOLDER = "./data" 

# Garante que a pasta 'data' exista
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Carrega as variáveis de ambiente (onde está sua API Key)
load_dotenv()

# As importações do Langchain e Gemini podem ser movidas para dentro da função 'process_xml_zip'
# se o LLM só for usado no processamento, mas para demonstração, mantemos aqui.
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents import create_pandas_dataframe_agent # Mantemos por enquanto, mas seu uso direto muda

# --- Configuração do LLM (Google Gemini) ---
# Pega a chave da variável de ambiente carregada por dotenv
google_api_key = os.getenv("GOOGLE_API_KEY")

# Esta parte será executada apenas se a chave for necessária para o processamento
# No MVP, podemos não precisar dela ativamente se o LLM não estiver gerando lançamentos.
# Mas a estrutura do seu projeto indica que a Langchain é usada.
if not google_api_key:
    # Apenas alerta, não st.stop() imediatamente se o LLM não for usado no MVP de upload
    st.warning("A GOOGLE_API_KEY não foi encontrada. Algumas funcionalidades (como agente Langchain) podem não funcionar.")
    llm = None # Define LLM como None se a chave não estiver disponível
else:
    # Inicializa o LLM se a chave estiver presente
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0.0)
    # Se a Opção A não funcionar:
    # llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.0)


# --- Funções Auxiliares de Processamento ---

def parse_nfe_xml_to_dataframe(xml_file_path):
    """
    Parses a simplified NFe XML file and returns a Pandas DataFrame.
    This is a basic example and might need to be expanded for full NFe parsing.
    It flattens item data by repeating header info for each item.
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # Tenta identificar o namespace automaticamente ou especifica-o.
        # Exemplo para NFe: ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        # Para evitar problemas com namespaces variáveis ou ausentes para este MVP de UI,
        # usaremos uma abordagem mais tolerante com find() e findall() sem namespace explícito
        # no nome da tag, mas usando './/{tag_name}' para buscar em qualquer nível.
        
        # Encontra a tag NFe (pode estar dentro de nfeProc)
        inf_nfe = root.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
        if inf_nfe is None:
             # Tenta encontrar sem namespace, para maior flexibilidade
            inf_nfe = root.find('.//infNFe')
        
        if inf_nfe is None:
            st.error(f"Erro: Elemento 'infNFe' não encontrado no XML {xml_file_path}. Verifique a estrutura.")
            return None

        # Dados da Identificação da Nota
        ide = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}ide') or inf_nfe.find('.//ide')
        chave_acesso = inf_nfe.get('Id')[3:] if inf_nfe.get('Id') else 'N/A' # Remove 'NFe' do ID
        natOp = ide.find('.//{http://www.portalfiscal.inf.br/nfe}natOp').text if ide and (ide.find('.//{http://www.portalfiscal.inf.br/nfe}natOp') or ide.find('.//natOp')) is not None else 'N/A'
        dtEmissao = ide.find('.//{http://www.portalfiscal.inf.br/nfe}dhEmi').text[:10] if ide and (ide.find('.//{http://www.portalfiscal.inf.br/nfe}dhEmi') or ide.find('.//dhEmi')) is not None else 'N/A'

        # Dados do Emitente
        emit = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}emit') or inf_nfe.find('.//emit')
        cnpj_emit = emit.find('.//{http://www.portalfiscal.inf.br/nfe}CNPJ').text if emit and (emit.find('.//{http://www.portalfiscal.inf.br/nfe}CNPJ') or emit.find('.//CNPJ')) is not None else 'N/A'
        nome_emit = emit.find('.//{http://www.portalfiscal.inf.br/nfe}xNome').text if emit and (emit.find('.//{http://www.portalfiscal.inf.br/nfe}xNome') or emit.find('.//xNome')) is not None else 'N/A'

        # Dados do Destinatário
        dest = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}dest') or inf_nfe.find('.//dest')
        cnpj_dest = dest.find('.//{http://www.portalfiscal.inf.br/nfe}CNPJ').text if dest and (dest.find('.//{http://www.portalfiscal.inf.br/nfe}CNPJ') or dest.find('.//CNPJ')) is not None else 'N/A'
        nome_dest = dest.find('.//{http://www.portalfiscal.inf.br/nfe}xNome').text if dest and (dest.find('.//{http://www.portalfiscal.inf.br/nfe}xNome') or dest.find('.//xNome')) is not None else 'N/A'

        # Valores Totais da Nota (simplificado, apenas vNF, pode expandir)
        total_node = inf_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}total') or inf_nfe.find('.//total')
        icms_tot_node = total_node.find('.//{http://www.portalfiscal.inf.br/nfe}ICMSTot') if total_node is not None else None
        
        vNF = icms_tot_node.find('.//{http://www.portalfiscal.inf.br/nfe}vNF').text if icms_tot_node and (icms_tot_node.find('.//{http://www.portalfiscal.inf.br/nfe}vNF') or icms_tot_node.find('.//vNF')) is not None else '0.00'
        # Adicione outros totais como vICMS, vIPI, vPIS, vCOFINS aqui de forma similar se necessário.
        
        data_rows = []
        # Para cada item ('det') na nota
        for det_node in inf_nfe.findall('.//{http://www.portalfiscal.inf.br/nfe}det') or inf_nfe.findall('.//det'):
            prod_node = det_node.find('.//{http://www.portalfiscal.inf.br/nfe}prod') or det_node.find('.//prod')
            imposto_node = det_node.find('.//{http://www.portalfiscal.inf.br/nfe}imposto') or det_node.find('.//imposto')

            # Dados do Produto/Serviço
            cProd = prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}cProd').text if prod_node and (prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}cProd') or prod_node.find('.//cProd')) is not None else 'N/A'
            xProd = prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}xProd').text if prod_node and (prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}xProd') or prod_node.find('.//xProd')) is not None else 'N/A'
            qCom = prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}qCom').text if prod_node and (prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}qCom') or prod_node.find('.//qCom')) is not None else '0.00'
            vUnCom = prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}vUnCom').text if prod_node and (prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}vUnCom') or prod_node.find('.//vUnCom')) is not None else '0.00'
            vProd_item = prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}vProd').text if prod_node and (prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}vProd') or prod_node.find('.//vProd')) is not None else '0.00'
            NCM = prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}NCM').text if prod_node and (prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}NCM') or prod_node.find('.//NCM')) is not None else 'N/A'
            CFOP = prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}CFOP').text if prod_node and (prod_node.find('.//{http://www.portalfiscal.inf.br/nfe}CFOP') or prod_node.find('.//CFOP')) is not None else 'N/A'

            # Exemplo para CST ICMS (pode ser mais complexo dependendo da tag ICMS específica)
            CST_ICMS = 'N/A'
            if imposto_node:
                icms_node = imposto_node.find('.//{http://www.portalfiscal.inf.br/nfe}ICMS') or imposto_node.find('.//ICMS')
                if icms_node:
                    for child in icms_node: # Iterar por ICMS00, ICMS10, etc.
                        if child.find('.//{http://www.portalfiscal.inf.br/nfe}CST') is not None:
                            CST_ICMS = child.find('.//{http://www.portalfiscal.inf.br/nfe}CST').text
                            break
                        elif child.find('.//{http://www.portalfiscal.inf.br/nfe}CSOSN') is not None:
                            CST_ICMS = child.find('.//{http://www.portalfiscal.inf.br/nfe}CSOSN').text
                            break

            data_rows.append({
                'chave_acesso': chave_acesso,
                'dtEmissao': dtEmissao,
                'natOp': natOp,
                'cnpj_emit': cnpj_emit,
                'nome_emit': nome_emit,
                'cnpj_dest': cnpj_dest,
                'nome_dest': nome_dest,
                'vNF_total': float(vNF),
                # 'vICMS_total': float(vICMS), # Adicionar se extraídos do total
                'cProd': cProd,
                'xProd': xProd,
                'qCom': float(qCom),
                'vUnCom': float(vUnCom),
                'vProd_item': float(vProd_item),
                'NCM': NCM,
                'CFOP': CFOP,
                'CST_ICMS': CST_ICMS,
                # Adicionar mais campos de impostos por item se necessário
            })
        
        if not data_rows:
            st.warning(f"Nenhum item de produto/serviço encontrado no XML {xml_file_path}.")
            return None

        df = pd.DataFrame(data_rows)
        return df

    except FileNotFoundError:
        st.error(f"Arquivo XML não encontrado: {xml_file_path}")
        return None
    except ET.ParseError as e:
        st.error(f"Erro ao parsear XML {xml_file_path}: {e}. Verifique se é um XML válido.")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao processar o XML {xml_file_path}: {e}")
        return None

def get_dataframe_from_file(file_path):
    """Carrega um arquivo CSV, Excel ou XML em um DataFrame do Pandas."""
    if file_path.lower().endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.lower().endswith(('.xls', '.xlsx')):
        return pd.read_excel(file_path)
    elif file_path.lower().endswith('.xml'): 
        st.info(f"Processando arquivo XML: {file_path}")
        # Aqui, você pode adicionar lógica para diferenciar NF-e de CT-e
        # Por exemplo: if "nfe" in os.path.basename(file_path).lower():
        # Ou tentar parsear como NFe, se der erro, tentar como CTe
        return parse_nfe_xml_to_dataframe(file_path) # Chama a nova função de parse XML
    else:
        st.warning(f"Formato de arquivo não suportado: {file_path}. Suportamos .csv, .xls, .xlsx, .xml.")
        return None

def unpack_zip_files(zip_file_path, destination_folder):
    """Descompacta um arquivo .zip na pasta de destino."""
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(destination_folder)
        st.success(f"Arquivo '{os.path.basename(zip_file_path)}' descompactado com sucesso para '{destination_folder}'.")
        # os.remove(zip_file_path) # Opcional: remover o .zip após descompactar
        return True
    except Exception as e:
        st.error(f"Erro ao descompactar '{os.path.basename(zip_file_path)}': {e}")
        return False

# --- Lógica de Processamento do Agente (AGORA SEPARADA E CHAMADA PELO BOTÃO) ---

def process_uploaded_xmls(llm_model):
    """
    Função principal que coordena o descompactar, ler XMLs e iniciar o processamento.
    Esta função conterá a lógica para gerar os lançamentos contábeis no futuro.
    """
    st.subheader("Processamento dos Arquivos XML")
    
    # Lista todos os arquivos XML disponíveis após upload/descompactação
    xml_files_in_data_folder = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith('.xml')]
    
    if not xml_files_in_data_folder:
        st.warning("Nenhum arquivo XML encontrado para processar. Por favor, carregue um ZIP de XMLs.")
        return
    
    st.info(f"Encontrados {len(xml_files_in_data_folder)} arquivos XML para processamento.")
    
    all_dfs = []
    for xml_file_name in xml_files_in_data_folder:
        xml_path = os.path.join(DATA_FOLDER, xml_file_name)
        df_xml = get_dataframe_from_file(xml_path) # Reusa a função para carregar o XML para DF
        if df_xml is not None and not df_xml.empty:
            all_dfs.append(df_xml)
            st.success(f"Dados do '{xml_file_name}' extraídos com sucesso em um DataFrame.")
            # Opcional: Mostrar uma amostra do DataFrame extraído
            # st.dataframe(df_xml.head())
        else:
            st.warning(f"Não foi possível extrair dados válidos de '{xml_file_name}'.")

    if all_dfs:
        # Concatenar todos os DataFrames de XMLs em um único DataFrame para análise consolidada
        final_df = pd.concat(all_dfs, ignore_index=True)
        st.success(f"Todos os {len(all_dfs)} DataFrames foram consolidados.")
        # st.dataframe(final_df.head()) # Mostra o DataFrame consolidado

        # --- AQUI É ONDE ENTRARIA A LÓGICA DO SEU AGENTE DE LANÇAMENTOS CONTÁBEIS ---
        # No MVP, isso pode ser a aplicação das "regras básicas implementadas"
        # Mapeamento CFOP -> Conta Contábil, CST, NCM, etc.
        st.subheader("Gerando Lançamentos Contábeis (MVP)")
        # Exemplo Simples:
        lancamentos_contabeis = []
        for index, row in final_df.iterrows():
            # Esta é uma lógica super simplificada para demonstração.
            # VOCÊ PRECISARÁ IMPLEMENTAR SUAS REGRAS AQUI
            # Ex:
            if str(row['CFOP']).startswith('5'): # Vendas
                lancamentos_contabeis.append({
                    'Documento': row['chave_acesso'],
                    'Tipo Operação': 'Venda',
                    'Conta Débito': '1.1.04.0001 - Clientes',
                    'Conta Crédito': '3.1.01.0001 - Receita de Vendas',
                    'Valor': row['vProd_item'],
                    'Observação': f"Venda do produto {row['xProd']} (CFOP: {row['CFOP']})"
                })
                # Adicionar lançamentos de impostos se a regra do seu projeto considerar.
            elif str(row['CFOP']).startswith('1'): # Compras
                lancamentos_contabeis.append({
                    'Documento': row['chave_acesso'],
                    'Tipo Operação': 'Compra',
                    'Conta Débito': '1.1.06.0001 - Estoque Mercadorias',
                    'Conta Crédito': '2.1.01.0001 - Fornecedores',
                    'Valor': row['vProd_item'],
                    'Observação': f"Compra do produto {row['xProd']} (CFOP: {row['CFOP']})"
                })
            # Mais regras aqui para diferentes CFOPs, CSTs, etc.

        if lancamentos_contabeis:
            df_lancamentos = pd.DataFrame(lancamentos_contabeis)
            st.success("Lançamentos Contábeis Gerados (MVP):")
            st.dataframe(df_lancamentos)
            
            # Entregável: Gerar CSV/JSON dos lançamentos
            csv_output = df_lancamentos.to_csv(index=False)
            st.download_button(
                label="Baixar Lançamentos Contábeis (CSV)",
                data=csv_output,
                file_name="lancamentos_contabeis_gerados.csv",
                mime="text/csv"
            )
        else:
            st.warning("Nenhum lançamento contábil gerado com as regras atuais.")

        # O agente Langchain pode ser usado AQUI para análises *sobre* o `final_df` ou `df_lancamentos`
        # Se você quiser que o LLM "audite" ou "classifique" os lançamentos gerados.
        # Por enquanto, mantemos o foco na geração e exibição dos lançamentos.
        # if llm_model and st.button("Analisar Lançamentos com Agente LLM (Experimental)"):
        #     agent_df_lancamentos = create_pandas_dataframe_agent(llm_model, df_lancamentos, verbose=True, allow_dangerous_code=True)
        #     st.info("Agente LLM analisando os lançamentos...")
        #     try:
        #         response_llm = agent_df_lancamentos.run("Quais são os 5 maiores valores de lançamentos de compra? Qual o CNPJ do emitente que gerou a maior venda?")
        #         st.write(response_llm)
        #     except Exception as e:
        #         st.error(f"Erro ao usar o Agente LLM: {e}")

    else:
        st.error("Não foi possível consolidar dados de nenhum arquivo XML válido.")


# --- Interface do Usuário com Streamlit ---

# Logo
# Certifique-se de que 'logo_lancai.png' está na mesma pasta do script ou forneça o caminho completo.
try:
    st.image("logo_lancai.png", width=200) # Ajuste a largura conforme necessário
except FileNotFoundError:
    st.warning("Logo não encontrada. Certifique-se de que 'logo_lancai.png' está no diretório correto.")

st.title("LançAI: Agente de Automação Contábil-Fiscal")
st.write("Bem-vindo ao LançAI! Faça o upload de seus arquivos XML fiscais (NF-e/CT-e) para automação de lançamentos contábeis.")

# Campo para upload do arquivo ZIP (ou múltiplos XMLs diretamente)
# Usaremos o file_uploader para o "Adicionar Arquivo"
uploaded_zip_file = st.file_uploader(
    "1. Adicionar arquivo ZIP de XMLs fiscais:",
    type=["zip"],
    accept_multiple_files=False, # Apenas um ZIP por vez para simplificar o MVP
    key="zip_uploader"
)

# Botão para enviar o arquivo para o agente
# Este botão agora disparará a lógica de processamento
if st.button("2. Enviar para o Agente", key="process_button"):
    if uploaded_zip_file is not None:
        # Salva o arquivo ZIP para processamento
        zip_path_in_data_folder = os.path.join(DATA_FOLDER, uploaded_zip_file.name)
        with open(zip_path_in_data_folder, "wb") as f:
            f.write(uploaded_zip_file.getbuffer())
        st.success(f"Arquivo '{uploaded_zip_file.name}' carregado com sucesso.")

        # Descompacta o arquivo ZIP
        if unpack_zip_files(zip_path_in_data_folder, DATA_FOLDER):
            # Inicia o processamento dos XMLs descompactados
            process_uploaded_xmls(llm) # Passa o LLM para a função de processamento
    else:
        st.warning("Por favor, adicione um arquivo ZIP antes de enviar para o agente.")

st.markdown("---")
st.markdown("### Interações Futuras:")
st.info("Nesta etapa (MVP), focamos na leitura e processamento. Em entregas futuras, incluiremos mais opções de interação, como:")
st.write("- **Configuração de Regras:** Interface para personalizar mapeamentos CFOP/CST/NCM.")
st.write("- **Relatórios Detalhados:** Relatórios de auditoria e análise de inconsistências.")
st.write("- **Integração com ERPs:** Opções para exportar lançamentos diretamente para sistemas contábeis.")
st.write("- **Assistente Consultor:** Perguntas sobre legislação e cenários tributários.")