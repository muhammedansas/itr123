import mimetypes
from django.shortcuts import render, redirect
from django.contrib import messages
import os
from datetime import datetime
import re
from django.http import FileResponse, HttpResponse
from tax.templatetags.custom_filters import get_file_type, get_document_type_display
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import zipfile
import io
from django.views.decorators.http import require_http_methods


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
CA_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ca_data')

def tax_questions(request):
    if not request.session.get('user_phone'):
        return redirect('signin')

    if request.method == 'POST':
        # Step 1: Personal Information (KYC)
        pan_number = request.POST.get('pan_number', '')
        user_name = request.POST.get('name', '')
        aadhaar_number = request.POST.get('aadhaar_number', '')
        aadhaar_mobile = request.POST.get('aadhaar_mobile', '')
        email = request.POST.get('email', '')
        it_password = request.POST.get('it_password', '')

        # Step 2: Tax Year and Income Details
        tax_year = request.POST.get('tax_year', '')
        income_type = request.POST.get('income_type', '')
        previous_filing = request.POST.get('previous_filing', '')
        rent_details = request.POST.get('rent_details', '')
        property_details = request.POST.get('property_details', '')
        fd_income = request.POST.get('fd_income', '')
        mutual_fund_details = request.POST.get('mutual_fund_details', '')
        other_income = request.POST.get('other_income', '')
        is_partner = request.POST.get('is_partner', 'No')
        is_director = request.POST.get('is_director', 'No')
        unlisted_shares = request.POST.get('unlisted_shares', 'No')
        refund_bank_details = request.POST.get('refund_bank_details', '')

        # Step 3: NRI Details (Conditional)
        is_nri = request.POST.get('is_nri', 'No')
        nri_days_in_india = request.POST.get('nri_days_in_india', '')
        nri_days_in_india_prev = request.POST.get('nri_days_in_india_prev', '')
        nri_bank_details = request.POST.get('nri_bank_details', '')

        # Validate critical fields
        if not pan_number or not tax_year:
            messages.error(request, 'PAN number and tax year are required!')
            return redirect('tax_questions')

        # Create folders and save files
        user_phone = request.session.get('user_phone', '')
        if not user_phone:
            messages.error(request, 'Session expired. Please sign in again.')
            return redirect('signin')

        try:
            # Create directory structure
            user_base_folder = os.path.join(DATA_DIR, user_phone)
            pan_folder = os.path.join(user_base_folder, pan_number)
            os.makedirs(pan_folder, exist_ok=True)

            year_folder = os.path.join(pan_folder, tax_year)
            documents_folder = os.path.join(year_folder, 'documents')
            os.makedirs(documents_folder, exist_ok=True)

            # Save uploaded files
            uploaded_docs = []
            file_fields = {
                'pan_card': request.FILES.get('pan_card'),
                'aadhaar_card': request.FILES.getlist('aadhaar_card'),
                'form16': request.FILES.get('form16'),
                'tax_pl_report': request.FILES.get('tax_pl_report'),
                'bank_statement': request.FILES.get('bank_statement'),
                'housing_loan_certificate': request.FILES.get('housing_loan_certificate'),
                'life_insurance_receipts': request.FILES.get('life_insurance_receipts'),
                'medical_insurance_receipts': request.FILES.get('medical_insurance_receipts'),
                'nri_govt_id': request.FILES.get('nri_govt_id'),
            }

            for field_name, file in file_fields.items():
                if file:
                    if isinstance(file, list):  # Handle multiple Aadhaar card uploads
                        for idx, f in enumerate(file):
                            if f:  # Make sure the file is not None
                                filename = f"{field_name}_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(f.name)[1]}"
                                file_path = os.path.join(documents_folder, filename)
                                with open(file_path, 'wb+') as destination:
                                    for chunk in f.chunks():
                                        destination.write(chunk)
                                uploaded_docs.append(f"{field_name}: {filename}")
                    else:
                        filename = f"{field_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(file.name)[1]}"
                        file_path = os.path.join(documents_folder, filename)
                        with open(file_path, 'wb+') as destination:
                            for chunk in file.chunks():
                                destination.write(chunk)
                        uploaded_docs.append(f"{field_name}: {filename}")

            # Save tax details
            tax_details_path = os.path.join(year_folder, 'tax_details.txt')
            with open(tax_details_path, 'w') as file:
                file.write(f"PAN Number: {pan_number}\n")
                file.write(f"Name: {user_name}\n")
                file.write(f"Aadhaar Number: {aadhaar_number}\n")
                file.write(f"Aadhaar Mobile: {aadhaar_mobile}\n")
                file.write(f"Email: {email}\n")
                file.write(f"IT Password: {it_password}\n")
                file.write(f"Tax Year: {tax_year}\n")
                file.write(f"Income Type: {income_type}\n")
                file.write(f"Previous Filing: {previous_filing}\n")
                file.write(f"Rent Details: {rent_details}\n")
                file.write(f"Property Details: {property_details}\n")
                file.write(f"FD Income: {fd_income}\n")
                file.write(f"Mutual Fund Details: {mutual_fund_details}\n")
                file.write(f"Other Income: {other_income}\n")
                file.write(f"Is Partner: {is_partner}\n")
                file.write(f"Is Director: {is_director}\n")
                file.write(f"Unlisted Shares: {unlisted_shares}\n")
                file.write(f"Refund Bank Details: {refund_bank_details}\n")
                file.write(f"Is NRI: {is_nri}\n")
                if is_nri == 'Yes':
                    file.write(f"Days in India (2024-25): {nri_days_in_india}\n")
                    file.write(f"Days in India (2020-24): {nri_days_in_india_prev}\n")
                    file.write(f"NRI Bank Details: {nri_bank_details}\n")
                file.write(f"Status: Pending with Customer\n")
                file.write(f"\nSubmission Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            request.session['tax_info'] = {
                'tax_year': tax_year,
                'user_name': user_name,
                'current_folder': year_folder
            }

            messages.success(request, 'Tax information and documents saved successfully!')
            return redirect('user_home')
            
        except Exception as e:
            messages.error(request, f'Error processing your submission: {str(e)}')
            return redirect('tax_questions')

    # For GET requests, prepare the form
    current_year = datetime.now().year
    years = list(range(current_year, current_year - 3, -1))

    context = {
        'years': years,
        'current_year': current_year
    }

    return render(request, 'tax_questions.html', context)


