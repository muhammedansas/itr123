from django.shortcuts import render, redirect
from django.contrib import messages
import os
from datetime import datetime
from django.contrib.auth.decorators import login_required

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def home(request):
    return render(request, 'home.html')


def signup(request):
    # Redirect if already logged in
    if request.session.get('user_phone'):
        return redirect('home')
        
    if request.method == 'POST':
        # Get form data
        full_name = request.POST.get('fullname')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Ensure passwords match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'signup.html')

        # Check if user already exists
        user_folder = os.path.join(DATA_DIR, phone)
        if os.path.exists(user_folder):
            messages.error(request, 'Phone number already registered!')
            return render(request, 'signup.html')

        # Create user directory inside the data folder
        os.makedirs(user_folder, exist_ok=True)

        # Create user information file inside the folder
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
    # Redirect if already logged in
    if request.session.get('user_phone'):
        return redirect('home')
        
    if request.method == 'POST':
        phone = request.POST.get('phone')
        password = request.POST.get('password')

        # Path to the user's folder
        user_folder = os.path.join(DATA_DIR, phone)
        user_info_path = os.path.join(user_folder, 'user_information.txt')

        # Check if the user folder exists
        if os.path.exists(user_folder) and os.path.isfile(user_info_path):
            # Read the stored password and name from the file
            with open(user_info_path, 'r') as file:
                lines = file.readlines()
                stored_password = None
                full_name = None
                for line in lines:
                    if line.startswith("Password:"):
                        stored_password = line.split(":", 1)[1].strip()
                    elif line.startswith("Full Name:"):
                        full_name = line.split(":", 1)[1].strip()

            # Validate the password
            if stored_password and password == stored_password:
                # Set session data
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