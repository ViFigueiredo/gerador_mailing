import pyodbc # type: ignore
import os, json, io
from flask import Flask, render_template, request, jsonify, send_file  # type: ignore
from dotenv import load_dotenv # type: ignore
# from pandas import json_normalize
import pandas as pd

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)

# Configuração do SQL Server
db_server = os.getenv('db_server')
db_instance = os.getenv('db_instance')
db_port = os.getenv('db_port')
db_name = os.getenv('db_name')
db_username = os.getenv('db_username')
db_password = os.getenv('db_password')
table_name = os.getenv('table_name')
print(table_name)

conn = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_server}\\{db_instance},{db_port};DATABASE={db_name};UID={db_username};PWD={db_password};Trusted_Connection=no;')

# Função para formatar listas para SQL
def format_sql_list(values):
    if not values:
        return ""  # Retorna uma string vazia se a lista estiver vazia
    return f"({', '.join(f'''{repr(str(v))}''' for v in values)})"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/test-db', methods=['GET'])
def test_db():
    try:
        # realizar teste de conexão com o banco de dados
        cursor = conn.cursor()
        cursor.execute(f"SELECT TOP 1 * FROM {table_name}")
        row = cursor.fetchone()

        if row:
            return jsonify({'message': 'Conexão bem-sucedida!'})
    except pyodbc.Error as e:
        return jsonify({'error': str(e)})    

@app.route('/executar', methods=['POST'])
def executar_consulta():    
    try:
        # Add error handling for JSON parsing
        if not request.is_json:
            return jsonify({"error": "Missing JSON in request"}), 400            

        dados = request.get_json()

        # dados recebidos da requisição
        print("[IN]REQUISIÇÃO:", dados)

        # Add validation for required fields
        required_fields = ['estado', 'cidade', 'repeticao', 'tipoTelefone', 'operadora', 'descanso']
        for field in required_fields:
            if field not in dados:
                return jsonify({"error": f"Missing required field: {field}"}), 400    

        # Extrai parâmetros do objeto dados
        descanso = dados.get('descanso', [])
        estados = dados.get('estado', [])
        cidades = dados.get('cidade', [])
        repeticao = dados.get('repeticao', [])
        tipoTelefone = dados.get('tipoTelefone', [])
        operadoras = dados.get('operadora', [])
        cnaes = dados.get('cnae', [])
        naturezas = dados.get('natureza', [])

        if not estados or not cidades or not repeticao or not tipoTelefone or not operadoras:
            return jsonify({"error": "One or more required fields are empty."}), 400
        
        # Formata cada parâmetro
        estados = format_sql_list(dados.get('estado', []))
        cidades = format_sql_list(dados.get('cidade', []))
        repeticao = format_sql_list(dados.get('repeticao', []))
        tipoTelefone = format_sql_list(dados.get('tipoTelefone', []))
        operadoras = format_sql_list(dados.get('operadora', []))
        cnaes = format_sql_list(dados.get('cnae', []))
        naturezas = format_sql_list(dados.get('natureza', []))
        
        # se conteudo de cnaes e naturezas for vazio
        if not cnaes and not naturezas:
            query = f"""
            SELECT * FROM {table_name}
            WHERE
                (start_time IS NULL OR start_time < DATEADD(MONTH, -{descanso}, GETDATE()))
                AND TIPO_TEL IN {tipoTelefone}
                AND CONTADORTEL IN {repeticao}
                AND UF_ IN {estados}
                AND CIDADE IN {cidades}
                AND OPERADOR_ATIVO IN {operadoras}
            """
        else:
            query = f"""
            SELECT * FROM {table_name}
            WHERE
                (start_time IS NULL OR start_time < DATEADD(MONTH, -{descanso}, GETDATE()))
                TIPO_TEL IN {tipoTelefone}
                AND CONTADORTEL IN {repeticao}
                AND UF_ IN {estados}
                AND CIDADE IN {cidades}
                AND OPERADOR_ATIVO IN {operadoras}
                AND CNAE_PRINCIPAL IN {cnaes}
                AND NATUREZA_JURIDICA IN {naturezas}
            """

        # Exibir a consulta SQL gerada
        print("Consulta SQL:", query)

        # Cria uma nova conexão para cada consulta
        with conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()  # Pega tudo do cursor
            
            if rows:
                # converte os dados para uma lista de dicionários
                columns = [column[0] for column in cursor.description]
                result = [dict(zip(columns, row)) for row in rows]  # Cria uma lista de dicionários
                return jsonify(result)  # Retorna a lista de dicionários como JSON
            else:
                return jsonify({'message': '[Exec] Sem registros.'}), 404
    except json.JSONDecodeError as e:
        return jsonify({"error": "Invalid JSON format", "details": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/exportar-csv', methods=['POST'])
def exportar_csv():
    try:
        if not request.is_json:
            return jsonify({"error": "Missing JSON in request"}), 400

        dados = request.get_json()
        # print('Dados recebidos:', dados)

        if not isinstance(dados, list):
            return jsonify({"error": "Expected a list of records"}), 400

        # Cria um DataFrame a partir do JSON recebido
        df = pd.DataFrame(dados)

        if df.empty:
            return jsonify({"error": "DataFrame is empty. Check the input data."}), 400

        output = io.BytesIO()
        df.to_csv(output, index=False, sep=';', encoding='utf-8', header=True)
        output.seek(0)

        return send_file(output, mimetype='text/csv', as_attachment=True, download_name='mailing.csv')
    except json.JSONDecodeError as e:
        return jsonify({"error": "Invalid JSON format", "details": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/exportar-xlsx', methods=['POST'])
def exportar_xlsx():
    try:
        if not request.is_json:
            return jsonify({"error": "Missing JSON in request"}), 400

        dados = request.get_json()
        # print('Dados recebidos:', dados)

        if not isinstance(dados, list):
            return jsonify({"error": "Expected a list of records"}), 400

        # Cria um DataFrame a partir do JSON recebido
        df = pd.DataFrame(dados)

        if df.empty:
            return jsonify({"error": "DataFrame is empty. Check the input data."}), 400

        # Cria um buffer em memória para o arquivo Excel
        output = io.BytesIO()
        # Exporta o DataFrame para um arquivo Excel
        df.to_excel(output, index=False, engine='openpyxl')  # Usando openpyxl como engine
        output.seek(0)

        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='mailing.xlsx')
    except json.JSONDecodeError as e:
        return jsonify({"error": "Invalid JSON format", "details": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)