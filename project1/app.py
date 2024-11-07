from flask import Flask, jsonify, render_template, request, redirect, url_for
import pandas as pd 
import io
import os
import matplotlib.pyplot as plt
import seaborn as sns
import psycopg2
import base64
from io import BytesIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import Form,StringField, PasswordField, RadioField
from wtforms.validators import DataRequired, Length, EqualTo

app=Flask(__name__)
processed_data=None
db_type = os.getenv('DB_TYPE', 'sqlite')
if db_type == 'postgresql':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root%40123@localhost/sample'
else:
    app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///sample.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY']='asdf_secret_key'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = RadioField('Role', choices=[('admin', 'Admin'), ('user', 'User')], default='user')

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)


@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # You might want to handle the form submission here
        return redirect(url_for('analysis'))
    return render_template('home.html')


@app.route('/login_page', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user_info = Users.query.filter_by(username=username).first()

        if user_info and check_password_hash(user_info.password, password):
            login_user(user_info)
            return redirect(url_for('home'))  
        else:
            return render_template('login.html', form=form, wrong_cred="Wrong Credentials or User not registered.")
    return render_template('login.html', form=form)

# Register page route
@app.route('/register_page', methods=['GET', 'POST'])
def register_page():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        role = form.role.data 
        new_user = Users(username=username, password=hashed_password,role=role)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login_page'))
    
    return render_template('register.html', form=form)

@app.route('/delete_student/<sid>',methods=['GET'])
def delete_student(sid):
        data=Student.query.filter_by(sid=sid).first()
        db.session.delete(data)
        db.session.commit()
        return redirect(url_for('showdata'))


# Register route for user registration handling
@app.route('/register', methods=['GET', 'POST'])
def register():
    return redirect(url_for('register_page'))

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))


# Design an optimized schema to accommodate ETL needs.
class Student(db.Model):
    __tablename__ = 'Students'
    # Define integrity constraints (e.g., primary keys, foreign keys)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sid = db.Column(db.String(50), nullable=False, unique=True) 
    name = db.Column(db.String(100), nullable=False)  
    mid1 = db.Column(db.Float, nullable=False, default=0.0)  
    mid2 = db.Column(db.Float, nullable=False, default=0.0) 
    mid_avg = db.Column(db.Float, nullable=False)  
    semester = db.Column(db.Float, nullable=False)  
    gpa = db.Column(db.Float, nullable=False, default=0.0)  
    percentage = db.Column(db.Float, nullable=False) 
    status = db.Column(db.String(10), nullable=False)
    def __repr__(self):
        return f"<Student sid={self.sid}, name={self.name}>"
    def to_dict(self):
        return {
            "sid": self.sid,
            "name": self.name,
            "gpa": self.gpa,
            "semester": self.semester,
            "status": self.status,
            "mid1": self.mid1,
            "mid2": self.mid2,
            "mid_avg": self.mid_avg,
            "percentage": self.percentage
        }

@app.before_request
def create_tables():
    db.create_all()

# @app.route('/getdata')
# @login_required
def getdata():
    global processed_data
    if processed_data is None:
        return jsonify({"message": "No processed data available"})

    if not isinstance(processed_data, pd.DataFrame):
        return jsonify({"message": "Processed data is not in the correct format"})
    table_name='Students'
    try:
        student_records = [
            Student(
                sid=row['sid'],
                name=row['name'],
                mid1=row['mid1'],
                mid2=row['mid2'],
                mid_avg=row['mid_avg'],
                semester=row['semester'],
                gpa=row['gpa'],
                percentage=row['percentage'],
                status=row['status']
            ) for _, row in processed_data.iterrows()
        ]
        db.session.bulk_save_objects(student_records)
        db.session.commit()
        return jsonify({"message": f"Data successfully inserted into {table_name} of database {db_type}"})
    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"})

@app.route('/showdata', methods=['GET'])
@login_required
def showdata():
    getdata()
    data = Student.query.all()
    student_data = [
        {
            'sid': student.sid,
            'name': student.name,
            'mid1': student.mid1,
            'mid2': student.mid2,
            'mid_avg': student.mid_avg,
            'semester': student.semester,
            'gpa': student.gpa,
            'percentage': student.percentage,
            'status': student.status
        }
        for student in data
    ]
    return render_template('students.html', students=student_data)

