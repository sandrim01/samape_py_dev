from markupsafe import Markup

def nl2br(value):
    """Convert newlines to <br> tags"""
    if value is None:
        return ""
    value = str(value)
    return Markup(value.replace('\n', '<br>'))