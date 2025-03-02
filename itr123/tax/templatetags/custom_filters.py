from django import template
import re

register = template.Library()

@register.filter
def get_file_type(filename):
    if filename.lower().endswith('.pdf'):
        return 'pdf'
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    if any(filename.lower().endswith(ext) for ext in image_extensions):
        return 'image'
    return 'other'

@register.filter
def get_document_type_display(filename):
    clean_name = re.sub(r'_\d{8}_\d{6}', '', filename.lower())
    if 'pan' in clean_name:
        return 'PAN Card'
    elif 'aadhar' in clean_name:
        return 'Aadhar Card'
    elif 'form16' in clean_name:
        return 'Form 16'
    elif 'bank' in clean_name:
        return 'Bank Statement'
    return 'Other Document'