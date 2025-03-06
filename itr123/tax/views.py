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
        pan_number = request.POST.get('pan_number')
        user_name = request.POST.get('name')
        tax_year = request.POST.get('tax_year')
        income_type = request.POST.get('income_type')
        previous_filing = request.POST.get('previous_filing')

        user_phone = request.session.get('user_phone')
        user_base_folder = os.path.join(DATA_DIR, user_phone)
        pan_folder = os.path.join(user_base_folder, pan_number)
        os.makedirs(pan_folder, exist_ok=True)

        year_folder = os.path.join(pan_folder, tax_year)
        documents_folder = os.path.join(year_folder, 'documents')
        os.makedirs(documents_folder, exist_ok=True)

        required_documents = ['pan_card', 'aadhar_card', 'form16', 'bank_statement']
        uploaded_docs = []

        for doc_type in required_documents:
            if doc_type in request.FILES:
                file = request.FILES[doc_type]
                filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(file.name)[1]}"
                file_path = os.path.join(documents_folder, filename)
                
                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                uploaded_docs.append(f"{doc_type}: {filename}")

        tax_details_path = os.path.join(year_folder, 'tax_details.txt')
        with open(tax_details_path, 'w') as file:
            file.write(f"PAN Number: {pan_number}\n")
            file.write(f"Name: {user_name}\n")
            file.write(f"Tax Year: {tax_year}\n")
            file.write(f"Income Type: {income_type}\n")
            file.write(f"Previous Filing: {previous_filing}\n")
            file.write(f"Status: Pending\n")
            file.write(f"\nSubmission Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        request.session['tax_info'] = {
            'tax_year': tax_year,
            'user_name': user_name,
            'current_folder': year_folder
        }

        messages.success(request, 'Tax information and documents saved successfully!')
        return redirect('user_home')

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
    tax_filings = []
   
    for name_folder in os.listdir(base_folder):
        name_path = os.path.join(base_folder, name_folder)
        if not os.path.isdir(name_path) or name_folder.startswith('.'):
            continue
        for tax_year in os.listdir(name_path):
            year_path = os.path.join(name_path, tax_year)
            if not os.path.isdir(year_path) or not tax_year.isdigit():
                continue
            tax_details_path = os.path.join(year_path, 'tax_details.txt')
            if os.path.exists(tax_details_path):
                filing_info = {
                    'id': f"{user_phone}_{name_folder}_{tax_year}",
                    'tax_year': tax_year,
                    'name': name_folder,
                    'client_name': name_folder if is_ca else None,
                }
                
                # Read the entire tax_details.txt file
                with open(tax_details_path, 'r') as file:
                    details = file.read()
                    
                    # Extract important fields using regex
                    name_match = re.search(r'Name: (.+)', details)
                    if name_match:
                        filing_info['name'] = name_match.group(1).strip()
                    
                    # Extract the Status field - exactly as shown in your example
                    status_match = re.search(r'Status: (.+)', details)
                    print(status_match,"llll")
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
                        print(filing_info)
                    else:
                        filing_info['filing_status'] = 'unknown'
                    
                    # Extract the Submission Date field
                    date_match = re.search(r'Submission Date: (.+)', details)
                    filing_info['filed_date'] = date_match.group(1) if date_match else 'Unknown'
                
                # Get the list of documents
                documents_folder = os.path.join(year_path, 'documents')
                filing_info['documents'] = (
                    [doc for doc in os.listdir(documents_folder) if os.path.isfile(os.path.join(documents_folder, doc))]
                    if os.path.exists(documents_folder)
                    else []
                )
                filing_info['num_documents'] = len(filing_info['documents'])
                tax_filings.append(filing_info)
    
    return tax_filings

def get_audit_trail(request):
    user_phone = request.session.get("user_phone")
    tax_file_name = request.GET.get("tax_file_name")
    tax_year = request.GET.get("tax_year")

    if not user_phone or not tax_file_name or not tax_year:
        return JsonResponse({"status": "error", "message": "Missing required fields"})

    user_folder = os.path.join(DATA_DIR, user_phone, tax_file_name, tax_year)
    message_file_path = os.path.join(user_folder, "audit_trail.txt")

    if not os.path.exists(message_file_path):
        return JsonResponse({"status": "error", "message": "Audit trail file not found"})

    with open(message_file_path, "r") as file:
        messages = file.read()
    print(messages,"ccccc")

    return JsonResponse({"status": "success", "messages": messages})

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