def getandcleandata(dataset):
    global processed_data
    try:
    # Clean and normalize raw data, handling null values # Clean and normalize raw data, handling null values, duplicates, and inconsistencies.
        dataset.dropna(inplace=True)
        dataset.drop_duplicates(subset=['sid'],inplace=True)
            # Data Validation Checks
            # 1. Number conversion with error handling
        dataset['mid1'] = pd.to_numeric(dataset['mid1'], errors='coerce')
        dataset['mid2'] = pd.to_numeric(dataset['mid2'], errors='coerce')
                
                # Check that mid marks and semester marks are >= 0
        if (dataset['mid1'] < 0).any():
            dataset['mid1'] = dataset['mid1'].clip(lower=0)
        if (dataset['mid2'] < 0).any():
            dataset['mid2'] = dataset['mid2'].clip(lower=0)
                
                # 2. GPA transformation and checks, range check and handling inconsistency
        dataset['gpa'] = dataset['gpa'].astype(str).str.strip().str.lower()
        dataset['gpa'] = dataset['gpa'].replace('fail', 0)
        dataset['gpa'] = pd.to_numeric(dataset['gpa'], errors='coerce')
                # Data Transformation Logic
                # 3. Adding assignment marks to midterm scores
        dataset['mid1'] += 10
        dataset['mid2'] += 10
        dataset['mid_avg']=(dataset['mid1']+dataset['mid2'])/2
        dataset['percentage'] = (dataset['gpa'] / 10) * 100
        dataset['status'] = dataset['gpa'].apply(lambda x: 'fail' if x <= 6 else 'pass')
        processed_data = dataset.dropna()
            # return processed_data
        return processed_data
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"})
@app.route("/analysis",methods=['GET','POST'])
@login_required
def analysis(): 
    # Set up API for file upload and data processing
    csv_path = r'C:\Users\chvry\OneDrive\Desktop\GUVI-CHUBB\datatrackAssignments\miniproject1\project\data\f1.csv'
    excel_path = r'C:\Users\chvry\OneDrive\Desktop\New folder\f2.xlsx'
    json_path = r'C:\Data\db\f3.json'
    html_path = r'C:\Users\chvry\OneDrive\Desktop\f4.html'
    xml_path = r'C:\Users\chvry\OneDrive\Desktop\GUVI-CHUBB\f5.lxml'
    # Read the data from each specified file
    try:
        data1 = pd.read_csv(csv_path)
        data2 = pd.read_excel(excel_path)
        data3 = pd.read_json(json_path)
        data4 = pd.read_html(html_path)[0] 
        data5 = pd.read_xml(xml_path, parser="etree")
        # Concatenate all dataset
        data = pd.concat([data1, data2, data3, data4, data5], ignore_index=True)
        dataset=getandcleandata(data)
        if isinstance(dataset, pd.DataFrame):
            return jsonify(dataset.to_dict(orient='records')) 
        else:
            return redirect(url_for('showdata'))
    except Exception as e:
        return f"Error reading files: {e}", 500
import matplotlib.pyplot as plt
import seaborn as sns
import os
from flask import url_for, render_template
import pandas as pd

@app.route("/student_analysis")
@login_required
def student_analysis():
    try:
        # Retrieve and prepare data
        if current_user.role == 'admin':
            student_data = Student.query.all()
        else:
            student_data = Student.query.filter_by(status='pass').all()
        student_list = [student.to_dict() for student in student_data]
        df = pd.DataFrame(student_list)
        # Directory for images
        img_dir = os.path.join("static", "images")
        os.makedirs(img_dir, exist_ok=True)
        # Bar chart for midterm scores
        plt.figure(figsize=(10, 6))
        sns.barplot(x='name', y='mid1', data=df, color='blue', label='Mid1')
        sns.barplot(x='name', y='mid2', data=df, color='orange', bottom=df['mid1'], label='Mid2')
        plt.legend()
        midterm_chart_path = os.path.join(img_dir, "midterm_chart.png")
        plt.savefig(midterm_chart_path)
        plt.close()
        # Line chart for GPA trends
        plt.figure(figsize=(10, 6))
        plt.plot(df['name'], df['gpa'], marker='o', color='green')
        plt.title('GPA of Students')
        gpa_chart_path = os.path.join(img_dir, "gpa_chart.png")
        plt.savefig(gpa_chart_path)
        plt.close()
        # Pie chart for pass/fail status
        status_counts = df['status'].value_counts()
        plt.figure(figsize=(6, 6))
        plt.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=140)
        plt.title('Pass/Fail Distribution')
        status_chart_path = os.path.join(img_dir, "status_chart.png")
        plt.savefig(status_chart_path)
        plt.close()
        # Heatmap for student scores
        plt.figure(figsize=(10, 6))
        sns.heatmap(df[['mid1', 'mid2', 'semester', 'gpa']], annot=True, cmap="YlGnBu", xticklabels=df['name'])
        plt.title('Score Heatmap')
        heatmap_chart_path = os.path.join(img_dir, "heatmap_chart.png")
        plt.savefig(heatmap_chart_path)
        plt.close()
        # Scatter plot for GPA vs. Percentage
        plt.figure(figsize=(10, 6))
        plt.scatter(df['gpa'], df['percentage'], c='purple')
        plt.xlabel('GPA')
        plt.ylabel('Percentage')
        plt.title('GPA vs. Percentage')
        scatter_chart_path = os.path.join(img_dir, "scatter_chart.png")
        plt.savefig(scatter_chart_path)
        plt.close()
        # Pass chart paths to template
        return render_template("student_dashboard.html", students=student_list,
                               midterm_chart=url_for('static', filename='images/midterm_chart.png'),
                               gpa_chart=url_for('static', filename='images/gpa_chart.png'),
                               status_chart=url_for('static', filename='images/status_chart.png'),
                               heatmap_chart=url_for('static', filename='images/heatmap_chart.png'),
                               scatter_chart=url_for('static', filename='images/scatter_chart.png'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__=='__main__':
    app.run(debug=True)