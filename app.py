from flask import Flask, render_template, request, redirect, url_for, session, flash
import datetime, math

app = Flask(__name__)
app.secret_key = "supersecretkey"

# In-memory "database"
community_needs = []
providers = [
    {"id": 1, "name": "Ravi", "lat": 13.360, "lng": 74.780, "available": True, "username": "ravi", "password": "ravi123"},
    {"id": 2, "name": "Sneha", "lat": 13.358, "lng": 74.785, "available": True, "username": "sneha", "password": "sneha123"}
]
current_id = 0
history_log = []

# Admin credentials
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# Haversine formula
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Assign nearest available provider
def assign_nearest_provider(need):
    nearest = None
    min_distance = float('inf')
    for provider in providers:
        if provider["available"]:
            dist = haversine(need["lat"], need["lng"], provider["lat"], provider["lng"])
            if dist < min_distance:
                min_distance = dist
                nearest = provider
    if nearest:
        need["assigned_to"] = nearest["name"]
        nearest["available"] = False

# Routes
@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/index')
def index():
    return render_template('index.html', needs=community_needs, providers=providers, is_admin=session.get("admin", False))

@app.route('/add', methods=['POST'])
def add_need():
    global current_id
    author = request.form.get("author")
    need_text = request.form.get("need")
    location = request.form.get("location", "Unknown")
    category = request.form.get("category", "General")
    lat = request.form.get("lat")
    lng = request.form.get("lng")

    if not author or not need_text or not lat or not lng:
        flash("All fields including location are required!", "danger")
        return redirect(url_for('index'))

    current_id += 1
    new_need = {
        "id": current_id,
        "author": author,
        "need": need_text,
        "location": location,
        "category": category,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "completed": False,
        "lat": float(lat),
        "lng": float(lng),
        "assigned_to": None
    }

    assign_nearest_provider(new_need)
    community_needs.append(new_need)
    flash(f"Need submitted! Assigned to: {new_need['assigned_to']}", "success")
    return redirect(url_for('index'))

@app.route('/complete/<int:need_id>', methods=['POST'])
def complete_need(need_id):
    for need in community_needs:
        if need["id"] == need_id and not need["completed"]:
            need["completed"] = True
            if need.get("assigned_to"):
                for provider in providers:
                    if provider["name"] == need["assigned_to"]:
                        provider["available"] = True
                        break
            history_log.append({
                "action": "Completed",
                "task": need["need"],
                "author": need["author"],
                "time": datetime.datetime.utcnow().isoformat() + "Z"
            })
            break
    return redirect(url_for('index'))

@app.route('/delete/<int:need_id>', methods=['POST'])
def delete_need(need_id):
    if not session.get("admin"):
        flash("You must be admin to delete needs.", "danger")
        return redirect(url_for("index"))

    global community_needs
    for need in community_needs:
        if need["id"] == need_id:
            history_log.append({
                "action": "Deleted",
                "task": need["need"],
                "author": need["author"],
                "time": datetime.datetime.utcnow().isoformat() + "Z"
            })
            break

    community_needs = [n for n in community_needs if n["id"] != need_id]
    flash("Need deleted successfully.", "info")
    return redirect(url_for('index'))

# --- Admin Login ---
@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin"] = True
            flash("Logged in as Admin", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials", "danger")
        return redirect(url_for("admin_login"))
    return render_template("login.html", role="Admin")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Logged out", "info")
    return redirect(url_for("index"))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        flash("You must be admin to view dashboard.", "danger")
        return redirect(url_for("admin_login"))
    return render_template("dashboard.html", history=history_log)

# --- Provider Login ---
@app.route("/provider/login", methods=["GET","POST"])
def provider_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        for p in providers:
            if p["username"] == username and p["password"] == password:
                session["provider"] = p["name"]
                flash(f"Logged in as {p['name']}", "success")
                return redirect(url_for("provider_dashboard"))
        flash("Invalid credentials", "danger")
        return redirect(url_for("provider_login"))
    return render_template("login.html", role="Provider")

@app.route("/provider/logout")
def provider_logout():
    session.pop("provider", None)
    flash("Logged out", "info")
    return redirect(url_for("index"))

@app.route("/provider/dashboard")
def provider_dashboard():
    if not session.get("provider"):
        flash("You must be logged in as provider.", "danger")
        return redirect(url_for("provider_login"))
    provider_name = session.get("provider")
    assigned_needs = [n for n in community_needs if n.get("assigned_to") == provider_name and not n["completed"]]
    return render_template("provider_dashboard.html", assigned_needs=assigned_needs, provider_name=provider_name)

if __name__ == "__main__":
    app.run(debug=True)
