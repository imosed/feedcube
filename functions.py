from re import sub


def df():
    return '%a, %d %b %Y %H:%M:%S GMT'


def get_fields_from_form(form):
    return [field for field in form][1:]


def xml_to_dict(element):
    return dict([(child.tagName, child.childNodes[0].data) for child in element.childNodes if child.nodeType == 1])


def format_description(desc, max_chars=500):
    return ' '.join(sub('<[^>]+(>|$)', '', desc)[:max_chars].split(' ')[:-1])
