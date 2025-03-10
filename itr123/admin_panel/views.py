# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
import os
import json
from pathlib import Path

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
CA_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ca_data')

def get_all_users():
    """Get all users from the data directory"""
    users = []
    if os.path.exists(DATA_DIR):
        for user_folder in os.listdir(DATA_DIR):
            if os.path.isdir(os.path.join(DATA_DIR, user_folder)) and user_folder.isdigit():
                user_info_path = os.path.join(DATA_DIR, user_folder, "user_information.txt")
                if os.path.exists(user_info_path):
                    try:
                        with open(user_info_path, 'r') as f:
                            user_info = json.load(f)
                            user_info['phone'] = user_folder
                            users.append(user_info)
                    except:
                        users.append({"name": "Unknown", "phone": user_folder})
                else:
                    users.append({"name": "Unknown", "phone": user_folder})
    return users

def get_all_cas():
    """Get all CAs from the ca_data directory"""
    cas = []
    if os.path.exists(CA_DATA_DIR):
        for ca_folder in os.listdir(CA_DATA_DIR):
            if os.path.isdir(os.path.join(CA_DATA_DIR, ca_folder)) and ca_folder.isdigit():
                ca_info_path = os.path.join(CA_DATA_DIR, ca_folder, "user_information.txt")
                if os.path.exists(ca_info_path):
                    try:
                        with open(ca_info_path, 'r') as f:
                            ca_info = json.load(f)
                            ca_info['phone'] = ca_folder
                            cas.append(ca_info)
                    except:
                        cas.append({"name": "Unknown CA", "phone": ca_folder})
                else:
                    cas.append({"name": "Unknown CA", "phone": ca_folder})
    return cas

def get_ca_mappings():
    """Get all CA to user mappings"""
    mappings = {}
    if os.path.exists(CA_DATA_DIR):
        for ca_folder in os.listdir(CA_DATA_DIR):
            if os.path.isdir(os.path.join(CA_DATA_DIR, ca_folder)) and ca_folder.isdigit():
                mapping_path = os.path.join(CA_DATA_DIR, ca_folder, "ca_mapping.txt")
                if os.path.exists(mapping_path):
                    try:
                        with open(mapping_path, 'r') as f:
                            user_phones = [line.strip() for line in f.readlines()]
                            mappings[ca_folder] = user_phones
                    except:
                        mappings[ca_folder] = []
                else:
                    mappings[ca_folder] = []
    return mappings

def save_ca_mapping(ca_phone, user_phones):
    """Save CA to user mappings"""
    ca_folder = os.path.join(CA_DATA_DIR, ca_phone)
    mapping_path = os.path.join(ca_folder, "ca_mapping.txt")
    
    # Create directory if it doesn't exist
    os.makedirs(ca_folder, exist_ok=True)
    
    with open(mapping_path, 'w') as f:
        for phone in user_phones:
            f.write(f"{phone}\n")
    return True

def admin_dashboard(request):
    users = get_all_users()
    cas = get_all_cas()
    mappings = get_ca_mappings()
    
    # Add assigned user count to each CA
    for ca in cas:
        ca_phone = ca['phone']
        ca['assigned_users_count'] = len(mappings.get(ca_phone, []))
    
    # Add assigned CA to each user
    user_to_ca = {}
    for ca_phone, user_phones in mappings.items():
        for user_phone in user_phones:
            user_to_ca[user_phone] = ca_phone
    
    for user in users:
        user_phone = user['phone']
        if user_phone in user_to_ca:
            user['assigned_ca'] = user_to_ca[user_phone]
        else:
            user['assigned_ca'] = None
    
    context = {
        'users': users,
        'cas': cas,
        'mappings': mappings,
    }
    
    return render(request, 'admin_panel.html', context)

def manage_ca(request, ca_phone):
    cas = get_all_cas()
    ca = None
    for c in cas:
        if c['phone'] == ca_phone:
            ca = c
            break
   
    if not ca:
        messages.error(request, 'CA not found')
        return redirect('admin_dashboard')
   
    users = get_all_users()
    mappings = get_ca_mappings()
    assigned_users = mappings.get(ca_phone, [])
    
    # Add assigned CA info to each user
    user_to_ca = {}
    for ca_phone_iter, user_phones in mappings.items():
        for user_phone in user_phones:
            user_to_ca[user_phone] = ca_phone_iter
    
    for user in users:
        user_phone = user['phone']
        if user_phone in user_to_ca:
            user['assigned_ca'] = user_to_ca[user_phone]
        else:
            user['assigned_ca'] = None
   
    context = {
        'ca': ca,
        'users': users,
        'assigned_users': assigned_users
    }
   
    return render(request, 'manage_ca.html', context)

def update_ca_mapping(request, ca_phone):
    if request.method != 'POST':
        return redirect('manage_ca', ca_phone=ca_phone)
    
    user_phones = request.POST.getlist('user_phones')
    
    # Validate that CA exists
    ca_folder = os.path.join(CA_DATA_DIR, ca_phone)
    if not os.path.isdir(ca_folder):
        os.makedirs(ca_folder, exist_ok=True)
    
    # Validate that users exist
    for user_phone in user_phones:
        user_folder = os.path.join(DATA_DIR, user_phone)
        if not os.path.exists(user_folder):
            messages.warning(request, f'User {user_phone} not found')
    
    # Save the mapping
    save_ca_mapping(ca_phone, user_phones)
    messages.success(request, 'CA to User mapping updated successfully')
    return redirect('admin_dashboard')