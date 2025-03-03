from django.shortcuts import render, redirect
from django.contrib import messages
import os
from datetime import datetime
from django.contrib.auth.decorators import login_required

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def home(request):
    return render(request, 'home.html')


def signup(request):
    if request.session.get('user_phone'):
        return redirect('home')
        
    if request.method == 'POST':
        full_name = request.POST.get('fullname')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'signup.html')

        user_folder = os.path.join(DATA_DIR, phone)
        if os.path.exists(user_folder):
            messages.error(request, 'Phone number already registered!')
            return render(request, 'signup.html')

        os.makedirs(user_folder, exist_ok=True)

        user_info_path = os.path.join(user_folder, 'user_information.txt')
        with open(user_info_path, 'w') as file:
            file.write(f"Full Name: {full_name}\n")
            file.write(f"Phone Number: {phone}\n")
            file.write(f"Email: {email}\n")
            file.write(f"Password: {password}\n")

        messages.success(request, 'Account created successfully!')
        return redirect('signin')

    return render(request, 'signup.html')


def signin(request):
    if request.session.get('user_phone'):
        return redirect('home')
        
    if request.method == 'POST':
        phone = request.POST.get('phone')
        password = request.POST.get('password')

        user_folder = os.path.join(DATA_DIR, phone)
        user_info_path = os.path.join(user_folder, 'user_information.txt')

        if os.path.exists(user_folder) and os.path.isfile(user_info_path):
            with open(user_info_path, 'r') as file:
                lines = file.readlines()
                stored_password = None
                full_name = None
                for line in lines:
                    if line.startswith("Password:"):
                        stored_password = line.split(":", 1)[1].strip()
                    elif line.startswith("Full Name:"):
                        full_name = line.split(":", 1)[1].strip()

            if stored_password and password == stored_password:
                request.session['user_phone'] = phone
                request.session['user_name'] = full_name
                messages.success(request, 'Successfully logged in!')
                return redirect('user_home')
            else:
                messages.error(request, 'Invalid password!')
        else:
            messages.error(request, 'Phone number not found!')

    return render(request, 'signin.html')

def logout(request):
    request.session.flush()
    messages.success(request, 'Successfully logged out!')
    return redirect('home')


def ca_signup(request):
    if request.session.get('user_phone'):
        return redirect('home')
       
    if request.method == 'POST':
        full_name = request.POST.get('fullname')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        ca_number = request.POST.get('ca_number')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'ca_signup.html')

        CA_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ca_data')
        os.makedirs(CA_DATA_DIR, exist_ok=True)
        
        ca_folder = os.path.join(CA_DATA_DIR, phone)
        if os.path.exists(ca_folder):
            messages.error(request, 'Phone number already registered!')
            return render(request, 'ca_signup.html')
            
        os.makedirs(ca_folder, exist_ok=True)
        
        ca_info_path = os.path.join(ca_folder, 'user_information.txt')
        with open(ca_info_path, 'w') as file:
            file.write(f"Full Name: {full_name}\n")
            file.write(f"Phone Number: {phone}\n")
            file.write(f"Email: {email}\n")
            file.write(f"CA Registration Number: {ca_number}\n")
            file.write(f"Password: {password}\n")
            file.write(f"Registration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
        messages.success(request, 'Account created successfully!')
        return redirect('ca_signin')
        
    return render(request, 'ca_signup.html')

def ca_signin(request):
    if request.session.get('user_phone'):
        return redirect('ca_home')
       
    if request.method == 'POST':
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        
        CA_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ca_data')
        ca_folder = os.path.join(CA_DATA_DIR, phone)
        ca_info_path = os.path.join(ca_folder, 'user_information.txt')
        
        if os.path.exists(ca_folder) and os.path.isfile(ca_info_path):
            with open(ca_info_path, 'r') as file:
                lines = file.readlines()
                stored_password = None
                full_name = None
                ca_number = None
                
                for line in lines:
                    if line.startswith("Password:"):
                        stored_password = line.split(":", 1)[1].strip()
                    elif line.startswith("Full Name:"):
                        full_name = line.split(":", 1)[1].strip()
                    elif line.startswith("CA Registration Number:"):
                        ca_number = line.split(":", 1)[1].strip()
            
            if stored_password and password == stored_password:
                request.session['user_phone'] = phone
                request.session['user_name'] = full_name
                request.session['ca_number'] = ca_number
                request.session['user_type'] = 'ca'
                
                messages.success(request, 'Successfully logged in!')
                return redirect('ca_home')
            else:
                messages.error(request, 'Invalid password!')
        else:
            messages.error(request, 'Phone number not found!')
            
    return render(request, 'ca_signin.html')

def ca_logout(request):
    request.session.flush()
    messages.success(request, 'Successfully logged out!')
    return redirect('home')

def ca_dashboard(request):
    if not request.session.get('user_phone') or request.session.get('user_type') != 'ca':
        messages.error(request, 'Please login to access this page!')
        return redirect('ca_signin')
        
    context = {
        'user_name': request.session.get('user_name'),
        'user_phone': request.session.get('user_phone'),
        'ca_number': request.session.get('ca_number')
    }
    return render(request, 'ca_dashboard.html', context)