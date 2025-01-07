import warnings
warnings.simplefilter("ignore")

from flask import Flask,Response, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from ppg_reading import read_ppg as read_ppg_func, set_cancel_flag, remove_csv
import time
from ppg_converters import combine_csv
from afib_detection import make_predictions
import os
import shutil
import matplotlib.pyplot as plt
import pandas as pd
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        return jsonify({"success": True, "message": "User is authenticated", "user": {"username": current_user.username}})
    else:
        return jsonify({"success": False, "message": "User is not authenticated"})


@app.route('/user')
def get_user():
    if current_user.is_authenticated:
        return jsonify({"success": True, "user": {"username": current_user.username}})
    else:
        return jsonify({"success": False, "message": "User is not authenticated"})
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return jsonify({"success": True, "message": "Login successful"})
        else:
            return jsonify({"success": False, "message": "Invalid username or password"})
    elif request.method == 'GET':
        if current_user.is_authenticated:
            return jsonify({"success": True, "message": "User is authenticated"})
        else:
            return jsonify({"success": False, "message": "User is not authenticated"})
        

@app.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        age = int(request.form['age'])
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({"success": False, "message": "Username already exists"})
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, age=age, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return jsonify({"success": True, "message": "Signup successful"})
    return jsonify({"success": False, "message": "Invalid request"})


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"success": True, "message": "Logout successful"})




@app.route('/read_ppg')
@login_required
def read_ppg_route():
    # Read PPG data for 120 seconds and save to CSV
    try:
        read_ppg_func(120, current_user.email.replace('@', '_').replace('.', '_'))  # Calling the imported function
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})
    
@app.route('/ppg_to_ecg_resp')
@login_required
def ppg_to_ecg_resp():
    try:
        combine_csv('ppg_data' + current_user.email.replace('@', '_').replace('.', '_') + '.csv')  # Calling the imported function
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})
    
@app.route('/afib_detection')
@login_required
def afib_detection():
    try:
        csv_path = 'ppg_data' + current_user.email.replace('@', '_').replace('.', '_') + '.csv'
        result = make_predictions('ppg_data' + current_user.email.replace('@', '_').replace('.', '_') + '.csv')
        # Read the CSV file into a DataFrame
        df = pd.read_csv(csv_path)
        df['afib'] = result
        df.to_csv(csv_path, index=False)
        return jsonify({'success': True,'result': str(result)})
    except:
        return jsonify({'success': False})
        
# Route to cancel the reading process
@app.route('/cancel_reading')
@login_required
def cancel_reading_route():
    set_cancel_flag()
    time.sleep(1)
    remove_csv('ppg_data' + current_user.email.replace('@', '_').replace('.', '_') + '.csv')
    return redirect(url_for('home'))  # Redirect to the home page


@app.route('/move_csv')
@login_required
def move_csv():
    try:
        # Define source and destination paths
        source_path = 'ppg_data' + current_user.email.replace('@', '_').replace('.', '_') + '.csv'
        destination_folder = os.path.join('prev_user_data', source_path)

        # Create the destination folder if it doesn't exist
        os.makedirs(os.path.dirname(destination_folder), exist_ok=True)

        # Move the CSV file to the new folder
        shutil.move(source_path, destination_folder)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_csv_data')
@login_required
def get_csv_data():
    try:
        # Define the path to the CSV file
        csv_path = 'prev_user_data/' + 'ppg_data' + current_user.email.replace('@', '_').replace('.', '_') + '.csv'
        
        # Check if the CSV file exists
        if not os.path.exists(csv_path):
            return jsonify({'success': False, 'error': 'CSV file not found'})
        
        # Read the CSV file into a DataFrame
        df = pd.read_csv(csv_path)
        
        # Convert DataFrame to JSON
        json_data = df.to_json(orient='records')
        
        # Return JSON data with Content-Type header set to application/json
        return Response(response=json_data, status=200, content_type='application/json')
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
    

    
@app.route('/get_results')
@login_required
def get_results():
    try:
        csv_path = 'prev_user_data/' + 'ppg_data' + current_user.email.replace('@', '_').replace('.', '_') + '.csv'
        
        if not os.path.exists(csv_path):
            return jsonify({'success': False, 'error': 'CSV file not found'})
        df = pd.read_csv(csv_path)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df['Time'], df['PPG'], marker='o', linestyle='-', color='blue', label='PPG')
        ax.plot(df['Time'], df['ECG'], marker='o', linestyle='-', color='green', label='ECG')
        ax.plot(df['Time'], df['resp'], marker='o', linestyle='-', color='red', label='Resp')

        ax.legend()
        ax.set_xlabel('Time')
        ax.set_ylabel('Signal Value')
        ax.set_title("AFib Detected" if df['afib'].iloc[0] == 0 else "AFib Not Detected")

        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png')
        img_bytes.seek(0)
        
        return Response(response=img_bytes, status=200, content_type='image/png')
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8080)
