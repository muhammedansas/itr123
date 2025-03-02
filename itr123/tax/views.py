from django.shortcuts import render, redirect
from django.contrib import messages
import os
from datetime import datetime

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
        
        # Get user's base folder
        user_phone = request.session.get('user_phone')
        user_base_folder = os.path.join(DATA_DIR, user_phone)
        
        # Create year folder structure
        year_folder = os.path.join(user_base_folder, tax_year)
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