def user_home(request):
    tax_filings = []
    client_filings = []
    user_phone = request.session.get('user_phone')
    user_type = request.session.get('user_type')
   
    if user_type == 'user' and user_phone:
        user_base_folder = os.path.join(DATA_DIR, user_phone)
        if os.path.exists(user_base_folder):
            tax_filings = get_tax_filings(user_base_folder, user_phone)
    elif user_type == 'ca' and user_phone:
        ca_base_folder = os.path.join(CA_DATA_DIR, user_phone, 'ca_mapping.txt')
        if os.path.exists(ca_base_folder):
            with open(ca_base_folder, 'r') as file:
                mapped_clients = file.read().splitlines()
            for client_phone in mapped_clients:
                client_base_folder = os.path.join(DATA_DIR, client_phone)
                if os.path.exists(client_base_folder):
                    client_filings.extend(get_tax_filings(client_base_folder, client_phone, is_ca=True))
   
    context = {
        'tax_filings': tax_filings if user_type == 'user' else [],
        'client_filings': client_filings if user_type == 'ca' else [],
        'total_clients': len(set(f.get('client_name') for f in client_filings if f.get('client_name'))) if user_type == 'ca' else len(tax_filings),
        'filed_client_filings': sum(1 for f in client_filings if f.get('filing_status', '').lower() == 'filed') if user_type == 'ca' else 0,
        'pending_client_filings': sum(1 for f in client_filings if f.get('filing_status', '').lower() in ['pending with customer', 'pending with ca']) if user_type == 'ca' else 0,
        'filed_filings': sum(1 for f in tax_filings if f.get('filing_status', '').lower() == 'filed') if user_type == 'user' else 0,
        'pending_filings': sum(1 for f in tax_filings if f.get('filing_status', '').lower() in ['pending with customer', 'pending with ca']) if user_type == 'user' else 0,
    }
    return render(request, 'user_home.html', context)

