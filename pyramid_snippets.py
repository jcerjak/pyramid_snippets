from pyramid.exceptions import ConfigurationError
from pyramid.i18n import TranslationStringFactory, get_localizer
from pyramid.request import Request
from pyramid.threadlocal import get_current_registry
from pyramid.view import render_view
import re
import urllib

_ = TranslationStringFactory('pyramid_snippets')


# Regexp based on Wordpress' shortcode implementation
snippet_regexp = re.compile(
    r'\['                            # Opening bracket
    r'(?P<escapeopen>\[?)'           # 1: Optional second opening bracket for escaping snippets: [[tag]]
    r'(?P<name>[\w\d\_-]+)'          # 2: Snippet name
    r'\b'                            # Word boundary
    r'(?P<arguments>'                # 3: Unroll the loop: Inside the opening snippet tag
        r'[^\]\/]*'                  # Not a closing bracket or forward slash
        r'(?:'
            r'\/(?!\])'              # A forward slash not followed by a closing bracket
            r'[^\]\/]*'              # Not a closing bracket or forward slash
        r')*?'
    r')'
    r'(?:'
        r'(?P<selfclosing>\/)'       # 4: Self closing tag ...
        r'\]'                        # ... and closing bracket
    r'|'
        r'\]'                        # Closing bracket
        r'(?:'
            r'(?P<content>'          # 5: Unroll the loop: Optionally, anything between the opening and closing snippet tags
                r'[^\[]*'            # Not an opening bracket
                r'(?:'
                    r'\[(?!\/(?P=name)\])'  # An opening bracket not followed by the closing snippet tag
                    r'[^\[]*'        # Not an opening bracket
                r')*'
            r')'
            r'\[\/(?P=name)\]'       # Closing snippet tag
        r')?'
    r')'
    r'(?P<escapeclose>\]?)')                        # 6: Optional second closing bracket for escaping snippets: [[tag]]


def register_snippet(self, name=None, title=None, view=None, schema=None):
    """Register view as a snippet.

    :param name: snippet name
    :param title: snippet title
    :param view: name of the view to register as a snippet.
    :param schema: snippet schema (optional)
    """
    if name is None or title is None or view is None:
        raise ConfigurationError(
            'You have to provide the name, title and view.')

    snippets = self.registry['pyramid.snippets']
    snippets[name] = {'title': title, 'view': view, 'schema': schema}


def get_snippets():
    return get_current_registry()['pyramid.snippets']


def render_snippet(context, request, name, arguments):
    snippet_request = Request.blank(
        request.path + name,
        base_url=request.application_url,
        POST=urllib.urlencode(arguments))
    snippet_request.registry = request.registry
    snippet = get_snippets().get(name)
    if not snippet:
        return None
    return render_view(context, snippet_request, snippet['view'])


def render_snippets(context, request, body):
    localizer = get_localizer(request)

    def sub(match):
        infos = match.groupdict()
        if infos['selfclosing'] is None and infos['content'] is None:
            return '<div class="alert alert-error">{0}</div>'.format(
                localizer.translate(
                    _("Snippet tag '${name}' not closed",
                      mapping=dict(name=infos['name']))))
        if infos['escapeopen'] and infos['escapeclose']:
            return ''.join((
                infos['escapeopen'],
                infos['name'],
                infos['arguments'],
                infos['selfclosing'],
                infos['escapeclose']))
        arguments = {}
        last_key = None
        for arg in infos['arguments'].split(' '):
            if '=' in arg:
                key, value = arg.split('=')
                key = key.strip()
                value = value.strip()
                arguments[key] = value
                last_key = key
            elif last_key is not None:
                arguments[last_key] = "%s %s" % (arguments[last_key], arg)
        arguments['body'] = infos['content']
        result = render_snippet(context, request, infos['name'], arguments)
        if result is None:
            return '<div class="alert alert-error">{0}</div>'.format(
                localizer.translate(
                    _("No snippet with name '${name}' registered.",
                      mapping=dict(name=infos['name']))))
        return result

    return snippet_regexp.sub(sub, body)


def includeme(config):
    config.registry['pyramid.snippets'] = {}
    config.add_directive('register_snippet', register_snippet)
