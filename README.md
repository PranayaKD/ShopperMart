# 🛒 ShopperMart  

![Django](https://img.shields.io/badge/Django-5.2-green?logo=django&logoColor=white)  
![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)  
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple?logo=bootstrap&logoColor=white)  
![License](https://img.shields.io/badge/License-MIT-yellow)  
![Status](https://img.shields.io/badge/Status-Active-brightgreen)  

---

## ✨ Overview  
**ShopperMart** is a **Django-based e-commerce platform** where users can:  
- 👤 Register & manage profiles  
- 📦 Browse & manage products  
- 🛒 Add products to cart & checkout  
- 📑 Track orders  
- 🎨 Enjoy a clean responsive UI with Bootstrap 5 & custom CSS  

It’s designed for **learning + production-ready deployment**.  

---

## 📂 Project Structure  

ShopperMart/
│── media/ # Uploaded media (avatars, product images)
│ ├── avatars/
│ └── products/
│
│── ShopperMart/ # Main Django project
│ ├── init.py
│ ├── asgi.py
│ ├── settings.py
│ ├── urls.py
│ └── wsgi.py
│
│── ShopperMartapp/ # Core Django app
│ ├── admin.py
│ ├── apps.py
│ ├── forms.py
│ ├── models.py
│ ├── signals.py
│ ├── urls.py
│ ├── views.py
│ ├── templatetags/
│ └── migrations/
│
│── static/ # Static files
│ ├── css/
│ │ └── style.css
│ └── images/
│
│── templates/ # Templates
│ ├── account/
│ │ ├── profile.html
│ │ └── profile_edit.html
│ ├── auth/
│ ├── registration/
│ ├── ShopperMartapp/
│ ├── base.html
│ ├── home.html
│ └── product.html
│
│── .env # Environment variables
│── manage.py
│── requirements.txt


---

## 🚀 Features  

✅ User Authentication (register, login, logout)  
✅ Profile Management (edit profile, upload avatar)  
✅ Product Management (CRUD operations with images)  
✅ Shopping Cart (add/remove/update products)  
✅ Order Checkout & Tracking  
✅ Responsive UI with Bootstrap 5  
✅ Dark/Light Theme Support 🌙☀️  

---

## ⚙️ Installation & Setup  

Clone the repository 👇  

git clone https://github.com/PranayaKD/ShopperMart.git
cd ShopperMart


Create and activate a virtual environment 👇

python -m venv venv
venv\Scripts\activate   # On Windows
source venv/bin/activate  # On macOS/Linux


Install dependencies 👇

pip install -r requirements.txt


Apply migrations 👇

python manage.py migrate


Create a superuser 👇

python manage.py createsuperuser


Run the server 👇

python manage.py runserver


Open in browser 👉 http://127.0.0.1:8000/

🌐 Deployment

Deployed on Render (or similar hosting).

Procfile

web: gunicorn ShopperMart.wsgi


Build Command

pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput


Start Command

gunicorn ShopperMart.wsgi

🖼️ Screenshots
🏠 Home Page
<img src="https://via.placeholder.com/800x400.png?text=Home+Page" alt="Home Page" width="700"/>
📦 Product Page
<img src="https://via.placeholder.com/800x400.png?text=Product+Page" alt="Product Page" width="700"/>
👤 Profile Page
<img src="https://via.placeholder.com/800x400.png?text=Profile+Page" alt="Profile Page" width="700"/>
🛠️ Tech Stack

Backend: Django 5.2 🐍

Frontend: Bootstrap 5 🎨 + Custom CSS

Database: SQLite (default) / PostgreSQL (prod) 🗄️

Deployment: Render / Railway / PythonAnywhere ☁️

🤝 Contributing

Fork this repo

Create a new branch: git checkout -b feature-name

Commit changes: git commit -m "Add feature XYZ"

Push: git push origin feature-name

Open a Pull Request 🚀

📜 License

Licensed under the MIT License – free to use, modify, and distribute.

👨‍💻 Author

Pranaya Kumar Dash
📧 Email: dashpranaya28@gmail.com

🔗 GitHub
 | LinkedIn

 
---

👉 This file should be saved as **`README.md`** in your project root (`ShopperMart/`).  

Do you also want me to give you the **`.gitignore`** (specific for Django + VS Code + Python) so your repo stays clean on GitHub?