def get_tax_filings(base_folder, user_phone, is_ca=False):
    import logging
    import os
    import re
    import time
    
    # Set up logging
    logger = logging.getLogger(__name__)
    
    tax_filings = []
    
    try:
        # Check if base folder exists before proceeding
        if not os.path.exists(base_folder):
            logger.warning(f"Base folder does not exist: {base_folder}")
            return tax_filings
            
        try:
            name_folders = os.listdir(base_folder)
        except (OSError, PermissionError) as e:
            logger.error(f"Error listing directory {base_folder}: {e}")
            return tax_filings
            
        for name_folder in name_folders:
            try:
                name_path = os.path.join(base_folder, name_folder)
                
                # Skip non-directories and hidden folders
                if not os.path.isdir(name_path) or name_folder.startswith('.'):
                    continue
                    
                try:
                    tax_years = os.listdir(name_path)
                except (OSError, PermissionError) as e:
                    logger.error(f"Error accessing folder {name_path}: {e}")
                    continue
                    
                for tax_year in tax_years:
                    try:
                        year_path = os.path.join(name_path, tax_year)
                        
                        # Skip non-directories and non-digit years
                        if not os.path.isdir(year_path) or not tax_year.isdigit():
                            continue
                            
                        tax_details_path = os.path.join(year_path, 'tax_details.txt')
                        
                        if not os.path.exists(tax_details_path):
                            logger.warning(f"Tax details file not found: {tax_details_path}")
                            continue
                            
                        filing_info = {
                            'id': f"{user_phone}_{name_folder}_{tax_year}",
                            'tax_year': tax_year,
                            'name': name_folder,
                            'client_name': name_folder if is_ca else None,
                            'filing_status': 'unknown',
                            'filed_date': 'Unknown',
                            'documents': [],
                            'num_documents': 0
                        }
                        
                        # Read tax details file with retry mechanism
                        max_retries = 3
                        retry_delay = 0.5  # seconds
                        
                        for attempt in range(max_retries):
                            try:
                                with open(tax_details_path, 'r') as file:
                                    details = file.read()
                                    
                                    # Extract important fields using regex
                                    name_match = re.search(r'Name: (.+)', details)
                                    if name_match:
                                        filing_info['name'] = name_match.group(1).strip()
                                    
                                    # Extract the Status field
                                    status_match = re.search(r'Status: (.+)', details)
                                    if status_match:
                                        raw_status = status_match.group(1).strip().lower()
                                        
                                        # Map the status to the filter options
                                        status_mapping = {
                                            'pending': 'pending',
                                            'in progress': 'in-progress',
                                            'payment pending': 'payment-pending',
                                            'completed': 'completed'
                                        }
                                        filing_info['filing_status'] = status_mapping.get(raw_status, raw_status)
                                    
                                    # Extract the Submission Date field
                                    date_match = re.search(r'Submission Date: (.+)', details)
                                    if date_match:
                                        filing_info['filed_date'] = date_match.group(1).strip()
                                
                                # If we got here, reading the file was successful
                                break
                                
                            except (OSError, IOError) as e:
                                logger.warning(f"Attempt {attempt+1}/{max_retries} failed for {tax_details_path}: {e}")
                                if attempt < max_retries - 1:
                                    time.sleep(retry_delay)
                                else:
                                    logger.error(f"Failed to read {tax_details_path} after {max_retries} attempts")
                        
                        # Get the list of documents with error handling
                        documents_folder = os.path.join(year_path, 'documents')
                        try:
                            if os.path.exists(documents_folder) and os.path.isdir(documents_folder):
                                doc_files = []
                                try:
                                    for doc in os.listdir(documents_folder):
                                        doc_path = os.path.join(documents_folder, doc)
                                        if os.path.isfile(doc_path):
                                            doc_files.append(doc)
                                except (OSError, PermissionError) as e:
                                    logger.error(f"Error listing documents in {documents_folder}: {e}")
                                
                                filing_info['documents'] = doc_files
                                filing_info['num_documents'] = len(doc_files)
                        except Exception as e:
                            logger.error(f"Error processing documents folder {documents_folder}: {e}")
                        
                        tax_filings.append(filing_info)
                    except Exception as e:
                        logger.error(f"Error processing tax year {tax_year} in {name_path}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error processing name folder {name_folder} in {base_folder}: {e}")
                continue
    except Exception as e:
        logger.error(f"Unexpected error in get_tax_filings for {base_folder}: {e}")
    
    return tax_filings

