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
db_type = os.getenv('DB_TYPE', 'mysql')
if db_type == 'mysql':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root%40123@localhost/sample'
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

@app.route('/delete_product/<pid>', methods=['POST'])
@login_required
def delete_product(pid):
    # Ensure the current user is an admin
    if current_user.role != 'admin':
        return jsonify({"message": "Unauthorized access."}), 403
    try:
        product = Products.query.filter_by(pid=pid).first()
        if not product:
            return jsonify({"message": "Product not found."}), 404
        db.session.delete(product)
        db.session.commit()
        return redirect(url_for('showproductdata'))
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error: {str(e)}"}), 500


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
class Products(db.Model):
    __tablename__ = 'Products'
    pid = db.Column(db.String(50), primary_key=True, unique=True, nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price_in_dollar = db.Column(db.Float, nullable=False)
    price_in_inr = db.Column(db.Float)  
    price_category = db.Column(db.String(20))  
    quantity = db.Column(db.Integer, nullable=False)
    return_rate = db.Column(db.Float, nullable=False)
    uid = db.Column(db.String(50), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(100), nullable=False)
    def __repr__(self):
        return f"<Product pid={self.pid}, name={self.product_name}>"
    def to_dict(self):
        return {
            "pid": self.pid,
            "product_name": self.product_name,
            "category": self.category,
            "price_in_dollar": self.price_in_dollar,
            "price_in_inr": self.price_in_inr,  
            "price_category": self.price_category,  
            "quantity": self.quantity,
            "return_rate": self.return_rate,
            "uid": self.uid,
            "user_name": self.user_name,
            "branch": self.branch}


@app.before_request
def create_tables():
    db.create_all()

@app.route('/getproductdata', methods=['GET'])
@login_required
def getproductdata():
    global processed_data
    if processed_data is None:
        return jsonify({"message": "No processed data available"})
    if not isinstance(processed_data, pd.DataFrame):
        return jsonify({"message": "Processed data is not in the correct format"})
    table_name = 'Products'
    try:
        product_records = [
            Products(
                pid=row['pid'],
                product_name=row['product_name'],
                category=row['category'],
                price_in_dollar=row['price_in_dollar'],
                price_in_inr=row['price_in_inr'],  
                price_category=row['price_category'],  
                quantity=row['quantity'],
                return_rate=row['return_rate'],
                uid=row['uid'],
                user_name=row['user_name'],
                branch=row['branch']
            ) for _, row in processed_data.iterrows()
        ]
        db.session.bulk_save_objects(product_records)
        db.session.commit()
        return redirect(url_for('showproductdata'))
    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"})


@app.route('/showproductdata', methods=['GET'])
@login_required
def showproductdata():
    # Ensure that data has been inserted only once or when necessary
    if processed_data is None:
        return jsonify({"message": "No processed data available"})
    data = Products.query.all()
    product_data = [
        {
            'pid': product.pid,
            'product_name': product.product_name,
            'category': product.category,
            'price_in_dollar': product.price_in_dollar,
            'price_in_inr': product.price_in_inr,  
            'price_category': product.price_category,  
            'quantity': product.quantity,
            'return_rate': product.return_rate,
            'uid': product.uid,
            'user_name': product.user_name,
            'branch': product.branch
        }
        for product in data
    ]
    return render_template('products.html', products=product_data)


def getandcleandata(dataset):
    global processed_data
    try:
        # Clean and normalize raw data, handling null values
        dataset.dropna(inplace=True)
        dataset.drop_duplicates(subset=['pid'], inplace=True)
        # Convert necessary fields to numeric with error handling
        dataset['price_in_dollar'] = pd.to_numeric(dataset['price_in_dollar'], errors='coerce')
        dataset['quantity'] = pd.to_numeric(dataset['quantity'], errors='coerce')
        dataset['return_rate'] = pd.to_numeric(dataset['return_rate'], errors='coerce')
        # Add conversion of price from USD to INR
        conversion_rate = 83  # Example conversion rate (1 USD = 83 INR)
        dataset['price_in_inr'] = dataset['price_in_dollar'] * conversion_rate
        # Add price category column based on INR range
        dataset['price_category'] = dataset['price_in_inr'].apply(
            lambda x: 'Expensive' if x > 5000 else 'Cheap' )
        # Data Transformation Logic
        # Ensure non-negative quantities
        dataset['quantity'] = dataset['quantity'].clip(lower=0)  
        # Ensure valid return rate between 0 and 100
        dataset['return_rate'] = dataset['return_rate'].clip(lower=0, upper=100) 
        # Validation checks:
        # 1. Ensure price_in_dollar and quantity are within reasonable ranges
        if not dataset['price_in_dollar'].between(0, 10000).all():  # Assuming price range for validation
            raise ValueError("Price in dollar is out of expected range.")
        if not dataset['quantity'].between(0, 1000).all():  # Assuming quantity range for validation
            raise ValueError("Quantity is out of expected range.")
        # 2. Check for missing critical columns like pid, price_in_dollar, and quantity
        if dataset[['pid', 'price_in_dollar', 'quantity']].isnull().any().any():
            raise ValueError("Missing critical data (pid, price_in_dollar, quantity).")
        # 3. Check for duplicates based on pid
        if dataset.duplicated(subset=['pid']).any():
            raise ValueError("Duplicate entries found based on pid.")
        # 4. Outlier check: Ensure there are no unreasonable outliers in price_in_dollar
        if dataset['price_in_dollar'].max() > 10000:
            raise ValueError("Outlier detected in price_in_dollar.")
        # 5. Ensure return_rate is between 0 and 100
        if not dataset['return_rate'].between(0, 100).all():
            raise ValueError("Return rate is out of expected range (0-100).")
        # Drop rows with any missing data that may remain after processing
        processed_data = dataset.dropna()
        return processed_data
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"})

@app.route("/analysis",methods=['GET','POST'])
@login_required
def analysis(): 
    # Set up API for file upload and data processing
    csv_path = r'C:\Users\chvry\OneDrive\Desktop\GUVI-CHUBB\datatrackAssignments\miniproject\project\data\f1.csv'
    excel_path = r'C:\Users\chvry\OneDrive\Desktop\New folder\data2.xlsx'
    json_path = r'C:\Data\db\data3.json'
    html_path = r'C:\Users\chvry\OneDrive\Desktop\data4.html'
    xml_path = r'C:\Users\chvry\OneDrive\Desktop\GUVI-CHUBB\data5.lxml'
    # Read the data from each specified file
    try:
        data1 = pd.read_csv(csv_path)
        data2 = pd.read_excel(excel_path)
        data3 = pd.read_json(json_path)
        data4 = pd.read_html(html_path)[0] 
        data5 = pd.read_xml(xml_path, parser="etree")
        # Concatenate all datasets
        data = pd.concat([data1, data2, data3, data4, data5], ignore_index=True)
        dataset=getandcleandata(data)
        if isinstance(dataset, pd.DataFrame):
            return redirect(url_for('showproductdata'))
        else:
            return redirect(url_for('getproductdata'))
    except Exception as e:
        return f"Error reading files: {e}", 500


@app.route("/sales_analysis")
@login_required
def sales_analysis():
    # Fetch the sales data from the database (using the Products model)
    sales_data = Products.query.all()  # Retrieve all products from the database
    # Process data for analysis (e.g., total sales, top-selling product, etc.)
    total_sales = sum([product.price_in_inr * product.quantity for product in sales_data])
    total_products = len(sales_data)
    # Calculate average sales per product
    avg_sales_per_product = total_sales / total_products if total_products else 0
    # Identify the top-selling product (highest sales volume)
    top_selling_product = max(sales_data, key=lambda x: x.price_in_inr * x.quantity, default=None)
    # Data visualization (e.g., bar chart of sales by category)
    import matplotlib.pyplot as plt
    import seaborn as sns
    import io
    import base64
    from flask import Response
    category_sales = {}
    for product in sales_data:
        if product.category not in category_sales:
            category_sales[product.category] = 0
        category_sales[product.category] += product.price_in_inr * product.quantity
    categories = list(category_sales.keys())
    sales_values = list(category_sales.values())
    plt.figure(figsize=(10, 6))
    plt.bar(categories, sales_values, color='skyblue')
    plt.title('Sales by Product Category')
    plt.xlabel('Category')
    plt.ylabel('Sales (INR)')
    bar_chart_img = save_plot_to_base64()

    # Create Pie Chart for Sales Distribution by Category
    plt.figure(figsize=(8, 8))
    plt.pie(sales_values, labels=categories, autopct='%1.1f%%', startangle=140)
    plt.title('Sales Distribution by Category')
    pie_chart_img = save_plot_to_base64()

    # Create Scatter Plot for Price vs Quantity Sold
    price_values = [product.price_in_inr for product in sales_data]
    quantity_values = [product.quantity for product in sales_data]
    plt.figure(figsize=(10, 6))
    plt.scatter(price_values, quantity_values, color='green', alpha=0.5)
    plt.title('Price vs Quantity Sold')
    plt.xlabel('Price (INR)')
    plt.ylabel('Quantity Sold')
    scatter_plot_img = save_plot_to_base64()

    # Return analysis data and the charts to the template for rendering
    return render_template('sales_analysis.html', 
                           total_sales=total_sales, 
                           avg_sales_per_product=avg_sales_per_product, 
                           top_selling_product=top_selling_product, 
                           bar_chart_img=bar_chart_img,
                           pie_chart_img=pie_chart_img,
                           scatter_plot_img=scatter_plot_img)


def save_plot_to_base64():
    """ Helper function to save the plot as a base64 image """
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    img_io.seek(0)
    img_b64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
    plt.close()  
    return img_b64


if __name__=='__main__':
    app.run(debug=True)