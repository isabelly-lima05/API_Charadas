from flask import Flask, jsonify, request
import random
import firebase_admin
from firebase_admin import credentials, firestore
from auth import gerar_token, token_obrigatorio
from flask_cors import CORS
import os
from dotenv import load_dotenv
import json 
from flasgger import Swagger

load_dotenv()

app = Flask(__name__)

# Versão do OPEN API
app.config['SWAGGER'] = {
    'openapi': '3.0.0'
}

#Chamar o OpenAPI para o código
swagger = Swagger(app, template_file='openapi.yaml')

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") 

CORS(app, origins="*")

AMD_USUARIO = os.getenv("AMD_USUARIO")
AMD_SENHA = os.getenv("AMD_SENHA") 

if os.getenv("VERCEL"):
    # Online na Vercel
    cred = credentials.Certificate(json.loads(os.getenv("FIREBASE_CREDENTIALS")))

else:
    # Local
    cred = credentials.Certificate("firebase.json")

# Carregar as Credenciais do Firebase
firebase_admin.initialize_app(cred)

# Conectar-se ao Firestore
db = firestore.client()

# Rota Principal de Boas-Vindas
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "api": "charadas",
        "version": "1.0",
        "Author": "Isabelly"
    }), 200

# Rota de Login 
@app.route("/login", methods=["POST"])
def login():
    dados = request.get_json()

    if not dados:
        return jsonify ({"error": "Envie os dados para login"}), 400
    
    usuario = dados.get("usuario")
    senha = dados.get("senha")

    if not usuario or not senha:
        return jsonify ({"error": "Usuário e senha são obrigatorios"}), 400
    
    if usuario == AMD_USUARIO and senha == AMD_SENHA:
        token = gerar_token(usuario)
        return jsonify ({"message": "Login realizado com sucesso", "token": token})
    
    return jsonify ({"error": "Usuário ou senha inválidos"})

# -----------------------------------------
# ROTAS PÚBLICAS
# -----------------------------------------

# Rota 1 (Rota Pública): Método GET - Todas as charadas
@app.route('/charadas', methods=['GET'])
def get_charadas():
    charadas = [] #Lista Vazia
    lista = db.collection('charadas').stream() #Lista todos os Documentos

    #Transforma o objeto do Firestore em Dicionário Python
    for item in lista:
        charadas.append(item.to_dict())
    
    return jsonify(charadas), 200

# Rota 2 (Rota Pública): Método GET - Charadas aleatórias
@app.route('/charadas/aleatoria', methods=['GET'])
def get_charadas_random():
    charadas = [] #Lista Vazia
    lista = db.collection('charadas').stream() #Lista todos os Documentos

    #Transforma o objeto do Firestore em Dicionário Python
    for item in lista:
        charadas.append(item.to_dict())
    
    return jsonify(random.choice(charadas)), 200

# Rota 3 (Rota Pública): Método GET - Retorna uma charada pelo ID
@app.route("/charadas/<int:id>", methods=['GET'])
def get_charada_by_id(id):
    lista = db.collection('charadas').where('id', '==', id).stream()

    for item in lista:
        return jsonify(item.to_dict()), 200
    
    return jsonify({"Error": "Charada não encontrada"}), 404

# -----------------------------------------
# ROTAS PRIVADAS
# -----------------------------------------

# Rota 4 (Rota Privada): Método POST - Cadastro de novas charadas
@app.route('/charadas', methods=['POST'])
@token_obrigatorio
def post_charadas():

    
    dados = request.get_json()

    if not dados or "pergunta" not in dados or "resposta" not in dados:
        return jsonify({"error": "Dados inválidos ou incompletos"}), 400
    try:
        # Busca pelo contador
        contador_ref = db.collection("contador").document("controle_id")
        contador_doc = contador_ref.get()
        ultimo_id = contador_doc.to_dict().get("ultimo_id")
        novo_id = ultimo_id + 1 # Somar um ao ultimo ID

        contador_ref.update({"ultimo_id": novo_id}) #Atualizar o ID do contador

        # Cadastrar a nova charada
        db.collection("charadas").add({
            "id": novo_id,
            "pergunta": dados["pergunta"],
            "resposta": dados['resposta']
        })

        return jsonify({"message": "Charada criada com sucesso"}), 201

    except:
        return jsonify({"message": "Falha no envio da charada"}), 400

# Rota 5 (Rota Privada): Método PUT - Alteração total 
@app.route('/charadas/<int:id>', methods=['PUT'])
@token_obrigatorio
def charadas_put(id):


    dados = request.get_json()

    if not dados or "pergunta" not in dados or "resposta" not in dados:
        return jsonify({"error": "Dados inválidos ou incompletos"}), 400
    
    try:
        docs = db.collection("charadas").where("id", "==", id).limit(1).get()
        if not docs:
            return jsonify({"error": "Charada não encontrada"}), 404
        
        # Pega o primeiro (e único) documento da lista
        for doc in docs:
            doc_ref = db.collection("charadas").document(doc.id)
            doc_ref.update({
                "pergunta": dados["pergunta"],
                "resposta": dados["resposta"]
            })
        
        return jsonify({"message": "Charada alterada com sucesso"}), 200
    
    except:

        return jsonify({"error": "Falha no envio da charada"})
    
# Rota 6 (Rota Privada): Método PATCH - Alteração parcial
@app.route('/charadas/<int:id>', methods=['PATCH'])
@token_obrigatorio
def charadas_patch(id):


    dados = request.get_json()

    if not dados: # Verifica se os dados estão presentes
        return jsonify({"error": "Dados inválidos ou incompletos"}), 400
    
    try:
        docs = db.collection("charadas").where("id", "==", id).limit(1).get()
        if not docs:
            return jsonify({"error": "Charada não encontrada"}), 404
        
        for doc in docs:
            doc_ref = db.collection("charadas").document(doc.id)
            update_data = {} # Dicionário para armazenar os campos a serem atualizados
            if "pergunta" in dados:
                update_data["pergunta"] = dados["pergunta"]
            
            if "resposta" in dados:
                update_data["resposta"] = dados["resposta"]
            
            if update_data: # Verifica se há campos para atualizar
                doc_ref.update(update_data)
                return jsonify({"message": "Charada alterada com sucesso"}), 200
            
            else:
                return jsonify({"error": "Nenhum campo para atualizar"}), 400
    
    except:
        return jsonify({"error": "Falha no envio da charada"}), 400

# Rota 7 (Rota Privada): Método DELETE - Apagar 
@app.route("/charadas/<int:id>", methods=['DELETE'])
@token_obrigatorio
def delete_charada(id):

    
    docs = db.collection("charadas").where("id", "==", id).limit(1).get()

    if not docs:
        return jsonify({"error": "Charada não encontrada"}), 404

    doc_ref = db.collection("charadas").document(docs[0].id)
    doc_ref.delete()
    return jsonify({"message": "Charada excluída com sucesso"}), 200

# -----------------------------------------
# ROTAS DE TRATAMENTO DE ERRO
# -----------------------------------------

# Rota 8 (Rota de tratamento de Erro): 404 - Erro de página não encontrada
@app.errorhandler(404)
def erro404(error):
    return jsonify ({"error": "URL não encontrada"}), 404

# Rota 9 (Rota de tartamento de Erro): 500 - Erro de servidor
@app.errorhandler(500)
def erro404(error):
    return jsonify ({"error": "Servidor interno com falhas. Tente mais tarde"}), 500

if __name__ == '__main__':
    app.run(debug=True)