@csrf_exempt
def save_message(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_phone = data.get("phone")  # Ensure correct variable usage
            pan_number = data.get("pan_number")
            tax_year = data.get("tax_year")
            message = data.get("message")
            name = request.session.get("user_name", "Unknown")  # Default if missing

            # Validate required fields
            if not user_phone or not pan_number or not tax_year or not message:
                return JsonResponse({"status": "error", "message": "Missing required fields"})

            # Construct the user folder path
            user_folder = os.path.join(DATA_DIR, user_phone, pan_number, tax_year)

            # Check if the directory exists
            if not os.path.exists(user_folder):
                return JsonResponse({"status": "error", "message": f"Directory not found: {user_folder}"})

            # Audit trail file path
            message_file_path = os.path.join(user_folder, "audit_trail.txt")

            # Format message correctly
            formatted_message = f"Name: {name}\nMessage: {message}\n{'-' * 40}\n"

            with open(message_file_path, "a") as file:
                file.write(formatted_message)

            return JsonResponse({"status": "success", "message": "Message saved successfully"})

        except Exception as e:
            messages.error(request, f'Error loading Messaging: {str(e)}')
            return JsonResponse({"status": "error", "message": f"Exception occurred: {str(e)}"}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)

def update_tax_filing_status(user_phone, name, tax_year, new_status):
    """
    Update the status in the tax details file
    """
    tax_details_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'tax_details.txt')
    
    # Read existing details
    with open(tax_details_path, 'r') as file:
        lines = file.readlines()
    
    # Update status
    updated_lines = []
    for line in lines:
        if line.startswith('Status: '):
            updated_lines.append(f'Status: {new_status}\n')
        else:
            updated_lines.append(line)
    
    # Write back to file
    with open(tax_details_path, 'w') as file:
        file.writelines(updated_lines)

def download_tax_details(request, filing_id):
    """
    View for downloading tax details file
    """
    try:
        # Extract filing details from filing_id
        user_phone, name, tax_year = filing_id.split('_')
        session_phone = request.session.get('user_phone')
        user_type = request.session.get('user_type')

        # Authorization checks
        if user_type == 'user' and session_phone != user_phone:
            messages.error(request, 'Unauthorized access')
            return redirect('user_home')
        
        if user_type == 'ca':
            ca_mapping_path = os.path.join(CA_DATA_DIR, session_phone, 'ca_mapping.txt')
            if not os.path.exists(ca_mapping_path) or user_phone not in open(ca_mapping_path).read().splitlines():
                messages.error(request, 'Unauthorized access')
                return redirect('user_home')

        # Construct the path to tax_details.txt
        tax_details_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'tax_details.txt')
        
        # Check if file exists
        if not os.path.exists(tax_details_path):
            messages.error(request, 'Tax details file not found')
            return redirect('view_tax_filing', filing_id=filing_id)

        # Read the file content
        with open(tax_details_path, 'rb') as file:
            file_content = file.read()

        # Determine the content type
        content_type, _ = mimetypes.guess_type(tax_details_path)
        if content_type is None:
            content_type = 'text/plain'

        # Create the response
        response = HttpResponse(file_content, content_type=content_type)
        
        # Set the filename for download
        filename = f"tax_details_{name}_{tax_year}.txt"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    except ValueError:
        # Invalid filing_id format
        messages.error(request, 'Invalid filing ID format')
        return redirect('user_home')
    except Exception as e:
        messages.error(request, f'Error downloading tax details: {str(e)}')
        return redirect('view_tax_filing', filing_id=filing_id)

