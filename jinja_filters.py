from markupsafe import Markup
from decimal import Decimal
from datetime import datetime

def nl2br(value):
    """Convert newlines to <br> tags"""
    if value is None:
        return ""
    value = str(value)
    return Markup(value.replace('\n', '<br>'))
    
def absolute_value(value):
    """Return absolute value of a number"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0

def format_document(value):
    """Format CPF/CNPJ documents"""
    if not value:
        return ""
    
    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, str(value)))
    
    # Format as CPF (xxx.xxx.xxx-xx)
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    # Format as CNPJ (xx.xxx.xxx/xxxx-xx)
    elif len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    # Return as is
    return value

def format_currency(value):
    """Format value as currency"""
    if value is None:
        return "0,00"
    
    # Convert to decimal and ensure two decimal places
    try:
        value = Decimal(value)
        # Format with Brazilian decimal and thousands separators
        integer_part = int(value)
        decimal_part = int((value % 1) * 100)
        
        # Format integer part with thousands separator
        integer_str = ""
        count = 0
        for digit in reversed(str(integer_part)):
            if count > 0 and count % 3 == 0:
                integer_str = "." + integer_str
            integer_str = digit + integer_str
            count += 1
        
        # Final formatted value
        if integer_part == 0 and decimal_part == 0:
            return "0,00"
        
        return f"{integer_str},{decimal_part:02d}"
    except (ValueError, TypeError):
        return "0,00"

def status_color(status):
    """Return Bootstrap color class based on status"""
    status_colors = {
        'aberta': 'primary',
        'em_andamento': 'warning',
        'fechada': 'success',
        'cancelada': 'danger'
    }
    return status_colors.get(status.name if hasattr(status, 'name') else status, 'secondary')

def format_datetime(value, format='%d/%m/%Y %H:%M'):
    """Format a datetime object to a string with the specified format"""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                value = datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                return value
    try:
        return value.strftime(format)
    except (ValueError, AttributeError):
        return str(value)