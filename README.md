📚 Quiz Master - Interactive Quiz Management System

An advanced multi-user quiz management platform built with Flask, SQLite, and Bootstrap.
It allows Administrators (Quiz Masters) to create/manage subjects, chapters, and quizzes, while Users can register, take quizzes, track their performance, and even generate certificates.

🚀 Features
👨‍💻 Admin (Quiz Master)

🔑 Secure Admin Login (predefined credentials)

📚 Subject & Chapter Management (Create, Edit, Delete)

📝 Quiz Management (Add/Edit/Delete Quizzes & Questions)

👥 User Management (Search & View Users)

📊 Analytics Dashboard (Quiz attempts, user performance, summary charts)

🙋 User

📝 Register & Login

📖 Select Subject → Chapter → Quiz

⏳ Interactive Quiz with optional timer

📈 View past scores and progress tracking

🏆 Certificate generation after completion

👤 Profile Management

🛠️ Tech Stack

Backend: Python (Flask)
Database: SQLite
Frontend: HTML, CSS, Bootstrap 5, Jinja2 Templating
Charts & Icons: Chart.js, Font Awesome

📂 Project Structure
quiz_master/
│── app.py                # Main application
│── models.py             # Database models
│── static/               # CSS, JS, Images
│── templates/            # HTML templates (Jinja2)
│── requirements.txt      # Dependencies
│── README.md             # Project documentation

⚡ Installation & Setup

Clone the repository

git clone https://github.com/Anjay12/quiz_quiz12.git
cd quiz_quiz12


Create Virtual Environment

python -m venv venv
source venv/bin/activate    # For Linux/Mac
venv\Scripts\activate       # For Windows


Install Dependencies

pip install -r requirements.txt


Initialize Database & Run App

python app.py


Open your browser at:
👉 http://127.0.0.1:5000/

🔑 Default Admin Credentials

Email: admin@example.com

Password: admin123

📊 Demo Screenshots (Optional)

Add images of your app UI (Login, Dashboard, Quiz Page, Analytics, etc.) here for better presentation.

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
