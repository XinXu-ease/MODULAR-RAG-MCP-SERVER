import langchain
import importlib

print('version', langchain.__version__)
for mod in ['langchain.text_splitter','langchain.text_splitters']:
    try:
        importlib.import_module(mod)
        print('import',mod,'OK')
    except Exception as e:
        print('import',mod,'failed',e)
