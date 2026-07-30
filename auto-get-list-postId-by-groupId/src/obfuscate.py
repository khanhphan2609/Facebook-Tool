import marshal
import os

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
main_py = os.path.join(SRC_DIR, 'main.py')
index_py = os.path.join(SRC_DIR, 'index.py')

with open(main_py, 'r', encoding='utf-8') as f:
    source_code = f.read()

compiled_code = compile(source_code, 'main.py', 'exec')
marshaled_code = marshal.dumps(compiled_code)

with open(index_py, 'w', encoding='utf-8') as f:
    f.write('import marshal\n')
    f.write('exec(marshal.loads({}), globals())\n'.format(repr(marshaled_code)))

print("Successfully obfuscated main.py to index.py")
