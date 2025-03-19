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
                file.write(f"Status: Pending\n")
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
        'total_clients': len(set(f['client_name'] for f in client_filings)) if user_type == 'ca' else 0,
        'completed_client_filings': sum(1 for f in client_filings if f['filing_status'] == 'completed'),
        'pending_client_filings': sum(1 for f in client_filings if f['filing_status'] == 'pending'),
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
            print(data,'bbb')
            user_phone = data.get("phone")  # Ensure correct variable usage
            pan_number = data.get("pan_number")
            tax_year = data.get("tax_year")
            message = data.get("message")
            name = request.session.get("user_name", "Unknown")  # Default if missing
            print(pan_number,"mmmm")

            # Validate required fields
            if not user_phone or not pan_number or not tax_year or not message:
                return JsonResponse({"status": "error", "message": "Missing required fields"})

            # Construct the user folder path
            user_folder = os.path.join(DATA_DIR, user_phone, pan_number, tax_year)

            print(user_folder,"mm")

            # Check if the directory exists
            if not os.path.exists(user_folder):
                return JsonResponse({"status": "error", "message": f"Directory not found: {user_folder}"})

            # Audit trail file path
            message_file_path = os.path.join(user_folder, "audit_trail.txt")

            # Format message correctly
            formatted_message = f"Name: {name}\nMessage: {message}\n{'-' * 40}\n"

            with open(message_file_path, "a") as file:
                file.write(formatted_message)

            messages.success(request, 'Successfully Message Sended')
            return JsonResponse({"status": "success", "message": "Message saved successfully"})

        except Exception as e:
            messages.error(request, f'Error loading Messaging: {str(e)}')
            return JsonResponse({"status": "error", "message": f"Exception occurred: {str(e)}"}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)

def view_tax_filing(request, filing_id):
    try:
        user_phone, name, tax_year = filing_id.split('_')
        session_phone = request.session.get('user_phone')
        user_type = request.session.get('user_type')

        if user_type == 'user' and session_phone != user_phone:
            messages.error(request, 'Unauthorized access')
            return redirect('user_home')

        if user_type == 'ca':
            ca_mapping_path = os.path.join(CA_DATA_DIR, session_phone, 'ca_mapping.txt')
            if not os.path.exists(ca_mapping_path) or user_phone not in open(ca_mapping_path).read().splitlines():
                messages.error(request, 'Unauthorized access')
                return redirect('user_home')

        tax_details_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'tax_details.txt')
        documents_folder = os.path.join(DATA_DIR, user_phone, name, tax_year, 'documents')
        audit_trail_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'audit_trail.txt')

        # Read tax details
        tax_details_lines = []
        with open(tax_details_path, 'r') as file:
            for line in file.read().split('\n'):
                if ': ' in line:
                    parts = line.split(': ', 1)
                    tax_details_lines.append({'label': parts[0], 'value': parts[1]})
        tax_details_dict = {item["label"]: item["value"] for item in tax_details_lines}
        pan_number = tax_details_dict.get("PAN Number")
        user_name = tax_details_dict.get("Name")
        submission_date = tax_details_dict.get("Submission Date")
        status = tax_details_dict.get("Status")

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

        # Read and format audit trail messages
        audit_messages = []
        if os.path.exists(audit_trail_path):
            with open(audit_trail_path, 'r') as file:
                lines = file.read().strip().split("\n----------------------------------------\n")
                for entry in lines:
                    parts = entry.split("\n")
                    name = ""
                    message = ""
                    for part in parts:
                        if part.startswith("Name: "):
                            name = part.replace("Name: ", "").strip()
                        elif part.startswith("Message: "):
                            message = part.replace("Message: ", "").strip()
                    if name and message:
                        audit_messages.append({"name": name, "message": message})
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
            'audit_messages': audit_messages,  # Properly formatted audit messages
        }
        return render(request, 'view_tax_filing.html', context)

    except Exception as e:
        messages.error(request, f'Error loading filing: {str(e)}')
        return redirect('user_home')


# def view_tax_filing(request, filing_id):
#     try:
#         user_phone, name, tax_year = filing_id.split('_')
#         session_phone = request.session.get('user_phone')
#         user_type = request.session.get('user_type')
        
#         # Authorization checks
#         if user_type == 'user' and session_phone != user_phone:
#             messages.error(request, 'Unauthorized access')
#             return redirect('user_home')
#         if user_type == 'ca':
#             ca_mapping_path = os.path.join(CA_DATA_DIR, session_phone, 'ca_mapping.txt')
#             if not os.path.exists(ca_mapping_path) or user_phone not in open(ca_mapping_path).read().splitlines():
#                 messages.error(request, 'Unauthorized access')
#                 return redirect('user_home')
                
