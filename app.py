from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import pyodbc
import pandas as pd
import os

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)

# Configuração do SQL Server
db_server = os.getenv('db_server')
db_name = os.getenv('db_name')
db_username = os.getenv('db_username')
db_password = os.getenv('db_password')
table_name = os.getenv('table_name')

conn = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_server};DATABASE={db_name};UID={db_username};PWD={db_password}')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/test-db')
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
    query = f"""
    SELECT * FROM {table_name}
    WHERE
        TIPO_TEL = 'CELULAR'
        AND CONTADORTEL IN ('1','2','3')
        AND CIDADE in ('RECIFE','CARUARU','OLINDA','JABOATAO','CABO DE SANTO AGOSTINHO','GARANHUNS','CARPINA','CAMARAGIBE','FORTALEZA','CAUCAIA','JUAZEIRO DO NORTE','SOBRAL','SALVADOR','BARREIRAS','ITABUNA','SIMOES FILHO','FEIRA DE SANTANA','PAULO AFONSO','ILHEUS','PORTO SEGURO','JOAO PESSOA','CAMPINA GRANDE','PATOS','NATAL','MOSSORO','PARNAMIRIM','MACEIO','ARAPIRACA','ARACAJU','TERESINA','PARANAIBA','PICOS','CRATO','LAGARTO')
        AND OPERADOR_ATIVO IN ('TIM S/A','CLARO S.A.','Tim')
    """
    
    try:
        # Cria uma nova conexão para cada consulta
        with pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_server};DATABASE={db_name};UID={db_username};PWD={db_password}') as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()  # Pega apenas o primeiro registro
            
            if row:
                # converte os dados para um dicionário
                columns = [column[0] for column in cursor.description]
                result = dict(zip(columns, row))  # Cria um dicionário com colunas e valores
                return jsonify(result)  # Retorna o primeiro registro como JSON
            else:
                return jsonify({'message': 'Nenhum registro encontrado.'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)