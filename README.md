# 📚 Quiz Master - Interactive Quiz Management System

**Quiz Master** is a multi-user quiz management system built with Flask and SQLite.  
Admins can create subjects, chapters, quizzes, and questions, while users can register, take quizzes, track scores, and view progress. Features include dashboards, analytics, and certificate generation.  

---

## 🚀 Features

### 👨‍💻 Admin (Quiz Master)
- 🔑 Secure Admin Login (predefined credentials)  
- 📚 Subject & Chapter Management (Create, Edit, Delete)  
- 📝 Quiz Management (Add/Edit/Delete Quizzes & Questions)  
- 👥 User Management (Search & View Users)  
- 📊 Analytics Dashboard (Quiz attempts, user performance, summary charts)  

### 🙋 User
- 📝 Register & Login  
- 📖 Select Subject → Chapter → Quiz  
- ⏳ Interactive Quiz with optional timer  
- 📈 View past scores and progress tracking  
- 🏆 Certificate generation after completion  
- 👤 Profile Management  

---

## 🛠️ Tech Stack

**Backend:** Python (Flask)  
**Database:** SQLite  
**Frontend:** HTML, CSS, Bootstrap 5, Jinja2 Templating  
**Charts & Icons:** Chart.js, Font Awesome  

---

## 📂 Project Structure
quiz_master/
│── app.py # Main application
│── models.py # Database models
│── static/ # CSS, JS, Images
│── templates/ # HTML templates (Jinja2)
│── requirements.txt # Dependencies
│── README.md # Project documentation

**Create Virtual Environment**
python -m venv venv
source venv/bin/activate    # For Linux/Mac
venv\Scripts\activate       # For Windows

**Install Dependencies**
pip install -r requirements.txt

**Initialize Database & Run App**
python app.py

Open your browser at:
👉 http://127.0.0.1:5000/

🔑 Default Admin Credentials

Email: admin@example.com

Password: admin123

📊 Demo Screenshots

Add images of your app UI (Login, Dashboard, Quiz Page, Analytics, etc.) here.

🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to fork this repo and submit a pull request.

📜 License

This project is licensed under the MIT License – see the LICENSE
 file for details.

🌟 Acknowledgements

Flask Documentation
Bootstrap
Chart.js
