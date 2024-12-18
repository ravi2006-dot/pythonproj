from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# In-memory user storage (for simplicity)
users = {
    'customer1': {'password': 'custpass', 'role': 'customer'},
    'driver1': {'password': 'driverpass', 'role': 'driver'}
}

# In-memory order storage
orders = []

class User(UserMixin):
    def __init__(self, username, role):
        self.id = username
        self.role = role

@login_manager.user_loader
def load_user(username):
    user_info = users.get(username)
    if user_info:
        return User(username, user_info['role'])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_info = users.get(username)
        if user_info and user_info['password'] == password:
            user = User(username, user_info['role'])
            login_user(user)
            flash('Logged in successfully.')
            if user.role == 'driver':
                return redirect(url_for('index_driver'))
            return redirect(url_for('index_customer'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/driver_login', methods=['GET', 'POST'])
def driver_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_info = users.get(username)
        if user_info and user_info['password'] == password and user_info['role'] == 'driver':
            user = User(username, user_info['role'])
            login_user(user)
            flash('Logged in successfully as driver.')
            return redirect(url_for('index_driver'))
        else:
            flash('Invalid username or password.')
    return render_template('driver_login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    if current_user.role == 'customer':
        return redirect(url_for('index_customer'))
    elif current_user.role == 'driver':
        return redirect(url_for('index_driver'))
    return "Unauthorized access"

@app.route('/index_customer')
@login_required
def index_customer():
    if current_user.role != 'customer':
        return "Unauthorized", 403
    return render_template('index_customer.html', orders=orders)

@app.route('/index_driver')
@login_required
def index_driver():
    if current_user.role != 'driver':
        return "Unauthorized", 403
    return render_template('index_driver.html', orders=orders)

@app.route('/add_order', methods=['POST'])
@login_required
def add_order():
    if current_user.role != 'customer':
        return "Unauthorized", 403
    customer_name = request.form['customer_name']
    address = request.form['address']
    delivery_status = 'Pending'
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    order = {
        'id': len(orders) + 1,
        'customer_name': customer_name,
        'address': address,
        'delivery_status': delivery_status,
        'time': time,
        'location': {'lat': None, 'lon': None}  # Placeholder for driver's location
    }
    orders.append(order)
    return redirect(url_for('index_customer'))

@app.route('/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    if current_user.role != 'driver':
        return "Unauthorized", 403
    new_status = request.form['status']
    lat = request.form['lat']
    lon = request.form['lon']
    for order in orders:
        if order['id'] == order_id:
            order['delivery_status'] = new_status
            order['location'] = {'lat': lat, 'lon': lon}  # Save driver's location
            break
    return redirect(url_for('index_driver'))

@app.route('/optimize_route/<int:order_id>', methods=['GET'])
@login_required
def optimize_route(order_id):
    if current_user.role != 'driver':
        return "Unauthorized", 403
    
    driver_location = request.args.get('driver_location')
    if not driver_location:
        return "Driver location not provided", 400
    
    driver_location = driver_location.split(',')
    if len(driver_location) != 2:
        return "Invalid driver location format", 400
    
    try:
        driver_lat = float(driver_location[0])
        driver_lon = float(driver_location[1])
    except ValueError:
        return "Invalid latitude or longitude", 400
    
    for order in orders:
        if order['id'] == order_id:
            destination_lat = order['location']['lat']
            destination_lon = order['location']['lon']
            if destination_lat and destination_lon:
                try:
                    duration = get_route(driver_lat, driver_lon, float(destination_lat), float(destination_lon))
                    return jsonify({'duration': duration})
                except Exception as e:
                    return f"Error retrieving route: {e}", 500
            return "Destination not found", 404
    return "Order not found", 404

def get_route(start_lat, start_lon, end_lat, end_lon):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=false"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if 'routes' in data and len(data['routes']) > 0:
            duration = data['routes'][0]['duration'] / 60  # Convert seconds to minutes
            return duration
        return "Route not found"
    except requests.RequestException as e:
        raise RuntimeError(f"Request failed: {e}")

if __name__ == '__main__':
    app.run(debug=True)
