from django.shortcuts import render, redirect
from django.contrib import messages
import os
from datetime import datetime
import re
from django.http import FileResponse, HttpResponse
from zipfile import ZipFile
from io import BytesIO
from tax.templatetags.custom_filters import get_file_type, get_document_type_display
from django.urls import reverse

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


def tax_questions(request):
    # Redirect to signin if not authenticated
    if not request.session.get('user_phone'):
        return redirect('signin')
   
    if request.method == 'POST':
        # Get form data
        tax_year = request.POST.get('tax_year')
        income_type = request.POST.get('income_type')
        filing_status = request.POST.get('filing_status')
        previous_filing = request.POST.get('previous_filing')
        user_entered_name = request.POST.get('user_entered_name')  # Get the new name field
       
        # Get user's base folder - this contains user_information.txt from signin
        user_phone = request.session.get('user_phone')
        user_base_folder = os.path.join(DATA_DIR, user_phone)
        
        # Create name subfolder within the phone number folder
        # This preserves the user_information.txt in the phone number folder
        name_folder = os.path.join(user_base_folder, user_entered_name)
        os.makedirs(name_folder, exist_ok=True)
       
        # Create year folder structure inside the name folder
        year_folder = os.path.join(name_folder, tax_year)
        documents_folder = os.path.join(year_folder, 'documents')
        os.makedirs(documents_folder, exist_ok=True)
       
        # Handle document uploads
        required_documents = ['pan_card', 'aadhar_card', 'form16', 'bank_statement']
        uploaded_docs = []
       
        for doc_type in required_documents:
            if doc_type in request.FILES:
                file = request.FILES[doc_type]
                # Create safe filename
                filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(file.name)[1]}"
                file_path = os.path.join(documents_folder, filename)
               
                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                uploaded_docs.append(f"{doc_type}: {filename}")
       
        # Create and write to tax_details.txt
        tax_details_path = os.path.join(year_folder, 'tax_details.txt')
        with open(tax_details_path, 'w') as file:
            file.write(f"Name: {user_entered_name}\n")
            file.write(f"Tax Year: {tax_year}\n")
            file.write(f"Income Type: {income_type}\n")
            file.write(f"Filing Status: {filing_status}\n")
            file.write(f"Previous Filing: {previous_filing}\n")
            file.write(f"\nSubmission Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            file.write("\nUploaded Documents:\n")
            for doc in uploaded_docs:
                file.write(f"- {doc}\n")
       
        # Store basic info in session
        request.session['tax_info'] = {
            'tax_year': tax_year,
            'user_name': user_entered_name,
            'current_folder': year_folder
        }
       
        messages.success(request, 'Tax information and documents saved successfully!')
        return redirect('home')  # Or redirect to next step
       
    # Generate year choices (current year and previous 2 years)
    current_year = datetime.now().year
    years = list(range(current_year, current_year - 3, -1))
   
    context = {
        'years': years,
        'income_types': [
            'Salary/Wages',
            'Self-employed/Business',
            'Rental Income',
            'Investment Income',
            'Multiple Sources'
        ],
        'filing_statuses': [
            'Single',
            'Married Filing Jointly',
            'Married Filing Separately',
            'Head of Household'
        ]
    }
   
    return render(request, 'tax_questions.html', context)

def user_home(request):
    tax_filings = []
    
    # Check if user is authenticated
    user_phone = request.session.get('user_phone')
    if user_phone:
        user_base_folder = os.path.join(DATA_DIR, user_phone)
        
        # Check if the base folder exists
        if os.path.exists(user_base_folder):
            # Iterate through all name folders
            for name_folder in os.listdir(user_base_folder):
                name_path = os.path.join(user_base_folder, name_folder)
                
                # Skip if not a directory or if it's a special file
                if not os.path.isdir(name_path) or name_folder.startswith('.'):
                    continue
                
                # Iterate through all year folders
                for tax_year in os.listdir(name_path):
                    year_path = os.path.join(name_path, tax_year)
                    
                    # Skip if not a directory or not a valid year
                    if not os.path.isdir(year_path) or not tax_year.isdigit():
                        continue
                    
                    # Check for tax_details.txt
                    tax_details_path = os.path.join(year_path, 'tax_details.txt')
                    if os.path.exists(tax_details_path):
                        # Extract information from tax_details.txt
                        filing_info = {
                            'id': f"{user_phone}_{name_folder}_{tax_year}",  # Create a unique ID
                            'tax_year': tax_year,
                            'name': name_folder,
                        }
                        
                        # Parse tax_details.txt to get additional info
                        with open(tax_details_path, 'r') as file:
                            details = file.read()
                            
                            # Extract filing status
                            filing_status_match = re.search(r'Filing Status: (.+)', details)
                            if filing_status_match:
                                filing_info['filing_status'] = filing_status_match.group(1)
                            else:
                                filing_info['filing_status'] = 'Unknown'
                            
                            # Extract submission date
                            date_match = re.search(r'Submission Date: (.+)', details)
                            if date_match:
                                filing_info['filed_date'] = date_match.group(1)
                            else:
                                filing_info['filed_date'] = 'Unknown'
                        
                        # Set default values for other fields
                        filing_info['status'] = 'completed'  # Or determine based on some logic
                        filing_info['amount'] = '0.00'  # You may need to calculate or store this elsewhere
                        
                        tax_filings.append(filing_info)
    
    # Sort filings by tax year (newest first)
    tax_filings.sort(key=lambda x: x['tax_year'], reverse=True)
    
    context = {
        'tax_filings': tax_filings
    }
    
    return render(request, 'user_home.html', context)

def view_tax_filing(request, filing_id):
    try:
        user_phone, name, tax_year = filing_id.split('_')
        if request.session.get('user_phone') != user_phone:
            messages.error(request, 'Unauthorized access')
            return redirect('user_home')

        tax_details_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'tax_details.txt')
        documents_folder = os.path.join(DATA_DIR, user_phone, name, tax_year, 'documents')

        # Read tax details
        tax_details_lines = []
        with open(tax_details_path, 'r') as file:
            for line in file.read().split('\n'):
                if ': ' in line:
                    parts = line.split(': ', 1)
                    tax_details_lines.append({'label': parts[0], 'value': parts[1]})

        # Process documents
        documents = []
        if os.path.exists(documents_folder):
            for filename in os.listdir(documents_folder):
                if os.path.isfile(os.path.join(documents_folder, filename)):
                    documents.append({
                        'name': filename,
                        'type': get_document_type_display(filename),
                        'file_type': get_file_type(filename),
                        'download_url': reverse('download_document', args=[
                            user_phone, 
                            name, 
                            tax_year, 
                            filename
                        ])
                    })

        context = {
            'filing_id': filing_id,
            'tax_details_lines': tax_details_lines,
            'documents': documents,
            'tax_year': tax_year,
            'name': name
        }
        return render(request, 'view_tax_filing.html', context)

    except Exception as e:
        messages.error(request, f'Error loading filing: {str(e)}')
        return redirect('user_home')

