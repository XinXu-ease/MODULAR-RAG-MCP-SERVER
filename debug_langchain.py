import langchain, pkgutil
print('version', langchain.__version__)
print('modules:', [m.name for m in pkgutil.iter_modules(langchain.__path__)])