# Also update your existing view_tax_filing function to include the download functionality
def view_tax_filing(request, filing_id):
    try:
        # Existing code for extracting filing details
        user_phone, name, tax_year = filing_id.split('_')
        session_phone = request.session.get('user_phone')
        user_type = request.session.get('user_type')

        # Authorization checks
        if user_type == 'user' and session_phone != user_phone:
            messages.error(request, 'Unauthorized access')
            return redirect('user_home')
        
        if user_type == 'ca':
            ca_mapping_path = os.path.join(CA_DATA_DIR, session_phone, 'ca_mapping.txt')
            if not os.path.exists(ca_mapping_path) or user_phone not in open(ca_mapping_path).read().splitlines():
                messages.error(request, 'Unauthorized access')
                return redirect('user_home')

        # Status options
        STATUS_OPTIONS = [
            'Pending with Customer', 
            'Pending with CA', 
            'Filed'
        ]

        # Read tax details
        tax_details_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'tax_details.txt')
        tax_details_lines = []
        with open(tax_details_path, 'r') as file:
            for line in file.read().split('\n'):
                if ': ' in line:
                    parts = line.split(': ', 1)
                    tax_details_lines.append({'label': parts[0], 'value': parts[1]})
        
        tax_details_dict = {item["label"]: item["value"] for item in tax_details_lines}
        
        # Read current status
        current_status = tax_details_dict.get("Status", "Pending with Customer")

        # Handle status update via POST request
        if request.method == 'POST':
            new_status = request.POST.get('status')
            
            # Allow status change for both user and CA
            if new_status in STATUS_OPTIONS:
                update_tax_filing_status(user_phone, name, tax_year, new_status)
                messages.success(request, 'Status updated successfully')
                return redirect('view_tax_filing', filing_id=filing_id)
            else:
                messages.error(request, 'Invalid status')
                return redirect('view_tax_filing', filing_id=filing_id)

        # Rest of the existing code for extracting details
        pan_number = tax_details_dict.get("PAN Number")
        user_name = tax_details_dict.get("Name")
        submission_date = tax_details_dict.get("Submission Date")
        status = current_status

        # Read documents and audit trail
        documents_folder = os.path.join(DATA_DIR, user_phone, name, tax_year, 'documents')
        audit_trail_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'audit_trail.txt')

        # Read documents
        documents = []
        if os.path.exists(documents_folder):
            for filename in os.listdir(documents_folder):
                if os.path.isfile(os.path.join(documents_folder, filename)):
                    documents.append({
                        'name': filename,
                        'type': get_document_type_display(filename),
                        'file_type': get_file_type(filename),
                    })

        # Read audit trail
        audit_messages = []
        if os.path.exists(audit_trail_path):
            with open(audit_trail_path, 'r') as file:
                lines = file.read().strip().split("\n----------------------------------------\n")
                for entry in lines:
                    parts = entry.split("\n")
                    name_val = ""
                    message = ""
                    timestamp = ""
                    for part in parts:
                        if part.startswith("Name: "):
                            name_val = part.replace("Name: ", "").strip()
                        elif part.startswith("Message: "):
                            message = part.replace("Message: ", "").strip()
                        elif part.startswith("Timestamp: "):
                            timestamp = part.replace("Timestamp: ", "").strip()
                    if name_val and message:
                        audit_messages.append({
                            "name": name_val, 
                            "message": message,
                            "timestamp": timestamp
                        })

        context = {
            'filing_id': filing_id,
            "pan_number": pan_number,
            "user_name": user_name,
            "submission_date": submission_date,
            "status": status,
            'documents': documents,
            'tax_year': tax_year,
            'name': name,
            "user_phone": user_phone,
            'audit_messages': audit_messages,
            'status_options': STATUS_OPTIONS,
            'user_type': user_type
        }
        return render(request, 'view_tax_filing.html', context)
    
    except Exception as e:
        messages.error(request, f'Error loading filing: {str(e)}')
        return redirect('user_home')