def delete_tax_filing(request, filing_id):
    # Check if user is authenticated
    user_phone = request.session.get('user_phone')
    if not user_phone:
        return redirect('signin')
    
    # Parse the filing_id
    try:
        id_user_phone, name, tax_year = filing_id.split('_')
        
        # Security check - ensure user can only delete their own filings
        if id_user_phone != user_phone:
            messages.error(request, 'You do not have permission to delete this filing')
            return redirect('user_home')
    except ValueError:
        messages.error(request, 'Invalid filing ID')
        return redirect('user_home')
    
    # Build the path to the year folder
    year_folder = os.path.join(DATA_DIR, user_phone, name, tax_year)
    
    if os.path.exists(year_folder):
        import shutil
        # Delete the entire year folder
        shutil.rmtree(year_folder)
        messages.success(request, f'Tax filing for {name} ({tax_year}) has been deleted successfully')
    else:
        messages.error(request, 'Tax filing not found')
    
    # Check if the name folder is now empty
    name_folder = os.path.join(DATA_DIR, user_phone, name)
    if os.path.exists(name_folder) and not os.listdir(name_folder):
        # If empty, remove the name folder too
        os.rmdir(name_folder)
    
    return redirect('user_home')

def download_document(request, user_phone, name, tax_year, filename):
    if request.session.get('user_phone') != user_phone:
        return HttpResponse("Unauthorized", status=401)
    
    file_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'documents', filename)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True)
    return HttpResponse("File not found", status=404)

def download_all_documents(request, filing_id):
    try:
        user_phone, name, tax_year = filing_id.split('_')
        if request.session.get('user_phone') != user_phone:
            return HttpResponse("Unauthorized", status=401)

        documents_folder = os.path.join(DATA_DIR, user_phone, name, tax_year, 'documents')
        if not os.path.exists(documents_folder):
            return HttpResponse("No documents found", status=404)

        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            for root, dirs, files in os.walk(documents_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    zip_file.write(file_path, arcname=file)

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{tax_year}_documents.zip"'
        return response

    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=400)