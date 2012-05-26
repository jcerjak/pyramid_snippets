from pyramid.testing import setUp, DummyRequest


def pytest_funcarg__config(request):
    config = setUp(settings={})
    config.include('pyramid_snippets')
    return config


def pytest_funcarg__request(request):
    config = request.getfuncargvalue('config')
    config.manager.get()['request'] = request = DummyRequest()
    return request