def view_tax_details(request, filing_id):
    """
    View for displaying and editing tax details
    """
    try:
        # Extract filing details from filing_id
        user_phone, name, tax_year = filing_id.split('_')
        session_phone = request.session.get('user_phone')
        user_type = request.session.get('user_type')

        # Authorization checks
        if user_type == 'user' and session_phone != user_phone:
            messages.error(request, 'Unauthorized access')
            return redirect('user_home')
        
        if user_type == 'ca':
            ca_mapping_path = os.path.join(CA_DATA_DIR, session_phone, 'ca_mapping.txt')
            if not os.path.exists(ca_mapping_path) or user_phone not in open(ca_mapping_path).read().splitlines():
                messages.error(request, 'Unauthorized access')
                return redirect('user_home')

        # Check if user can edit (only 'user' type can edit)
        can_edit = (user_type == 'user')

        # Read tax details from file
        tax_details_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'tax_details.txt')
        
        if not os.path.exists(tax_details_path):
            messages.error(request, 'Tax details file not found')
            return redirect('view_tax_filing', filing_id=filing_id)

        # Parse tax details
        tax_details = []
        tax_details_dict = {}
        additional_notes = ""
        
        with open(tax_details_path, 'r') as file:
            content = file.read().strip()
            
            # Check if there are additional notes section
            if '\n\nAdditional Notes:\n' in content:
                main_content, notes_section = content.split('\n\nAdditional Notes:\n', 1)
                additional_notes = notes_section.strip()
            else:
                main_content = content
            
            # Parse main tax details
            for line in main_content.split('\n'):
                if ': ' in line:
                    label, value = line.split(': ', 1)
                    tax_details.append({
                        'label': label.strip(),
                        'value': value.strip()
                    })
                    tax_details_dict[label.strip()] = value.strip()

        # Extract specific values for summary
        total_income = tax_details_dict.get('Total Income', '0')
        total_tax = tax_details_dict.get('Total Tax', '0')
        user_name = tax_details_dict.get('Name', name)

        context = {
            'filing_id': filing_id,
            'tax_details': tax_details,
            'user_name': user_name,
            'tax_year': tax_year,
            'total_income': total_income,
            'total_tax': total_tax,
            'additional_notes': additional_notes,
            'user_type': user_type,
            'can_edit': can_edit
        }

        return render(request, 'tax_details.html', context)

    except Exception as e:
        messages.error(request, f'Error loading tax details: {str(e)}')
        return redirect('view_tax_filing', filing_id=filing_id)