#         # File paths
#         tax_details_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'tax_details.txt')
#         documents_folder = os.path.join(DATA_DIR, user_phone, name, tax_year, 'documents')
#         audit_trail_path = os.path.join(DATA_DIR, user_phone, name, tax_year, 'audit_trail.txt')
        
#         # Read tax details
#         tax_details_lines = []
#         with open(tax_details_path, 'r') as file:
#             for line in file.read().split('\n'):
#                 if ': ' in line:
#                     parts = line.split(': ', 1)
#                     tax_details_lines.append({'label': parts[0], 'value': parts[1]})
        
#         # Create dictionary for easy access
#         tax_details_dict = {item["label"]: item["value"] for item in tax_details_lines}
        
#         # Group tax details into categories for better organization
#         personal_info = []
#         financial_info = []
#         nri_info = []
#         other_info = []
        
#         for item in tax_details_lines:
#             label = item['label']
#             # Personal information
#             if label in ["Name", "PAN Number", "Aadhaar Number", "Aadhaar Mobile", "Email", "IT Password"]:
#                 personal_info.append(item)
#             # NRI related
#             elif label in ["Is NRI", "Days in India (2024-25)", "Days in India (2020-24)", "NRI Bank Details"]:
#                 nri_info.append(item)
#             # Financial details
#             elif label in ["Income Type", "Rent Details", "Property Details", "FD Income", 
#                          "Mutual Fund Details", "Other Income", "Refund Bank Details"]:
#                 financial_info.append(item)
#             # Other information
#             else:
#                 other_info.append(item)
        
#         # Get basic details
#         pan_number = tax_details_dict.get("PAN Number")
#         user_name = tax_details_dict.get("Name")
#         submission_date = tax_details_dict.get("Submission Date")
#         status = tax_details_dict.get("Status")
        
#         # Read documents
#         documents = []
#         if os.path.exists(documents_folder):
#             for filename in os.listdir(documents_folder):
#                 if os.path.isfile(os.path.join(documents_folder, filename)):
#                     file_path = os.path.join(documents_folder, filename)
#                     file_size = os.path.getsize(file_path)
#                     # Format file size
#                     if file_size < 1024:
#                         size_str = f"{file_size} B"
#                     elif file_size < 1024 * 1024:
#                         size_str = f"{file_size/1024:.1f} KB"
#                     else:
#                         size_str = f"{file_size/(1024*1024):.1f} MB"
                    
#                     # Get file modification time
#                     mod_time = os.path.getmtime(file_path)
#                     upload_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M')
                    
#                     documents.append({
#                         'name': filename,
#                         'type': get_document_type_display(filename),
#                         'file_type': get_file_type(filename),
#                         'size': size_str,
#                         'upload_date': upload_date
#                     })
        
#         # Read and format audit trail messages
#         audit_messages = []
#         if os.path.exists(audit_trail_path):
#             with open(audit_trail_path, 'r') as file:
#                 lines = file.read().strip().split("\n----------------------------------------\n")
#                 for entry in lines:
#                     parts = entry.split("\n")
#                     name = ""
#                     message = ""
#                     timestamp = ""
#                     for part in parts:
#                         if part.startswith("Name: "):
#                             name = part.replace("Name: ", "").strip()
#                         elif part.startswith("Message: "):
#                             message = part.replace("Message: ", "").strip()
#                         elif part.startswith("Timestamp: "):
#                             timestamp = part.replace("Timestamp: ", "").strip()
#                     if name and message:
#                         audit_messages.append({
#                             "name": name, 
#                             "message": message,
#                             "timestamp": timestamp if timestamp else "Unknown"
#                         })
        
#         context = {
#             'filing_id': filing_id,
#             "pan_number": pan_number,
#             "user_name": user_name,
#             "submission_date": submission_date,
#             "status": status,
#             'documents': documents,
#             'tax_year': tax_year,
#             'name': name,
#             "user_phone": user_phone,
#             'audit_messages': audit_messages,
#             'tax_details_lines': tax_details_lines,
#             'personal_info': personal_info,
#             'financial_info': financial_info,
#             'nri_info': nri_info,
#             'other_info': other_info
#         }
#         return render(request, 'view_tax_filing.html', context)
#     except Exception as e:
#         messages.error(request, f'Error loading filing: {str(e)}')
#         return redirect('user_home')
    
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

            # Ensure directory exists
            os.makedirs(documents_folder, exist_ok=True)

            # Save the file
            file_path = os.path.join(documents_folder, file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            messages.success(request, f'File Successfully Added')
        except Exception as e:
            messages.error(request, f'Error Uploading documents: {str(e)}')


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