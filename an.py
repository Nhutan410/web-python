# Import các module cần thiết
import os
import re
from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
import openai

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Thay đổi bằng một mã bảo mật mạnh khi triển khai ở môi trường thực tế
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"  # Thay đổi tên cơ sở dữ liệu tùy ý
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase2.db"
app.config["UPLOAD_FOLDER"] = "static/uploads"
db = SQLAlchemy(app)

# Model User để lưu trữ thông tin người dùng
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Model Admin để lưu trữ thông tin admin
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Model Post để lưu trữ thông tin bài post
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    file_path = db.Column(db.String(200))
    post_time = db.Column(db.DateTime, default=datetime.utcnow)  # Đặt giá trị mặc định

# Function kiểm tra xem file upload có hợp lệ không
def allowed_file(filename):
    allowed_extensions = {"jpg", "jpeg", "png", "gif", "mp4", "avi", "mkv", "mov" "pdf"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

# Chuyển múi giờ từ UTC sang múi giờ Việt Nam (UTC+7)
def convert_to_vietnam_time(utc_time):
    return utc_time + timedelta(hours=7)

# Function kiểm tra xem người dùng có phải là admin không
def is_admin():
    if "username" in session:
        username = session["username"]
        admin = Admin.query.filter_by(username=username).first()
        return admin is not None
    return False

# Function để sử dụng GPT-3.5 API của OpenAI để trả lời chat
def generate_gpt3_response(prompt):
    openai.api_key = "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"  # Thay thế bằng mã khóa API của bạn
    response = openai.Completion.create(
        engine="text-davinci-002",  # GPT-3.5 engine
        prompt=prompt,
        max_tokens=150,  # Điều chỉnh số ký tự tối đa của phản hồi
    )
    return response.choices[0].text.strip()

# Trang chủ với form để viết bài post và chat
@app.route("/", methods=["GET", "POST"])
def home():
    if "username" not in session:
        return redirect("/login")

    if request.method == "POST":
        if is_admin():
            title = request.form["title"]
            content = request.form["content"]
            file = request.files["file"]

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                file_path = f"uploads/{filename}"
            else:
                file_path = None

            author = session["username"]
            post = Post(author=author, title=title, content=content, file_path=file_path)
            db.session.add(post)
            db.session.commit()
        else:
            flash("Bạn không có quyền viết bài.", "danger")

    # Thay thế dữ liệu bài post mẫu bằng các bài post từ cơ sở dữ liệu
    posts = Post.query.order_by(Post.post_time.desc()).all()

    # Chuyển đổi múi giờ cho các bài post
    for post in posts:
        post.post_time = convert_to_vietnam_time(post.post_time)

    return render_template("home.html", username=session["username"], posts=posts, is_admin=is_admin())

# Route for handling the chat
@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.get_json().get("user_input")
    ai_response = generate_gpt3_response(user_input)
    return ai_response

# Trang đăng ký
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Kiểm tra xem tên người dùng đã tồn tại chưa
        if User.query.filter_by(username=username).first():
            flash("Tên người dùng đã tồn tại. Hãy chọn tên khác.", "danger")
        # Kiểm tra yêu cầu mật khẩu
        elif not (re.search(r"[A-Z]", password) and re.search(r"\d", password) and re.search(r"[!@#$%^&*]", password)):
            flash("Mật khẩu phải chứa ít nhất một chữ in hoa, một chữ số và một ký tự đặc biệt.", "danger")
        # Kiểm tra xem mật khẩu và xác nhận mật khẩu có khớp nhau không
        elif password != confirm_password:
            flash("Mật khẩu không khớp. Hãy nhập lại mật khẩu.", "danger")
        else:
            # Lưu thông tin người dùng vào cơ sở dữ liệu
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
            flash("Đăng ký thành công. Hãy đăng nhập.", "success")
            return redirect("/login")

    return render_template("register.html")

# Trang đăng nhập
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session["username"] = username
            return redirect("/")
        else:
            flash("Tên người dùng hoặc mật khẩu không đúng. Hãy thử lại.", "danger")

    return render_template("login.html")

# Đăng xuất
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/login")

# Chỉnh sửa bài post
@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if "username" not in session:
        return redirect("/login")

    post = Post.query.get_or_404(post_id)

    if not is_admin():
        flash("Bạn không có quyền chỉnh sửa bài post.", "danger")
        return redirect("/")

    if request.method == "POST":
        post.title = request.form["title"]
        post.content = request.form["content"]
        db.session.commit()
        flash("Bài post đã được cập nhật thành công.", "success")
        return redirect("/")

    return render_template("edit_post.html", post=post, is_admin=is_admin())

@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    if "username" not in session:
        return redirect("/login")

    post = Post.query.get_or_404(post_id)

    if not is_admin():
        flash("Bạn không có quyền xóa bài post.", "danger")
        return redirect("/")

    db.session.delete(post)
    db.session.commit()
    flash("Bài post đã được xóa thành công.", "success")
    return redirect("/")

if __name__ == "__main__":
    with app.app_context():
        # Tạo các bảng trong cơ sở dữ liệu
        db.create_all()

        # Thêm người dùng admin (nếu chưa tồn tại)
        admin_user = Admin.query.filter_by(username="Nhut An").first()
        if not admin_user:
            admin_user = Admin(username="Nhut An", password="An04102004@")
            db.session.add(admin_user)
            db.session.commit()  # <-- Thêm dòng này để lưu các thay đổi vào cơ sở dữ liệu

    app.run(debug=True)