@require_http_methods(["POST"])
def update_tax_details(request, filing_id):
    """
    AJAX endpoint for updating tax details
    """
    try:
        # Extract filing details from filing_id
        user_phone, name, tax_year = filing_id.split('_')
        session_phone = request.session.get('user_phone')
        user_type = request.session.get('user_type')

        # Authorization checks - only users can edit
        if user_type == 'user' and session_phone != user_phone:
            return JsonResponse({'success': False, 'error': 'Unauthorized access'})
        
        if user_type == 'ca':
            return JsonResponse({'success': False, 'error': 'CAs cannot edit tax details. Only users can edit their own details.'})
        
        # Double-check that this is a user trying to edit their own details
        if user_type != 'user' or session_phone != user_phone:
            return JsonResponse({'success': False, 'error': 'Unauthorized access'})

        # Get form data
        form_data = request.POST

        # Build updated tax details content
        tax_details_lines = []
        
        # Read current file to maintain order and get existing fields
        tax_details_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'tax_details.txt')
        existing_fields = []
        
        if os.path.exists(tax_details_path):
            with open(tax_details_path, 'r') as file:
                content = file.read().strip()
                
                # Extract main content (before additional notes)
                if '\n\nAdditional Notes:\n' in content:
                    main_content = content.split('\n\nAdditional Notes:\n', 1)[0]
                else:
                    main_content = content
                
                # Get existing field order
                for line in main_content.split('\n'):
                    if ': ' in line:
                        field_name = line.split(': ', 1)[0].strip()
                        existing_fields.append(field_name)

        # Build new content maintaining field order
        for field_name in existing_fields:
            if field_name in form_data:
                value = form_data[field_name].strip()
                tax_details_lines.append(f"{field_name}: {value}")
            else:
                # Keep original value if not in form (for read-only fields)
                with open(tax_details_path, 'r') as file:
                    for line in file:
                        if line.startswith(f"{field_name}: "):
                            tax_details_lines.append(line.strip())
                            break

        # Add any new fields from form that weren't in original file
        for field_name, value in form_data.items():
            if field_name not in existing_fields and field_name != 'csrfmiddlewaretoken' and field_name != 'Additional Notes':
                tax_details_lines.append(f"{field_name}: {value.strip()}")

        # Build final content
        final_content = '\n'.join(tax_details_lines)
        
        # Add additional notes if provided
        additional_notes = form_data.get('Additional Notes', '').strip()
        if additional_notes:
            final_content += f"\n\nAdditional Notes:\n{additional_notes}"

        # Update the Last Updated field with current timestamp
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Replace or add Last Updated field
        lines = final_content.split('\n')
        updated_lines = []
        last_updated_found = False
        
        for line in lines:
            if line.startswith('Last Updated: '):
                updated_lines.append(f"Last Updated: {current_time}")
                last_updated_found = True
            else:
                updated_lines.append(line)
        
        if not last_updated_found:
            # Add Last Updated before additional notes if it exists
            if '\n\nAdditional Notes:\n' in final_content:
                main_part = '\n'.join([l for l in updated_lines if not l.startswith('Additional Notes:')])
                notes_part = additional_notes
                final_content = f"{main_part}\nLast Updated: {current_time}\n\nAdditional Notes:\n{notes_part}"
            else:
                final_content = '\n'.join(updated_lines) + f"\nLast Updated: {current_time}"
        else:
            final_content = '\n'.join(updated_lines)

        # Write updated content to file
        with open(tax_details_path, 'w') as file:
            file.write(final_content)

        return JsonResponse({'success': True, 'message': 'Tax details updated successfully'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def update_tax_filing_status(user_phone, name, tax_year, new_status):
    """
    Helper function to update tax filing status in the tax_details.txt file
    """
    try:
        tax_details_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'tax_details.txt')
        
        if not os.path.exists(tax_details_path):
            return False
        
        # Read current content
        with open(tax_details_path, 'r') as file:
            content = file.read()
        
        # Update status and last updated time
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.startswith('Status: '):
                updated_lines.append(f"Status: {new_status}")
            elif line.startswith('Last Updated: '):
                updated_lines.append(f"Last Updated: {current_time}")
            else:
                updated_lines.append(line)
        
        # Write back to file
        with open(tax_details_path, 'w') as file:
            file.write('\n'.join(updated_lines))
        
        return True
        
    except Exception as e:
        print(f"Error updating tax filing status: {e}")
        return False


def user_profile(request):
    """
    View for displaying user profile information
    """
    try:
        # Get user session data
        user_phone = request.session.get('user_phone')
        user_type = request.session.get('user_type')
        
        if not user_phone:
            messages.error(request, 'Session expired. Please login again.')
            return redirect('login')
        
        # Read user information from file
        user_info_path = os.path.join(DATA_DIR, user_phone, 'user_information.txt')
        
        if not os.path.exists(user_info_path):
            messages.error(request, 'User information not found')
            return redirect('user_home')
        
        # Parse user information
        user_details = {}
        with open(user_info_path, 'r') as file:
            for line in file:
                if ': ' in line:
                    key, value = line.strip().split(': ', 1)
                    user_details[key] = value
        
        # Get filing statistics (optional - you can calculate these based on your filing structure)
        user_folder = os.path.join(DATA_DIR, user_phone)
        total_filings = 0
        completed_filings = 0
        pending_filings = 0
        
        # Count filings by iterating through user's folders
        if os.path.exists(user_folder):
            for item in os.listdir(user_folder):
                item_path = os.path.join(user_folder, item)
                if os.path.isdir(item_path) and item != 'user_information.txt':
                    # Count tax year folders for each name folder
                    for subitem in os.listdir(item_path):
                        subitem_path = os.path.join(item_path, subitem)
                        if os.path.isdir(subitem_path):
                            total_filings += 1
                            # Check if filing is completed (you can adjust this logic based on your file structure)
                            status_file = os.path.join(subitem_path, 'status.txt')
                            if os.path.exists(status_file):
                                with open(status_file, 'r') as f:
                                    status = f.read().strip()
                                    if status.lower() == 'completed':
                                        completed_filings += 1
                                    else:
                                        pending_filings += 1
                            else:
                                pending_filings += 1
        
        # Prepare context data
        context = {
            'user_name': user_details.get('Full Name', ''),
            'user_phone': user_details.get('Phone Number', user_phone),
            'user_email': user_details.get('Email', ''),
            'user_password': '••••••••',  # Never show actual password
            'registration_date': user_details.get('Registration Date', ''),
            'user_type': user_type,
            'total_filings': total_filings,
            'completed_filings': completed_filings,
            'pending_filings': pending_filings,
            # Additional fields if they exist in your user_information.txt
            'user_pan': user_details.get('PAN Number', ''),
            'user_dob': user_details.get('Date of Birth', ''),
            'user_gender': user_details.get('Gender', ''),
            'user_address': user_details.get('Address', ''),
            'user_city': user_details.get('City', ''),
            'user_state': user_details.get('State', ''),
            'user_pincode': user_details.get('PIN Code', ''),
            'user_country': user_details.get('Country', 'India'),
        }
        
        return render(request, 'user_profile.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading profile: {str(e)}')
        return redirect('user_home')


def update_user_profile(request):
    """
    View for updating user profile information
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        user_phone = request.session.get('user_phone')
        
        if not user_phone:
            return JsonResponse({'success': False, 'error': 'Session expired'})
        
        # Read current user information
        user_info_path = os.path.join(DATA_DIR, user_phone, 'user_information.txt')
        
        if not os.path.exists(user_info_path):
            return JsonResponse({'success': False, 'error': 'User information not found'})
        
        # Parse current user information
        user_details = {}
        with open(user_info_path, 'r') as file:
            for line in file:
                if ': ' in line:
                    key, value = line.strip().split(': ', 1)
                    user_details[key] = value
        
        # Update with new values from form (excluding phone number and password)
        updatable_fields = {
            'Full Name': request.POST.get('name', '').strip(),
            'Email': request.POST.get('email', '').strip(),
            'PAN Number': request.POST.get('pan', '').strip(),
            'Date of Birth': request.POST.get('dob', '').strip(),
            'Gender': request.POST.get('gender', '').strip(),
            'Address': request.POST.get('address', '').strip(),
            'City': request.POST.get('city', '').strip(),
            'State': request.POST.get('state', '').strip(),
            'PIN Code': request.POST.get('pincode', '').strip(),
            'Country': request.POST.get('country', '').strip(),
        }
        
        # Update only non-empty fields
        for key, value in updatable_fields.items():
            if value:  # Only update if value is provided
                user_details[key] = value
        
        # Write updated information back to file
        with open(user_info_path, 'w') as file:
            for key, value in user_details.items():
                file.write(f"{key}: {value}\n")
        
        return JsonResponse({'success': True, 'message': 'Profile updated successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

    
def download_all_documents(request, filing_id):
    try:
        user_phone, name, tax_year = filing_id.split('_')
        documents_folder = os.path.join(DATA_DIR, user_phone, name, tax_year, 'documents')

        if not os.path.exists(documents_folder):
            messages.error(request, 'No documents found.')
            return redirect('view_tax_filing', filing_id=filing_id)

        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename in os.listdir(documents_folder):
                file_path = os.path.join(documents_folder, filename)
                if os.path.isfile(file_path):
                    zip_file.write(file_path, arcname=filename)

        zip_buffer.seek(0)

        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="documents_{filing_id}.zip"'
        return response

    except Exception as e:
        messages.error(request, f'Error downloading documents: {str(e)}')
        return redirect('view_tax_filing', filing_id=filing_id)
    
@csrf_exempt
def upload_document(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        filing_id = request.POST.get("filing_id")
        if not file or not filing_id:
            return JsonResponse({"success": False, "error": "Missing file or filing ID"})
        try:
            user_phone, name, tax_year = filing_id.split('_')
            documents_folder = os.path.join(DATA_DIR, user_phone, name, tax_year, 'documents')
            os.makedirs(documents_folder, exist_ok=True)
            file_path = os.path.join(documents_folder, file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            return JsonResponse({"success": True, "message": "File successfully uploaded"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    
    return JsonResponse({"success": False, "error": "Invalid request method"})


def my_filings(request):
    tax_filings = []
    client_filings = []

    user_phone = request.session.get('user_phone')
    user_type = request.session.get('user_type')

    if user_type == 'user' and user_phone:
        user_base_folder = os.path.join(DATA_DIR, user_phone)
        if os.path.exists(user_base_folder):
            tax_filings = get_tax_filings(user_base_folder, user_phone)

    elif user_type == 'ca' and user_phone:
        ca_base_folder = os.path.join(CA_DATA_DIR, user_phone, 'ca_mapping.txt')

        if os.path.exists(ca_base_folder):
            with open(ca_base_folder, 'r') as file:
                mapped_clients = file.read().splitlines()

            for client_phone in mapped_clients:
                client_base_folder = os.path.join(DATA_DIR, client_phone)
                if os.path.exists(client_base_folder):
                    client_filings.extend(get_tax_filings(client_base_folder, client_phone, is_ca=True))

    context = {
        'tax_filings': tax_filings if user_type == 'user' else [],
        'client_filings': client_filings if user_type == 'ca' else [],
        'user_type': user_type,
    }

    return render(request, 'my_filings.html', context)