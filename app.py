from flask import Flask, render_template, request, session, jsonify
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
import secrets
import traceback

# === HARDCODED API KEYS (REPLACE WITH YOUR KEYS) ===
GEMINI_API_KEY = "AIzaSyCWaru2um-xS0O5xZONJIU2G8n8B36FQes"
SPOONACULAR_API_KEY = "4cbc50510fb04ec58c4adbc732686687"
HUGGINGFACE_API_KEY = "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"
SECRET_KEY = "your-flask-secret-key-here"

# === Flask Setup ===
app = Flask(__name__)
app.secret_key = SECRET_KEY

# === Configure Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')
chat = model.start_chat(history=[])

# === Routes ===

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_meals', methods=['POST'])
def get_meals():
    try:
        name = request.form.get('name', '')
        diabetes_type = request.form.get('diabetes_type', '')
        gender = request.form.get('gender', '')
        email = request.form.get('email', '')
        weight = request.form.get('weight', '')
        diet = request.form.get('diet', '')
        calories = request.form.get('calories', '')
        meal_type = request.form.get('meal_type', '')
        allergies = request.form.getlist('allergies')

        if not all([name, diabetes_type, gender, email, weight, diet, calories, meal_type]):
            return jsonify({'status': 'error', 'message': 'All required fields must be filled'}), 400

        session['user_data'] = {
            'name': name,
            'diabetes_type': diabetes_type,
            'diet': diet,
            'calories': calories,
            'allergies': allergies
        }

        prompt = (
            f"Generate a {meal_type} meal plan for someone with {diabetes_type}, on a {diet} diet, "
            f"within {calories} calories"
        )
        if allergies:
            prompt += f" and allergies to: {', '.join(allergies)}"
        prompt += ". Include nutritional info and cooking instructions."

        response = chat.send_message(prompt)

        return jsonify({
            'status': 'success',
            'name': name,
            'meal_type': meal_type.capitalize(),
            'ai_analysis': response.text if response.text else "No response generated"
        })

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Unexpected error occurred'}), 500

@app.route('/schedule')
def schedule():
    if 'meal_schedule' not in session:
        session['meal_schedule'] = {}

    saved_recipes = session.get('saved_recipes', [])
    dates = [(datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    meal_types = ['Breakfast', 'Lunch', 'Dinner', 'Snack']

    return render_template('schedule.html',
                           dates=dates,
                           meal_types=meal_types,
                           saved_schedule=session['meal_schedule'],
                           saved_recipes=saved_recipes)

@app.route('/save_schedule', methods=['POST'])
def save_schedule():
    try:
        schedule_data = request.get_json()
        if not schedule_data:
            return jsonify({'status': 'error', 'message': 'No schedule data provided'}), 400

        session['meal_schedule'] = schedule_data
        session.modified = True
        return jsonify({'status': 'success'})

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Failed to save schedule'}), 500

@app.route('/get_scheduled_meals', methods=['POST'])
def get_scheduled_meals():
    try:
        date = request.form.get('date')
        meal_type = request.form.get('meal_type')
        if not date or not meal_type:
            return jsonify({'status': 'error', 'message': 'Date and meal type required'}), 400

        user_prefs = session.get('user_data', {})
        params = {
            "apiKey": SPOONACULAR_API_KEY,
            "type": meal_type.lower(),
            "number": 5,
            "addRecipeInformation": True,
            "addRecipeNutrition": True,
            "diet": user_prefs.get('diet', ''),
            "maxCalories": user_prefs.get('calories', '')
        }

        response = requests.get("https://api.spoonacular.com/recipes/complexSearch", params=params)
        data = response.json()

        return jsonify({'status': 'success', 'meals': data.get('results', [])})

    except requests.exceptions.RequestException as e:
        print(f"API error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to contact Spoonacular API'}), 500
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Unexpected error occurred'}), 500

@app.route('/save_recipe', methods=['POST'])
def save_recipe():
    try:
        recipe_data = request.get_json()
        if not recipe_data:
            return jsonify({'status': 'error', 'message': 'No recipe data provided'}), 400

        if 'saved_recipes' not in session:
            session['saved_recipes'] = []

        if recipe_data not in session['saved_recipes']:
            session['saved_recipes'].append(recipe_data)
            session.modified = True

        return jsonify({'status': 'success', 'message': 'Recipe saved'})

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Failed to save recipe'}), 500

@app.route('/get_saved_recipes', methods=['GET'])
def get_saved_recipes():
    try:
        return jsonify({
            'status': 'success',
            'recipes': session.get('saved_recipes', [])
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Could not retrieve saved recipes'}), 500

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.get_json()
        user_input = data.get('message', '').strip()
        if not user_input:
            return jsonify({'status': 'error', 'message': 'Empty message'}), 400

        response = chat.send_message(user_input)
        return jsonify({
            'status': 'success',
            'response': response.text if response.text else "No response generated"
        })

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Chat processing failed'}), 500

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d'):
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d')
    return value.strftime(format)

if __name__ == '__main__':
    app.run(debug=True)
