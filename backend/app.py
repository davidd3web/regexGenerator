from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

app = Flask(__name__)
CORS(app)


# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:" \
                                        f"{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/" \
                                        f"{os.getenv('DB_NAME')}"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define a model for the chat history
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500))
    answer = db.Column(db.String(5000))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize DB (Create tables if they don't exist)
with app.app_context():
    db.create_all()

@app.route('/generate-regex', methods=['POST'])
def generate_regex():
    data = request.json
    user_input = data['userInput']

    # Set up OpenAI API key
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in regex. you will only answer prompts related to regex. "
                               "if the prompt is not related to regex, please mention to the user that your "
                               "capabilities are limited to regular expressions.",
                },
                {
                    "role": "user",
                    "content": user_input,
                }
            ],
            model="gpt-3.5-turbo",
        )
        response = chat_completion.choices[0].message.content

        new_chat = ChatHistory(question=user_input, answer=response)
        db.session.add(new_chat)
        db.session.commit()

        return jsonify({
            'regex': response,
            'newChat': {
                'id': new_chat.id,
                'question': user_input,
                'answer': response,
                'created_at': new_chat.created_at.isoformat()
            }
        })
    
        
    except Exception as e:
        print("Error:", e)
        return jsonify(error=str(e)), 500

@app.route('/fetch-chat', methods=['GET'])
def fetch_chat():
    try:
        all_chats = ChatHistory.query.order_by(ChatHistory.created_at.desc()).all()
        return jsonify([{'id': chat.id ,'question': chat.question, 'answer': chat.answer, 'created_at': chat.created_at} for chat in all_chats])
    except Exception as e:
        print(e)
        return jsonify(error=str(e)), 500
    
@app.route('/delete-chat/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    # Start a session context
    with db.session.begin():
        # Use the session to get your chat instance
        chat = db.session.get(ChatHistory, chat_id)
        
        # If chat exists, delete it
        if chat:
            db.session.delete(chat)
            
    return jsonify({'message': 'Chat deleted successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True)
